"""Duplicate file finder using size + hash approach."""

import os
import hashlib
from collections import defaultdict
from pathlib import Path


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def _file_hash(path: str, partial: bool = False, chunk: int = 65536) -> str | None:
    hasher = hashlib.md5()
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if partial and size > chunk * 2:
                hasher.update(f.read(chunk))
                f.seek(-chunk, 2)
                hasher.update(f.read(chunk))
            else:
                while True:
                    data = f.read(chunk)
                    if not data:
                        break
                    hasher.update(data)
        return hasher.hexdigest()
    except OSError:
        return None


def find_duplicates(
    search_paths: list[str],
    min_size_kb: int = 1,
    progress_cb=None,
) -> list[dict]:
    """
    Returns list of duplicate groups:
    [{"hash": ..., "size": int, "size_str": str, "files": [path, ...]}, ...]
    sorted by wasted space descending.
    """
    min_bytes = min_size_kb * 1024
    by_size: dict[int, list[str]] = defaultdict(list)

    # --- pass 1: group by size ---
    scanned = 0
    for root_path in search_paths:
        for root, _dirs, files in os.walk(root_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                    if sz >= min_bytes:
                        by_size[sz].append(fp)
                        scanned += 1
                        if progress_cb:
                            progress_cb(f"Indexing... {scanned} files", 0)
                except OSError:
                    pass

    # keep only sizes with 2+ files
    candidates = {sz: paths for sz, paths in by_size.items() if len(paths) >= 2}

    # --- pass 2: partial hash ---
    by_partial: dict[str, list[str]] = defaultdict(list)
    for sz, paths in candidates.items():
        for fp in paths:
            h = _file_hash(fp, partial=True)
            if h:
                by_partial[f"{sz}_{h}"].append(fp)

    # --- pass 3: full hash for partial-hash collisions ---
    by_full: dict[str, list[str]] = defaultdict(list)
    total = sum(len(v) for v in by_partial.values() if len(v) >= 2)
    done = 0
    for key, paths in by_partial.items():
        if len(paths) < 2:
            continue
        sz = int(key.split("_")[0])
        for fp in paths:
            h = _file_hash(fp, partial=False)
            if h:
                by_full[h].append(fp)
            done += 1
            if progress_cb:
                progress_cb(f"Hashing {done}/{total}...", int(done / max(total, 1) * 100))

    groups = []
    for h, paths in by_full.items():
        if len(paths) >= 2:
            try:
                sz = os.path.getsize(paths[0])
            except OSError:
                sz = 0
            wasted = sz * (len(paths) - 1)
            groups.append({
                "hash": h,
                "size": sz,
                "size_str": _fmt_bytes(sz),
                "wasted": wasted,
                "wasted_str": _fmt_bytes(wasted),
                "files": paths,
            })

    groups.sort(key=lambda x: x["wasted"], reverse=True)
    return groups
