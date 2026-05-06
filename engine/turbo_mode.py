"""
turbo_mode.py — System performance / gaming turbo mode toggle.
Part of FreeSystemDoctor engine.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
import winreg
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "turbo_mode.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------
_STATE_FILE = os.path.join(_LOG_DIR, "turbo_state.json")

# ---------------------------------------------------------------------------
# Turbo profile definition
# ---------------------------------------------------------------------------

TURBO_PROFILE: dict = {
    "performance": {
        "description": "High-performance CPU, disabled visual effects, stopped non-essential services, disabled telemetry.",
        "power_plan": "High performance",
        "power_plan_guid": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "services_to_stop": [
            "SysMain",          # Superfetch
            "DiagTrack",        # Connected User Experiences & Telemetry
            "WSearch",          # Windows Search indexing
            "TabletInputService", # Touch keyboard
            "Fax",
            "PrintSpooler",
        ],
        "visual_effects": "minimal",
        "disable_telemetry": True,
        "free_ram": True,
    },
    "gaming": {
        "description": "Performance mode + Game Mode, disabled Xbox services, CPU priority boost, no notifications.",
        "power_plan": "High performance",
        "power_plan_guid": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "services_to_stop": [
            "SysMain",
            "DiagTrack",
            "WSearch",
            "TabletInputService",
            "Fax",
            "PrintSpooler",
            "XblAuthManager",    # Xbox Live Auth
            "XblGameSave",       # Xbox Live Game Save
            "XboxNetApiSvc",     # Xbox Live Networking
        ],
        "visual_effects": "minimal",
        "disable_telemetry": True,
        "free_ram": True,
        "disable_game_dvr": True,
        "disable_notifications": True,
        "cpu_priority_boost": True,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return result.returncode, result.stdout or ""
    except subprocess.TimeoutExpired:
        return -1, "Timeout"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"
    except Exception as exc:
        logger.exception("_run error: %s", exc)
        return -1, str(exc)


def _run_powershell(script: str, timeout: int = 60) -> tuple[int, str]:
    return _run(
        ["powershell", "-NonInteractive", "-NoProfile", "-Command", script],
        timeout=timeout,
    )


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
# Service management
# ---------------------------------------------------------------------------

def _get_service_start_type(service: str) -> Optional[str]:
    """Return current start type (Auto/Manual/Disabled) or None if not found."""
    rc, out = _run(["sc", "qc", service], timeout=10)
    if rc == 0:
        for line in out.splitlines():
            if "START_TYPE" in line.upper():
                if "AUTO" in line.upper():
                    return "Auto"
                elif "DEMAND" in line.upper():
                    return "Manual"
                elif "DISABLED" in line.upper():
                    return "Disabled"
    return None


def _get_service_status(service: str) -> str:
    """Return current state (Running/Stopped/etc.)."""
    rc, out = _run(["sc", "query", service], timeout=10)
    if rc == 0:
        for line in out.splitlines():
            if "STATE" in line.upper() and "RUNNING" in line.upper():
                return "Running"
            elif "STATE" in line.upper() and "STOPPED" in line.upper():
                return "Stopped"
    return "Unknown"


def _stop_service(service: str) -> bool:
    rc, _ = _run(["sc", "stop", service], timeout=20)
    return rc == 0


def _start_service(service: str) -> bool:
    rc, _ = _run(["sc", "start", service], timeout=20)
    return rc == 0


# ---------------------------------------------------------------------------
# Power plan
# ---------------------------------------------------------------------------

def _get_active_power_plan_guid() -> str:
    rc, out = _run(["powercfg", "/getactivescheme"], timeout=15)
    if rc == 0:
        match_obj = __import__("re").search(r"([0-9a-f-]{36})", out, __import__("re").IGNORECASE)
        if match_obj:
            return match_obj.group(1)
    return ""


def _set_power_plan(guid: str) -> bool:
    rc, _ = _run(["powercfg", "/setactive", guid], timeout=15)
    return rc == 0


# ---------------------------------------------------------------------------
# Visual effects
# ---------------------------------------------------------------------------

_VISUAL_EFFECTS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
_PERF_SETTINGS_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"


def _set_visual_effects_minimal() -> Optional[int]:
    """Set visual effects to 'Adjust for best performance'. Returns previous value."""
    root = winreg.HKEY_CURRENT_USER
    prev = _reg_read(root, _VISUAL_EFFECTS_KEY, "VisualFXSetting", None)
    _reg_write(root, _VISUAL_EFFECTS_KEY, "VisualFXSetting", 2)  # 2 = Best performance
    return prev


def _restore_visual_effects(prev_value: Optional[int]) -> None:
    root = winreg.HKEY_CURRENT_USER
    if prev_value is not None:
        _reg_write(root, _VISUAL_EFFECTS_KEY, "VisualFXSetting", prev_value)


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

_TELEMETRY_KEY = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"


def _disable_telemetry() -> Optional[int]:
    root = winreg.HKEY_LOCAL_MACHINE
    prev = _reg_read(root, _TELEMETRY_KEY, "AllowTelemetry", None)
    _reg_write(root, _TELEMETRY_KEY, "AllowTelemetry", 0)
    return prev


def _restore_telemetry(prev_value: Optional[int]) -> None:
    root = winreg.HKEY_LOCAL_MACHINE
    if prev_value is not None:
        _reg_write(root, _TELEMETRY_KEY, "AllowTelemetry", prev_value)
    else:
        try:
            with winreg.OpenKey(root, _TELEMETRY_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, "AllowTelemetry")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Gaming-specific tweaks
# ---------------------------------------------------------------------------

_GAME_DVR_KEY = r"SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR"
_GAME_DVR_KEY2 = r"System\GameConfigStore"
_NOTIFICATIONS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications"


def _disable_game_dvr() -> dict:
    """Disable Windows Game Bar / GameDVR. Returns previous values for restoration."""
    prev: dict = {}
    root = winreg.HKEY_LOCAL_MACHINE
    # Policy key
    prev["AllowGameDVR"] = _reg_read(root, _GAME_DVR_KEY, "value", None)
    _reg_write(root, _GAME_DVR_KEY, "value", 0)

    # GameConfigStore
    root2 = winreg.HKEY_LOCAL_MACHINE
    prev["GameDVR_Enabled"] = _reg_read(root2, _GAME_DVR_KEY2, "GameDVR_Enabled", None)
    _reg_write(root2, _GAME_DVR_KEY2, "GameDVR_Enabled", 0)

    return prev


def _restore_game_dvr(prev: dict) -> None:
    root = winreg.HKEY_LOCAL_MACHINE
    if prev.get("AllowGameDVR") is not None:
        _reg_write(root, _GAME_DVR_KEY, "value", prev["AllowGameDVR"])
    if prev.get("GameDVR_Enabled") is not None:
        _reg_write(root, _GAME_DVR_KEY2, "GameDVR_Enabled", prev["GameDVR_Enabled"])


def _disable_notifications() -> Optional[int]:
    root = winreg.HKEY_CURRENT_USER
    prev = _reg_read(root, _NOTIFICATIONS_KEY, "ToastEnabled", None)
    _reg_write(root, _NOTIFICATIONS_KEY, "ToastEnabled", 0)
    return prev


def _restore_notifications(prev_value: Optional[int]) -> None:
    root = winreg.HKEY_CURRENT_USER
    if prev_value is not None:
        _reg_write(root, _NOTIFICATIONS_KEY, "ToastEnabled", prev_value)


# ---------------------------------------------------------------------------
# RAM free
# ---------------------------------------------------------------------------

def _free_ram() -> None:
    """Attempt to free standby list via EmptyWorkingSet trick."""
    try:
        _run_powershell(
            "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()",
            timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _get_nonessential_services() -> list[str]:
    """
    Return list of service names that are safe to stop temporarily during turbo mode.
    """
    return [
        "SysMain",             # Superfetch — disk caching, fine to stop during gaming
        "DiagTrack",           # Telemetry collection
        "WSearch",             # Indexing service — heavy I/O
        "TabletInputService",  # Touch keyboard / handwriting (not needed on desktops)
        "Fax",                 # Fax service
        "PrintSpooler",        # Print spooler (stop only if no printing needed)
    ]


def get_turbo_status() -> dict:
    """
    Return the current turbo mode status.

    Returns:
        {active: bool, mode: str, changes_applied: list[str]}
    """
    try:
        state = _load_state()
        return {
            "active": state.get("active", False),
            "mode": state.get("mode", ""),
            "changes_applied": state.get("changes_applied", []),
        }
    except Exception as exc:
        logger.exception("get_turbo_status failed: %s", exc)
        return {"active": False, "mode": "", "changes_applied": []}


def enable_turbo(
    mode: str = "performance",
    progress_cb: Optional[Callable[[str], None]] = None,
) -> list[str]:
    """
    Enable turbo mode ('performance' or 'gaming').

    Args:
        mode: "performance" or "gaming"
        progress_cb: Optional callable receiving step description strings.

    Returns:
        List of changes made.
    """
    changes: list[str] = []
    state: dict = {"active": True, "mode": mode, "timestamp": time.time(), "restore": {}, "changes_applied": []}

    def _step(msg: str) -> None:
        changes.append(msg)
        logger.info("enable_turbo [%s]: %s", mode, msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    profile = TURBO_PROFILE.get(mode, TURBO_PROFILE["performance"])

    try:
        # 1. Power plan
        _step(f"Setting power plan to: {profile['power_plan']}")
        prev_plan = _get_active_power_plan_guid()
        state["restore"]["power_plan_guid"] = prev_plan
        _set_power_plan(profile["power_plan_guid"])

        # 2. Visual effects
        _step("Adjusting visual effects for best performance")
        prev_ve = _set_visual_effects_minimal()
        state["restore"]["visual_effects"] = prev_ve

        # 3. Stop non-essential services
        services = profile.get("services_to_stop", [])
        service_states: dict = {}
        for svc in services:
            status = _get_service_status(svc)
            start_type = _get_service_start_type(svc)
            service_states[svc] = {"status": status, "start_type": start_type}
            if status == "Running":
                _step(f"Stopping service: {svc}")
                _stop_service(svc)
        state["restore"]["services"] = service_states

        # 4. Disable telemetry
        if profile.get("disable_telemetry"):
            _step("Disabling telemetry collection")
            prev_telemetry = _disable_telemetry()
            state["restore"]["telemetry"] = prev_telemetry

        # 5. Free RAM
        if profile.get("free_ram"):
            _step("Freeing unused RAM")
            _free_ram()

        # Gaming-specific steps
        if profile.get("disable_game_dvr"):
            _step("Disabling Windows Game Bar and GameDVR")
            prev_dvr = _disable_game_dvr()
            state["restore"]["game_dvr"] = prev_dvr

        if profile.get("disable_notifications"):
            _step("Disabling desktop notifications")
            prev_notif = _disable_notifications()
            state["restore"]["notifications"] = prev_notif

        if profile.get("cpu_priority_boost"):
            _step("Enabling CPU priority boost for foreground processes")
            _reg_write(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                "Win32PrioritySeparation",
                38,  # Foreground apps get maximum priority boost
            )
            state["restore"]["win32_priority_separation"] = _reg_read(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                "Win32PrioritySeparation",
                2,
            )

    except Exception as exc:
        logger.exception("enable_turbo failed mid-way: %s", exc)
        changes.append(f"Error during enable: {exc}")

    state["changes_applied"] = changes
    _save_state(state)
    return changes


def disable_turbo(progress_cb: Optional[Callable[[str], None]] = None) -> list[str]:
    """
    Disable turbo mode and restore previous system state.

    Args:
        progress_cb: Optional callable receiving step description strings.

    Returns:
        List of changes made (restoration steps).
    """
    changes: list[str] = []
    state = _load_state()

    def _step(msg: str) -> None:
        changes.append(msg)
        logger.info("disable_turbo: %s", msg)
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    if not state.get("active"):
        _step("Turbo mode was not active — nothing to restore.")
        return changes

    restore = state.get("restore", {})

    try:
        # Restore power plan
        prev_plan = restore.get("power_plan_guid")
        if prev_plan:
            _step(f"Restoring power plan (GUID: {prev_plan})")
            _set_power_plan(prev_plan)
        else:
            _step("Restoring Balanced power plan")
            _set_power_plan("381b4222-f694-41f0-9685-ff5bb260df2e")  # Balanced

        # Restore visual effects
        prev_ve = restore.get("visual_effects")
        _step("Restoring visual effects settings")
        _restore_visual_effects(prev_ve)

        # Restart services that were stopped
        service_states: dict = restore.get("services", {})
        for svc, info in service_states.items():
            if info.get("status") == "Running":
                _step(f"Restarting service: {svc}")
                _start_service(svc)

        # Restore telemetry
        if "telemetry" in restore:
            _step("Restoring telemetry settings")
            _restore_telemetry(restore["telemetry"])

        # Restore Game DVR
        if "game_dvr" in restore:
            _step("Restoring Windows Game Bar / GameDVR settings")
            _restore_game_dvr(restore["game_dvr"])

        # Restore notifications
        if "notifications" in restore:
            _step("Restoring notification settings")
            _restore_notifications(restore["notifications"])

        # Restore CPU priority
        if "win32_priority_separation" in restore:
            _step("Restoring CPU priority settings")
            _reg_write(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                "Win32PrioritySeparation",
                restore["win32_priority_separation"],
            )

    except Exception as exc:
        logger.exception("disable_turbo failed: %s", exc)
        changes.append(f"Error during restore: {exc}")

    # Clear state
    state_cleared = {"active": False, "mode": "", "changes_applied": [], "restore": {}}
    _save_state(state_cleared)

    return changes
