"""Startup Insights — detailed analysis of startup impact and recommendations."""

import subprocess
import winreg
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class StartupEntry:
    def __init__(self, name, path, impact, enabled, category):
        self.name = name
        self.path = path
        self.impact = impact  # "High", "Medium", "Low"
        self.enabled = enabled
        self.category = category  # "System", "Security", "Utility", "Game", "Other"
        self.launch_time_ms = 0
        self.memory_mb = 0


def _get_impact_score(name: str, path: str) -> str:
    """Estimate startup impact based on known patterns."""
    high_impact = {
        "nvidia", "amd", "intel", "game", "uplay", "steam", "origin",
        "antivirus", "avast", "kaspersky", "mcafee", "norton",
        "spotify", "slack", "discord", "teams", "zoom",
    }

    name_lower = name.lower()
    path_lower = path.lower()

    for keyword in high_impact:
        if keyword in name_lower or keyword in path_lower:
            return "High"

    return "Low" if "windows" not in name_lower else "Medium"


def _get_category(name: str) -> str:
    """Categorize startup entry."""
    name_lower = name.lower()

    if any(x in name_lower for x in ["nvidia", "amd", "intel", "gpu", "graphics"]):
        return "Graphics"
    elif any(x in name_lower for x in ["antivirus", "avast", "kaspersky", "mcafee", "norton", "defender"]):
        return "Security"
    elif any(x in name_lower for x in ["steam", "game", "origin", "uplay", "epic"]):
        return "Gaming"
    elif any(x in name_lower for x in ["slack", "discord", "teams", "zoom", "skype"]):
        return "Communication"
    elif any(x in name_lower for x in ["spotify", "itunes", "music", "media"]):
        return "Media"
    elif "windows" in name_lower:
        return "System"
    else:
        return "Other"


def scan_startup_with_impact() -> list[StartupEntry]:
    """Scan startup items with detailed impact analysis."""
    entries = []

    startup_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ]

    startup_folder = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    # Registry entries
    for hive, path in startup_paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        impact = _get_impact_score(name, value)
                        category = _get_category(name)

                        entries.append(StartupEntry(
                            name=name,
                            path=value,
                            impact=impact,
                            enabled=True,
                            category=category,
                        ))
                    except OSError:
                        pass
        except OSError:
            pass

    # Startup folder entries
    if startup_folder.exists():
        try:
            for item in startup_folder.iterdir():
                if item.is_file() and item.suffix in [".lnk", ".exe"]:
                    impact = _get_impact_score(item.name, str(item))
                    category = _get_category(item.name)

                    entries.append(StartupEntry(
                        name=item.name,
                        path=str(item),
                        impact=impact,
                        enabled=True,
                        category=category,
                    ))
        except (PermissionError, OSError):
            pass

    return sorted(entries, key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(x.impact, 3))


def estimate_startup_time() -> dict:
    """Estimate total startup time impact."""
    if not _PSUTIL:
        return {"estimated_ms": 0, "high_impact_count": 0}

    entries = scan_startup_with_impact()
    high_impact = [e for e in entries if e.impact == "High" and e.enabled]

    # Rough estimate: High impact = 500ms, Medium = 200ms, Low = 50ms
    total_ms = 0
    for entry in entries:
        if entry.enabled:
            if entry.impact == "High":
                total_ms += 500
            elif entry.impact == "Medium":
                total_ms += 200
            else:
                total_ms += 50

    return {
        "estimated_ms": total_ms,
        "estimated_seconds": total_ms / 1000,
        "high_impact_count": len(high_impact),
        "total_count": len(entries),
        "savings_if_disabled": sum(500 for e in high_impact),
    }


def get_startup_recommendations() -> list[str]:
    """Get recommendations for startup optimization."""
    recommendations = []
    startup_time = estimate_startup_time()
    entries = scan_startup_with_impact()

    high_impact = [e for e in entries if e.impact == "High" and e.enabled]

    if len(high_impact) > 5:
        recommendations.append(f"Disable {len(high_impact) - 3} of {len(high_impact)} high-impact programs to save ~{(len(high_impact) - 3) * 500}ms on startup")

    if startup_time["estimated_seconds"] > 30:
        recommendations.append(f"Your startup takes ~{startup_time['estimated_seconds']:.0f} seconds. Disabling high-impact items could reduce this by 50%")

    game_items = [e for e in high_impact if e.category == "Gaming"]
    if game_items:
        recommendations.append(f"Disable {len(game_items)} gaming app(s) at startup ({', '.join(e.name for e in game_items[:2])}...)")

    unnecessary = [e for e in entries if e.category == "Other" and e.impact == "Low"]
    if len(unnecessary) > 3:
        recommendations.append(f"Consider disabling {len(unnecessary)} non-essential startup items")

    return recommendations[:5]  # Top 5 recommendations


def disable_startup_entry(name: str) -> bool:
    """Disable a startup entry."""
    try:
        for hive, path in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        ]:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_WRITE) as key:
                    winreg.DeleteValue(key, name)
                    return True
            except OSError:
                pass
    except Exception:
        pass
    return False


def enable_startup_entry(name: str, path: str) -> bool:
    """Re-enable a startup entry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                           0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, path)
            return True
    except Exception:
        pass
    return False
