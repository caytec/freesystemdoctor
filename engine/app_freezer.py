"""App Freezer — suspend and resume background processes to free CPU/RAM."""

import os
try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SYSTEM_BLACKLIST = frozenset([
    "system", "registry", "csrss", "winlogon", "svchost", "lsass",
    "lsm", "smss", "wininit", "services", "dwm", "conhost",
    "explorer", "taskhostw", "sihost", "fontdrvhost", "runtimebroker",
])

_frozen_pids: set[int] = set()


def get_background_processes() -> list[dict]:
    """Enumerate non-system processes suitable for freezing.
    Returns list of dicts: name, pid, cpu_percent, ram_mb, status."""
    if not _PSUTIL:
        return []

    results = []
    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
            try:
                if proc.pid == 0 or proc.pid == os.getpid():
                    continue
                name = proc.name().lower()
                if not is_safe_to_freeze(name):
                    continue
                status = "Frozen" if proc.pid in _frozen_pids or proc.status() == "stopped" else "Running"
                ram_mb = proc.memory_info().rss // (1024 * 1024)
                results.append({
                    "pid": proc.pid,
                    "name": proc.name(),
                    "cpu_percent": proc.cpu_percent(interval=None),
                    "ram_mb": ram_mb,
                    "status": status,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass

    results.sort(key=lambda x: x["cpu_percent"], reverse=True)
    return results


def freeze_process(pid: int) -> bool:
    """Suspend a process. Adds pid to _frozen_pids on success. Returns True on success."""
    if not _PSUTIL:
        return False

    try:
        name = psutil.Process(pid).name().lower()
        if not is_safe_to_freeze(name):
            return False
        psutil.Process(pid).suspend()
        _frozen_pids.add(pid)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return False


def unfreeze_process(pid: int) -> bool:
    """Resume a process. Removes pid from _frozen_pids on success. Returns True on success."""
    if not _PSUTIL:
        return False

    try:
        psutil.Process(pid).resume()
        _frozen_pids.discard(pid)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return False


def unfreeze_all() -> tuple[int, int]:
    """Unfreeze all tracked frozen processes. Returns (unfrozen_count, error_count)."""
    if not _PSUTIL:
        return 0, 0

    unfrozen = 0
    errors = 0
    pids_to_unfreeze = list(_frozen_pids)
    for pid in pids_to_unfreeze:
        if unfreeze_process(pid):
            unfrozen += 1
        else:
            errors += 1
    return unfrozen, errors


def is_frozen(pid: int) -> bool:
    """Check if process status is 'stopped' or pid is in _frozen_pids."""
    if not _PSUTIL:
        return False

    if pid in _frozen_pids:
        return True

    try:
        return psutil.Process(pid).status() == "stopped"
    except Exception:
        return False


def is_safe_to_freeze(name: str) -> bool:
    """Return True if process name is NOT in the system blacklist."""
    name_lower = name.lower()
    return not any(b in name_lower for b in _SYSTEM_BLACKLIST)
