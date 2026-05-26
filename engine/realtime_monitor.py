"""Real-time Monitor — continuous system metrics tracking with time-series data."""

import threading
import time
from collections import deque
from datetime import datetime, timedelta

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_HISTORY_SIZE = 1440  # 24 hours at 1-minute intervals
_SAMPLE_INTERVAL = 60  # Sample every 60 seconds

_lock = threading.Lock()

_cpu_history = deque(maxlen=_HISTORY_SIZE)
_ram_history = deque(maxlen=_HISTORY_SIZE)
_disk_history = deque(maxlen=_HISTORY_SIZE)
_network_history = deque(maxlen=_HISTORY_SIZE)
_temp_history = deque(maxlen=_HISTORY_SIZE)

_last_net_counters = None
_monitor_thread = None
_stop_event = threading.Event()
_alerts = []


class MetricSample:
    """Represents a single metric sample at a point in time."""
    def __init__(self, timestamp: datetime, value: float, unit: str = ""):
        self.timestamp = timestamp
        self.value = value
        self.unit = unit


class AlertEvent:
    """Represents a threshold alert."""
    def __init__(self, metric: str, timestamp: datetime, value: float, threshold: float, severity: str):
        self.metric = metric
        self.timestamp = timestamp
        self.value = value
        self.threshold = threshold
        self.severity = severity  # "INFO", "WARNING", "CRITICAL"


def _monitor_loop():
    """Background monitoring thread."""
    global _last_net_counters

    while not _stop_event.is_set():
        if not _PSUTIL:
            time.sleep(_SAMPLE_INTERVAL)
            continue

        try:
            now = datetime.now()

            # CPU
            cpu_pct = psutil.cpu_percent(interval=1)
            with _lock:
                _cpu_history.append(MetricSample(now, cpu_pct, "%"))

            # RAM
            mem = psutil.virtual_memory()
            with _lock:
                _ram_history.append(MetricSample(now, mem.percent, "%"))

            # Disk
            disk = psutil.disk_usage("C:\\")
            with _lock:
                _disk_history.append(MetricSample(now, disk.percent, "%"))

            # Network (delta)
            net = psutil.net_io_counters()
            if _last_net_counters:
                bytes_sent_delta = max(0, (net.bytes_sent - _last_net_counters.bytes_sent) / (1024**2))  # MB
                bytes_recv_delta = max(0, (net.bytes_recv - _last_net_counters.bytes_recv) / (1024**2))
                total_mbps = (bytes_sent_delta + bytes_recv_delta) / max(1, _SAMPLE_INTERVAL)

                with _lock:
                    _network_history.append(MetricSample(now, total_mbps, "MB/s"))

            _last_net_counters = net

            # Check thresholds
            _check_alerts(cpu_pct, mem.percent, disk.percent)

        except Exception:
            pass

        _stop_event.wait(_SAMPLE_INTERVAL)


def _check_alerts(cpu: float, ram: float, disk: float):
    """Check metrics against alert thresholds."""
    now = datetime.now()

    if cpu > 90:
        _add_alert(AlertEvent("CPU", now, cpu, 90, "CRITICAL"))
    elif cpu > 75:
        _add_alert(AlertEvent("CPU", now, cpu, 75, "WARNING"))

    if ram > 90:
        _add_alert(AlertEvent("RAM", now, ram, 90, "CRITICAL"))
    elif ram > 80:
        _add_alert(AlertEvent("RAM", now, ram, 80, "WARNING"))

    if disk > 95:
        _add_alert(AlertEvent("Disk", now, disk, 95, "CRITICAL"))
    elif disk > 90:
        _add_alert(AlertEvent("Disk", now, disk, 90, "WARNING"))


def _add_alert(alert: AlertEvent):
    """Add alert if not duplicate."""
    global _alerts

    with _lock:
        # Avoid duplicate alerts within 5 minutes
        for existing in _alerts[-5:]:
            if (existing.metric == alert.metric and
                (alert.timestamp - existing.timestamp).total_seconds() < 300):
                return

        _alerts.append(alert)
        if len(_alerts) > 500:
            _alerts = _alerts[-500:]


def start_monitoring() -> bool:
    """Start real-time monitoring thread."""
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
    """Stop monitoring thread."""
    _stop_event.set()
    if _monitor_thread:
        _monitor_thread.join(timeout=5)


def get_current_metrics() -> dict:
    """Get current metrics snapshot."""
    if not _PSUTIL:
        return {}

    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        return {
            "cpu": cpu,
            "ram": mem.percent,
            "disk": disk.percent,
            "ram_used_gb": mem.used / (1024**3),
            "ram_total_gb": mem.total / (1024**3),
            "disk_used_gb": disk.used / (1024**3),
            "disk_total_gb": disk.total / (1024**3),
        }
    except Exception:
        return {}


def get_metric_history(metric: str, minutes: int = 60) -> list[MetricSample]:
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
            return []

    # Filter to requested time range
    cutoff = datetime.now() - timedelta(minutes=minutes)
    return [s for s in history if s.timestamp >= cutoff]


def get_peak_metrics(minutes: int = 60) -> dict:
    """Get peak values over time period."""
    cpu_hist = get_metric_history("cpu", minutes)
    ram_hist = get_metric_history("ram", minutes)
    disk_hist = get_metric_history("disk", minutes)

    cpu_values = [s.value for s in cpu_hist]
    ram_values = [s.value for s in ram_hist]
    disk_values = [s.value for s in disk_hist]

    return {
        "cpu_peak": max(cpu_values) if cpu_values else 0,
        "cpu_avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
        "ram_peak": max(ram_values) if ram_values else 0,
        "ram_avg": sum(ram_values) / len(ram_values) if ram_values else 0,
        "disk_peak": max(disk_values) if disk_values else 0,
        "disk_avg": sum(disk_values) / len(disk_values) if disk_values else 0,
    }


def get_recent_alerts(metric: str = None, limit: int = 20) -> list[AlertEvent]:
    """Get recent alert events."""
    with _lock:
        alerts = list(_alerts)

    if metric:
        alerts = [a for a in alerts if a.metric == metric]

    return alerts[-limit:]


def get_alerts_summary() -> dict:
    """Get summary of recent alerts."""
    with _lock:
        alerts = list(_alerts[-100:])

    critical = sum(1 for a in alerts if a.severity == "CRITICAL")
    warning = sum(1 for a in alerts if a.severity == "WARNING")

    return {
        "total_alerts": len(alerts),
        "critical_count": critical,
        "warning_count": warning,
        "last_alert_time": alerts[-1].timestamp.isoformat() if alerts else None,
    }


def get_trend(metric: str, minutes: int = 60) -> str:
    """Get trend direction (up, down, stable)."""
    history = get_metric_history(metric, minutes)
    if len(history) < 2:
        return "unknown"

    first_half = [s.value for s in history[:len(history)//2]]
    second_half = [s.value for s in history[len(history)//2:]]

    if not first_half or not second_half:
        return "unknown"

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    diff = avg_second - avg_first
    if abs(diff) < 2:
        return "stable"
    elif diff > 0:
        return "increasing"
    else:
        return "decreasing"


def clear_alerts():
    """Clear alert history."""
    global _alerts
    with _lock:
        _alerts = []
