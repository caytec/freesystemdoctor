"""
ultimate_boost.py — ONE CLICK. Every layer. Measured proof.

Chains every boost FreeSystemDoctor has into a single staged sequence:

  0. BASELINE   — measure RAM, kernel timer, DPC latency (before)
  1. SAFETY     — system restore point
  2. SYSTEM     — scheduler quantum, power throttling, MMCSS multimedia class
  3. CPU        — Ultimate Performance plan, min/max 100%, core parking off,
                  turbo AGGRESSIVE + ROCKET ramp, EPP 0, boost policy 100%,
                  0.5 ms kernel timer      (+ C-states off in EXTREME)
  4. GPU        — HAGS, PCIe link power off, windowed-game flip model,
                  Game Mode ON / DVR capture OFF   (+ NV max perf in EXTREME)
  5. RAM + SW   — kill background bloat, trim working sets, purge standby
                  list, low-latency network stack
  6. PROOF      — re-measure and report the actual gains

What no competitor has: the whole stack in one sequence, with a BEFORE/AFTER
measurement of RAM freed, kernel timer and DPC latency — and a single-click
full revert. Boosters that can't measure can't prove anything.

Honest by design: every step reports its own ok/fail; nothing is hidden in
a fake progress bar.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, Optional

_STATE_FILE = Path(os.path.expanduser("~")) / ".fsd" / "ultimate_boost.json"

ProgressCb = Optional[Callable[[str, int], None]]


# ── state ────────────────────────────────────────────────────────────────────

def _save_state(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, _STATE_FILE)
    except Exception:
        pass


def get_boost_state() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def is_boost_active() -> bool:
    return bool(get_boost_state().get("active"))


# ── measurement ──────────────────────────────────────────────────────────────

def _measure(dpc_seconds: int = 2) -> dict:
    """RAM available, kernel timer, DPC latency — the proof numbers."""
    m = {"ram_available_mb": None, "timer_ms": None, "dpc_pct": None}
    try:
        import psutil
        m["ram_available_mb"] = int(psutil.virtual_memory().available
                                    / (1024 * 1024))
    except Exception:
        pass
    try:
        from engine import cpu_optimizer
        tr = cpu_optimizer.get_timer_resolution()
        if tr.get("ok"):
            m["timer_ms"] = round(tr["current_ms"], 2)
    except Exception:
        pass
    try:
        from engine import deep_optimize
        d = deep_optimize.measure_dpc_latency(seconds=dpc_seconds)
        if d.get("ok"):
            m["dpc_pct"] = d["dpc_time_pct"]
    except Exception:
        pass
    return m


# ── the sequence ─────────────────────────────────────────────────────────────

def verify_tweaks(tweaks: list[tuple[str, str, str]] | None = None,
                  progress_cb: ProgressCb = None) -> dict:
    """Apply tweaks one at a time, measuring each — and automatically undo any
    that made the machine measurably worse.

    Every other optimizer applies changes and asserts they helped. This checks.
    Slow by nature (roughly 25-40 s per tweak) because it takes several
    baseline samples to work out this machine's own measurement noise first.

    tweaks: list of (module, tweak_id, display name). Defaults to the
    low-risk, no-reboot tweaks — the only ones whose effect a measurement
    taken seconds later can actually detect.
    """
    from engine import boost_verifier

    if tweaks is None:
        tweaks = [
            ("deep_optimize", "quantum", "Foreground CPU priority"),
            ("deep_optimize", "power_throttle", "CPU power throttling off"),
            ("cpu_optimizer", "epp", "Energy-Performance Preference → 0"),
            ("cpu_optimizer", "boost_pol", "Turbo boost policy → 100%"),
            ("gpu_boost", "pcie_aspm", "PCIe link power management off"),
        ]

    results: list[dict] = []
    for i, (module, tweak_id, name) in enumerate(tweaks):
        base = int((i / max(1, len(tweaks))) * 100)
        span = int(100 / max(1, len(tweaks)))

        def sub(msg, pct, _b=base, _s=span):
            if progress_cb:
                try:
                    progress_cb(msg, _b + int(pct * _s / 100))
                except Exception:
                    pass

        try:
            rep = boost_verifier.verify_tweak(module, tweak_id, name,
                                              samples=3, with_cpu=True,
                                              progress_cb=sub)
        except Exception as exc:
            rep = {"name": name, "verdict": "apply_failed", "reverted": False,
                   "summary": str(exc), "comparison": {}}
        rep["module"] = module
        rep["tweak_id"] = tweak_id
        results.append(rep)

    kept = sum(1 for r in results if r["verdict"] in ("improved", "no_change"))
    reverted = sum(1 for r in results if r.get("reverted"))
    return {"results": results, "kept": kept, "reverted": reverted,
            "total": len(results)}


def run_ultimate_boost(extreme: bool = False,
                       progress_cb: ProgressCb = None) -> dict:
    """Run every boost layer in order. Returns a full report:

    {steps: [{name, ok, msg}], before: {...}, after: {...},
     gains: {...}, extreme: bool}
    """
    steps: list[dict] = []
    applied: list[str] = []

    def emit(msg: str, pct: int) -> None:
        if progress_cb:
            try:
                progress_cb(msg, pct)
            except Exception:
                pass

    def step(name: str, fn, tag: str | None = None) -> bool:
        try:
            res = fn()
            ok, msg = res if isinstance(res, tuple) else (True, str(res))
        except Exception as exc:
            ok, msg = False, str(exc)
        steps.append({"name": name, "ok": bool(ok), "msg": str(msg)[:200]})
        if ok and tag:
            applied.append(tag)
        return bool(ok)

    # ── 0. baseline ─────────────────────────────────────────────────────────
    emit("Measuring baseline (RAM, timer, DPC latency)…", 2)
    before = _measure()

    # ── 1. safety ───────────────────────────────────────────────────────────
    emit("Creating system restore point…", 8)
    try:
        from engine import system_restore
        system_restore.ensure_checkpoint("Ultimate Boost")
        steps.append({"name": "System restore point", "ok": True,
                      "msg": "Checkpoint ready"})
    except Exception as exc:
        steps.append({"name": "System restore point", "ok": False,
                      "msg": str(exc)[:200]})

    # ── 2. system layer ─────────────────────────────────────────────────────
    from engine import deep_optimize as dopt
    emit("SYSTEM: foreground CPU priority (scheduler quantum)…", 14)
    step("Foreground CPU priority", dopt.apply_quantum_tuning, "quantum")
    emit("SYSTEM: disabling CPU power throttling…", 18)
    step("Power throttling OFF", dopt.apply_disable_power_throttling,
         "power_throttle")

    from engine import game_booster as gbst
    emit("SYSTEM: MMCSS multimedia scheduling for games…", 22)
    step("MMCSS game scheduling", gbst.apply_mmcss_tuning, "mmcss")

    # ── 3. CPU layer ────────────────────────────────────────────────────────
    from engine import cpu_optimizer as cpu
    emit("CPU: Ultimate Performance, parking off, turbo aggressive, EPP 0…", 30)
    try:
        changes = cpu.optimize_cpu()
        steps.append({"name": "CPU max performance",
                      "ok": True, "msg": f"{len(changes)} tweaks applied"})
        applied.append("cpu_max")
    except Exception as exc:
        steps.append({"name": "CPU max performance", "ok": False,
                      "msg": str(exc)[:200]})

    emit("CPU: 0.5 ms kernel timer…", 40)
    step("0.5 ms kernel timer", lambda: cpu.apply_deep_tweak("timer_res"),
         "timer_res")

    if extreme:
        emit("CPU EXTREME: disabling idle states (C-states)…", 45)
        step("C-states OFF (extreme)",
             lambda: cpu.apply_deep_tweak("idle_disable"), "idle_disable")

    # ── 4. GPU layer ────────────────────────────────────────────────────────
    from engine import gpu_boost as gpu
    emit("GPU: hardware-accelerated scheduling (HAGS)…", 52)
    step("GPU hardware scheduling", lambda: gpu.apply_tweak("hags"), "hags")
    emit("GPU: PCIe link power management off…", 58)
    step("PCIe link full speed", lambda: gpu.apply_tweak("pcie_aspm"),
         "pcie_aspm")
    emit("GPU: low-latency flip model for windowed games…", 62)
    step("Windowed-game flip model",
         lambda: gpu.apply_tweak("windowed_optim"), "windowed_optim")
    emit("GPU: Game Mode ON, background recording OFF…", 66)
    step("Game Mode / DVR capture",
         lambda: gpu.apply_tweak("game_capture"), "game_capture")

    if extreme:
        try:
            if gpu.get_nv_max_perf_status() is not None:
                emit("GPU EXTREME: NVIDIA maximum performance state…", 70)
                step("NVIDIA max perf (extreme)",
                     lambda: gpu.apply_tweak("nv_max_perf"), "nv_max_perf")
        except Exception:
            pass

    # ── 5. RAM + software layer ─────────────────────────────────────────────
    emit("RAM: closing background bloat…", 76)
    try:
        killed, names = gbst.kill_background_bloat()
        steps.append({"name": "Background bloat closed", "ok": True,
                      "msg": (f"{killed} app(s): " + ", ".join(names[:6]))
                      if killed else "Nothing to close"})
        if killed:
            applied.append("bloat")
    except Exception as exc:
        steps.append({"name": "Background bloat closed", "ok": False,
                      "msg": str(exc)[:200]})

    emit("RAM: deep clean (working sets, modified, standby, file cache)…", 82)
    try:
        from engine import ram_master
        rep = ram_master.deep_clean(level="deep")
        for s in rep["stages"]:
            steps.append({"name": s["label"], "ok": s["ok"],
                          "msg": (f"freed {s['freed_mb']} MB"
                                  if s["ok"] else s["msg"])[:200]})
        applied.append("ram_deep")
    except Exception as exc:
        steps.append({"name": "RAM deep clean", "ok": False,
                      "msg": str(exc)[:200]})

    emit("NETWORK: low-latency stack (no Nagle, no throttling)…", 90)
    step("Low-latency network", gbst.apply_low_latency_network, "network")

    # ── 6. proof ────────────────────────────────────────────────────────────
    emit("Measuring result (RAM, timer, DPC latency)…", 94)
    after = _measure()

    gains: dict = {}
    if before.get("ram_available_mb") is not None \
            and after.get("ram_available_mb") is not None:
        gains["ram_freed_mb"] = after["ram_available_mb"] \
            - before["ram_available_mb"]
    if before.get("timer_ms") is not None \
            and after.get("timer_ms") is not None:
        gains["timer_before_ms"] = before["timer_ms"]
        gains["timer_after_ms"] = after["timer_ms"]
    if before.get("dpc_pct") is not None and after.get("dpc_pct") is not None:
        gains["dpc_before_pct"] = before["dpc_pct"]
        gains["dpc_after_pct"] = after["dpc_pct"]

    ok_count = sum(1 for s in steps if s["ok"])
    _save_state({"active": True, "extreme": extreme,
                 "applied": applied,
                 "applied_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "steps_ok": ok_count, "steps_total": len(steps)})

    emit(f"Done — {ok_count}/{len(steps)} steps applied.", 100)
    return {"steps": steps, "before": before, "after": after,
            "gains": gains, "extreme": extreme,
            "ok_count": ok_count, "total": len(steps)}


# ── full revert ──────────────────────────────────────────────────────────────

def revert_ultimate_boost(progress_cb: ProgressCb = None) -> dict:
    """Undo every layer the boost applied, in reverse order."""
    steps: list[dict] = []
    state = get_boost_state()
    applied = set(state.get("applied") or [])

    def emit(msg: str, pct: int) -> None:
        if progress_cb:
            try:
                progress_cb(msg, pct)
            except Exception:
                pass

    def step(name: str, fn) -> None:
        try:
            res = fn()
            ok, msg = res if isinstance(res, tuple) else (True, str(res))
        except Exception as exc:
            ok, msg = False, str(exc)
        steps.append({"name": name, "ok": bool(ok), "msg": str(msg)[:200]})

    from engine import game_booster as gbst
    from engine import gpu_boost as gpu
    from engine import cpu_optimizer as cpu
    from engine import deep_optimize as dopt

    emit("Reverting network stack…", 10)
    if "network" in applied or not applied:
        try:
            gbst.revert_all()
            steps.append({"name": "Game booster layer",
                          "ok": True, "msg": "Network/MMCSS/timer reverted"})
        except Exception as exc:
            steps.append({"name": "Game booster layer", "ok": False,
                          "msg": str(exc)[:200]})

    emit("Reverting GPU layer…", 35)
    for tag, name in (("nv_max_perf", "NVIDIA max perf"),
                      ("game_capture", "Game Mode / DVR"),
                      ("windowed_optim", "Windowed flip model"),
                      ("pcie_aspm", "PCIe link power"),
                      ("hags", "GPU hardware scheduling")):
        if tag in applied or not applied:
            step(name, lambda t=tag: gpu.revert_tweak(t))

    emit("Reverting CPU layer…", 65)
    if "idle_disable" in applied:
        step("C-states restored",
             lambda: cpu.revert_deep_tweak("idle_disable"))
    if "timer_res" in applied or not applied:
        step("Kernel timer released",
             lambda: cpu.revert_deep_tweak("timer_res"))
    if "cpu_max" in applied or not applied:
        try:
            changes = cpu.restore_defaults()
            steps.append({"name": "CPU defaults restored", "ok": True,
                          "msg": f"{len(changes)} steps"})
        except Exception as exc:
            steps.append({"name": "CPU defaults restored", "ok": False,
                          "msg": str(exc)[:200]})

    emit("Reverting system layer…", 85)
    if "mmcss" in applied or not applied:
        step("MMCSS restored",
             lambda: (True, f"{gbst.revert_mmcss_and_gpu()} value(s) restored"))
    if "power_throttle" in applied or not applied:
        step("Power throttling restored", dopt.revert_power_throttling)
    if "quantum" in applied or not applied:
        step("Scheduler quantum restored", dopt.revert_quantum_tuning)

    _save_state({"active": False, "applied": [],
                 "reverted_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    ok_count = sum(1 for s in steps if s["ok"])
    emit(f"Revert complete — {ok_count}/{len(steps)} layers restored.", 100)
    return {"steps": steps, "ok_count": ok_count, "total": len(steps)}
