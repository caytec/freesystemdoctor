"""Large file scanner and disk space analyzer."""

import os
from pathlib import Path
from collections import defaultdict


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def find_large_files(
    search_paths: list[str],
    min_size_mb: float = 50,
    progress_cb=None,
) -> list[dict]:
    """Return files larger than min_size_mb, sorted by size desc."""
    min_bytes = int(min_size_mb * 1024 * 1024)
    results = []
    count = 0

    for root_path in search_paths:
        for root, _dirs, files in os.walk(root_path):
            for f in files:
                fp = os.path.join(root, f)
                count += 1
                try:
                    sz = os.path.getsize(fp)
                    if sz >= min_bytes:
                        ext = Path(f).suffix.lower() or "(none)"
                        results.append({
                            "path": fp,
                            "name": f,
                            "ext": ext,
                            "size": sz,
                            "size_str": _fmt_bytes(sz),
                        })
                except OSError:
                    pass
                if progress_cb and count % 500 == 0:
                    progress_cb(f"Scanned {count} files...", len(results))

    results.sort(key=lambda x: x["size"], reverse=True)
    return results


def get_folder_sizes(root_path: str, max_depth: int = 2) -> list[dict]:
    """Return top-level subdirectory sizes (non-recursive past max_depth)."""
    sizes: dict[str, int] = {}

    def _walk(path: str, depth: int) -> int:
        total = 0
        try:
            with os.scandir(path) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total += entry.stat().st_size
                        elif entry.is_dir(follow_symlinks=False):
                            if depth < max_depth:
                                total += _walk(entry.path, depth + 1)
                    except OSError:
                        pass
        except OSError:
            pass
        sizes[path] = total
        return total

    _walk(root_path, 0)

    result = [
        {"path": p, "name": os.path.basename(p) or p, "size": s, "size_str": _fmt_bytes(s)}
        for p, s in sizes.items()
    ]
    return sorted(result, key=lambda x: x["size"], reverse=True)


def get_file_type_breakdown(search_path: str) -> list[dict]:
    types: dict[str, dict] = defaultdict(lambda: {"count": 0, "size": 0})

    for root, _dirs, files in os.walk(search_path):
        for f in files:
            ext = Path(f).suffix.lower() or "(no ext)"
            try:
                sz = os.path.getsize(os.path.join(root, f))
                types[ext]["count"] += 1
                types[ext]["size"] += sz
            except OSError:
                pass

    result = [
        {"ext": ext, "count": d["count"], "size": d["size"], "size_str": _fmt_bytes(d["size"])}
        for ext, d in types.items()
    ]
    return sorted(result, key=lambda x: x["size"], reverse=True)
