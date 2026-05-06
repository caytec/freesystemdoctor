"""Secure file shredder — multi-pass overwrite before deletion."""

import os
import secrets
import stat


_METHODS = {
    "Fast (1-pass zeros)":   [(b"\x00", False)],
    "DoD 3-pass":            [(b"\x00", False), (b"\xFF", False), (None, True)],
    "DoD 7-pass":            [
        (b"\x00", False), (b"\xFF", False), (None, True),
        (b"\x00", False), (b"\xFF", False), (None, True),
        (None, True),
    ],
    "Gutmann-like (9-pass)": [
        (b"\x00", False), (b"\xFF", False), (None, True),
        (b"\x55", False), (b"\xAA", False), (None, True),
        (b"\x92\x49\x24", False), (b"\x6D\xB6\xDB", False),
        (None, True),
    ],
}

DEFAULT_METHOD = "DoD 3-pass"

CHUNK = 65536


def _fill_pattern(size: int, pattern: bytes | None) -> bytes:
    if pattern is None:
        return secrets.token_bytes(min(size, CHUNK))
    rep = (size // len(pattern)) + 1
    return (pattern * rep)[:size]


def shred_file(path: str, method: str = DEFAULT_METHOD, progress_cb=None) -> bool:
    """
    Securely delete a file.
    progress_cb(pass_num, total_passes, bytes_done, total_bytes) called each chunk.
    Returns True on success.
    """
    passes = _METHODS.get(method, _METHODS[DEFAULT_METHOD])
    try:
        size = os.path.getsize(path)
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)

        with open(path, "r+b") as f:
            for p_idx, (pattern, random) in enumerate(passes):
                f.seek(0)
                written = 0
                while written < size:
                    chunk_size = min(CHUNK, size - written)
                    if random:
                        data = secrets.token_bytes(chunk_size)
                    else:
                        data = _fill_pattern(chunk_size, pattern)
                    f.write(data[:chunk_size])
                    written += chunk_size
                    if progress_cb:
                        progress_cb(p_idx + 1, len(passes), written, size)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

        # Rename to random name before delete (frustrates some recovery tools)
        dir_ = os.path.dirname(path)
        tmp = os.path.join(dir_, secrets.token_hex(8))
        os.rename(path, tmp)
        os.remove(tmp)
        return True
    except Exception:
        # Last-ditch: just delete
        try:
            os.remove(path)
        except OSError:
            pass
        return False


def shred_folder(folder: str, method: str = DEFAULT_METHOD,
                 progress_cb=None) -> tuple[int, int]:
    """Shred all files in folder. Returns (shredded, errors)."""
    shredded = errors = 0
    for root, dirs, files in os.walk(folder, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            if progress_cb:
                progress_cb(fp)
            ok = shred_file(fp, method)
            if ok:
                shredded += 1
            else:
                errors += 1
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
    try:
        os.rmdir(folder)
    except OSError:
        pass
    return shredded, errors


def get_methods() -> list[str]:
    return list(_METHODS.keys())
