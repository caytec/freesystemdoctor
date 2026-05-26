"""Batch Uninstaller engine — multi-app removal with residual cleanup."""

import subprocess
import winreg
from pathlib import Path
import os
import json
from datetime import datetime

_PROTECTED_APPS = frozenset([
    "windows", "microsoft", ".net framework", "visual studio",
    "office", "onedrive", "defender", "antimalware", "firewall",
    "driver", "chipset", "intel", "nvidia", "amd"
])

_APP_CATEGORIES = {
    "System Apps": ["windows", "microsoft", "driver"],
    "Development": ["visual studio", ".net", "java", "python", "node", "git"],
    "Games": ["steam", "epic", "origin", "ubisoft", "game"],
    "Utilities": ["7-zip", "winrar", "putty", "notepad++", "vlc"],
    "Communication": ["discord", "slack", "teams", "skype", "telegram", "zoom"],
    "Office": ["office", "onedrive", "word", "excel", "powerpoint"],
    "Media": ["adobe", "photoshop", "premiere", "after effects"],
    "Browsers": ["chrome", "firefox", "edge", "safari", "opera"],
    "Security": ["antivirus", "malware", "defender", "kaspersky", "bitdefender"],
}


def _categorize_app(app_name: str) -> str:
    """Categorize application based on name."""
    lower_name = app_name.lower()
    for category, keywords in _APP_CATEGORIES.items():
        if any(kw in lower_name for kw in keywords):
            return category
    return "Other"


def _is_protected(app_name: str) -> bool:
    """Check if app is in protected list."""
    lower_name = app_name.lower()
    return any(protected in lower_name for protected in _PROTECTED_APPS)


def get_installed_apps() -> list[dict]:
    """Get list of installed applications from registry."""
    apps = []
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, path in registry_paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(hive, f"{path}\\{subkey_name}") as subkey:
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            except OSError:
                                name = subkey_name
                            try:
                                version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                            except OSError:
                                version = ""

                            try:
                                uninstall_str = winreg.QueryValueEx(subkey, "UninstallString")[0]
                            except OSError:
                                uninstall_str = ""

                            try:
                                install_date = winreg.QueryValueEx(subkey, "InstallDate")[0]
                            except OSError:
                                install_date = ""

                            if name:
                                apps.append({
                                    "name": name,
                                    "version": version,
                                    "uninstall_string": uninstall_str,
                                    "registry_key": subkey_name,
                                    "category": _categorize_app(name),
                                    "protected": _is_protected(name),
                                    "install_date": install_date,
                                })
                    except OSError:
                        pass
        except OSError:
            pass

    return sorted(list({a["name"]: a for a in apps}.values()), key=lambda x: x["name"])


def get_residual_files(app_name: str) -> list[str]:
    """Find potential residual files for an app."""
    residuals = []
    home = Path.home()
    appdata_local = Path(os.environ.get("LOCALAPPDATA", ""))
    appdata_roaming = Path(os.environ.get("APPDATA", ""))

    search_paths = [
        appdata_local,
        appdata_roaming,
        home / "Documents",
        Path("C:\\Program Files"),
        Path("C:\\Program Files (x86)"),
    ]

    app_keywords = app_name.lower().split()[0:2]  # First 2 words

    for base_path in search_paths:
        if not base_path.exists():
            continue
        try:
            for item in base_path.iterdir():
                item_lower = item.name.lower()
                if any(kw in item_lower for kw in app_keywords):
                    residuals.append(str(item))
                    if len(residuals) >= 20:
                        return residuals
        except (PermissionError, OSError):
            pass

    return residuals


def uninstall_app(app_name: str, uninstall_string: str) -> bool:
    """Attempt to uninstall application."""
    if not uninstall_string:
        return False

    try:
        # Remove quotes and split command
        cmd = uninstall_string.strip('"').split()
        subprocess.run(cmd + ["/quiet", "/norestart"], timeout=60, capture_output=True, creationflags=0x08000000)
        return True
    except Exception:
        try:
            subprocess.run([uninstall_string], timeout=60, capture_output=True, creationflags=0x08000000)
            return True
        except Exception:
            return False


def remove_residual_files(paths: list[str]) -> tuple[int, int]:
    """Remove residual files. Returns (bytes_freed, files_deleted)."""
    freed = 0
    deleted = 0

    for path_str in paths:
        path = Path(path_str)
        try:
            if path.is_file():
                freed += path.stat().st_size
                path.unlink()
                deleted += 1
            elif path.is_dir():
                for item in path.rglob("*"):
                    try:
                        if item.is_file():
                            freed += item.stat().st_size
                            item.unlink()
                            deleted += 1
                    except (PermissionError, OSError):
                        pass
                try:
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
                except Exception:
                    pass
        except (PermissionError, OSError):
            pass

    return freed, deleted


def log_uninstall(app_name: str):
    """Log uninstalled app for potential rollback."""
    log_dir = Path.home() / "AppData" / "Local" / "FreeSystemDoctor"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "uninstall_log.json"

    log_entry = {
        "app": app_name,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        if log_file.exists():
            with open(log_file, "r") as f:
                log_data = json.load(f)
        else:
            log_data = []

        log_data.append(log_entry)
        # Keep last 20 uninstalls
        log_data = log_data[-20:]

        with open(log_file, "w") as f:
            json.dump(log_data, f, indent=2)
    except Exception:
        pass


def get_uninstall_history() -> list[dict]:
    """Get history of uninstalled apps."""
    log_file = Path.home() / "AppData" / "Local" / "FreeSystemDoctor" / "uninstall_log.json"

    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return []


def estimate_space_freed(app_names: list[str]) -> int:
    """Estimate total space that would be freed."""
    total_bytes = 0

    for app_name in app_names:
        residuals = get_residual_files(app_name)
        for path_str in residuals:
            try:
                path = Path(path_str)
                if path.is_file():
                    total_bytes += path.stat().st_size
                elif path.is_dir():
                    for item in path.rglob("*"):
                        if item.is_file():
                            total_bytes += item.stat().st_size
            except (PermissionError, OSError):
                pass

    return total_bytes


def get_app_by_category(category: str) -> list[dict]:
    """Get all apps in a specific category."""
    all_apps = get_installed_apps()
    return [app for app in all_apps if app["category"] == category]


def uninstall_apps_batch(app_names: list[str]) -> tuple[int, int, list[str]]:
    """Uninstall multiple apps and return (success_count, failed_count, uninstalled_names)."""
    success = 0
    failed = 0
    uninstalled = []

    all_apps = get_installed_apps()
    app_dict = {app["name"]: app for app in all_apps}

    for app_name in app_names:
        if app_name not in app_dict:
            failed += 1
            continue

        app = app_dict[app_name]
        if app["protected"]:
            failed += 1
            continue

        if uninstall_app(app_name, app["uninstall_string"]):
            log_uninstall(app_name)
            uninstalled.append(app_name)
            success += 1
        else:
            failed += 1

    return (success, failed, uninstalled)
