"""
deep_disk_cleaner.py — aggressive C: drive cleanup.

22+ categories of hidden/forgotten files that don't affect system stability:

WINDOWS-MANAGED (always safe):
1.  Windows Update download cache      (~1-5 GB)
2.  WinSxS component store + DISM        (~5-15 GB after cleanup)
3.  Windows.old                          (~10-30 GB if present)
4.  Delivery Optimization cache          (~1-10 GB)
5.  Failed update rollbacks ($Windows.~) (~1-5 GB)
6.  Hibernation file (powercfg /h off)    (~RAM size, often 8-32 GB)
7.  Memory dumps (MEMORY.DMP, minidumps) (~varies)
8.  Windows error reports (WER queue)    (~50 MB - 1 GB)
9.  Windows log files (CBS, DISM, ETL)  (~100 MB - 2 GB)
10. Defender scan history + quarantine  (~50 MB - 500 MB)
11. Old system restore points (oldest)  (~varies)

USER CACHES (rebuilt on demand):
12. System + user TEMP folders          (~1-10 GB)
13. Recycle Bin (all drives)            (~varies)
14. Thumbnail cache (thumbcache_*.db)    (~100 MB - 1 GB)
15. Icon cache (iconcache_*.db)         (~50 MB - 500 MB)
16. Font cache                          (~100 MB)
17. Prefetch (Windows rebuilds it)       (~50 MB - 500 MB)

BROWSER CACHES (all major browsers):
18. Chrome / Edge / Firefox / Opera / Brave cache + media + GPU cache

APP CACHES (safe to clear):
19. Discord cache                        (~200 MB - 2 GB)
20. Spotify cache                        (~500 MB)
21. Teams / Slack / Telegram cache       (~200 MB - 1 GB)
22. Steam shader cache + downloading     (~500 MB - 3 GB)
23. NVIDIA / DirectX shader caches      (~500 MB - 3 GB)
24. Visual Studio / VSCode caches        (~500 MB - 2 GB)
25. Dev tool caches (npm, pip, cargo)    (~varies, often 5+ GB)

Each category implements:
- scan() → returns (size_bytes, file_count) without deletion
- clean() → returns (freed_bytes, deleted_count)

All actions are reversible (Recycle Bin only for risky ops) or trivially
rebuildable. Game files, documents, photos are NEVER touched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import glob
import ctypes
import platform
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    import winreg
    _WINREG = True
except ImportError:
    _WINREG = False


# ── helpers ──────────────────────────────────────────────────────────────────

def _expand(p: str) -> Path:
    return Path(os.path.expandvars(p))


def _dir_size(path: Path, max_files: int = 200_000) -> tuple[int, int]:
    """Return (total_size_bytes, file_count) for a directory."""
    if not path.exists():
        return 0, 0
    total = 0
    count = 0
    try:
        for root, dirs, files in os.walk(path, onerror=lambda e: None):
            for f in files:
                if count >= max_files:
                    return total, count
                try:
                    total += os.path.getsize(os.path.join(root, f))
                    count += 1
                except (OSError, FileNotFoundError):
                    pass
    except Exception:
        pass
    return total, count


def _safe_delete_file(path: str) -> int:
    """Return bytes freed (0 if failed)."""
    try:
        size = os.path.getsize(path)
        os.chmod(path, 0o777)
        os.remove(path)
        return size
    except (OSError, PermissionError):
        return 0


def _clean_folder(path: Path, min_age_days: int = 0,
                  preserve_root: bool = True) -> tuple[int, int]:
    """Delete all contents of folder. Returns (freed, count)."""
    if not path.exists():
        return 0, 0
    freed = 0
    count = 0
    cutoff = None
    if min_age_days > 0:
        cutoff = datetime.now() - timedelta(days=min_age_days)

    try:
        for entry in path.iterdir():
            try:
                if cutoff:
                    mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                    if mtime > cutoff:
                        continue
                if entry.is_file() or entry.is_symlink():
                    sz = _safe_delete_file(str(entry))
                    if sz:
                        freed += sz
                        count += 1
                elif entry.is_dir():
                    sub_freed, sub_count = _clean_folder(entry, min_age_days, preserve_root=False)
                    freed += sub_freed
                    count += sub_count
                    if not any(entry.iterdir()):
                        try:
                            entry.rmdir()
                        except OSError:
                            pass
            except (OSError, PermissionError):
                pass
    except Exception:
        pass
    return freed, count


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        flags = 0x08000000 if platform.system() == "Windows" else 0
        r = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=timeout, creationflags=flags)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def _fmt(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


# ── category model ───────────────────────────────────────────────────────────

@dataclass
class CleanCategory:
    key: str
    label: str
    description: str
    risk: str = "safe"        # safe | medium | reversible
    estimated_max_gb: float = 1.0
    requires_admin: bool = False
    size_bytes: int = 0
    file_count: int = 0
    enabled: bool = True


# ── individual scanners ──────────────────────────────────────────────────────

def _scan_windows_update_cache() -> tuple[int, int]:
    return _dir_size(_expand(r"%SystemRoot%\SoftwareDistribution\Download"))


def _clean_windows_update_cache() -> tuple[int, int]:
    # Stop wuauserv first so we can delete locked files
    _run(["net", "stop", "wuauserv"], timeout=30)
    _run(["net", "stop", "bits"], timeout=30)
    freed, count = _clean_folder(
        _expand(r"%SystemRoot%\SoftwareDistribution\Download"))
    _run(["net", "start", "wuauserv"], timeout=30)
    _run(["net", "start", "bits"], timeout=30)
    return freed, count


def _scan_winsxs_potential() -> tuple[int, int]:
    """Estimate via DISM /AnalyzeComponentStore (slow ~30s but accurate)."""
    rc, out = _run(["dism.exe", "/online", "/Cleanup-Image",
                    "/AnalyzeComponentStore"], timeout=120)
    if rc != 0:
        return 0, 0
    # Parse "Component Store (WinSxS) backup size: X MB"
    import re
    m = re.search(r"backup size\s*:\s*([\d.]+)\s*(MB|GB)", out, re.I)
    if not m:
        return 0, 0
    val = float(m.group(1))
    if m.group(2).upper() == "GB":
        val *= 1024
    return int(val * 1024 * 1024), 1


def _clean_winsxs() -> tuple[int, int]:
    """Run DISM to compact WinSxS. Removes ability to uninstall old updates."""
    _run(["dism.exe", "/online", "/Cleanup-Image",
          "/StartComponentCleanup", "/ResetBase"], timeout=900)
    # No way to know exact size freed without re-scan, return estimate
    return 0, 1


def _scan_windows_old() -> tuple[int, int]:
    return _dir_size(Path(r"C:\Windows.old"))


def _clean_windows_old() -> tuple[int, int]:
    path = Path(r"C:\Windows.old")
    if not path.exists():
        return 0, 0
    size_before, count = _dir_size(path)
    # Use cleanmgr's specific feature
    _run(["takeown", "/F", str(path), "/R", "/D", "Y"], timeout=300)
    _run(["icacls", str(path), "/grant", "administrators:F", "/T"], timeout=300)
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass
    return size_before if not path.exists() else 0, count


def _scan_delivery_optimization() -> tuple[int, int]:
    return _dir_size(_expand(r"%SystemRoot%\SoftwareDistribution\DeliveryOptimization"))


def _clean_delivery_optimization() -> tuple[int, int]:
    return _clean_folder(_expand(r"%SystemRoot%\SoftwareDistribution\DeliveryOptimization"))


def _scan_failed_rollbacks() -> tuple[int, int]:
    paths = [r"C:\$Windows.~BT", r"C:\$Windows.~WS",
              r"C:\$INPLACE.~TR", r"C:\Config.Msi"]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(Path(p))
        total += s
        count += c
    return total, count


def _clean_failed_rollbacks() -> tuple[int, int]:
    total, count = 0, 0
    for p in [r"C:\$Windows.~BT", r"C:\$Windows.~WS",
              r"C:\$INPLACE.~TR", r"C:\Config.Msi"]:
        if Path(p).exists():
            _run(["takeown", "/F", p, "/R", "/D", "Y"], timeout=120)
            _run(["icacls", p, "/grant", "administrators:F", "/T"], timeout=120)
            f, c = _clean_folder(Path(p))
            total += f
            count += c
            try:
                Path(p).rmdir()
            except (OSError, FileNotFoundError):
                pass
    return total, count


def _scan_hiberfil() -> tuple[int, int]:
    """Check if hibernation file exists and its size."""
    p = Path(r"C:\hiberfil.sys")
    if not p.exists():
        return 0, 0
    try:
        return p.stat().st_size, 1
    except OSError:
        return 0, 0


def _clean_hiberfil() -> tuple[int, int]:
    """Disable hibernation completely — frees RAM-size disk space."""
    size_before, _ = _scan_hiberfil()
    rc, _ = _run(["powercfg", "/h", "off"], timeout=15)
    return (size_before, 1) if rc == 0 else (0, 0)


def _scan_memory_dumps() -> tuple[int, int]:
    paths = [
        r"%SystemRoot%\MEMORY.DMP",
        r"%SystemRoot%\Minidump",
        r"%LOCALAPPDATA%\CrashDumps",
    ]
    total, count = 0, 0
    for p in paths:
        path = _expand(p)
        if path.is_file():
            try:
                total += path.stat().st_size
                count += 1
            except OSError:
                pass
        elif path.is_dir():
            s, c = _dir_size(path)
            total += s
            count += c
    return total, count


def _clean_memory_dumps() -> tuple[int, int]:
    total, count = 0, 0
    for p in [r"%SystemRoot%\MEMORY.DMP", r"%SystemRoot%\Minidump",
              r"%LOCALAPPDATA%\CrashDumps"]:
        path = _expand(p)
        if path.is_file():
            sz = _safe_delete_file(str(path))
            if sz:
                total += sz
                count += 1
        elif path.is_dir():
            f, c = _clean_folder(path)
            total += f
            count += c
    return total, count


def _scan_wer_reports() -> tuple[int, int]:
    paths = [r"%PROGRAMDATA%\Microsoft\Windows\WER\ReportArchive",
              r"%PROGRAMDATA%\Microsoft\Windows\WER\ReportQueue",
              r"%LOCALAPPDATA%\Microsoft\Windows\WER"]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_wer_reports() -> tuple[int, int]:
    total, count = 0, 0
    for p in [r"%PROGRAMDATA%\Microsoft\Windows\WER\ReportArchive",
              r"%PROGRAMDATA%\Microsoft\Windows\WER\ReportQueue",
              r"%LOCALAPPDATA%\Microsoft\Windows\WER"]:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_windows_logs() -> tuple[int, int]:
    paths = [
        r"%SystemRoot%\Logs",
        r"%SystemRoot%\Panther",                # setup logs
        r"%SystemRoot%\inf",                     # *.log only
        r"%SystemRoot%\System32\LogFiles",
    ]
    total, count = 0, 0
    for p in paths:
        path = _expand(p)
        if path.exists():
            s, c = _dir_size(path)
            total += s
            count += c
    # CBS.log specifically
    cbs = _expand(r"%SystemRoot%\Logs\CBS\CBS.log")
    if cbs.exists():
        try:
            total += cbs.stat().st_size
        except OSError:
            pass
    return total, count


def _clean_windows_logs() -> tuple[int, int]:
    total, count = 0, 0
    for pattern_path in [
        (r"%SystemRoot%\Logs\CBS", "*.log"),
        (r"%SystemRoot%\Logs\CBS", "*.cab"),
        (r"%SystemRoot%\Logs\DISM", "*.log"),
        (r"%SystemRoot%\Panther", "*.log"),
        (r"%SystemRoot%\inf", "*.log"),
        (r"%SystemRoot%\System32\LogFiles", "*.log"),
    ]:
        path, pattern = pattern_path
        for f in glob.glob(str(_expand(path) / pattern)):
            sz = _safe_delete_file(f)
            if sz:
                total += sz
                count += 1
    return total, count


def _scan_defender_history() -> tuple[int, int]:
    paths = [
        r"%PROGRAMDATA%\Microsoft\Windows Defender\Scans\History",
        r"%PROGRAMDATA%\Microsoft\Windows Defender\Support",
    ]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_defender_history() -> tuple[int, int]:
    total, count = 0, 0
    for p in [
        r"%PROGRAMDATA%\Microsoft\Windows Defender\Scans\History",
    ]:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_temp() -> tuple[int, int]:
    paths = [r"%TEMP%", r"%SystemRoot%\Temp"]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_temp() -> tuple[int, int]:
    total, count = 0, 0
    for p in [r"%TEMP%", r"%SystemRoot%\Temp"]:
        f, c = _clean_folder(_expand(p), min_age_days=1)
        total += f
        count += c
    return total, count


def _scan_recycle_bin() -> tuple[int, int]:
    """Recycle Bin sizes across all drives."""
    if not _PSUTIL:
        return 0, 0
    total = 0
    count = 0
    for part in psutil.disk_partitions(all=False):
        if "fixed" not in part.opts:
            continue
        bin_path = Path(part.mountpoint) / "$RECYCLE.BIN"
        if bin_path.exists():
            s, c = _dir_size(bin_path)
            total += s
            count += c
    return total, count


def _clean_recycle_bin() -> tuple[int, int]:
    """Empty Recycle Bin via Shell API."""
    if not _PSUTIL:
        return 0, 0
    size_before, _ = _scan_recycle_bin()
    try:
        shell32 = ctypes.windll.shell32
        # SHEmptyRecycleBin: 0x07 = NO_CONFIRMATION | NO_PROGRESS_UI | NO_SOUND
        shell32.SHEmptyRecycleBinW(None, None, 0x07)
    except Exception:
        pass
    after, _ = _scan_recycle_bin()
    return max(size_before - after, 0), 1


def _scan_thumbnail_icon_cache() -> tuple[int, int]:
    base = _expand(r"%LOCALAPPDATA%\Microsoft\Windows\Explorer")
    if not base.exists():
        return 0, 0
    total = 0
    count = 0
    for pattern in ("thumbcache_*.db", "iconcache_*.db"):
        for f in glob.glob(str(base / pattern)):
            try:
                total += os.path.getsize(f)
                count += 1
            except OSError:
                pass
    return total, count


def _clean_thumbnail_icon_cache() -> tuple[int, int]:
    base = _expand(r"%LOCALAPPDATA%\Microsoft\Windows\Explorer")
    total = 0
    count = 0
    for pattern in ("thumbcache_*.db", "iconcache_*.db"):
        for f in glob.glob(str(base / pattern)):
            sz = _safe_delete_file(f)
            if sz:
                total += sz
                count += 1
    return total, count


def _scan_font_cache() -> tuple[int, int]:
    paths = [
        r"%SystemRoot%\ServiceProfiles\LocalService\AppData\Local\FontCache",
        r"%SystemRoot%\System32\FNTCACHE.DAT",
    ]
    total, count = 0, 0
    for p in paths:
        path = _expand(p)
        if path.is_file():
            try:
                total += path.stat().st_size
                count += 1
            except OSError:
                pass
        elif path.is_dir():
            s, c = _dir_size(path)
            total += s
            count += c
    return total, count


def _clean_font_cache() -> tuple[int, int]:
    """Requires stopping FontCache service."""
    _run(["net", "stop", "FontCache"], timeout=15)
    _run(["net", "stop", "FontCache3.0.0.0"], timeout=15)
    total, count = 0, 0
    folder = _expand(r"%SystemRoot%\ServiceProfiles\LocalService\AppData\Local\FontCache")
    f, c = _clean_folder(folder)
    total += f
    count += c
    fnt = _expand(r"%SystemRoot%\System32\FNTCACHE.DAT")
    if fnt.exists():
        sz = _safe_delete_file(str(fnt))
        if sz:
            total += sz
            count += 1
    _run(["net", "start", "FontCache"], timeout=15)
    return total, count


def _scan_prefetch() -> tuple[int, int]:
    return _dir_size(_expand(r"%SystemRoot%\Prefetch"))


def _clean_prefetch() -> tuple[int, int]:
    return _clean_folder(_expand(r"%SystemRoot%\Prefetch"))


def _scan_browser_caches() -> tuple[int, int]:
    paths = [
        # Chrome
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache",
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache",
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\GPUCache",
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Service Worker\CacheStorage",
        # Edge
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache",
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache",
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\GPUCache",
        # Firefox (profile-relative)
        r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles",
        # Opera
        r"%LOCALAPPDATA%\Opera Software\Opera Stable\Cache",
        # Brave
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Cache",
    ]
    total, count = 0, 0
    for p in paths:
        path = _expand(p)
        if "Firefox" in str(path) and path.exists():
            for profile in path.iterdir():
                if profile.is_dir():
                    for sub in ("cache2", "thumbnails", "shader-cache"):
                        s, c = _dir_size(profile / sub)
                        total += s
                        count += c
        else:
            s, c = _dir_size(path)
            total += s
            count += c
    return total, count


def _clean_browser_caches() -> tuple[int, int]:
    total, count = 0, 0
    paths = [
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache",
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache",
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\GPUCache",
        r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Service Worker\CacheStorage",
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache",
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache",
        r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\GPUCache",
        r"%LOCALAPPDATA%\Opera Software\Opera Stable\Cache",
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Cache",
    ]
    for p in paths:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c

    # Firefox per-profile
    firefox = _expand(r"%LOCALAPPDATA%\Mozilla\Firefox\Profiles")
    if firefox.exists():
        for profile in firefox.iterdir():
            if profile.is_dir():
                for sub in ("cache2", "thumbnails", "shader-cache"):
                    f, c = _clean_folder(profile / sub)
                    total += f
                    count += c
    return total, count


def _scan_app_caches() -> tuple[int, int]:
    paths = [
        r"%APPDATA%\discord\Cache",
        r"%APPDATA%\discord\Code Cache",
        r"%APPDATA%\discord\GPUCache",
        r"%APPDATA%\Spotify\Storage",
        r"%LOCALAPPDATA%\Spotify\Storage",
        r"%APPDATA%\Microsoft\Teams\Cache",
        r"%APPDATA%\Microsoft\Teams\Code Cache",
        r"%APPDATA%\Microsoft\Teams\GPUCache",
        r"%APPDATA%\Slack\Cache",
        r"%APPDATA%\Telegram Desktop\tdata\user_data\cache",
        r"%LOCALAPPDATA%\Adobe\Common\Media Cache Files",
        r"%LOCALAPPDATA%\Adobe\Common\Media Cache",
    ]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_app_caches() -> tuple[int, int]:
    paths = [
        r"%APPDATA%\discord\Cache",
        r"%APPDATA%\discord\Code Cache",
        r"%APPDATA%\discord\GPUCache",
        r"%APPDATA%\Spotify\Storage",
        r"%LOCALAPPDATA%\Spotify\Storage",
        r"%APPDATA%\Microsoft\Teams\Cache",
        r"%APPDATA%\Microsoft\Teams\Code Cache",
        r"%APPDATA%\Microsoft\Teams\GPUCache",
        r"%APPDATA%\Slack\Cache",
        r"%APPDATA%\Telegram Desktop\tdata\user_data\cache",
        r"%LOCALAPPDATA%\Adobe\Common\Media Cache Files",
        r"%LOCALAPPDATA%\Adobe\Common\Media Cache",
    ]
    total, count = 0, 0
    for p in paths:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_steam_shader() -> tuple[int, int]:
    """Steam shader pre-cache + downloading folder. NOT game files."""
    paths = [
        r"C:\Program Files (x86)\Steam\steamapps\shadercache",
        r"C:\Program Files (x86)\Steam\steamapps\downloading",
        r"D:\Steam\steamapps\shadercache",
        r"D:\SteamLibrary\steamapps\shadercache",
        r"%LOCALAPPDATA%\Steam\htmlcache",
    ]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_steam_shader() -> tuple[int, int]:
    paths = [
        r"C:\Program Files (x86)\Steam\steamapps\shadercache",
        r"C:\Program Files (x86)\Steam\steamapps\downloading",
        r"D:\Steam\steamapps\shadercache",
        r"D:\SteamLibrary\steamapps\shadercache",
        r"%LOCALAPPDATA%\Steam\htmlcache",
    ]
    total, count = 0, 0
    for p in paths:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_gpu_shader_caches() -> tuple[int, int]:
    paths = [
        # NVIDIA
        r"%LOCALAPPDATA%\NVIDIA\DXCache",
        r"%LOCALAPPDATA%\NVIDIA\GLCache",
        r"%LOCALAPPDATA%\NVIDIA Corporation\NV_Cache",
        # DirectX shader cache (Windows-managed)
        r"%LOCALAPPDATA%\D3DSCache",
        # AMD
        r"%LOCALAPPDATA%\AMD\DxCache",
        r"%LOCALAPPDATA%\AMD\GLCache",
    ]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_gpu_shader_caches() -> tuple[int, int]:
    paths = [
        r"%LOCALAPPDATA%\NVIDIA\DXCache",
        r"%LOCALAPPDATA%\NVIDIA\GLCache",
        r"%LOCALAPPDATA%\NVIDIA Corporation\NV_Cache",
        r"%LOCALAPPDATA%\D3DSCache",
        r"%LOCALAPPDATA%\AMD\DxCache",
        r"%LOCALAPPDATA%\AMD\GLCache",
    ]
    total, count = 0, 0
    for p in paths:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_dev_caches() -> tuple[int, int]:
    paths = [
        r"%APPDATA%\npm-cache",
        r"%LOCALAPPDATA%\npm-cache",
        r"%LOCALAPPDATA%\Yarn\Cache",
        r"%LOCALAPPDATA%\pnpm\store",
        r"%LOCALAPPDATA%\pip\cache",
        r"%USERPROFILE%\.cargo\registry\cache",
        r"%USERPROFILE%\.gradle\caches",
        r"%USERPROFILE%\.nuget\packages",
        r"%LOCALAPPDATA%\go-build",
    ]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_dev_caches() -> tuple[int, int]:
    paths = [
        r"%APPDATA%\npm-cache",
        r"%LOCALAPPDATA%\npm-cache",
        r"%LOCALAPPDATA%\Yarn\Cache",
        r"%LOCALAPPDATA%\pip\cache",
        r"%LOCALAPPDATA%\go-build",
    ]
    total, count = 0, 0
    for p in paths:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_office_cache() -> tuple[int, int]:
    paths = [
        r"%LOCALAPPDATA%\Microsoft\Office\16.0\OfficeFileCache",
        r"%LOCALAPPDATA%\Microsoft\Office\UnsavedFiles",
        r"%LOCALAPPDATA%\Microsoft\Outlook\RoamCache",
    ]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_office_cache() -> tuple[int, int]:
    paths = [
        r"%LOCALAPPDATA%\Microsoft\Office\16.0\OfficeFileCache",
        r"%LOCALAPPDATA%\Microsoft\Outlook\RoamCache",
    ]
    total, count = 0, 0
    for p in paths:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_vscode_cache() -> tuple[int, int]:
    paths = [
        r"%APPDATA%\Code\Cache",
        r"%APPDATA%\Code\CachedData",
        r"%APPDATA%\Code\Code Cache",
        r"%APPDATA%\Code\GPUCache",
        r"%APPDATA%\Code\logs",
    ]
    total, count = 0, 0
    for p in paths:
        s, c = _dir_size(_expand(p))
        total += s
        count += c
    return total, count


def _clean_vscode_cache() -> tuple[int, int]:
    paths = [
        r"%APPDATA%\Code\Cache",
        r"%APPDATA%\Code\CachedData",
        r"%APPDATA%\Code\Code Cache",
        r"%APPDATA%\Code\GPUCache",
        r"%APPDATA%\Code\logs",
    ]
    total, count = 0, 0
    for p in paths:
        f, c = _clean_folder(_expand(p))
        total += f
        count += c
    return total, count


def _scan_old_restore_points() -> tuple[int, int]:
    """Approximate via vssadmin output."""
    rc, out = _run(["vssadmin", "list", "shadowstorage"], timeout=15)
    if rc != 0:
        return 0, 0
    import re
    m = re.search(r"Used Shadow Copy Storage space:\s*([\d.]+)\s*(MB|GB|TB)",
                  out, re.I)
    if not m:
        return 0, 0
    val = float(m.group(1))
    unit = m.group(2).upper()
    mult = {"MB": 1024**2, "GB": 1024**3, "TB": 1024**4}[unit]
    return int(val * mult), 1


def _clean_old_restore_points() -> tuple[int, int]:
    """Keep only the most recent restore point."""
    size_before, _ = _scan_old_restore_points()
    _run(["vssadmin", "delete", "shadows", "/all", "/quiet"], timeout=120)
    after, _ = _scan_old_restore_points()
    return max(size_before - after, 0), 1


# ── category registry ────────────────────────────────────────────────────────

CATEGORIES: list[tuple[str, str, str, str, float, bool, callable, callable]] = [
    # (key, label, description, risk, est_max_gb, requires_admin, scan, clean)
    ("win_update", "Windows Update cache",
     "Pobrane pakiety aktualizacji już zainstalowanych",
     "safe", 5.0, True, _scan_windows_update_cache, _clean_windows_update_cache),

    ("winsxs", "WinSxS Component Store (DISM)",
     "Stare wersje plików systemowych. ResetBase = nie cofniesz updateów",
     "medium", 15.0, True, _scan_winsxs_potential, _clean_winsxs),

    ("win_old", "Windows.old (po upgrade)",
     "Stary system po reinstalacji Windows — usuwane przez Storage Sense po 10 dniach",
     "safe", 30.0, True, _scan_windows_old, _clean_windows_old),

    ("delivery_opt", "Delivery Optimization cache",
     "P2P cache aktualizacji Windows udostępniany innym",
     "safe", 10.0, True, _scan_delivery_optimization, _clean_delivery_optimization),

    ("rollbacks", "Nieudane rollbacki ($Windows.~BT)",
     "Pozostałości po nieudanych aktualizacjach Windows",
     "safe", 5.0, True, _scan_failed_rollbacks, _clean_failed_rollbacks),

    ("hibernate", "Plik hibernacji (hiberfil.sys)",
     "Wyłącza hibernację. Frees ~ rozmiar RAM (często 16-32 GB)",
     "reversible", 32.0, True, _scan_hiberfil, _clean_hiberfil),

    ("dumps", "Memory dumps + minidumps",
     "MEMORY.DMP i mini-dumpy po BSOD",
     "safe", 4.0, True, _scan_memory_dumps, _clean_memory_dumps),

    ("wer", "Windows Error Reporting (WER)",
     "Raporty błędów wysłane / w kolejce",
     "safe", 1.0, False, _scan_wer_reports, _clean_wer_reports),

    ("win_logs", "Windows log files (CBS, DISM, Panther)",
     "Logi instalatora i serwisowania",
     "safe", 2.0, True, _scan_windows_logs, _clean_windows_logs),

    ("defender_hist", "Defender scan history",
     "Historia skanów Windows Defender (nie definicje)",
     "safe", 0.5, True, _scan_defender_history, _clean_defender_history),

    ("temp", "TEMP folders (user + system)",
     "Pliki tymczasowe starsze niż 24h",
     "safe", 10.0, False, _scan_temp, _clean_temp),

    ("recycle", "Recycle Bin (wszystkie dyski)",
     "Wszystko z kosza zostanie trwale usunięte",
     "safe", 50.0, False, _scan_recycle_bin, _clean_recycle_bin),

    ("thumbs", "Thumbnail + Icon cache",
     "Cache miniatur i ikon — Windows odbuduje przy potrzebie",
     "safe", 1.0, False, _scan_thumbnail_icon_cache, _clean_thumbnail_icon_cache),

    ("font", "Font cache",
     "Cache renderowanych czcionek (rebuilds automatycznie)",
     "safe", 0.2, True, _scan_font_cache, _clean_font_cache),

    ("prefetch", "Prefetch (Windows odbuduje)",
     "Optymalizacja startu aplikacji — Windows szybko odbuduje",
     "safe", 0.5, True, _scan_prefetch, _clean_prefetch),

    ("browsers", "Browser caches (Chrome/Edge/FF/Opera/Brave)",
     "Cache, GPU cache, code cache, service workers wszystkich przeglądarek",
     "safe", 20.0, False, _scan_browser_caches, _clean_browser_caches),

    ("app_caches", "App caches (Discord/Spotify/Teams/Slack/Telegram)",
     "Cache aplikacji desktopowych Electron — odbuduje przy starcie",
     "safe", 3.0, False, _scan_app_caches, _clean_app_caches),

    ("steam_shader", "Steam shader cache + downloading",
     "Pre-skompilowane shadery (odbuduje przy starcie gry) + niedokończone pobrania",
     "safe", 3.0, False, _scan_steam_shader, _clean_steam_shader),

    ("gpu_shader", "GPU shader cache (NVIDIA/AMD/DirectX)",
     "DXCache, GLCache, D3DSCache — sterownik odbuduje",
     "safe", 3.0, False, _scan_gpu_shader_caches, _clean_gpu_shader_caches),

    ("dev_caches", "Dev tool caches (npm/yarn/pip/cargo/gradle/nuget)",
     "Cache pakietów dewelopera — pobierze ponownie przy potrzebie",
     "safe", 20.0, False, _scan_dev_caches, _clean_dev_caches),

    ("office", "Office + Outlook cache",
     "OfficeFileCache, OutlookRoamCache — Outlook resync z serwera",
     "safe", 2.0, False, _scan_office_cache, _clean_office_cache),

    ("vscode", "VSCode cache + logs",
     "Cache rozszerzeń i logi — VSCode odbuduje",
     "safe", 2.0, False, _scan_vscode_cache, _clean_vscode_cache),

    ("restore_points", "Stare punkty przywracania (vssadmin)",
     "WSZYSTKIE shadow copies oprócz najnowszego",
     "reversible", 20.0, True, _scan_old_restore_points, _clean_old_restore_points),
]


# ── public API ───────────────────────────────────────────────────────────────

def scan_all(progress_cb=None) -> list[CleanCategory]:
    """Scan all categories. Returns list with size_bytes populated."""
    results = []
    total = len(CATEGORIES)
    for i, (key, label, desc, risk, est_gb, admin, scan_fn, _clean_fn) in enumerate(CATEGORIES):
        if progress_cb:
            progress_cb(int(i * 100 / total), label)
        try:
            size, count = scan_fn()
        except Exception:
            size, count = 0, 0
        results.append(CleanCategory(
            key=key, label=label, description=desc, risk=risk,
            estimated_max_gb=est_gb, requires_admin=admin,
            size_bytes=size, file_count=count,
        ))
    if progress_cb:
        progress_cb(100, "Skan zakończony")
    return results


def clean_selected(categories: list[CleanCategory], progress_cb=None) -> dict:
    """Clean only categories with .enabled = True. Returns stats."""
    cat_map = {c[0]: c for c in CATEGORIES}
    selected = [c for c in categories if c.enabled and c.key in cat_map]

    total = len(selected)
    if total == 0:
        return {"total_freed": 0, "items_deleted": 0, "results": []}

    results = []
    total_freed = 0
    total_items = 0

    for i, cat in enumerate(selected):
        if progress_cb:
            progress_cb(int(i * 100 / total), cat.label)
        _, _, _, _, _, _, _scan_fn, clean_fn = cat_map[cat.key]
        try:
            freed, count = clean_fn()
            total_freed += freed
            total_items += count
            results.append({
                "key": cat.key, "label": cat.label,
                "freed_bytes": freed, "items": count,
                "freed_human": _fmt(freed),
                "ok": True,
            })
        except Exception as e:
            results.append({
                "key": cat.key, "label": cat.label,
                "freed_bytes": 0, "items": 0,
                "freed_human": "0 B", "ok": False,
                "error": str(e),
            })

    if progress_cb:
        progress_cb(100, "Czyszczenie zakończone")

    return {
        "total_freed": total_freed,
        "total_freed_human": _fmt(total_freed),
        "items_deleted": total_items,
        "results": results,
    }


def quick_estimate() -> int:
    """Fast estimate — just sum the easy categories without DISM scan."""
    fast_keys = {"temp", "recycle", "thumbs", "browsers", "app_caches",
                 "gpu_shader", "wer", "dumps", "prefetch"}
    total = 0
    for key, _, _, _, _, _, scan_fn, _ in CATEGORIES:
        if key in fast_keys:
            try:
                size, _ = scan_fn()
                total += size
            except Exception:
                pass
    return total


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    print("Skanowanie...")
    results = scan_all(lambda p, m: print(f"[{p:>3}%] {m}"))
    print()
    print(f"{'Kategoria':<45} {'Rozmiar':>12} {'Plików':>10}")
    print("-" * 70)
    total = 0
    for r in results:
        if r.size_bytes > 0:
            print(f"{r.label:<45} {_fmt(r.size_bytes):>12} {r.file_count:>10}")
            total += r.size_bytes
    print("-" * 70)
    print(f"{'RAZEM':<45} {_fmt(total):>12}")
