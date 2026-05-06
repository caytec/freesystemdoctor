"""Startup Link Analyzer — scan .lnk shortcut files in startup folders for impact scoring."""

import struct
import subprocess
from datetime import datetime
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_STARTUP_FOLDERS = [
    Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
    Path("C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"),
]

_BLOATWARE_KEYWORDS = [
    "updater", "installer", "download", "manager", "cleaner",
    "optimizer", "booster", "toolbar", "extension", "plugin",
    "adware", "pup", "crypto", "miner", "malware"
]

_SYSTEM_APPS = frozenset([
    "windows defender", "windows update", "windows security",
    "antimalware", "defender", "firewall", ".net framework",
    "visual studio", "office", "onedrive"
])


class StartupLink:
    """Represents a startup shortcut link."""
    def __init__(self, path: Path, target: str, args: str, category: str, impact: str):
        self.path = path
        self.name = path.stem
        self.target = target
        self.args = args
        self.category = category
        self.impact = impact


def _extract_shortcut_target(lnk_path: Path) -> tuple[str, str]:
    """Extract target executable and arguments from .lnk file."""
    try:
        with open(lnk_path, "rb") as f:
            header = f.read(4)
            if header != b'\x4C\x00\x00\x00':
                return ("", "")

            f.seek(76)
            data_flags = struct.unpack("<I", f.read(4))[0]

            if data_flags & 0x01:
                icon_location_size = struct.unpack("<H", f.read(2))[0]
                f.read(icon_location_size)

            f.seek(0x4C + 4)
            if data_flags & 0x01:
                f.read(2)

            if data_flags & 0x08:
                args_length = struct.unpack("<H", f.read(2))[0]
                args = f.read(args_length).decode("utf-16-le", errors="ignore").rstrip('\x00')
            else:
                args = ""

            if data_flags & 0x04:
                work_dir_length = struct.unpack("<H", f.read(2))[0]
                f.read(work_dir_length)

            if data_flags & 0x10:
                cmd_line_length = struct.unpack("<H", f.read(2))[0]
                f.read(cmd_line_length)

            if data_flags & 0x20:
                icon_file_length = struct.unpack("<H", f.read(2))[0]
                f.read(icon_file_length)

            try:
                f.seek(0x4C + 4)
                target_location_size = struct.unpack("<H", f.read(2))[0]
                target = f.read(target_location_size).decode("utf-16-le", errors="ignore").rstrip('\x00')
            except Exception:
                target = ""

            return (target or "", args or "")
    except Exception:
        return ("", "")


def _classify_link(name: str, target: str, args: str) -> tuple[str, str]:
    """Classify startup link by category and impact."""
    lower_name = name.lower()
    lower_target = target.lower()

    if any(sys_app in lower_name or sys_app in lower_target for sys_app in _SYSTEM_APPS):
        return ("System", "LOW")

    if any(keyword in lower_name or keyword in lower_target for keyword in _BLOATWARE_KEYWORDS):
        return ("Bloatware", "HIGH")

    if "antivirus" in lower_name or "antimalware" in lower_name or "defender" in lower_name:
        return ("Security", "HIGH")

    if any(keyword in lower_name for keyword in ["chrome", "firefox", "edge", "browser"]):
        return ("Browser", "MEDIUM")

    if any(keyword in lower_name for keyword in ["nvidia", "amd", "intel", "driver"]):
        return ("Drivers", "LOW")

    if any(keyword in lower_name for keyword in ["steam", "discord", "slack", "teams"]):
        return ("Communication", "MEDIUM")

    return ("Application", "MEDIUM")


def scan_startup_links() -> list[StartupLink]:
    """Scan all startup link files and return parsed entries."""
    links = []

    for folder in _STARTUP_FOLDERS:
        if not folder.exists():
            continue

        try:
            for lnk_file in folder.glob("*.lnk"):
                target, args = _extract_shortcut_target(lnk_file)
                if not target:
                    continue

                category, impact = _classify_link(lnk_file.stem, target, args)

                link = StartupLink(
                    path=lnk_file,
                    target=target,
                    args=args,
                    category=category,
                    impact=impact
                )
                links.append(link)
        except Exception:
            pass

    return links


def get_link_process_info(target: str) -> dict:
    """Get process information for target executable."""
    if not _PSUTIL:
        return {}

    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "create_time"]):
            try:
                if target.lower() in proc.info["name"].lower() or proc.info["name"].lower() in target.lower():
                    return {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "cpu_percent": proc.info["cpu_percent"] or 0,
                        "memory_percent": proc.info["memory_percent"] or 0,
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass

    return {}


def get_target_details(target: str) -> dict:
    """Get file details about target executable."""
    try:
        target_path = Path(target)
        if target_path.exists():
            stat = target_path.stat()
            return {
                "exists": True,
                "size_kb": stat.st_size / 1024,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "directory": target_path.parent.as_posix(),
            }
    except Exception:
        pass

    return {"exists": False}


def disable_startup_link(lnk_path: Path) -> bool:
    """Disable a startup link by renaming it."""
    try:
        disabled_name = lnk_path.parent / (lnk_path.stem + ".disabled")
        lnk_path.rename(disabled_name)
        return True
    except Exception:
        pass

    return False


def enable_startup_link(disabled_path: Path) -> bool:
    """Re-enable a disabled startup link."""
    try:
        if ".disabled" in disabled_path.stem:
            enabled_name = disabled_path.parent / (disabled_path.stem.replace(".disabled", "") + ".lnk")
            disabled_path.rename(enabled_name)
            return True
    except Exception:
        pass

    return False


def get_startup_recommendations() -> list[str]:
    """Get recommendations for startup optimization based on links."""
    recommendations = []
    links = scan_startup_links()

    high_impact = sum(1 for link in links if link.impact == "HIGH")
    bloatware = sum(1 for link in links if link.category == "Bloatware")

    if high_impact > 3:
        recommendations.append(f"Disable {high_impact} high-impact startup items to speed up boot time")

    if bloatware > 0:
        recommendations.append(f"Found {bloatware} potential bloatware startup item(s) — safe to disable")

    return recommendations
