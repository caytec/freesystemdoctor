"""Idle-Time Auto-Maintenance — schedules cleanups when system is idle."""

import os
import time
import threading
import json
from pathlib import Path
from datetime import datetime

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_IDLE_TIMEOUT = 300  # 5 minutes of inactivity = idle
_CONFIG_FILE = Path(os.environ.get("TEMP", ".")) / "FreeSystemDoctor" / "idle_maintenance.json"

_maintenance_thread = None
_stop_event = threading.Event()
_last_activity = time.time()


def _get_last_input_time() -> float:
    """Get timestamp of last user input (keyboard/mouse)."""
    try:
        import ctypes
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        return lii.dwTime / 1000.0
    except Exception:
        return time.time()


def is_system_idle() -> bool:
    """Check if system has been idle for _IDLE_TIMEOUT seconds."""
    if not _PSUTIL:
        return False
    try:
        last_input = _get_last_input_time()
        idle_seconds = time.time() - last_input
        return idle_seconds > _IDLE_TIMEOUT
    except Exception:
        return False


def is_cpu_busy() -> bool:
    """Check if CPU is busy (>50% usage)."""
    if not _PSUTIL:
        return True
    try:
        return psutil.cpu_percent(interval=1) > 50
    except Exception:
        return True


def is_disk_busy() -> bool:
    """Check if disk is busy (I/O >30%)."""
    if not _PSUTIL:
        return True
    try:
        io_counters = psutil.disk_io_counters(perdisk=True)
        return any(counter.write_count > 100 for counter in io_counters.values())
    except Exception:
        return True


def can_run_maintenance() -> bool:
    """Return True if system is idle, CPU/disk not busy, and no user activity."""
    return is_system_idle() and not is_cpu_busy() and not is_disk_busy()


def get_maintenance_config() -> dict:
    """Load or create default maintenance config."""
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass

    default = {
        "enabled": False,
        "run_disk_clean": True,
        "run_registry_clean": True,
        "run_privacy_clean": True,
        "idle_timeout_seconds": 300,
        "last_run": None,
        "min_interval_hours": 24,
    }

    return default


def set_maintenance_config(config: dict):
    """Save maintenance configuration."""
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def _run_scheduled_maintenance():
    """Execute maintenance tasks (called when idle conditions met)."""
    config = get_maintenance_config()

    try:
        if config.get("run_disk_clean"):
            from engine import disk_cleaner
            items = disk_cleaner.scan_junk()
            disk_cleaner.clean_items([i for i in items if i.selected][:50])
    except Exception:
        pass

    try:
        if config.get("run_registry_clean"):
            from engine import registry_cleaner
            issues = registry_cleaner.scan_registry()
            if issues:
                registry_cleaner.fix_issues(issues[:20])
    except Exception:
        pass

    try:
        if config.get("run_privacy_clean"):
            from engine import privacy_cleaner
            items = privacy_cleaner.scan_browser_privacy()
            privacy_cleaner.clean_browser_privacy(items[:30])
    except Exception:
        pass

    config["last_run"] = datetime.now().isoformat()
    set_maintenance_config(config)


def _maintenance_loop():
    """Background loop that monitors system and runs maintenance when idle."""
    global _last_activity
    config = get_maintenance_config()

    while not _stop_event.is_set():
        if config.get("enabled", False) and can_run_maintenance():
            _run_scheduled_maintenance()
            _last_activity = time.time()
            _stop_event.wait(3600)  # Wait 1 hour before next check
        else:
            _stop_event.wait(10)  # Check every 10 seconds if idle conditions met


def start_maintenance_daemon() -> bool:
    """Start idle maintenance background thread."""
    global _maintenance_thread

    config = get_maintenance_config()
    if not config.get("enabled", False):
        return False

    if _maintenance_thread and _maintenance_thread.is_alive():
        return True

    _stop_event.clear()
    _maintenance_thread = threading.Thread(target=_maintenance_loop, daemon=True)
    _maintenance_thread.start()
    return True


def stop_maintenance_daemon():
    """Stop idle maintenance thread."""
    _stop_event.set()


def enable_idle_maintenance(enabled: bool = True):
    """Enable or disable idle maintenance."""
    config = get_maintenance_config()
    config["enabled"] = enabled
    set_maintenance_config(config)

    if enabled:
        start_maintenance_daemon()
    else:
        stop_maintenance_daemon()


def is_maintenance_enabled() -> bool:
    """Check if idle maintenance is enabled."""
    config = get_maintenance_config()
    return config.get("enabled", False)


def get_next_maintenance_time() -> str:
    """Estimate next maintenance run time."""
    config = get_maintenance_config()
    last_run = config.get("last_run")
    min_interval = config.get("min_interval_hours", 24)

    if not last_run:
        return "Next idle period"

    try:
        last = datetime.fromisoformat(last_run)
        next_eligible = last.timestamp() + (min_interval * 3600)
        if next_eligible > time.time():
            hours_wait = (next_eligible - time.time()) / 3600
            return f"In {hours_wait:.1f} hours (when idle)"
    except Exception:
        pass

    return "Next idle period"
