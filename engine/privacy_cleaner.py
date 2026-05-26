"""Privacy cleaner — Windows telemetry, tracking, activity history, browser privacy."""

import os
import subprocess
import winreg
import shutil
from pathlib import Path


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=True,
                           creationflags=0x08000000)


def _rw(hkey, path, name, vtype, value) -> bool:
    try:
        with winreg.CreateKey(hkey, path) as k:
            winreg.SetValueEx(k, name, 0, vtype, value)
        return True
    except OSError:
        return False


def _rr(hkey, path, name, default=None):
    try:
        with winreg.OpenKey(hkey, path) as k:
            v, _ = winreg.QueryValueEx(k, name)
            return v
    except OSError:
        return default


# ── telemetry ─────────────────────────────────────────────────────────────────

_TELEMETRY_TWEAKS = [
    # (hkey, path, name, type, value_off, value_on)
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
     "AllowTelemetry", winreg.REG_DWORD, 0, 1),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "ContentDeliveryAllowed", winreg.REG_DWORD, 0, 1),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SoftLandingEnabled", winreg.REG_DWORD, 0, 1),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "OemPreInstalledAppsEnabled", winreg.REG_DWORD, 0, 1),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "PreInstalledAppsEnabled", winreg.REG_DWORD, 0, 1),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\InputPersonalization",
     "RestrictImplicitInkCollection", winreg.REG_DWORD, 1, 0),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\InputPersonalization",
     "RestrictImplicitTextCollection", winreg.REG_DWORD, 1, 0),
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Policies\Microsoft\Windows\System",
     "PublishUserActivities", winreg.REG_DWORD, 0, 1),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
     "CortanaEnabled", winreg.REG_DWORD, 0, 1),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
     "TailoredExperiencesWithDiagnosticDataEnabled", winreg.REG_DWORD, 0, 1),
]

_TELEMETRY_SERVICES = ["DiagTrack", "dmwappushservice"]

_TELEMETRY_TASKS = [
    r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
    r"\Microsoft\Windows\Application Experience\ProgramDataUpdater",
    r"\Microsoft\Windows\Autochk\Proxy",
    r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
    r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
    r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
]


def disable_telemetry(progress_cb=None) -> list[str]:
    done = []
    for hkey, path, name, vtype, off_val, _ in _TELEMETRY_TWEAKS:
        if progress_cb:
            progress_cb(f"Setting {name}...")
        if _rw(hkey, path, name, vtype, off_val):
            done.append(f"Registry: {name} = {off_val}")

    for svc in _TELEMETRY_SERVICES:
        subprocess.run(["sc", "config", svc, "start=disabled"], capture_output=True)
        subprocess.run(["net", "stop", svc], capture_output=True)
        done.append(f"Service disabled: {svc}")

    for task in _TELEMETRY_TASKS:
        r = subprocess.run(["schtasks", "/change", "/tn", task, "/disable"],
                           capture_output=True)
        if r.returncode == 0:
            done.append(f"Task disabled: {task.split('\\')[-1]}")

    return done


def enable_telemetry(progress_cb=None) -> list[str]:
    done = []
    for hkey, path, name, vtype, _, on_val in _TELEMETRY_TWEAKS:
        if _rw(hkey, path, name, vtype, on_val):
            done.append(f"Registry: {name} = {on_val}")
    for svc in _TELEMETRY_SERVICES:
        subprocess.run(["sc", "config", svc, "start=auto"], capture_output=True)
        subprocess.run(["net", "start", svc], capture_output=True)
        done.append(f"Service enabled: {svc}")
    return done


def get_telemetry_status() -> dict:
    status = {}
    h = winreg.HKEY_LOCAL_MACHINE
    path = r"SOFTWARE\Policies\Microsoft\Windows\DataCollection"
    status["telemetry_level"] = _rr(h, path, "AllowTelemetry", "Not set")

    h2 = winreg.HKEY_CURRENT_USER
    status["cortana_enabled"] = _rr(h2,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Search", "CortanaEnabled", 1)
    status["tailored_xp"] = _rr(h2,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Privacy",
        "TailoredExperiencesWithDiagnosticDataEnabled", "Not set")
    return status


# ── activity history ──────────────────────────────────────────────────────────

def clear_activity_history() -> list[str]:
    done = []
    # Timeline / ConnectedDevicesPlatform
    cdp = Path.home() / "AppData/Local/ConnectedDevicesPlatform"
    if cdp.exists():
        for db in cdp.rglob("ActivitiesCache.db"):
            try:
                db.unlink()
                done.append(f"Deleted: {db.name}")
            except OSError:
                pass
    # Recent documents
    recent = Path.home() / "AppData/Roaming/Microsoft/Windows/Recent"
    if recent.exists():
        for f in recent.iterdir():
            try:
                f.unlink()
                done.append(f"Cleared recent: {f.name}")
            except OSError:
                pass
    # Disable activity history in registry
    _rw(winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Policies\Microsoft\Windows\System",
        "EnableActivityFeed", winreg.REG_DWORD, 0)
    done.append("Registry: activity feed disabled")
    return done


# ── location tracking ────────────────────────────────────────────────────────

def disable_location() -> bool:
    return _rw(winreg.HKEY_CURRENT_USER,
               r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager"
               r"\ConsentStore\location",
               "Value", winreg.REG_SZ, "Deny")


def enable_location() -> bool:
    return _rw(winreg.HKEY_CURRENT_USER,
               r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager"
               r"\ConsentStore\location",
               "Value", winreg.REG_SZ, "Allow")


def get_location_status() -> str:
    return _rr(winreg.HKEY_CURRENT_USER,
               r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager"
               r"\ConsentStore\location",
               "Value", "Allow")


# ── advertising ID ────────────────────────────────────────────────────────────

def disable_advertising_id() -> bool:
    return _rw(winreg.HKEY_CURRENT_USER,
               r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
               "Enabled", winreg.REG_DWORD, 0)


def enable_advertising_id() -> bool:
    return _rw(winreg.HKEY_CURRENT_USER,
               r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
               "Enabled", winreg.REG_DWORD, 1)


def get_advertising_id_status() -> int:
    return _rr(winreg.HKEY_CURRENT_USER,
               r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
               "Enabled", 1)


# ── browser privacy ───────────────────────────────────────────────────────────

def _fmt(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def _dir_size(p):
    total = 0
    try:
        for r, _, files in os.walk(p):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(r, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _delete_dir(path):
    freed = 0
    try:
        p = Path(path)
        if p.is_dir():
            freed = _dir_size(path)
            shutil.rmtree(path, ignore_errors=True)
        elif p.is_file():
            freed = p.stat().st_size
            p.unlink(missing_ok=True)
    except OSError:
        pass
    return freed


BROWSER_PRIVACY_ITEMS = [
    # (label, path_glob_or_path)
    ("Chrome Cache",         Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cache"),
    ("Chrome Code Cache",    Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Code Cache"),
    ("Chrome Cookies",       Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Cookies"),
    ("Chrome History",       Path.home() / "AppData/Local/Google/Chrome/User Data/Default/History"),
    ("Chrome Login Data",    Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Login Data"),
    ("Edge Cache",           Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/Cache"),
    ("Edge Cookies",         Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/Cookies"),
    ("Edge History",         Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default/History"),
    ("IE Cache",             Path.home() / "AppData/Local/Microsoft/Windows/INetCache"),
    ("IE Cookies",           Path.home() / "AppData/Roaming/Microsoft/Windows/Cookies"),
]


def scan_browser_privacy() -> list[dict]:
    results = []
    for label, path in BROWSER_PRIVACY_ITEMS:
        p = Path(path)
        if p.exists():
            sz = _dir_size(str(p)) if p.is_dir() else p.stat().st_size
            results.append({"label": label, "path": str(p), "size": sz,
                             "size_str": _fmt(sz), "selected": True})

    # Firefox profiles
    ff_profiles = Path.home() / "AppData/Roaming/Mozilla/Firefox/Profiles"
    if ff_profiles.exists():
        for profile in ff_profiles.iterdir():
            if profile.is_dir():
                for item, name in [("cache2", "Firefox Cache"),
                                   ("cookies.sqlite", "Firefox Cookies"),
                                   ("places.sqlite", "Firefox History")]:
                    p = profile / item
                    if p.exists():
                        sz = _dir_size(str(p)) if p.is_dir() else p.stat().st_size
                        results.append({"label": f"{name} ({profile.name[:12]})",
                                        "path": str(p), "size": sz,
                                        "size_str": _fmt(sz), "selected": True})
    return results


def clean_browser_privacy(items: list[dict], progress_cb=None) -> tuple[int, int]:
    freed = 0
    count = 0
    for item in items:
        if not item.get("selected"):
            continue
        if progress_cb:
            progress_cb(item["label"])
        freed += _delete_dir(item["path"])
        count += 1
    return freed, count
