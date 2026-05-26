"""Performance Profiles — context-aware optimization modes (Work/Gaming/Streaming)."""

import os
import json
import subprocess
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_CONFIG_DIR = Path(os.environ.get("TEMP", ".")) / "FreeSystemDoctor"
_PROFILES_FILE = _CONFIG_DIR / "performance_profiles.json"

_ACTIVE_PROFILE = None


def _ensure_config_dir():
    """Ensure config directory exists."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_default_profiles() -> dict:
    """Return default performance profiles."""
    return {
        "work": {
            "name": "Work Mode",
            "description": "Balanced performance for office/productivity apps",
            "cpu_power_plan": "balanced",
            "disable_animations": False,
            "disable_notifications": False,
            "close_bandwidth_hogs": False,
            "max_cpu_cores": 0,  # 0 = all cores
            "gpu_performance": "balanced",
        },
        "gaming": {
            "name": "Gaming Mode",
            "description": "Maximum performance for gaming",
            "cpu_power_plan": "high_performance",
            "disable_animations": True,
            "disable_notifications": True,
            "close_bandwidth_hogs": True,
            "max_cpu_cores": 0,  # Use all
            "gpu_performance": "maximum",
        },
        "streaming": {
            "name": "Streaming Mode",
            "description": "Optimized for video streaming/recording",
            "cpu_power_plan": "high_performance",
            "disable_animations": False,
            "disable_notifications": True,
            "close_bandwidth_hogs": True,
            "max_cpu_cores": 4,  # Reserve cores
            "gpu_performance": "maximum",
        },
        "battery": {
            "name": "Battery Saver",
            "description": "Extend laptop battery life",
            "cpu_power_plan": "power_saver",
            "disable_animations": True,
            "disable_notifications": False,
            "close_bandwidth_hogs": False,
            "max_cpu_cores": 2,
            "gpu_performance": "minimum",
        },
    }


def get_profiles() -> dict:
    """Load or create default profiles."""
    _ensure_config_dir()

    if _PROFILES_FILE.exists():
        try:
            with open(_PROFILES_FILE) as f:
                return json.load(f)
        except Exception:
            pass

    profiles = get_default_profiles()
    save_profiles(profiles)
    return profiles


def save_profiles(profiles: dict):
    """Save profiles to file."""
    _ensure_config_dir()
    try:
        with open(_PROFILES_FILE, "w") as f:
            json.dump(profiles, f, indent=2)
    except Exception:
        pass


def activate_profile(profile_name: str) -> bool:
    """Activate a performance profile."""
    global _ACTIVE_PROFILE

    profiles = get_profiles()
    if profile_name not in profiles:
        return False

    profile = profiles[profile_name]

    # Set power plan
    power_plans = {
        "power_saver": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df3b",
        "high_performance": "8c5e7fda-e8bf-45a6-a6cc-4b3c1f7d313b",
    }

    if profile["cpu_power_plan"] in power_plans:
        try:
            guid = power_plans[profile["cpu_power_plan"]]
            subprocess.run(
                ["powercfg", "/setactive", guid],
                capture_output=True,
                timeout=5, creationflags=0x08000000)
        except Exception:
            pass

    # Close bandwidth hogs if requested
    if profile["close_bandwidth_hogs"]:
        try:
            _close_bandwidth_hogs()
        except Exception:
            pass

    _ACTIVE_PROFILE = profile_name
    return True


def _close_bandwidth_hogs() -> int:
    """Suspend bandwidth-intensive apps. Returns count closed."""
    if not _PSUTIL:
        return 0

    hogs = []
    try:
        for proc in psutil.process_iter(["pid", "name", "connections"]):
            try:
                conns = proc.connections(kind="inet")
                if len(conns) > 10:
                    hogs.append(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

    # Don't close critical processes
    skip_names = {"explorer", "svchost", "dwm", "taskhostw", "lsass", "csrss"}

    closed = 0
    for pid in hogs:
        try:
            proc = psutil.Process(pid)
            if proc.name().lower() not in skip_names:
                proc.suspend()
                closed += 1
        except Exception:
            pass

    return closed


def get_active_profile() -> str:
    """Get currently active profile name."""
    return _ACTIVE_PROFILE


def get_power_plan() -> dict:
    """Get current Windows power plan."""
    try:
        result = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True,
            text=True,
            timeout=5, creationflags=0x08000000)
        output = result.stdout
        if "power_saver" in output.lower():
            return {"name": "Power Saver", "guid": "a1841308-3541-4fab-bc81-f71556f20b4a"}
        elif "balanced" in output.lower():
            return {"name": "Balanced", "guid": "381b4222-f694-41f0-9685-ff5bb260df3b"}
        elif "high" in output.lower():
            return {"name": "High Performance", "guid": "8c5e7fda-e8bf-45a6-a6cc-4b3c1f7d313b"}
    except Exception:
        pass

    return {"name": "Unknown", "guid": ""}


def get_profile_info(profile_name: str) -> dict:
    """Get detailed info about a profile."""
    profiles = get_profiles()
    if profile_name in profiles:
        return profiles[profile_name]
    return {}


def list_profiles() -> list[dict]:
    """List all available profiles."""
    profiles = get_profiles()
    return [
        {
            "key": key,
            "name": profile["name"],
            "description": profile["description"],
            "active": key == _ACTIVE_PROFILE,
        }
        for key, profile in profiles.items()
    ]
