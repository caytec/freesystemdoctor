"""
space_hogs.py — WinDirStat-style finder for the biggest files and folders.
Part of FreeSystemDoctor engine.

Public API:
    find_largest_files(root, top_n=500, min_size_bytes=1_000_000,
                       progress_cb=None, cancel_flag=None) -> list[dict]
    find_largest_folders(root, top_n=100, depth=4,
                         progress_cb=None, cancel_flag=None) -> list[dict]
    list_drives() -> list[dict]
"""

from __future__ import annotations

import heapq
import logging
import os
import subprocess
import tempfile
from typing import Callable, Optional

_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "space_hogs.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmt_bytes(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024:
            return f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} PB"


class CancelFlag:
    """Thread-safe cancellation flag (no lock needed for bool)."""
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


def _should_skip_dir(name: str) -> bool:
    """Skip directories that are noisy, system-protected, or symlinks."""
    low = name.lower()
    return low in {
        "$recycle.bin", "system volume information",
        "windows.old", "config.msi", "$windows.~ws", "$windows.~bt",
    }


# ---------------------------------------------------------------------------
# Drives
# ---------------------------------------------------------------------------
def list_drives() -> list[dict]:
    """Return a list of mountable drives with free/total info."""
    out = []
    try:
        import psutil
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                out.append({
                    "device":     part.device,
                    "mountpoint": part.mountpoint,
                    "fstype":     part.fstype,
                    "total":      usage.total,
                    "used":       usage.used,
                    "free":       usage.free,
                    "percent":    usage.percent,
                    "label":      f"{part.device}  ({fmt_bytes(usage.used)} / {fmt_bytes(usage.total)} used)",
                })
            except Exception:
                pass
    except ImportError:
        # Fallback: enumerate via Windows drive letters
        import string
        for letter in string.ascii_uppercase:
            path = f"{letter}:\\"
            if os.path.exists(path):
                out.append({
                    "device": path, "mountpoint": path,
                    "fstype": "", "total": 0, "used": 0, "free": 0,
                    "percent": 0, "label": path,
                })
    return out


# ---------------------------------------------------------------------------
# Largest files (heap-based — keeps memory bounded)
# ---------------------------------------------------------------------------
def find_largest_files(
    root: str,
    top_n: int = 500,
    min_size_bytes: int = 1_000_000,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_flag: Optional[CancelFlag] = None,
) -> list[dict]:
    """
    Walk `root` and return the `top_n` largest files (>= min_size_bytes).

    Uses a min-heap of fixed size = top_n so memory usage stays bounded
    even when scanning millions of files.

    progress_cb(files_scanned, total_bytes_seen, current_dir) is called every ~5k files.
    """
    root = os.path.normpath(root)
    heap: list[tuple[int, str, float]] = []   # (size, path, mtime)
    scanned = 0
    total_bytes = 0

    for cur_dir, dirs, files in os.walk(root, topdown=True):
        if cancel_flag and cancel_flag.cancelled:
            break

        # Prune noisy / system-protected dirs in-place
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]

        for fname in files:
            if cancel_flag and cancel_flag.cancelled:
                break
            full = os.path.join(cur_dir, fname)
            try:
                st = os.stat(full, follow_symlinks=False)
                sz = st.st_size
                scanned += 1
                total_bytes += sz
                if sz >= min_size_bytes:
                    if len(heap) < top_n:
                        heapq.heappush(heap, (sz, full, st.st_mtime))
                    elif sz > heap[0][0]:
                        heapq.heapreplace(heap, (sz, full, st.st_mtime))
            except OSError:
                continue

            if progress_cb and scanned % 5000 == 0:
                try:
                    progress_cb(scanned, total_bytes, cur_dir)
                except Exception:
                    pass

    if progress_cb:
        try:
            progress_cb(scanned, total_bytes, root)
        except Exception:
            pass

    largest = sorted(heap, key=lambda t: t[0], reverse=True)
    return [
        {
            "path":      path,
            "name":      os.path.basename(path),
            "folder":    os.path.dirname(path),
            "size":      size,
            "size_str":  fmt_bytes(size),
            "mtime":     mtime,
            "ext":       os.path.splitext(path)[1].lower(),
        }
        for size, path, mtime in largest
    ]


# ---------------------------------------------------------------------------
# Largest folders (aggregate size up to `depth` levels)
# ---------------------------------------------------------------------------
def find_largest_folders(
    root: str,
    top_n: int = 100,
    depth: int = 4,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_flag: Optional[CancelFlag] = None,
) -> list[dict]:
    """
    Walk `root` once and aggregate cumulative size per directory.
    Returns the `top_n` largest folders limited to `depth` levels deep.
    """
    root = os.path.normpath(root)
    root_depth = root.count(os.sep)
    sizes: dict[str, int] = {}
    scanned = 0
    total_bytes = 0

    for cur_dir, dirs, files in os.walk(root, topdown=True):
        if cancel_flag and cancel_flag.cancelled:
            break

        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]

        # Files contribute size to every ancestor up to depth limit
        dir_total = 0
        for fname in files:
            try:
                sz = os.path.getsize(os.path.join(cur_dir, fname))
                dir_total += sz
                scanned += 1
                total_bytes += sz
            except OSError:
                continue

        if dir_total:
            ancestor = cur_dir
            while True:
                a_depth = ancestor.count(os.sep) - root_depth
                if a_depth < 0:
                    break
                if a_depth <= depth:
                    sizes[ancestor] = sizes.get(ancestor, 0) + dir_total
                if ancestor == root or len(ancestor) <= len(root):
                    break
                parent = os.path.dirname(ancestor)
                if parent == ancestor:
                    break
                ancestor = parent

        if progress_cb and scanned % 5000 == 0:
            try:
                progress_cb(scanned, total_bytes, cur_dir)
            except Exception:
                pass

    if progress_cb:
        try:
            progress_cb(scanned, total_bytes, root)
        except Exception:
            pass

    root_total = sizes.get(root, total_bytes) or 1
    top = heapq.nlargest(top_n, sizes.items(), key=lambda kv: kv[1])
    return [
        {
            "path":     path,
            "name":     os.path.basename(path) or path,
            "size":     size,
            "size_str": fmt_bytes(size),
            "percent":  (size / root_total) * 100,
        }
        for path, size in top
    ]


# ---------------------------------------------------------------------------
# Shell integrations
# ---------------------------------------------------------------------------
def reveal_in_explorer(path: str) -> bool:
    """Open Windows Explorer with the given file selected."""
    try:
        if os.path.isdir(path):
            subprocess.Popen(["explorer", path])
        else:
            subprocess.Popen(["explorer", "/select,", path])
        return True
    except Exception as exc:
        logger.warning("reveal_in_explorer failed: %s", exc)
        return False


def send_to_recycle_bin(path: str) -> bool:
    """Move file/folder to the Recycle Bin via Shell32 SHFileOperationW."""
    try:
        import ctypes
        from ctypes import wintypes

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x40
        FOF_NOCONFIRMATION = 0x10
        FOF_SILENT = 0x4
        FOF_NOERRORUI = 0x400

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd",    wintypes.HWND),
                ("wFunc",   wintypes.UINT),
                ("pFrom",   wintypes.LPCWSTR),
                ("pTo",     wintypes.LPCWSTR),
                ("fFlags",  ctypes.c_uint16),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle",     wintypes.LPCWSTR),
            ]

        op = SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = path + "\0\0"
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI

        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        return res == 0
    except Exception as exc:
        logger.warning("send_to_recycle_bin failed for %s: %s", path, exc)
        return False
