"""Disk cleanup engine — scans and removes junk files."""

import os
import stat
import ctypes
import time
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def _format_size(bytes_: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


def _safe_delete(path: str) -> bool:
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        os.remove(path)
        return True
    except Exception:
        return False


def _dir_size(folder: str) -> int:
    total = 0
    try:
        for root, _dirs, files in os.walk(folder):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


# ── scan targets ─────────────────────────────────────────────────────────────

def _get_temp_paths() -> list[str]:
    appdata_local = os.environ.get("LOCALAPPDATA", "")
    paths = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        r"C:\Windows\Temp",
        os.path.join(appdata_local, "Temp"),
        r"C:\Windows\Prefetch",
    ]
    return [p for p in paths if p and os.path.isdir(p)]


def _get_browser_cache_paths() -> list[tuple[str, str]]:
    """Return (label, path) pairs for browser caches and storage."""
    home = Path.home()
    candidates = [
        ("Chrome Cache",      home / "AppData/Local/Google/Chrome/User Data/Default/Cache"),
        ("Chrome Code Cache", home / "AppData/Local/Google/Chrome/User Data/Default/Code Cache"),
        ("Chrome Storage",    home / "AppData/Local/Google/Chrome/User Data/Default/Cache"),
        ("Edge Cache",        home / "AppData/Local/Microsoft/Edge/User Data/Default/Cache"),
        ("Edge Code Cache",   home / "AppData/Local/Microsoft/Edge/User Data/Default/Code Cache"),
        ("Firefox Cache",     home / "AppData/Local/Mozilla/Firefox/Profiles"),
        ("IE Cache",          home / "AppData/Local/Microsoft/Windows/INetCache"),
        ("IE Cookies",        home / "AppData/Roaming/Microsoft/Windows/Cookies"),
    ]
    result = []
    for label, path in candidates:
        if label == "Firefox Cache":
            # enumerate actual profile folders
            if path.exists():
                for profile in path.iterdir():
                    cache = profile / "cache2"
                    if cache.is_dir():
                        result.append((f"Firefox ({profile.name})", str(cache)))
        else:
            if Path(path).is_dir():
                result.append((label, str(path)))
    return result


def _get_app_cache_paths() -> list[tuple[str, str]]:
    """Return (label, path) pairs for application-specific caches."""
    home = Path.home()
    appdata_local = os.environ.get("LOCALAPPDATA", "")
    appdata_roaming = os.environ.get("APPDATA", "")

    candidates = [
        ("VS Code Cache",         Path(appdata_local) / "Code" / "Cache"),
        ("VS Code Extensions",    Path(appdata_local) / "Code" / "CachedData"),
        ("Node npm Cache",        Path(appdata_local) / "npm-cache"),
        ("Node Yarn Cache",       home / ".yarn" / "cache"),
        ("Python pip Cache",      Path(appdata_local) / "pip" / "cache"),
        ("Java Cache",            home / ".java" / "deployment" / "cache"),
        ("Git Repo Cache",        home / ".git" / "objects"),
        ("Chocolatey Cache",      r"C:\ProgramData\chocolatey\cache"),
        ("Windows Update Cache",  r"C:\Windows\SoftwareDistribution\Download"),
        ("Windows Install Cache", Path(appdata_local) / "Temp"),
    ]

    result = []
    for label, path in candidates:
        if isinstance(path, str):
            path = Path(path)
        if path.exists() and path.is_dir():
            result.append((label, str(path)))
    return result


def _get_windows_log_paths() -> list[tuple[str, str]]:
    appdata_local = os.environ.get("LOCALAPPDATA", "")
    return [
        ("Windows Error Reports", r"C:\ProgramData\Microsoft\Windows\WER\ReportArchive"),
        ("User Crash Dumps",      os.path.join(appdata_local, "CrashDumps")),
        ("Windows CBS Logs",      r"C:\Windows\Logs\CBS"),
    ]


# ── public scan API ───────────────────────────────────────────────────────────

class ScanResult:
    def __init__(self, label: str, path: str, size: int, file_count: int):
        self.label = label
        self.path = path
        self.size = size
        self.file_count = file_count
        self.size_str = _format_size(size)
        self.selected = True  # default: user wants to clean this


def scan_junk(progress_cb=None) -> list[ScanResult]:
    """
    Scan for junk files. progress_cb(label) called for each category.
    Returns list of ScanResult objects.
    """
    results = []

    # Temp folders
    for path in _get_temp_paths():
        if progress_cb:
            progress_cb(f"Scanning temp: {path}")
        size = _dir_size(path)
        count = sum(len(files) for _, _, files in os.walk(path))
        if size > 0 or count > 0:
            results.append(ScanResult("Temporary Files", path, size, count))

    # Browser caches
    for label, path in _get_browser_cache_paths():
        if progress_cb:
            progress_cb(f"Scanning {label}")
        size = _dir_size(path)
        count = sum(len(files) for _, _, files in os.walk(path))
        if size > 0:
            results.append(ScanResult(label, path, size, count))

    # Application-specific caches
    for label, path in _get_app_cache_paths():
        if progress_cb:
            progress_cb(f"Scanning {label}")
        size = _dir_size(path)
        count = sum(len(files) for _, _, files in os.walk(path))
        if size > 0:
            results.append(ScanResult(label, path, size, count))

    # Windows logs
    for label, path in _get_windows_log_paths():
        if progress_cb:
            progress_cb(f"Scanning {label}")
        if os.path.isdir(path):
            size = _dir_size(path)
            count = sum(len(files) for _, _, files in os.walk(path))
            if size > 0:
                results.append(ScanResult(label, path, size, count))

    return results


# ── clean ─────────────────────────────────────────────────────────────────────

def clean_folder(path: str, min_age_hours: float = 0, progress_cb=None) -> tuple[int, int]:
    """
    Delete files in folder. Returns (bytes_freed, files_deleted).
    min_age_hours: skip files newer than this (0 = delete all).
    """
    cutoff = time.time() - min_age_hours * 3600
    freed = 0
    deleted = 0

    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if min_age_hours > 0 and os.path.getmtime(fp) > cutoff:
                    continue
                size = os.path.getsize(fp)
                if progress_cb:
                    progress_cb(fp)
                if _safe_delete(fp):
                    freed += size
                    deleted += 1
            except OSError:
                pass
        # try to remove empty dirs
        for d in dirs:
            dp = os.path.join(root, d)
            try:
                os.rmdir(dp)
            except OSError:
                pass

    return freed, deleted


def empty_recycle_bin() -> bool:
    try:
        # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND = 7
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        return True
    except Exception:
        return False


def get_recycle_bin_size() -> int:
    total = 0
    for drive_letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        rb = f"{drive_letter}:\\$Recycle.Bin"
        if os.path.isdir(rb):
            total += _dir_size(rb)
    return total
