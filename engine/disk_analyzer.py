"""Disk Analyzer engine — folder size aggregation and breakdown."""

import os
from pathlib import Path


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def analyze_folder(root_path: str, max_depth: int = 3,
                   progress_cb=None) -> dict:
    """Single-pass scan: walks root once, attributing size to each direct child.

    Returns: {path, total_size, total_size_str, subfolders: [...] }
    """
    root_norm = os.path.normpath(root_path)
    total_size = 0
    # direct child folder name -> bytes
    subfolder_sizes: dict[str, int] = {}
    file_count = 0

    try:
        # Build a map of root's direct children (folders + their normalized prefix)
        try:
            children = []
            with os.scandir(root_norm) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            children.append(entry.name)
                            subfolder_sizes[entry.name] = 0
                    except OSError:
                        pass
        except OSError:
            children = []

        # Single os.walk that attributes each file to the matching child
        for root, dirs, files in os.walk(root_norm):
            # Determine which direct-child this directory belongs to
            try:
                rel = os.path.relpath(root, root_norm)
            except ValueError:
                rel = ""
            if rel in (".", ""):
                # Files directly under root_path don't belong to a subfolder
                child_name = None
            else:
                child_name = rel.split(os.sep, 1)[0]

            for f in files:
                try:
                    fpath = os.path.join(root, f)
                    sz = os.path.getsize(fpath)
                    total_size += sz
                    file_count += 1
                    if child_name and child_name in subfolder_sizes:
                        subfolder_sizes[child_name] += sz
                except OSError:
                    pass

            if progress_cb and file_count % 1000 == 0:
                try:
                    progress_cb(file_count, _fmt_bytes(total_size))
                except Exception:
                    pass

    except OSError:
        pass

    sorted_subs = sorted(subfolder_sizes.items(), key=lambda x: x[1], reverse=True)
    return {
        "path": root_norm,
        "total_size": total_size,
        "total_size_str": _fmt_bytes(total_size),
        "file_count": file_count,
        "subfolders": [
            {
                "path": os.path.join(root_norm, name),
                "name": name,
                "size": size,
                "size_str": _fmt_bytes(size),
                "percent": (size / total_size * 100) if total_size > 0 else 0,
            }
            for name, size in sorted_subs
        ],
    }


def _get_dir_size(path: str) -> int:
    """Calculate total size of a directory tree (single os.walk pass)."""
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def list_drives() -> list[dict]:
    """FAST drive enumeration — no filesystem walking.

    Returns list of dicts with drive letter, mountpoint, fs type, total/used/free.
    Used to populate UI dropdowns without blocking.
    """
    try:
        import psutil
    except ImportError:
        return []

    results = []
    for part in psutil.disk_partitions(all=False):
        # Skip non-fixed mounts (CD-ROM, removable empty, etc.)
        opts = (part.opts or "").lower()
        if "cdrom" in opts:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            results.append({
                "drive":      part.device,           # "C:\\"
                "mountpoint": part.mountpoint,       # "C:\\"
                "fstype":     part.fstype,           # "NTFS"
                "total":      usage.total,
                "used":       usage.used,
                "free":       usage.free,
                "percent":    usage.percent,
                "total_str":  _fmt_bytes(usage.total),
                "used_str":   _fmt_bytes(usage.used),
                "free_str":   _fmt_bytes(usage.free),
                "label":      f"{part.device}  ({_fmt_bytes(usage.free)} free of {_fmt_bytes(usage.total)})",
            })
        except (PermissionError, OSError):
            # Disk not ready / empty drive (e.g. card reader)
            continue
    return results


def analyze_all_drives(progress_cb=None) -> list[dict]:
    """Heavy: walks every drive's filesystem. Use list_drives() for dropdowns."""
    drives = list_drives()
    results = []
    for d in drives:
        try:
            analysis = analyze_folder(d["mountpoint"], progress_cb=progress_cb)
            analysis["drive"] = d["drive"]
            results.append(analysis)
        except Exception:
            pass
    return results
