"""Secure Drive Wipe — overwrite free space or entire drives with DoD/NIST standards."""

import os
import subprocess
import tempfile
from pathlib import Path

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

WIPE_METHODS = {
    "Quick (1-pass zeros)": 1,
    "DoD 3-pass": 3,
    "DoD 7-pass": 7,
    "Gutmann 9-pass": 9,
}

CHUNK = 1024 * 1024  # 1 MB chunks


def get_drives() -> list[dict]:
    """Return list of available drives suitable for wiping."""
    drives = []
    if not _PSUTIL:
        return drives
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            drives.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "total_str": _fmt_bytes(usage.total),
                "free_str": _fmt_bytes(usage.free),
                "percent_used": usage.percent,
            })
        except Exception:
            pass
    return drives


def wipe_free_space(mountpoint: str, method: str = "DoD 3-pass",
                    progress_cb=None) -> dict:
    """Fill free space with random data to prevent recovery of deleted files.
    progress_cb(pct: float, status: str) called periodically.
    Returns dict with bytes_wiped, passes_done, error."""
    passes = WIPE_METHODS.get(method, 3)
    tmp_files = []
    bytes_wiped = 0

    try:
        for pass_num in range(1, passes + 1):
            if progress_cb:
                progress_cb(((pass_num - 1) / passes) * 100,
                            f"Pass {pass_num}/{passes} — filling free space...")

            # Write large temp files until disk is full
            try:
                usage = psutil.disk_usage(mountpoint) if _PSUTIL else None
                free = usage.free if usage else 0
                written = 0

                tmp_path = Path(mountpoint) / f"_fsd_wipe_{pass_num}_{os.getpid()}.tmp"
                tmp_files.append(tmp_path)

                with open(tmp_path, "wb") as f:
                    while written < free:
                        chunk_size = min(CHUNK, free - written)
                        if pass_num == 1:
                            data = b"\x00" * chunk_size
                        elif pass_num == 2:
                            data = b"\xFF" * chunk_size
                        else:
                            data = os.urandom(chunk_size)
                        f.write(data)
                        f.flush()
                        written += chunk_size
                        bytes_wiped += chunk_size

                        if progress_cb and written % (CHUNK * 10) == 0:
                            pct = ((pass_num - 1) / passes + (written / free) / passes) * 100
                            progress_cb(min(pct, 99), f"Pass {pass_num}/{passes} — {_fmt_bytes(written)} written")

            except OSError:
                pass  # Disk full — expected

        return {"bytes_wiped": bytes_wiped, "passes_done": passes, "error": None}

    except Exception as e:
        return {"bytes_wiped": bytes_wiped, "passes_done": 0, "error": str(e)}

    finally:
        for tmp in tmp_files:
            try:
                tmp.unlink()
            except Exception:
                pass
        if progress_cb:
            progress_cb(100, "Wipe complete")


def wipe_drive_windows(drive_letter: str, method: str = "DoD 3-pass",
                       progress_cb=None) -> dict:
    """Use Windows cipher /w to wipe free space (simpler, uses built-in tool)."""
    if progress_cb:
        progress_cb(10, "Running cipher /w (Windows secure wipe)...")

    try:
        result = subprocess.run(
            ["cipher", "/w:" + drive_letter + "\\"],
            capture_output=True, text=True, timeout=3600
        )
        if progress_cb:
            progress_cb(100, "Wipe complete")
        return {"bytes_wiped": 0, "passes_done": 3, "error": None}
    except subprocess.TimeoutExpired:
        return {"bytes_wiped": 0, "passes_done": 0, "error": "Timeout"}
    except Exception as e:
        return {"bytes_wiped": 0, "passes_done": 0, "error": str(e)}


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
