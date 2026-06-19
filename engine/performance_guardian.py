"""
Performance Guardian — always-on background monitor that keeps the system
performing well *while you work*.

Unlike ``idle_maintenance`` (which runs cleaners only when the PC is idle), the
Guardian samples the system continuously and reacts the moment a sustained
threshold is crossed:

    • RAM above threshold for a sustained window  → trim working sets
    • CPU sustained high                          → flag the top offending process
    • Free disk space below threshold             → alert
    • High package temperature (if readable)      → alert

Monitoring is read-only and cheap (psutil). Auto-remediation is **opt-in** and
rate-limited by a cooldown so it never thrashes. State/history live in memory;
configuration persists via ``engine.app_settings`` under the ``guardian`` key.

Public API
----------
    start() / stop() / is_running()
    get_config() / set_config(dict)
    get_status() -> dict          # latest sample + rolling averages + flags
    get_events(n) -> list[dict]   # recent guardian actions/alerts
    subscribe(cb) / unsubscribe(cb)
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Optional

try:
    import psutil
    _PSUTIL = True
except Exception:
    _PSUTIL = False

from engine import app_settings

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "enabled":          True,    # run the monitor (read-only) on launch
    "auto_actions":     False,   # take corrective action automatically (opt-in)
    "notify":           True,    # surface alerts via callbacks (GUI toast)
    "sample_interval":  5,       # seconds between samples
    "ram_threshold":    88,      # % used that counts as pressure
    "ram_sustained":    20,      # seconds of sustained pressure before acting
    "cpu_threshold":    90,      # % used that counts as pressure
    "cpu_sustained":    30,      # seconds before flagging a CPU offender
    "disk_min_free_gb": 5,       # GB free below which we alert
    "cooldown":         300,     # min seconds between auto-actions
}

_SAMPLES_MAX = 720               # ~1h at 5s
_EVENTS_MAX  = 100

_lock = threading.RLock()
_thread: Optional[threading.Thread] = None
_stop = threading.Event()
_samples: deque = deque(maxlen=_SAMPLES_MAX)
_events: deque = deque(maxlen=_EVENTS_MAX)
_subscribers: list[Callable[[dict], None]] = []
_last_action_ts = 0.0
_ram_pressure_since: Optional[float] = None
_cpu_pressure_since: Optional[float] = None


# ── config ────────────────────────────────────────────────────────────────────
def get_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        saved = app_settings.get("guardian", {})
        if isinstance(saved, dict):
            cfg.update({k: saved[k] for k in saved if k in DEFAULT_CONFIG})
    except Exception:
        pass
    return cfg


def set_config(updates: dict) -> dict:
    cfg = get_config()
    for k, v in (updates or {}).items():
        if k in DEFAULT_CONFIG:
            cfg[k] = v
    try:
        app_settings.set_and_save("guardian", cfg)
    except Exception:
        pass
    return cfg


# ── events / subscribers ──────────────────────────────────────────────────────
def _emit(kind: str, message: str, detail: dict | None = None):
    evt = {"ts": time.time(), "kind": kind, "message": message,
           "detail": detail or {}}
    with _lock:
        _events.append(evt)
        subs = list(_subscribers)
    for cb in subs:
        try:
            cb(evt)
        except Exception:
            pass


def subscribe(cb: Callable[[dict], None]):
    with _lock:
        if cb not in _subscribers:
            _subscribers.append(cb)


def unsubscribe(cb: Callable[[dict], None]):
    with _lock:
        if cb in _subscribers:
            _subscribers.remove(cb)


def get_events(n: int = 50) -> list[dict]:
    with _lock:
        return list(_events)[-n:][::-1]


# ── sampling ──────────────────────────────────────────────────────────────────
def _read_temp() -> Optional[float]:
    """Best-effort CPU package temperature (°C). Often unavailable on Windows."""
    if not _PSUTIL or not hasattr(psutil, "sensors_temperatures"):
        return None
    try:
        temps = psutil.sensors_temperatures()
        for _name, entries in (temps or {}).items():
            for e in entries:
                if e.current and e.current > 0:
                    return float(e.current)
    except Exception:
        pass
    return None


def _sample() -> dict:
    s = {"ts": time.time(), "cpu": 0.0, "ram": 0.0,
         "disk_free_gb": 0.0, "temp": None}
    if not _PSUTIL:
        return s
    try:
        s["cpu"] = psutil.cpu_percent(interval=None)
        s["ram"] = psutil.virtual_memory().percent
        du = psutil.disk_usage("C:\\" if _is_windows() else "/")
        s["disk_free_gb"] = du.free / (1024 ** 3)
        s["temp"] = _read_temp()
    except Exception:
        pass
    return s


def _is_windows() -> bool:
    import sys
    return sys.platform == "win32"


def _top_cpu_process() -> Optional[dict]:
    if not _PSUTIL:
        return None
    try:
        best = None
        for p in psutil.process_iter(["name", "cpu_percent"]):
            cpu = p.info.get("cpu_percent") or 0
            if best is None or cpu > best[1]:
                best = (p.info.get("name") or "?", cpu, p.pid)
        if best:
            return {"name": best[0], "cpu": best[1], "pid": best[2]}
    except Exception:
        pass
    return None


# ── status ────────────────────────────────────────────────────────────────────
def get_status() -> dict:
    with _lock:
        samples = list(_samples)
    if not samples:
        return {"running": is_running(), "latest": None,
                "avg_cpu": 0.0, "avg_ram": 0.0, "samples": 0}
    latest = samples[-1]
    recent = samples[-12:]  # ~1 min at 5s
    avg_cpu = sum(x["cpu"] for x in recent) / len(recent)
    avg_ram = sum(x["ram"] for x in recent) / len(recent)
    return {
        "running":  is_running(),
        "latest":   latest,
        "avg_cpu":  round(avg_cpu, 1),
        "avg_ram":  round(avg_ram, 1),
        "samples":  len(samples),
    }


def get_series(metric: str, n: int = 120) -> list[float]:
    with _lock:
        return [x.get(metric, 0.0) or 0.0 for x in list(_samples)[-n:]]


# ── remediation ───────────────────────────────────────────────────────────────
def _trim_ram() -> str:
    try:
        from engine import memory_optimizer
        trimmed, _errs = memory_optimizer.trim_working_sets()
        return f"Trimmed {trimmed} process working sets"
    except Exception as e:
        return f"RAM trim failed: {e}"


def _evaluate(cfg: dict, sample: dict):
    """Apply threshold rules to the latest sample; alert / act as configured."""
    global _last_action_ts, _ram_pressure_since, _cpu_pressure_since
    now = sample["ts"]

    # ── RAM pressure ──
    if sample["ram"] >= cfg["ram_threshold"]:
        if _ram_pressure_since is None:
            _ram_pressure_since = now
        sustained = now - _ram_pressure_since
        if sustained >= cfg["ram_sustained"]:
            if cfg["auto_actions"] and (now - _last_action_ts) >= cfg["cooldown"]:
                msg = _trim_ram()
                _last_action_ts = now
                _ram_pressure_since = None
                _emit("action", f"High RAM ({sample['ram']:.0f}%) — {msg}",
                      {"ram": sample["ram"]})
            elif cfg["notify"]:
                _emit("alert", f"RAM under pressure: {sample['ram']:.0f}% used",
                      {"ram": sample["ram"]})
                _ram_pressure_since = now  # re-arm so we don't spam every sample
    else:
        _ram_pressure_since = None

    # ── CPU pressure ──
    if sample["cpu"] >= cfg["cpu_threshold"]:
        if _cpu_pressure_since is None:
            _cpu_pressure_since = now
        if (now - _cpu_pressure_since) >= cfg["cpu_sustained"] and cfg["notify"]:
            top = _top_cpu_process()
            who = f" — top: {top['name']} ({top['cpu']:.0f}%)" if top else ""
            _emit("alert", f"Sustained high CPU: {sample['cpu']:.0f}%{who}",
                  {"cpu": sample["cpu"], "top": top})
            _cpu_pressure_since = now  # re-arm
    else:
        _cpu_pressure_since = None

    # ── Disk space ──
    if sample["disk_free_gb"] and sample["disk_free_gb"] < cfg["disk_min_free_gb"]:
        if cfg["notify"]:
            _emit("alert",
                  f"Low disk space: {sample['disk_free_gb']:.1f} GB free",
                  {"disk_free_gb": sample["disk_free_gb"]})

    # ── Temperature ──
    if sample.get("temp") and sample["temp"] >= 90 and cfg["notify"]:
        _emit("alert", f"High CPU temperature: {sample['temp']:.0f}°C",
              {"temp": sample["temp"]})


# ── loop ──────────────────────────────────────────────────────────────────────
def _loop():
    # Prime cpu_percent so the first real reading isn't 0.
    if _PSUTIL:
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass
    while not _stop.is_set():
        cfg = get_config()
        if not cfg.get("enabled", True):
            _stop.wait(2)
            continue
        sample = _sample()
        with _lock:
            _samples.append(sample)
        try:
            _evaluate(cfg, sample)
        except Exception:
            pass
        _stop.wait(max(1, int(cfg.get("sample_interval", 5))))


def start() -> bool:
    """Start the guardian thread (no-op if already running or disabled)."""
    global _thread
    cfg = get_config()
    if not cfg.get("enabled", True):
        return False
    with _lock:
        if _thread and _thread.is_alive():
            return True
        _stop.clear()
        _thread = threading.Thread(target=_loop, daemon=True,
                                   name="PerfGuardian")
        _thread.start()
    _emit("info", "Performance Guardian started")
    return True


def stop():
    _stop.set()
    _emit("info", "Performance Guardian stopped")


def is_running() -> bool:
    return _thread is not None and _thread.is_alive() and not _stop.is_set()
