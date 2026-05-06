"""Disk Analyzer engine — folder size aggregation and breakdown."""

import os
from pathlib import Path


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def analyze_folder(root_path: str, max_depth: int = 3) -> dict:
    """
    Recursively analyze folder and return size breakdown.
    Returns: {
        'path': root_path,
        'total_size': bytes,
        'total_size_str': formatted,
        'subfolders': [{'path', 'size', 'size_str', 'percent'}, ...]
    }
    """
    total_size = 0
    subfolder_sizes = {}

    try:
        for root, dirs, files in os.walk(root_path):
            try:
                for f in files:
                    try:
                        fpath = os.path.join(root, f)
                        total_size += os.path.getsize(fpath)
                    except OSError:
                        pass
            except OSError:
                pass

        # Group by direct children
        try:
            for item in os.listdir(root_path):
                item_path = os.path.join(root_path, item)
                if os.path.isdir(item_path):
                    size = _get_dir_size(item_path)
                    subfolder_sizes[item_path] = size
        except OSError:
            pass

    except OSError:
        pass

    # Sort by size descending
    sorted_subs = sorted(subfolder_sizes.items(), key=lambda x: x[1], reverse=True)

    return {
        "path": root_path,
        "total_size": total_size,
        "total_size_str": _fmt_bytes(total_size),
        "subfolders": [
            {
                "path": path,
                "name": os.path.basename(path),
                "size": size,
                "size_str": _fmt_bytes(size),
                "percent": (size / total_size * 100) if total_size > 0 else 0,
            }
            for path, size in sorted_subs
        ],
    }


def _get_dir_size(path: str) -> int:
    """Recursively calculate directory size."""
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            try:
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
            except OSError:
                pass
    except OSError:
        pass
    return total


def analyze_all_drives() -> list[dict]:
    """Analyze all system drives."""
    try:
        import psutil
    except ImportError:
        return []

    results = []
    for part in psutil.disk_partitions(all=False):
        try:
            analysis = analyze_folder(part.mountpoint)
            analysis["drive"] = part.device
            results.append(analysis)
        except Exception:
            pass
    return results
