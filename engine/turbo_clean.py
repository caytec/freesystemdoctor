"""Turbo Clean — one-click rapid cleanup orchestrator.

Chains the most-impactful operations:
- Trim working sets (free RAM)
- Empty recycle bin
- Delete %TEMP% files older than 1h
- Flush DNS cache

Designed to run from the HUD widget's Turbo button. Background thread; emits
progress callbacks at each step.
"""

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

try:
    from . import disk_cleaner
except Exception:
    disk_cleaner = None

try:
    from . import memory_optimizer
except Exception:
    memory_optimizer = None


def _delete_tree(path: Path) -> int:
    freed = 0
    try:
        if not path.exists():
            return 0
        for f in path.rglob("*"):
            try:
                if f.is_file():
                    s = f.stat().st_size
                    f.unlink(missing_ok=True)
                    freed += s
            except Exception:
                pass
    except Exception:
        pass
    return freed


def _clean_temp(min_age_hours: float = 1.0) -> int:
    """Delete temp files older than min_age_hours. Returns bytes freed."""
    freed = 0
    candidates = [
        Path(os.environ.get("TEMP", "")),
        Path(os.environ.get("TMP", "")),
        Path("C:/Windows/Temp"),
    ]
    cutoff = time.time() - min_age_hours * 3600
    seen = set()
    for base in candidates:
        if not base or not base.exists() or str(base) in seen:
            continue
        seen.add(str(base))
        for f in base.rglob("*"):
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    s = f.stat().st_size
                    f.unlink(missing_ok=True)
                    freed += s
            except Exception:
                pass
    return freed


def _flush_dns() -> bool:
    try:
        r = subprocess.run(["ipconfig", "/flushdns"],
                            capture_output=True, text=True, timeout=8,
                            creationflags=0x08000000)
        return r.returncode == 0
    except Exception:
        return False


def run(progress_cb=None) -> dict:
    """Run all turbo steps. Returns a stats dict."""
    stats = {"ram_freed_mb": 0, "disk_freed_mb": 0, "recycle_emptied": False,
             "dns_flushed": False, "errors": []}

    def emit(step: str, pct: int):
        if progress_cb:
            try:
                progress_cb(step, pct)
            except Exception:
                pass

    # 1. Trim working sets
    emit("Freeing RAM…", 10)
    try:
        import psutil
        ram_before = psutil.virtual_memory().available
        if memory_optimizer:
            # trim_working_sets returns (processes_trimmed, errors); ignore both
            memory_optimizer.trim_working_sets()
        ram_after = psutil.virtual_memory().available
        stats["ram_freed_mb"] = max(0, (ram_after - ram_before) / 1024 / 1024)
    except Exception as e:
        stats["errors"].append(f"RAM trim: {e}")

    # 2. Clean temp files
    emit("Removing temp files…", 35)
    try:
        freed = _clean_temp(min_age_hours=1.0)
        stats["disk_freed_mb"] += freed / 1024 / 1024
    except Exception as e:
        stats["errors"].append(f"Temp clean: {e}")

    # 3. Empty recycle bin
    emit("Emptying recycle bin…", 65)
    try:
        if disk_cleaner:
            if disk_cleaner.empty_recycle_bin():
                stats["recycle_emptied"] = True
    except Exception as e:
        stats["errors"].append(f"Recycle bin: {e}")

    # 4. Flush DNS
    emit("Flushing DNS cache…", 85)
    stats["dns_flushed"] = _flush_dns()

    emit("Done", 100)
    return stats


def run_async(progress_cb=None, done_cb=None) -> threading.Thread:
    def _worker():
        result = run(progress_cb)
        if done_cb:
            try: done_cb(result)
            except Exception: pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t
