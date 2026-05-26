"""Resource Monitor — real-time CPU/RAM/Disk/Network monitoring with alerts."""

import threading
import time
from collections import deque
from datetime import datetime

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_HISTORY_LEN = 60  # Keep last 60 samples
_monitor_thread = None
_stop_event = threading.Event()
_lock = threading.Lock()

_cpu_history = deque(maxlen=_HISTORY_LEN)
_ram_history = deque(maxlen=_HISTORY_LEN)
_disk_history = deque(maxlen=_HISTORY_LEN)
_network_history = deque(maxlen=_HISTORY_LEN)

_alerts = []


def _monitor_loop():
    """Background monitoring loop."""
    while not _stop_event.is_set():
        if _PSUTIL:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage("C:\\").percent
                net = psutil.net_io_counters()

                with _lock:
                    _cpu_history.append({"time": datetime.now(), "value": cpu})
                    _ram_history.append({"time": datetime.now(), "value": ram})
                    _disk_history.append({"time": datetime.now(), "value": disk})
                    _network_history.append({
                        "time": datetime.now(),
                        "sent": net.bytes_sent,
                        "recv": net.bytes_recv
                    })

                    # Check for alerts
                    if cpu > 90:
                        _add_alert("HIGH", f"CPU usage critical: {cpu:.0f}%")
                    elif cpu > 75:
                        _add_alert("WARNING", f"CPU usage high: {cpu:.0f}%")

                    if ram > 90:
                        _add_alert("HIGH", f"RAM usage critical: {ram:.0f}%")
                    elif ram > 80:
                        _add_alert("WARNING", f"RAM usage high: {ram:.0f}%")

                    if disk > 95:
                        _add_alert("CRITICAL", f"Disk usage critical: {disk:.0f}%")
                    elif disk > 90:
                        _add_alert("HIGH", f"Disk usage high: {disk:.0f}%")

            except Exception:
                pass

        _stop_event.wait(2)


def _add_alert(severity: str, message: str):
    """Add an alert if not already recent."""
    global _alerts

    # Avoid duplicate alerts within 5 minutes
    now = datetime.now()
    for alert in _alerts[-5:]:
        if alert["message"] == message:
            if (now - alert["time"]).total_seconds() < 300:
                return

    _alerts.append({
        "severity": severity,
        "message": message,
        "time": now,
    })

    # Keep only last 100 alerts
    if len(_alerts) > 100:
        _alerts = _alerts[-100:]


def start_monitoring() -> bool:
    """Start background monitoring."""
    global _monitor_thread

    if not _PSUTIL:
        return False

    if _monitor_thread and _monitor_thread.is_alive():
        return True

    _stop_event.clear()
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    return True


def stop_monitoring():
    """Stop background monitoring."""
    _stop_event.set()


def get_current_metrics() -> dict:
    """Get current system metrics."""
    if not _PSUTIL:
        return {}

    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        net = psutil.net_io_counters()

        return {
            "cpu_percent": cpu,
            "ram_percent": mem.percent,
            "ram_available_gb": mem.available / (1024**3),
            "ram_used_gb": mem.used / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3),
            "disk_used_gb": disk.used / (1024**3),
            "network_sent_mb": net.bytes_sent / (1024**2),
            "network_recv_mb": net.bytes_recv / (1024**2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return {}


def get_history(metric: str = "cpu", samples: int = 60) -> list[dict]:
    """Get historical data for a metric."""
    with _lock:
        if metric == "cpu":
            history = list(_cpu_history)
        elif metric == "ram":
            history = list(_ram_history)
        elif metric == "disk":
            history = list(_disk_history)
        elif metric == "network":
            history = list(_network_history)
        else:
            history = []

    return history[-samples:]


def get_alerts(severity: str = None, limit: int = 20) -> list[dict]:
    """Get recent alerts."""
    with _lock:
        alerts = list(_alerts)

    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]

    return alerts[-limit:]


def get_peak_metrics(minutes: int = 60) -> dict:
    """Get peak metrics over a time period."""
    with _lock:
        cpu_values = [s["value"] for s in _cpu_history]
        ram_values = [s["value"] for s in _ram_history]
        disk_values = [s["value"] for s in _disk_history]

    return {
        "cpu_peak": max(cpu_values) if cpu_values else 0,
        "cpu_average": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
        "ram_peak": max(ram_values) if ram_values else 0,
        "ram_average": sum(ram_values) / len(ram_values) if ram_values else 0,
        "disk_peak": max(disk_values) if disk_values else 0,
    }


def get_top_processes(metric: str = "cpu", limit: int = 10) -> list[dict]:
    """Get top processes by CPU or RAM.

    psutil.cpu_percent() returns 0 on first call per-process — it needs a
    baseline. So for CPU we do a 2-pass: prime + sleep + read. For RAM
    a single pass is enough.
    """
    if not _PSUTIL:
        return []

    if metric == "cpu":
        # ── pass 1: prime every process's CPU baseline (returns 0 each)
        procs = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                p.cpu_percent(interval=None)   # prime
                procs.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # ── short wait to accumulate CPU time
        import time
        time.sleep(0.5)

        # ── pass 2: read actual values
        results = []
        n_cores = psutil.cpu_count() or 1
        for p in procs:
            try:
                # Divide by cores to express as % of total system CPU
                pct = p.cpu_percent(interval=None) / n_cores
                name = p.info.get("name") or f"PID {p.info['pid']}"
                # Skip Idle / empty / kernel placeholder rows
                if name in ("System Idle Process", "System", ""):
                    continue
                if pct <= 0:
                    continue
                results.append({
                    "pid": p.info["pid"],
                    "name": name,
                    "usage": pct,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        results.sort(key=lambda x: x["usage"], reverse=True)
        return results[:limit]

    # ── RAM metric (single-pass) ────────────────────────────────────────────
    results = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            mem = p.info.get("memory_percent") or 0
            name = p.info.get("name") or f"PID {p.info['pid']}"
            if name in ("System Idle Process", "System", "") or mem <= 0:
                continue
            results.append({
                "pid": p.info["pid"],
                "name": name,
                "usage": mem,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    results.sort(key=lambda x: x["usage"], reverse=True)
    return results[:limit]


def clear_alerts():
    """Clear alert history."""
    global _alerts
    with _lock:
        _alerts = []
