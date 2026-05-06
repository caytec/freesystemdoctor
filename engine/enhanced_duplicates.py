"""Enhanced Duplicate Finder — group by file type, content hash, similarity detection."""

import os
import hashlib
from pathlib import Path
from collections import defaultdict


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def _get_file_type(path: str) -> str:
    """Categorize file by extension."""
    ext = Path(path).suffix.lower()
    type_map = {
        # Images
        ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image",
        ".bmp": "image", ".webp": "image", ".svg": "image", ".ico": "image",
        # Audio
        ".mp3": "audio", ".wav": "audio", ".flac": "audio", ".aac": "audio",
        ".m4a": "audio", ".opus": "audio", ".wma": "audio",
        # Video
        ".mp4": "video", ".avi": "video", ".mkv": "video", ".mov": "video",
        ".flv": "video", ".wmv": "video", ".webm": "video", ".m4v": "video",
        # Documents
        ".pdf": "document", ".doc": "document", ".docx": "document", ".txt": "document",
        ".xlsx": "document", ".xls": "document", ".ppt": "document", ".pptx": "document",
        # Archives
        ".zip": "archive", ".rar": "archive", ".7z": "archive", ".tar": "archive",
        ".gz": "archive", ".bz2": "archive",
        # Code
        ".py": "code", ".js": "code", ".cpp": "code", ".java": "code",
        ".cs": "code", ".go": "code", ".rs": "code",
    }
    return type_map.get(ext, "other")


def _file_full_hash(path: str, chunk: int = 65536) -> str | None:
    """Calculate full file MD5 hash."""
    hasher = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except OSError:
        return None


def find_duplicates_by_type(
    search_paths: list[str],
    file_type: str = None,  # "image", "audio", "video", "document", etc.
    min_size_kb: int = 1,
    progress_cb=None,
) -> list[dict]:
    """
    Find duplicates grouped by file type.
    Returns list of duplicate groups with file type, count, total wasted space.
    """
    min_bytes = min_size_kb * 1024
    by_hash: dict[str, list[str]] = defaultdict(list)
    scanned = 0

    for root_path in search_paths:
        for root, _dirs, files in os.walk(root_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                    if sz < min_bytes:
                        continue

                    # Filter by type if specified
                    if file_type and _get_file_type(fp) != file_type:
                        continue

                    h = _file_full_hash(fp)
                    if h:
                        by_hash[h].append(fp)
                        scanned += 1
                        if progress_cb:
                            progress_cb(f"Scanning... {scanned} files", 0)
                except OSError:
                    pass

    # Build result: only groups with 2+ files
    groups = []
    for h, paths in by_hash.items():
        if len(paths) >= 2:
            try:
                sz = os.path.getsize(paths[0])
            except OSError:
                sz = 0

            wasted = sz * (len(paths) - 1)
            file_type_detected = _get_file_type(paths[0])

            groups.append({
                "hash": h,
                "file_type": file_type_detected,
                "size": sz,
                "size_str": _fmt_bytes(sz),
                "count": len(paths),
                "wasted": wasted,
                "wasted_str": _fmt_bytes(wasted),
                "files": paths,
            })

    groups.sort(key=lambda x: x["wasted"], reverse=True)
    return groups


def find_similar_files(
    search_paths: list[str],
    similarity_threshold: float = 0.90,  # 0.0-1.0
    progress_cb=None,
) -> list[dict]:
    """
    Find similar files (not exact duplicates) based on size similarity.
    Useful for finding near-duplicates with different quality/compression.
    """
    by_size: dict[int, list[str]] = defaultdict(list)
    scanned = 0

    for root_path in search_paths:
        for root, _dirs, files in os.walk(root_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                    by_size[sz].append(fp)
                    scanned += 1
                    if progress_cb:
                        progress_cb(f"Indexing... {scanned} files", 0)
                except OSError:
                    pass

    # Find size ranges that might indicate similar files
    groups = []
    sorted_sizes = sorted(by_size.items())

    for i, (sz1, paths1) in enumerate(sorted_sizes):
        for sz2, paths2 in sorted_sizes[i+1:]:
            if sz2 == 0:
                continue
            similarity = min(sz1, sz2) / max(sz1, sz2)
            if similarity >= similarity_threshold and len(paths1) > 0 and len(paths2) > 0:
                all_paths = paths1 + paths2
                wasted = sz1 * (len(paths1) - 1) if len(paths1) > 1 else 0

                groups.append({
                    "size_ratio": similarity,
                    "primary_size": sz1,
                    "similar_size": sz2,
                    "count": len(all_paths),
                    "files": all_paths,
                    "wasted": wasted,
                    "wasted_str": _fmt_bytes(wasted),
                    "note": "Potential near-duplicates (similar sizes)",
                })

    return groups


def get_file_type_summary(search_paths: list[str]) -> dict:
    """Get summary of file types and their counts."""
    summary = defaultdict(lambda: {"count": 0, "total_size": 0})

    for root_path in search_paths:
        for root, _dirs, files in os.walk(root_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    file_type = _get_file_type(fp)
                    sz = os.path.getsize(fp)
                    summary[file_type]["count"] += 1
                    summary[file_type]["total_size"] += sz
                except OSError:
                    pass

    # Convert to sorted list
    result = []
    for ftype, data in sorted(summary.items(), key=lambda x: x[1]["total_size"], reverse=True):
        result.append({
            "type": ftype,
            "count": data["count"],
            "total_size": data["total_size"],
            "total_size_str": _fmt_bytes(data["total_size"]),
        })

    return result
