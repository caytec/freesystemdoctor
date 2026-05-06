"""Browser History Manager — clear history, cookies, cache across all browsers."""

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

_LOCAL = Path(os.environ.get("LOCALAPPDATA", ""))
_ROAMING = Path(os.environ.get("APPDATA", ""))

BROWSERS = {
    "Chrome": {
        "base": _LOCAL / "Google" / "Chrome" / "User Data",
        "profiles": ["Default"],
        "items": {
            "History": {"path": "History", "type": "sqlite", "table": "urls"},
            "Cache": {"path": "Cache", "type": "dir"},
            "Code Cache": {"path": "Code Cache", "type": "dir"},
            "Cookies": {"path": "Cookies", "type": "file"},
            "Saved Passwords": {"path": "Login Data", "type": "file"},
            "Download History": {"path": "History", "type": "sqlite", "table": "downloads"},
            "Autofill": {"path": "Web Data", "type": "file"},
        },
    },
    "Edge": {
        "base": _LOCAL / "Microsoft" / "Edge" / "User Data",
        "profiles": ["Default"],
        "items": {
            "History": {"path": "History", "type": "sqlite", "table": "urls"},
            "Cache": {"path": "Cache", "type": "dir"},
            "Code Cache": {"path": "Code Cache", "type": "dir"},
            "Cookies": {"path": "Cookies", "type": "file"},
            "Saved Passwords": {"path": "Login Data", "type": "file"},
        },
    },
    "Firefox": {
        "base": _ROAMING / "Mozilla" / "Firefox" / "Profiles",
        "profiles": None,  # auto-detect
        "items": {
            "History": {"path": "places.sqlite", "type": "file"},
            "Cache": {"path": "cache2", "type": "dir"},
            "Cookies": {"path": "cookies.sqlite", "type": "file"},
            "Saved Passwords": {"path": "logins.json", "type": "file"},
            "Session": {"path": "sessionstore-backups", "type": "dir"},
        },
    },
}


def _get_profiles(browser: str) -> list[Path]:
    cfg = BROWSERS.get(browser, {})
    base = cfg.get("base", Path())
    profiles_list = cfg.get("profiles")

    if not base.exists():
        return []

    if profiles_list is None:
        # Firefox — enumerate profile dirs
        return [d for d in base.iterdir() if d.is_dir()]

    # Chrome/Edge — Default + Profile N
    result = []
    for name in profiles_list:
        p = base / name
        if p.exists():
            result.append(p)
    # Also scan Profile 1, Profile 2, etc.
    for d in base.iterdir():
        if d.is_dir() and d.name.startswith("Profile "):
            result.append(d)
    return result


def _item_size(profile_dir: Path, item: dict) -> int:
    path = profile_dir / item["path"]
    if not path.exists():
        return 0
    if item["type"] == "dir":
        total = 0
        for f in path.rglob("*"):
            try:
                if f.is_file():
                    total += f.stat().st_size
            except OSError:
                pass
        return total
    try:
        return path.stat().st_size
    except OSError:
        return 0


def scan_browser_data() -> list[dict]:
    """Scan all browsers and return list of cleanable items with sizes."""
    results = []
    for browser, cfg in BROWSERS.items():
        profiles = _get_profiles(browser)
        for profile_dir in profiles:
            for item_name, item_cfg in cfg["items"].items():
                size = _item_size(profile_dir, item_cfg)
                results.append({
                    "browser": browser,
                    "profile": profile_dir.name,
                    "item": item_name,
                    "size": size,
                    "size_str": _fmt_bytes(size),
                    "path": str(profile_dir / item_cfg["path"]),
                    "type": item_cfg["type"],
                    "selected": True,
                })
    return results


def clear_item(item: dict) -> tuple[bool, int]:
    """Clear a single browser data item. Returns (success, bytes_freed)."""
    path = Path(item["path"])
    size = item["size"]

    if not path.exists():
        return True, 0

    try:
        if item["type"] == "dir":
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(exist_ok=True)
        elif item["type"] in ("file", "sqlite"):
            path.unlink(missing_ok=True)
        return True, size
    except Exception:
        return False, 0


def clear_selected(items: list[dict]) -> tuple[int, int]:
    """Clear all selected items. Returns (bytes_freed, error_count)."""
    total_freed = 0
    errors = 0
    for item in items:
        if not item.get("selected", False):
            continue
        ok, freed = clear_item(item)
        if ok:
            total_freed += freed
        else:
            errors += 1
    return total_freed, errors


def get_browser_summary() -> dict[str, dict]:
    """Return per-browser summary of total cleanable data."""
    items = scan_browser_data()
    summary = {}
    for item in items:
        b = item["browser"]
        if b not in summary:
            summary[b] = {"total_size": 0, "item_count": 0, "detected": True}
        summary[b]["total_size"] += item["size"]
        summary[b]["item_count"] += 1
    return summary


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
