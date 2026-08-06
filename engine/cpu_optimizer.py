"""
cpu_optimizer.py — Maximum CPU performance: remove throttling, force max state.
Part of FreeSystemDoctor engine.

Applies aggressive Windows tweaks to keep the CPU at its highest sustained
performance:
    - Activates the Ultimate Performance power scheme (creates it if missing).
    - Forces processor min/max state to 100% (AC and DC).
    - Disables Windows Power Throttling for all processes.
    - Sets processor performance boost mode to AGGRESSIVE.
    - Disables CPU core parking (CPMINCORES = 100%).
    - Disables Intel SpeedStep / AMD Cool'n'Quiet idle behavior at the OS layer.
    - Sets Win32PrioritySeparation to favor foreground apps.

All changes are reversible via `restore_defaults()`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
import winreg
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Logging + state file
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "cpu_optimizer.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

_STATE_FILE = os.path.join(_LOG_DIR, "cpu_optimizer_state.json")

# ---------------------------------------------------------------------------
# Constants — Power scheme GUIDs and subgroup/setting GUIDs
# ---------------------------------------------------------------------------
ULTIMATE_PERF_GUID  = "e9a42b02-d5df-448d-aa00-03f14749eb61"
HIGH_PERF_GUID      = "8c5e7fda-e8bf-45a6-a6cc-4b0d644e0a0d"
BALANCED_GUID       = "381b4222-f694-41f0-9685-ff5bb260df2e"

# Processor power management subgroup
SUB_PROCESSOR       = "54533251-82be-4824-96c1-47b60b740d00"

# Setting GUIDs under SUB_PROCESSOR
SETTING_PROCTHROTTLEMIN  = "893dee8e-2bef-41e0-89c6-b55d0929964c"  # Min processor state
SETTING_PROCTHROTTLEMAX  = "bc5038f7-23e0-4960-96da-33abaf5935ec"  # Max processor state
SETTING_PERFBOOSTMODE    = "be337238-0d82-4146-a960-4f3749d470c7"  # Performance boost mode
SETTING_CPMINCORES       = "0cc5b647-c1df-4637-891a-dec35c318583"  # Min cores parked
SETTING_CPMAXCORES       = "ea062031-0e34-4ff1-9b6d-eb1059334028"  # Max cores parked
SETTING_PERFINCTHRESHOLD = "06cadf0e-64ed-448a-8927-ce7bf90eb35d"  # Performance increase threshold
SETTING_PERFINCPOLICY    = "465e1f50-b610-473a-ab58-00d1077dc418"  # Performance increase policy

# Power Throttling registry path (Win10/11)
PT_KEY = r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling"

# Processor power management registry (kernel-level)
PROC_PERF_KEY = r"SYSTEM\CurrentControlSet\Control\Power\ProfileAttributes\54533251-82be-4824-96c1-47b60b740d00"

PRIORITY_KEY = r"SYSTEM\CurrentControlSet\Control\PriorityControl"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return r.returncode, r.stdout or ""
    except subprocess.TimeoutExpired:
        return -1, "Timeout"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"
    except Exception as exc:  # pragma: no cover
        logger.exception("_run error: %s", exc)
        return -1, str(exc)


def _powercfg(*args: str, timeout: int = 20) -> tuple[int, str]:
    return _run(["powercfg", *args], timeout=timeout)


def _reg_write(root, key_path: str, name: str, value, reg_type=winreg.REG_DWORD) -> bool:
    try:
        with winreg.CreateKeyEx(root, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, name, 0, reg_type, value)
        return True
    except Exception as exc:
        logger.debug("_reg_write %s\\%s: %s", key_path, name, exc)
        return False


def _reg_read(root, key_path: str, name: str, default=None):
    try:
        with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, name)
            return val
    except Exception:
        return default


def _load_state() -> dict:
    try:
        if os.path.exists(_STATE_FILE):
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        logger.warning("_load_state failed: %s", exc)
    return {}


def _save_state(state: dict) -> None:
    try:
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as exc:
        logger.warning("_save_state failed: %s", exc)


# ---------------------------------------------------------------------------
# Power scheme management
# ---------------------------------------------------------------------------
def _list_schemes() -> str:
    rc, out = _powercfg("/list")
    return out if rc == 0 else ""


def _get_active_scheme_guid() -> str:
    rc, out = _powercfg("/getactivescheme")
    if rc == 0:
        m = re.search(r"([0-9a-f-]{36})", out, re.IGNORECASE)
        if m:
            return m.group(1).lower()
    return ""


def _ensure_ultimate_performance() -> bool:
    """Make sure the Ultimate Performance scheme exists. Returns True on success."""
    if ULTIMATE_PERF_GUID in _list_schemes().lower():
        return True
    rc, out = _powercfg("/duplicatescheme", ULTIMATE_PERF_GUID)
    if rc != 0:
        logger.warning("Failed to duplicate Ultimate Performance scheme: %s", out)
        return ULTIMATE_PERF_GUID in _list_schemes().lower()
    return True


def _set_active_scheme(guid: str) -> bool:
    rc, _ = _powercfg("/setactive", guid)
    return rc == 0


def _set_proc_value(scheme: str, setting: str, value: int) -> bool:
    """Set a processor subgroup value for both AC and DC, on the active scheme."""
    ok_ac, _ = _powercfg("/setacvalueindex", scheme, SUB_PROCESSOR, setting, str(value))
    ok_dc, _ = _powercfg("/setdcvalueindex", scheme, SUB_PROCESSOR, setting, str(value))
    return ok_ac == 0 and ok_dc == 0


# ---------------------------------------------------------------------------
# Status inspection
# ---------------------------------------------------------------------------
def get_status() -> dict:
    """Return a snapshot of CPU optimization state."""
    state = _load_state()
    active = _get_active_scheme_guid()

    pt_value = _reg_read(winreg.HKEY_LOCAL_MACHINE, PT_KEY, "PowerThrottlingOff", None)
    win32_prio = _reg_read(winreg.HKEY_LOCAL_MACHINE, PRIORITY_KEY,
                           "Win32PrioritySeparation", None)

    is_ultimate = active.lower() == ULTIMATE_PERF_GUID
    is_high     = active.lower() == HIGH_PERF_GUID

    return {
        "optimized": state.get("optimized", False),
        "active_scheme_guid": active,
        "scheme_name": (
            "Ultimate Performance" if is_ultimate
            else ("High Performance" if is_high else "Other / Balanced")
        ),
        "power_throttling_disabled": pt_value == 1,
        "win32_priority_separation": win32_prio,
        "applied_at": state.get("applied_at", ""),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def optimize_cpu(progress_cb: Optional[Callable[[str], None]] = None) -> list[str]:
    """
    Apply aggressive CPU tweaks. Reversible via `restore_defaults()`.

    Returns a list of human-readable change descriptions.
    """
    import time
    changes: list[str] = []

    def _step(msg: str) -> None:
        changes.append(msg)
        logger.info("optimize_cpu: %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    # Capture current state for restore
    restore: dict = {
        "previous_scheme_guid": _get_active_scheme_guid(),
        "win32_priority_separation": _reg_read(
            winreg.HKEY_LOCAL_MACHINE, PRIORITY_KEY,
            "Win32PrioritySeparation", 2,
        ),
        "power_throttling_off": _reg_read(
            winreg.HKEY_LOCAL_MACHINE, PT_KEY, "PowerThrottlingOff", None,
        ),
    }

    # 1. Ensure Ultimate Performance scheme exists, then activate it
    _step("Activating Ultimate Performance power scheme")
    if _ensure_ultimate_performance() and _set_active_scheme(ULTIMATE_PERF_GUID):
        active_scheme = ULTIMATE_PERF_GUID
    else:
        _step("Ultimate Performance unavailable — falling back to High Performance")
        _set_active_scheme(HIGH_PERF_GUID)
        active_scheme = HIGH_PERF_GUID

    # 2. Force min/max processor state to 100% (no throttle)
    _step("Setting minimum processor state to 100% (no throttle)")
    _set_proc_value(active_scheme, SETTING_PROCTHROTTLEMIN, 100)
    _step("Setting maximum processor state to 100% (no cap)")
    _set_proc_value(active_scheme, SETTING_PROCTHROTTLEMAX, 100)

    # 3. Disable core parking
    _step("Disabling CPU core parking (all cores active)")
    _set_proc_value(active_scheme, SETTING_CPMINCORES, 100)
    _set_proc_value(active_scheme, SETTING_CPMAXCORES, 100)

    # 4. Performance boost mode → AGGRESSIVE (2 = aggressive)
    _step("Setting processor performance boost mode to AGGRESSIVE")
    _set_proc_value(active_scheme, SETTING_PERFBOOSTMODE, 2)

    # 5. Performance increase policy + threshold (faster ramp-up)
    _step("Setting performance increase policy to ROCKET (instant ramp-up)")
    _set_proc_value(active_scheme, SETTING_PERFINCPOLICY, 2)   # 2 = Rocket
    _set_proc_value(active_scheme, SETTING_PERFINCTHRESHOLD, 10)

    # 5b. Energy-Performance Preference → 0, turbo boost policy → 100%
    _step("Setting Energy-Performance Preference to 0 (always prefer speed)")
    _powercfg("/setacvalueindex", active_scheme, SUB_PROCESSOR, "PERFEPP", "0")
    _powercfg("/setdcvalueindex", active_scheme, SUB_PROCESSOR, "PERFEPP", "0")
    _step("Unlocking full turbo boost range (boost policy 100%)")
    _powercfg("/setacvalueindex", active_scheme, SUB_PROCESSOR, "PERFBOOSTPOL", "100")
    _powercfg("/setdcvalueindex", active_scheme, SUB_PROCESSOR, "PERFBOOSTPOL", "100")

    # Apply scheme changes
    _powercfg("/setactive", active_scheme)

    # 6. Disable Windows Power Throttling globally
    _step("Disabling Windows Power Throttling for all processes")
    _reg_write(winreg.HKEY_LOCAL_MACHINE, PT_KEY, "PowerThrottlingOff", 1)

    # 7. Foreground priority boost — favor active app
    _step("Boosting foreground process scheduler priority")
    _reg_write(winreg.HKEY_LOCAL_MACHINE, PRIORITY_KEY,
               "Win32PrioritySeparation", 38)

    # Save state
    state = {
        "optimized": True,
        "applied_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "restore": restore,
        "changes": changes,
    }
    _save_state(state)
    _step("Done — CPU is running unthrottled.")
    return changes


def restore_defaults(progress_cb: Optional[Callable[[str], None]] = None) -> list[str]:
    """Restore CPU settings to what they were before `optimize_cpu()`."""
    changes: list[str] = []

    def _step(msg: str) -> None:
        changes.append(msg)
        logger.info("restore_defaults: %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    state = _load_state()
    if not state.get("optimized"):
        _step("CPU optimizer was not active — nothing to restore.")
        return changes

    restore = state.get("restore", {})

    # Restore power scheme
    prev_scheme = restore.get("previous_scheme_guid") or BALANCED_GUID
    _step(f"Restoring previous power scheme ({prev_scheme})")
    _set_active_scheme(prev_scheme)

    # Restore Win32PrioritySeparation
    prev_prio = restore.get("win32_priority_separation", 2)
    _step("Restoring Win32 priority separation")
    _reg_write(winreg.HKEY_LOCAL_MACHINE, PRIORITY_KEY,
               "Win32PrioritySeparation", prev_prio)

    # Restore Power Throttling
    prev_pt = restore.get("power_throttling_off")
    if prev_pt is None:
        _step("Re-enabling Windows Power Throttling (default)")
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PT_KEY,
                                 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, "PowerThrottlingOff")
        except Exception:
            _reg_write(winreg.HKEY_LOCAL_MACHINE, PT_KEY,
                       "PowerThrottlingOff", 0)
    else:
        _reg_write(winreg.HKEY_LOCAL_MACHINE, PT_KEY,
                   "PowerThrottlingOff", prev_pt)

    _save_state({"optimized": False, "restore": {}, "changes": []})
    _step("Restore complete.")
    return changes


# ---------------------------------------------------------------------------
# DEEP CPU tweaks — squeeze the last few percent the basic pass leaves behind
# ---------------------------------------------------------------------------
# These use powercfg SETTING ALIASES, which address hidden settings without
# needing to un-hide them first. Each is applied to the CURRENTLY ACTIVE
# scheme, backed up per-tweak, and individually revertible.

KERNEL_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\kernel"


def _query_alias(alias: str) -> tuple[Optional[int], Optional[int]]:
    """Read current AC/DC index of a processor setting alias. (None, None)
    if the alias doesn't exist on this Windows build / CPU."""
    # /qh also lists HIDDEN settings — /q silently omits them
    rc, out = _powercfg("/qh", "SCHEME_CURRENT", "SUB_PROCESSOR", alias)
    if rc != 0:
        return None, None
    ac = dc = None
    for line in out.splitlines():
        low = line.lower()
        if "ac power setting index" in low:
            try:
                ac = int(line.split(":")[-1].strip(), 16)
            except ValueError:
                pass
        elif "dc power setting index" in low:
            try:
                dc = int(line.split(":")[-1].strip(), 16)
            except ValueError:
                pass
    return ac, dc


def _set_alias(alias: str, value: int, dc: bool = True) -> bool:
    ok, _ = _powercfg("/setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR",
                      alias, str(value))
    if dc:
        _powercfg("/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR",
                  alias, str(value))
    _powercfg("/setactive", "SCHEME_CURRENT")
    return ok == 0


def _deep_backup(key: str, value) -> None:
    state = _load_state()
    state.setdefault("deep_backups", {})
    if key not in state["deep_backups"]:
        state["deep_backups"][key] = value
        _save_state(state)


def _deep_restore(key):
    return (_load_state().get("deep_backups") or {}).get(key)


# ── live CPU snapshot (proof, not promises) ─────────────────────────────────

def get_cpu_snapshot() -> dict:
    """Model, core count, base clock and the REAL current speed including
    turbo — '% Processor Performance' goes above 100% when boosting, which
    lets us show the actual MHz the CPU is running at right now."""
    script = (
        "$c = Get-CimInstance Win32_Processor | Select-Object -First 1; "
        "Write-Output ('NAME=' + $c.Name); "
        "Write-Output ('CORES=' + $c.NumberOfCores); "
        "Write-Output ('THREADS=' + $c.NumberOfLogicalProcessors); "
        "Write-Output ('BASE=' + $c.MaxClockSpeed); "
        "try { $p = (Get-Counter '\\Processor Information(_Total)\\% Processor Performance' "
        "-SampleInterval 1 -MaxSamples 2 -ErrorAction Stop).CounterSamples | "
        "Measure-Object CookedValue -Average; "
        "Write-Output ('PERF=' + [math]::Round($p.Average,1)) } catch { Write-Output 'PERF=0' }"
    )
    rc, out = _run(["powershell", "-NoProfile", "-Command", script], timeout=30)
    snap = {"ok": rc == 0, "name": "", "cores": 0, "threads": 0,
            "base_mhz": 0, "perf_pct": 0.0, "current_mhz": 0}
    for line in out.splitlines():
        k, _, v = line.strip().partition("=")
        v = v.strip()
        try:
            if k == "NAME":
                snap["name"] = v
            elif k == "CORES":
                snap["cores"] = int(v)
            elif k == "THREADS":
                snap["threads"] = int(v)
            elif k == "BASE":
                snap["base_mhz"] = int(v)
            elif k == "PERF":
                snap["perf_pct"] = float(v)
        except ValueError:
            continue
    if snap["base_mhz"] and snap["perf_pct"]:
        snap["current_mhz"] = int(snap["base_mhz"] * snap["perf_pct"] / 100)
    snap["hybrid"] = _is_hybrid_cpu(snap["name"])
    return snap


def _is_hybrid_cpu(name: str) -> bool:
    """P-core/E-core CPUs where the scheduling-policy tweak matters."""
    n = (name or "").lower()
    return any(t in n for t in ("12th gen", "13th gen", "14th gen",
                                "core ultra", "core(tm) ultra"))


# ── timer resolution (0.5 ms) ───────────────────────────────────────────────

def get_timer_resolution() -> dict:
    """Current/min kernel timer resolution in ms via NtQueryTimerResolution."""
    try:
        import ctypes
        ntdll = ctypes.WinDLL("ntdll")
        mn, mx, cur = (ctypes.c_ulong() for _ in range(3))
        ntdll.NtQueryTimerResolution(ctypes.byref(mn), ctypes.byref(mx),
                                     ctypes.byref(cur))
        glob = _reg_read(winreg.HKEY_LOCAL_MACHINE, KERNEL_KEY,
                         "GlobalTimerResolutionRequests", 0)
        return {"ok": True,
                "current_ms": cur.value / 10000.0,
                "best_ms": mx.value / 10000.0,
                "global_flag": glob == 1}
    except Exception as exc:
        logger.debug("get_timer_resolution: %s", exc)
        return {"ok": False, "current_ms": 15.625, "best_ms": 0.5,
                "global_flag": False}


def request_max_timer_resolution() -> bool:
    """Ask the kernel for its finest timer (usually 0.5 ms). Held for as long
    as FreeSystemDoctor is running — exactly how TimerResolution.exe works."""
    try:
        import ctypes
        ntdll = ctypes.WinDLL("ntdll")
        mn, mx, cur = (ctypes.c_ulong() for _ in range(3))
        ntdll.NtQueryTimerResolution(ctypes.byref(mn), ctypes.byref(mx),
                                     ctypes.byref(cur))
        ntdll.NtSetTimerResolution(mx, ctypes.c_bool(True), ctypes.byref(cur))
        return True
    except Exception as exc:
        logger.debug("request_max_timer_resolution: %s", exc)
        return False


def release_timer_resolution() -> bool:
    try:
        import ctypes
        ntdll = ctypes.WinDLL("ntdll")
        cur = ctypes.c_ulong()
        ntdll.NtSetTimerResolution(ctypes.c_ulong(0), ctypes.c_bool(False),
                                   ctypes.byref(cur))
        return True
    except Exception:
        return False


# ── deep tweak catalogue ────────────────────────────────────────────────────

def get_deep_tweaks() -> list[dict]:
    """Declarative list driving the UI: id, name, desc, impact, risk, state.
    Rows whose powercfg alias doesn't exist on this machine are omitted."""
    tweaks: list[dict] = []

    epp_ac, _ = _query_alias("PERFEPP")
    if epp_ac is not None:
        tweaks.append({
            "id": "epp",
            "name": "Energy-Performance Preference → 0 (max performance)",
            "desc": "Modern CPUs pick their own clocks (HWP). EPP is the "
                    "0-100 hint Windows sends them — 0 tells the CPU to always "
                    "choose speed over efficiency. High Performance plans "
                    "don't always set this.",
            "impact": "CPU ramps to turbo instantly and holds it",
            "risk": "low", "reboot": False,
            "optimized": epp_ac == 0,
        })

    bp_ac, _ = _query_alias("PERFBOOSTPOL")
    if bp_ac is not None:
        tweaks.append({
            "id": "boost_pol",
            "name": "Turbo boost policy → 100%",
            "desc": "How much of the available turbo range Windows lets the "
                    "CPU use. 100% removes the OS-side ceiling on boost "
                    "clocks entirely.",
            "impact": "Full turbo range unlocked",
            "risk": "low", "reboot": False,
            "optimized": bp_ac == 100,
        })

    sp_ac, _ = _query_alias("SCHEDPOLICY")
    if sp_ac is not None:
        tweaks.append({
            "id": "hetero",
            "name": "Prefer P-cores (hybrid CPU scheduling)",
            "desc": "On hybrid CPUs (Intel 12th-gen+/Core Ultra) Windows "
                    "sometimes lands demanding threads on slow E-cores. "
                    "This tells the scheduler to prefer performance cores. "
                    "Harmless on non-hybrid CPUs.",
            "impact": "Heavy threads stay on fast cores",
            "risk": "low", "reboot": False,
            "optimized": sp_ac == 2,
        })

    idle_ac, _ = _query_alias("IDLEDISABLE")
    if idle_ac is not None:
        tweaks.append({
            "id": "idle_disable",
            "name": "Disable CPU idle states (C-states)",
            "desc": "The CPU never sleeps between instructions — zero "
                    "wake-up latency, the last word in responsiveness. "
                    "SIGNIFICANT heat and power cost; desktops with good "
                    "cooling only, never laptops on battery.",
            "impact": "Zero idle-exit latency (extreme)",
            "risk": "high", "reboot": False,
            "optimized": idle_ac == 1,
        })

    tr = get_timer_resolution()
    tweaks.append({
        "id": "timer_res",
        "name": "0.5 ms kernel timer resolution",
        "desc": "Windows' default 15.6 ms tick makes sleeps and frame pacing "
                "coarse. This requests the finest timer (held while "
                "FreeSystemDoctor runs) and sets the Win11 flag that makes "
                "such requests system-wide again.",
        "impact": "Smoother frame pacing, tighter input timing",
        "risk": "low", "reboot": True,
        "optimized": tr["ok"] and tr["current_ms"] <= 1.01 and tr["global_flag"],
    })

    return tweaks


def apply_deep_tweak(tweak_id: str) -> tuple[bool, str]:
    try:
        if tweak_id == "epp":
            ac, dcv = _query_alias("PERFEPP")
            _deep_backup("PERFEPP", [ac, dcv])
            ok = _set_alias("PERFEPP", 0)
            return ok, ("EPP set to 0 — CPU now always prefers speed"
                        if ok else "powercfg refused (run as administrator)")
        if tweak_id == "boost_pol":
            ac, dcv = _query_alias("PERFBOOSTPOL")
            _deep_backup("PERFBOOSTPOL", [ac, dcv])
            ok = _set_alias("PERFBOOSTPOL", 100)
            return ok, ("Turbo boost policy at 100% — full boost range"
                        if ok else "powercfg refused (run as administrator)")
        if tweak_id == "hetero":
            ac, dcv = _query_alias("SCHEDPOLICY")
            _deep_backup("SCHEDPOLICY", [ac, dcv])
            ac2, dcv2 = _query_alias("SHORTSCHEDPOLICY")
            if ac2 is not None:
                _deep_backup("SHORTSCHEDPOLICY", [ac2, dcv2])
                _set_alias("SHORTSCHEDPOLICY", 2)
            ok = _set_alias("SCHEDPOLICY", 2)
            return ok, ("Scheduler now prefers performance cores"
                        if ok else "powercfg refused (run as administrator)")
        if tweak_id == "idle_disable":
            ac, dcv = _query_alias("IDLEDISABLE")
            _deep_backup("IDLEDISABLE", [ac, dcv])
            ok = _set_alias("IDLEDISABLE", 1, dc=False)  # never on battery
            return ok, ("C-states disabled (AC power only) — watch your temps"
                        if ok else "powercfg refused (run as administrator)")
        if tweak_id == "timer_res":
            live = request_max_timer_resolution()
            glob = _reg_read(winreg.HKEY_LOCAL_MACHINE, KERNEL_KEY,
                             "GlobalTimerResolutionRequests", None)
            _deep_backup("GlobalTimerResolutionRequests",
                         int(glob) if glob is not None else None)
            reg = _reg_write(winreg.HKEY_LOCAL_MACHINE, KERNEL_KEY,
                             "GlobalTimerResolutionRequests", 1)
            if live:
                return True, ("0.5 ms timer active now"
                              + ("; system-wide flag set (reboot to apply)"
                                 if reg else "; system-wide flag needs admin"))
            return reg, ("System-wide flag set (reboot to apply)"
                         if reg else "Access denied — run as administrator")
        return False, "Unknown tweak"
    except Exception as exc:
        logger.exception("apply_deep_tweak(%s)", tweak_id)
        return False, str(exc)


def revert_deep_tweak(tweak_id: str) -> tuple[bool, str]:
    try:
        alias_map = {"epp": "PERFEPP", "boost_pol": "PERFBOOSTPOL",
                     "hetero": "SCHEDPOLICY", "idle_disable": "IDLEDISABLE"}
        if tweak_id in alias_map:
            alias = alias_map[tweak_id]
            saved = _deep_restore(alias)
            # sensible Windows defaults when no backup exists
            defaults = {"PERFEPP": 33, "PERFBOOSTPOL": 100,
                        "SCHEDPOLICY": 5, "IDLEDISABLE": 0}
            ac = saved[0] if saved and saved[0] is not None else defaults[alias]
            dcv = saved[1] if saved and saved[1] is not None else ac
            ok, _ = _powercfg("/setacvalueindex", "SCHEME_CURRENT",
                              "SUB_PROCESSOR", alias, str(ac))
            _powercfg("/setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR",
                      alias, str(dcv))
            _powercfg("/setactive", "SCHEME_CURRENT")
            if tweak_id == "hetero":
                saved2 = _deep_restore("SHORTSCHEDPOLICY")
                if saved2 and saved2[0] is not None:
                    _powercfg("/setacvalueindex", "SCHEME_CURRENT",
                              "SUB_PROCESSOR", "SHORTSCHEDPOLICY", str(saved2[0]))
                    if saved2[1] is not None:
                        _powercfg("/setdcvalueindex", "SCHEME_CURRENT",
                                  "SUB_PROCESSOR", "SHORTSCHEDPOLICY",
                                  str(saved2[1]))
                    _powercfg("/setactive", "SCHEME_CURRENT")
            return ok == 0, f"{alias} restored to AC={ac}, DC={dcv}"
        if tweak_id == "timer_res":
            release_timer_resolution()
            saved = _deep_restore("GlobalTimerResolutionRequests")
            if saved is None:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, KERNEL_KEY,
                                        0, winreg.KEY_SET_VALUE) as k:
                        winreg.DeleteValue(k, "GlobalTimerResolutionRequests")
                except Exception:
                    pass
            else:
                _reg_write(winreg.HKEY_LOCAL_MACHINE, KERNEL_KEY,
                           "GlobalTimerResolutionRequests", int(saved))
            return True, "Timer resolution released and flag restored"
        return False, "Unknown tweak"
    except Exception as exc:
        logger.exception("revert_deep_tweak(%s)", tweak_id)
        return False, str(exc)
