"""
benchmark.py — CPU, RAM, and disk performance benchmarks.
Part of FreeSystemDoctor engine.
"""

from __future__ import annotations

import array
import datetime
import logging
import math
import os
import tempfile
import threading
import time
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "benchmark.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Reference values for normalisation to 0-100 score
# ---------------------------------------------------------------------------
_REF_CPU_OPS_PER_SEC  = 50_000_000   # 50 M ops/s = 100 points
_REF_RAM_MBPS         = 10_000.0     # 10 GB/s     = 100 points
_REF_DISK_MBPS        = 500.0        # 500 MB/s    = 100 points


def _clamp_score(raw: float) -> int:
    """Clamp a raw score to 0-100."""
    return max(0, min(100, int(round(raw))))


# ---------------------------------------------------------------------------
# CPU Benchmark
# ---------------------------------------------------------------------------

def _cpu_worker(duration_sec: float, result_holder: list) -> None:
    """Perform integer/float math for *duration_sec* seconds (single-thread)."""
    ops = 0
    deadline = time.perf_counter() + duration_sec
    x = 1.0
    while time.perf_counter() < deadline:
        x = math.sqrt(abs(math.sin(x + 1.0) * math.cos(x + 0.5)) + 1e-12)
        ops += 1
    result_holder.append((ops, duration_sec))


def _cpu_worker_proc(duration_sec: float, q):
    """Multiprocessing worker — runs in separate process (no GIL contention)."""
    ops = 0
    deadline = time.perf_counter() + duration_sec
    x = 1.0
    while time.perf_counter() < deadline:
        x = math.sqrt(abs(math.sin(x + 1.0) * math.cos(x + 0.5)) + 1e-12)
        ops += 1
    q.put(ops)


def cpu_benchmark(
    duration_sec: int = 5,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Stress-test all logical CPU cores with floating-point operations.

    Args:
        duration_sec: How many seconds to run the benchmark per core.
        progress_cb: Optional callable receiving status strings.

    Returns:
        {score, ops_per_sec, cores_tested, duration}
    """
    result = {"score": 0, "ops_per_sec": 0, "cores_tested": 0, "duration": duration_sec}
    try:
        import multiprocessing
        cores = multiprocessing.cpu_count()
        result["cores_tested"] = cores

        if progress_cb:
            try:
                progress_cb(f"CPU benchmark: testing {cores} logical cores for {duration_sec}s each...")
            except Exception:
                pass

        # Use multiprocessing to bypass the GIL — gives a real multi-core score.
        # Falls back to threading if multiprocessing isn't available (e.g. frozen
        # PyInstaller exe with the spawn-method limitation).
        total_ops = 0
        elapsed = 0.0
        try:
            ctx = multiprocessing.get_context("spawn")
            q = ctx.Queue()
            procs = [ctx.Process(target=_cpu_worker_proc,
                                   args=(duration_sec, q))
                     for _ in range(cores)]
            start = time.perf_counter()
            for p in procs:
                p.start()
            collected = 0
            while collected < cores:
                try:
                    total_ops += q.get(timeout=duration_sec + 10)
                    collected += 1
                except Exception:
                    break
            for p in procs:
                p.join(timeout=2)
            elapsed = time.perf_counter() - start
        except Exception:
            # Fallback to threads
            holders: list[list] = [[] for _ in range(cores)]
            threads = [
                threading.Thread(target=_cpu_worker,
                                  args=(duration_sec, holders[i]), daemon=True)
                for i in range(cores)
            ]
            start = time.perf_counter()
            for t in threads: t.start()
            for t in threads: t.join(timeout=duration_sec + 10)
            elapsed = time.perf_counter() - start
            total_ops = sum(h[0][0] for h in holders if h)
        if elapsed <= 0:
            elapsed = duration_sec
        ops_per_sec = int(total_ops / elapsed) if elapsed > 0 else 0
        score = _clamp_score(ops_per_sec / _REF_CPU_OPS_PER_SEC * 100)

        result = {
            "score": score,
            "ops_per_sec": ops_per_sec,
            "cores_tested": cores,
            "duration": round(elapsed, 2),
        }
        logger.info("cpu_benchmark: score=%d ops/s=%d cores=%d", score, ops_per_sec, cores)

        if progress_cb:
            try:
                progress_cb(f"CPU benchmark complete. Score: {score}/100 ({ops_per_sec:,} ops/s)")
            except Exception:
                pass

    except Exception as exc:
        logger.exception("cpu_benchmark failed: %s", exc)
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# RAM Benchmark
# ---------------------------------------------------------------------------

def ram_benchmark(
    size_mb: int = 256,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Allocate a memory block and measure sequential read/write throughput.

    Args:
        size_mb: Size of the test buffer in megabytes.
        progress_cb: Optional callable receiving status strings.

    Returns:
        {read_mbps, write_mbps, score}
    """
    result = {"read_mbps": 0.0, "write_mbps": 0.0, "score": 0}
    try:
        if progress_cb:
            try:
                progress_cb(f"RAM benchmark: allocating {size_mb} MB buffer...")
            except Exception:
                pass

        size_bytes = size_mb * 1024 * 1024
        # Use array of unsigned bytes for efficient allocation
        chunk = size_bytes // 4  # number of unsigned ints

        # Write test
        t0 = time.perf_counter()
        buf = array.array("I", [0xDEADBEEF] * chunk)  # type: ignore[arg-type]
        write_elapsed = time.perf_counter() - t0
        write_mbps = (size_bytes / 1024 / 1024) / write_elapsed if write_elapsed > 0 else 0.0

        if progress_cb:
            try:
                progress_cb(f"RAM write: {write_mbps:.0f} MB/s")
            except Exception:
                pass

        # Read test — sum all values (prevent optimiser from eliding the loop)
        t1 = time.perf_counter()
        _checksum = sum(buf)  # noqa: F841
        read_elapsed = time.perf_counter() - t1
        read_mbps = (size_bytes / 1024 / 1024) / read_elapsed if read_elapsed > 0 else 0.0

        if progress_cb:
            try:
                progress_cb(f"RAM read: {read_mbps:.0f} MB/s")
            except Exception:
                pass

        del buf  # Release memory

        avg_mbps = (read_mbps + write_mbps) / 2
        score = _clamp_score(avg_mbps / _REF_RAM_MBPS * 100)

        result = {
            "read_mbps":  round(read_mbps, 2),
            "write_mbps": round(write_mbps, 2),
            "score":      score,
        }
        logger.info("ram_benchmark: read=%.1f MB/s write=%.1f MB/s score=%d", read_mbps, write_mbps, score)

    except MemoryError:
        logger.warning("ram_benchmark: MemoryError, buffer too large (%d MB)", size_mb)
        result["error"] = "Insufficient memory for requested buffer size."
    except Exception as exc:
        logger.exception("ram_benchmark failed: %s", exc)
        result["error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Disk Benchmark
# ---------------------------------------------------------------------------

_DISK_TEMP_FILENAME = "fsd_disk_bench.tmp"


def disk_benchmark(
    drive: str = "C:",
    size_mb: int = 100,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Write and read a temporary file on the given drive to measure throughput.

    Args:
        drive: Drive root, e.g. "C:"
        size_mb: Size of the test file in MB.
        progress_cb: Optional callable receiving status strings.

    Returns:
        {read_mbps, write_mbps, score, drive}
    """
    result: dict = {"read_mbps": 0.0, "write_mbps": 0.0, "score": 0, "drive": drive}
    tmp_path: Optional[str] = None

    try:
        drive_clean = drive.strip().upper().rstrip("\\").rstrip("/")
        if not drive_clean.endswith(":"):
            drive_clean += ":"

        tmp_dir = os.path.join(drive_clean + "\\", "Temp", "FreeSystemDoctor")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, _DISK_TEMP_FILENAME)

        size_bytes = size_mb * 1024 * 1024
        block_size = 64 * 1024  # 64 KB blocks
        data_block = bytes([0xAB] * block_size)
        blocks = size_bytes // block_size

        if progress_cb:
            try:
                progress_cb(f"Disk benchmark ({drive_clean}): writing {size_mb} MB...")
            except Exception:
                pass

        # Write test
        t0 = time.perf_counter()
        with open(tmp_path, "wb", buffering=0) as f:
            for _ in range(blocks):
                f.write(data_block)
            f.flush()
            os.fsync(f.fileno())
        write_elapsed = time.perf_counter() - t0
        write_mbps = (size_bytes / 1024 / 1024) / write_elapsed if write_elapsed > 0 else 0.0

        if progress_cb:
            try:
                progress_cb(f"Disk write: {write_mbps:.0f} MB/s")
            except Exception:
                pass

        # Read test
        t1 = time.perf_counter()
        total_read = 0
        with open(tmp_path, "rb", buffering=0) as f:
            while True:
                chunk = f.read(block_size)
                if not chunk:
                    break
                total_read += len(chunk)
        read_elapsed = time.perf_counter() - t1
        read_mbps = (total_read / 1024 / 1024) / read_elapsed if read_elapsed > 0 else 0.0

        if progress_cb:
            try:
                progress_cb(f"Disk read: {read_mbps:.0f} MB/s")
            except Exception:
                pass

        avg_mbps = (read_mbps + write_mbps) / 2
        score = _clamp_score(avg_mbps / _REF_DISK_MBPS * 100)

        result = {
            "read_mbps":  round(read_mbps, 2),
            "write_mbps": round(write_mbps, 2),
            "score":      score,
            "drive":      drive_clean,
        }
        logger.info("disk_benchmark %s: read=%.1f write=%.1f score=%d", drive_clean, read_mbps, write_mbps, score)

    except PermissionError as exc:
        logger.warning("disk_benchmark: permission denied on %s: %s", drive, exc)
        result["error"] = f"Permission denied: {exc}"
    except OSError as exc:
        logger.warning("disk_benchmark: OS error on %s: %s", drive, exc)
        result["error"] = str(exc)
    except Exception as exc:
        logger.exception("disk_benchmark failed: %s", exc)
        result["error"] = str(exc)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return result


# ---------------------------------------------------------------------------
# Combined run
# ---------------------------------------------------------------------------

def run_all(progress_cb: Optional[Callable[[str], None]] = None) -> dict:
    """
    Run CPU, RAM, and disk benchmarks and return a combined result.

    Args:
        progress_cb: Optional callable receiving status strings.

    Returns:
        {cpu, ram, disk, overall_score, timestamp}
    """
    combined: dict = {
        "cpu": {},
        "ram": {},
        "disk": {},
        "overall_score": 0,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    try:
        if progress_cb:
            try:
                progress_cb("Starting CPU benchmark...")
            except Exception:
                pass
        combined["cpu"] = cpu_benchmark(duration_sec=5, progress_cb=progress_cb)

        if progress_cb:
            try:
                progress_cb("Starting RAM benchmark...")
            except Exception:
                pass
        combined["ram"] = ram_benchmark(size_mb=256, progress_cb=progress_cb)

        if progress_cb:
            try:
                progress_cb("Starting Disk benchmark...")
            except Exception:
                pass
        combined["disk"] = disk_benchmark(drive="C:", size_mb=100, progress_cb=progress_cb)

        # Overall score: equal-weighted average of the three sub-scores
        cpu_score  = combined["cpu"].get("score", 0)
        ram_score  = combined["ram"].get("score", 0)
        disk_score = combined["disk"].get("score", 0)
        combined["overall_score"] = _clamp_score((cpu_score + ram_score + disk_score) / 3)

        if progress_cb:
            try:
                progress_cb(f"Benchmark complete. Overall score: {combined['overall_score']}/100")
            except Exception:
                pass

        logger.info("run_all: overall_score=%d", combined["overall_score"])

    except Exception as exc:
        logger.exception("run_all failed: %s", exc)
        combined["error"] = str(exc)

    return combined
