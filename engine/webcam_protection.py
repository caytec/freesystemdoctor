"""Webcam Protection — monitor camera access via Windows registry."""

import json
import os
import winreg
from datetime import datetime, timezone
from pathlib import Path

_WEBCAM_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"
_WEBCAM_NONPKG_KEY = _WEBCAM_KEY + r"\NonPackaged"

_CONFIG_DIR = Path(os.path.join(os.environ.get("TEMP", "C:\\Temp"), "FreeSystemDoctor"))
_ALLOWED_APPS_FILE = _CONFIG_DIR / "webcam_allowed_apps.json"


def get_camera_processes() -> list[dict]:
    """Read registry to find apps with camera access.
    Returns list of dicts: app_name, last_used_start, last_used_stop, is_active."""
    results = []

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WEBCAM_NONPKG_KEY) as key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{_WEBCAM_NONPKG_KEY}\\{subkey_name}") as subkey:
                        try:
                            last_start, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStart")
                            last_stop, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStop")
                        except OSError:
                            last_start, last_stop = 0, 0

                        app_name = subkey_name.split("#")[-1] if "#" in subkey_name else subkey_name
                        is_active = last_stop == 0 and last_start > 0

                        last_start_dt = _filetime_to_datetime(last_start) if last_start else None
                        last_stop_dt = _filetime_to_datetime(last_stop) if last_stop else None

                        results.append({
                            "app_name": app_name,
                            "last_used_start": last_start_dt,
                            "last_used_stop": last_stop_dt,
                            "is_active": is_active,
                        })
                    i += 1
                except OSError:
                    break
    except OSError:
        pass

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WEBCAM_KEY) as key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    if subkey_name == "NonPackaged":
                        i += 1
                        continue

                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{_WEBCAM_KEY}\\{subkey_name}") as subkey:
                        try:
                            last_start, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStart")
                            last_stop, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStop")
                        except OSError:
                            last_start, last_stop = 0, 0

                        app_name = subkey_name.replace("_8wekyb3d8bbwe", "").replace("_6rq1f2ca2t790", "")
                        is_active = last_stop == 0 and last_start > 0

                        last_start_dt = _filetime_to_datetime(last_start) if last_start else None
                        last_stop_dt = _filetime_to_datetime(last_stop) if last_stop else None

                        results.append({
                            "app_name": app_name,
                            "last_used_start": last_start_dt,
                            "last_used_stop": last_stop_dt,
                            "is_active": is_active,
                        })
                    i += 1
                except OSError:
                    break
    except OSError:
        pass

    results.sort(key=lambda x: x["last_used_start"] or datetime.now(timezone.utc), reverse=True)
    return results


def is_camera_in_use() -> bool:
    """Return True if any process has an open camera session."""
    procs = get_camera_processes()
    return any(p["is_active"] for p in procs)


def get_allowed_apps() -> list[str]:
    """Load the whitelist of trusted camera apps from JSON config."""
    try:
        if _ALLOWED_APPS_FILE.exists():
            with open(_ALLOWED_APPS_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_allowed_apps(apps: list[str]) -> None:
    """Persist the whitelist to JSON."""
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_ALLOWED_APPS_FILE, "w") as f:
            json.dump(apps, f)
    except Exception:
        pass


def add_allowed_app(app_name: str) -> None:
    """Add an app to the whitelist and save."""
    apps = get_allowed_apps()
    if app_name not in apps:
        apps.append(app_name)
        save_allowed_apps(apps)


def remove_allowed_app(app_name: str) -> None:
    """Remove an app from the whitelist and save."""
    apps = get_allowed_apps()
    if app_name in apps:
        apps.remove(app_name)
        save_allowed_apps(apps)


def get_camera_history() -> list[dict]:
    """Return all apps that have ever accessed the camera, with status."""
    procs = get_camera_processes()
    allowed = set(get_allowed_apps())

    results = []
    for p in procs:
        status = "Active" if p["is_active"] else ("Allowed" if p["app_name"] in allowed else "Unknown")
        last_used = p["last_used_start"] if p["last_used_start"] else p["last_used_stop"]
        results.append({
            "app_name": p["app_name"],
            "last_used": last_used,
            "last_used_str": last_used.strftime("%Y-%m-%d %H:%M:%S") if last_used else "Never",
            "status": status,
            "is_active": p["is_active"],
        })

    return results


def _filetime_to_datetime(filetime: int) -> datetime | None:
    """Convert Windows FILETIME (100-ns intervals since 1601) to Python datetime."""
    if filetime <= 0:
        return None
    try:
        epoch_offset = 116444736000000000
        unix_timestamp = (filetime - epoch_offset) / 10_000_000
        return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    except Exception:
        return None
