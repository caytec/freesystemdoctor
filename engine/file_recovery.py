"""File Recovery engine — recover deleted files from Windows Recycle Bin.

Windows Vista+ stores each deleted file as a pair:
  $I<id>.<ext>  — metadata: header (8b), size (8b), deleted time (8b),
                  filename length (4b, V2 only), original path (UTF-16LE)
  $R<id>.<ext>  — actual file data

V1 (Vista/7): no filename length field, path is null-terminated 260*2 bytes
V2 (Win 10+): version byte 2 at offset 0, filename length present at offset 24
"""

import os
import shutil
import struct
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone


_FILETIME_EPOCH = 116444736000000000  # Jan 1 1601 → Jan 1 1970 in 100ns units


def _filetime_to_unix(filetime: int) -> float:
    if filetime <= 0:
        return 0.0
    return max(0.0, (filetime - _FILETIME_EPOCH) / 10_000_000)


def _parse_dollar_i(path: Path) -> dict | None:
    """Parse a $I metadata file. Returns {original_path, size, deleted_time}."""
    try:
        with open(path, "rb") as f:
            data = f.read(2048)
        if len(data) < 24:
            return None

        version = struct.unpack("<Q", data[0:8])[0]
        size    = struct.unpack("<Q", data[8:16])[0]
        ftime   = struct.unpack("<q", data[16:24])[0]

        if version == 2:
            if len(data) < 28:
                return None
            name_len = struct.unpack("<I", data[24:28])[0]  # chars including null
            start = 28
            byte_len = name_len * 2
            raw_path = data[start:start + byte_len]
        else:
            # V1: 260 UTF-16LE chars (520 bytes), null-terminated
            raw_path = data[24:24 + 520]

        try:
            original_path = raw_path.decode("utf-16-le", errors="ignore").rstrip("\x00")
        except Exception:
            original_path = ""

        return {
            "original_path": original_path,
            "size": size,
            "deleted_time": _filetime_to_unix(ftime),
        }
    except Exception:
        return None


def _scan_one_recycle_bin(rb_path: Path) -> list[dict]:
    """Scan one drive's $Recycle.Bin and pair $I files with $R data files."""
    out: list[dict] = []
    try:
        # Each user has their own SID-named subfolder
        for sid_dir in rb_path.iterdir():
            try:
                if not sid_dir.is_dir():
                    continue
                # Index $R files for fast lookup
                r_files: dict[str, Path] = {}
                i_files: list[Path] = []
                for entry in sid_dir.iterdir():
                    name = entry.name
                    if name.startswith("$R"):
                        r_files[name[2:]] = entry  # key: id+ext
                    elif name.startswith("$I"):
                        i_files.append(entry)

                for i_path in i_files:
                    suffix = i_path.name[2:]   # id + ext
                    r_path = r_files.get(suffix)
                    if not r_path or not r_path.exists():
                        continue
                    meta = _parse_dollar_i(i_path)
                    if not meta:
                        continue

                    original = meta["original_path"] or r_path.name
                    name = os.path.basename(original)
                    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

                    try:
                        actual_size = r_path.stat().st_size
                    except OSError:
                        actual_size = meta["size"]

                    out.append({
                        "path":          str(r_path),
                        "metadata_path": str(i_path),
                        "name":          name,
                        "original_path": original,
                        "size":          actual_size,
                        "size_str":      _fmt_bytes(actual_size),
                        "deleted_time":  meta["deleted_time"],
                        "deleted_str":   datetime.fromtimestamp(
                            meta["deleted_time"]).strftime("%Y-%m-%d %H:%M")
                            if meta["deleted_time"] > 0 else "Unknown",
                        "extension":     ext,
                        "drive":         os.path.splitdrive(str(r_path))[0],
                        "is_directory":  r_path.is_dir(),
                    })
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    return out


def scan_recoverable_files(drive: str = None, max_results: int = 10000) -> list[dict]:
    """Scan all drive Recycle Bins in parallel.

    drive parameter kept for backward compat but ignored — always scans all.
    """
    rb_paths = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        rb = Path(f"{letter}:/$Recycle.Bin")
        if rb.is_dir():
            rb_paths.append(rb)

    if not rb_paths:
        return []

    results = []
    with ThreadPoolExecutor(max_workers=min(4, len(rb_paths))) as ex:
        for batch in ex.map(_scan_one_recycle_bin, rb_paths):
            results.extend(batch)
            if len(results) >= max_results:
                break

    # Newest first
    results.sort(key=lambda r: r.get("deleted_time", 0), reverse=True)
    return results[:max_results]


def recover_file(recycle_file_path: str, dest_dir: str,
                 keep_original_path: bool = False) -> bool:
    """Recover a $R file. Restores original filename via paired $I file."""
    try:
        source = Path(recycle_file_path)
        if not source.exists():
            return False

        # Find paired $I file
        original_name = source.name
        sid_dir = source.parent
        if source.name.startswith("$R"):
            i_name = "$I" + source.name[2:]
            i_path = sid_dir / i_name
            if i_path.exists():
                meta = _parse_dollar_i(i_path)
                if meta and meta.get("original_path"):
                    if keep_original_path:
                        # Restore to original location preserving directory tree
                        try:
                            target = Path(meta["original_path"])
                            target.parent.mkdir(parents=True, exist_ok=True)
                            _copy(source, target)
                            try: i_path.unlink()
                            except Exception: pass
                            try:
                                if source.is_dir(): shutil.rmtree(source)
                                else: source.unlink()
                            except Exception: pass
                            return target.exists()
                        except Exception:
                            pass
                    original_name = os.path.basename(meta["original_path"])

        dest_dir_p = Path(dest_dir)
        dest_dir_p.mkdir(parents=True, exist_ok=True)
        dest = dest_dir_p / original_name

        # Avoid overwriting existing files
        counter = 1
        while dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            dest = dest_dir_p / f"{stem} ({counter}){suffix}"
            counter += 1

        _copy(source, dest)
        return dest.exists()
    except Exception:
        return False


def _copy(src: Path, dst: Path):
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def recover_multiple(file_paths: list[str], dest_dir: str,
                     keep_original_path: bool = False) -> tuple[int, int]:
    """Recover multiple files. Returns (success_count, total_count)."""
    success = 0
    for filepath in file_paths:
        if recover_file(filepath, dest_dir, keep_original_path):
            success += 1
    return success, len(file_paths)


def get_recycle_bin_size() -> int:
    """Get total Recycle Bin size across all drives."""
    total = 0
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        rb = Path(f"{letter}:/$Recycle.Bin")
        if not rb.is_dir():
            continue
        try:
            for root, _dirs, files in os.walk(rb):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def _fmt_bytes(b: int) -> str:
    if b is None:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
