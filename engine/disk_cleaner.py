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


def _dir_size_and_count(folder: str) -> tuple[int, int]:
    """Single-pass: return (total_bytes, file_count). Uses scandir for speed."""
    total = 0
    count = 0
    stack = [folder]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            try:
                                total += entry.stat(follow_symlinks=False).st_size
                                count += 1
                            except OSError:
                                pass
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except OSError:
                        pass
        except OSError:
            pass
    return total, count


def _dir_size(folder: str) -> int:
    """Legacy alias kept for callers that only need bytes."""
    size, _ = _dir_size_and_count(folder)
    return size


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
    """Scan for junk files in parallel.

    Each cleaning category is scanned with a single-pass scandir walk
    (~5–10x faster than the previous double-walk via os.walk + listcomp).
    Categories scan concurrently in a thread pool.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    targets: list[tuple[str, str]] = []   # (label, path)

    # Temp folders
    for path in _get_temp_paths():
        targets.append(("Temporary Files", path))

    targets.extend(_get_browser_cache_paths())
    targets.extend(_get_app_cache_paths())
    for label, path in _get_windows_log_paths():
        if os.path.isdir(path):
            targets.append((label, path))

    # Deduplicate by path
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for label, path in targets:
        norm = os.path.normpath(path)
        if norm in seen:
            continue
        seen.add(norm)
        unique.append((label, path))

    results: list[ScanResult] = []

    def scan_one(item):
        label, path = item
        if progress_cb:
            try: progress_cb(f"Scanning {label}")
            except Exception: pass
        size, count = _dir_size_and_count(path)
        return label, path, size, count

    with ThreadPoolExecutor(max_workers=min(8, len(unique) or 1)) as ex:
        for fut in as_completed(ex.submit(scan_one, t) for t in unique):
            try:
                label, path, size, count = fut.result()
                if size > 0 or count > 0:
                    results.append(ScanResult(label, path, size, count))
            except Exception:
                pass

    # Sort by size desc for the UI
    results.sort(key=lambda r: r.size, reverse=True)
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
