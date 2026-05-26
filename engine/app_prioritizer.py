"""App Priority Manager — set Windows CPU scheduling priority for running processes."""

import os
try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

# Windows priority class constants mapped to friendly names
if _PSUTIL:
    PRIORITY_CLASSES = {
        "IDLE":         psutil.IDLE_PRIORITY_CLASS,
        "BELOW_NORMAL": psutil.BELOW_NORMAL_PRIORITY_CLASS,
        "NORMAL":       psutil.NORMAL_PRIORITY_CLASS,
        "ABOVE_NORMAL": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
        "HIGH":         psutil.HIGH_PRIORITY_CLASS,
    }
else:
    PRIORITY_CLASSES = {
        "IDLE":         0x00000040,
        "BELOW_NORMAL": 0x00004000,
        "NORMAL":       0x00000020,
        "ABOVE_NORMAL": 0x00008000,
        "HIGH":         0x00000080,
    }

PRIORITY_NAMES = {v: k for k, v in PRIORITY_CLASSES.items()}


def get_running_processes() -> list[dict]:
    """Return list of running processes with name, pid, cpu_percent, memory_percent, priority.
    Returns empty list if psutil unavailable."""
    if not _PSUTIL:
        return []

    results = []
    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                if proc.pid == 0:
                    continue
                priority_class = proc.nice()
                priority_name = PRIORITY_NAMES.get(priority_class, "UNKNOWN")
                results.append({
                    "pid": proc.pid,
                    "name": proc.name(),
                    "cpu_percent": proc.cpu_percent(interval=None),
                    "memory_percent": proc.memory_percent(),
                    "priority": priority_name,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass

    results.sort(key=lambda x: x["cpu_percent"], reverse=True)
    return results


def get_priority_name(pid: int) -> str:
    """Return the human-readable priority class name for a given PID. Returns 'UNKNOWN' on error."""
    if not _PSUTIL:
        return "UNKNOWN"

    try:
        proc = psutil.Process(pid)
        priority_class = proc.nice()
        return PRIORITY_NAMES.get(priority_class, "UNKNOWN")
    except Exception:
        return "UNKNOWN"


def set_process_priority(pid: int, priority_class_name: str) -> bool:
    """Set process priority by name key (e.g. 'ABOVE_NORMAL'). Returns True on success."""
    if not _PSUTIL:
        return False

    if priority_class_name not in PRIORITY_CLASSES:
        return False

    try:
        proc = psutil.Process(pid)
        proc.nice(PRIORITY_CLASSES[priority_class_name])
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
        return False


def boost_process(pid: int) -> bool:
    """Convenience: set process to ABOVE_NORMAL priority."""
    return set_process_priority(pid, "ABOVE_NORMAL")


def set_normal_priority(pid: int) -> bool:
    """Convenience: reset process to NORMAL priority."""
    return set_process_priority(pid, "NORMAL")


def set_high_priority(pid: int) -> bool:
    """Convenience: set process to HIGH priority."""
    return set_process_priority(pid, "HIGH")
