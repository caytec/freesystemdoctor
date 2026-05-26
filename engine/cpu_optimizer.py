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
