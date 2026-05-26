"""Bandwidth Monitor — real-time network usage per process and adapter."""

import time
import threading
from collections import deque

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

# Rolling history: last 60 samples (at 1-second intervals)
_HISTORY_LEN = 60
_history_lock = threading.Lock()
_net_history: deque = deque(maxlen=_HISTORY_LEN)
_prev_counters = {}
_monitor_thread = None
_stop_event = threading.Event()


def _sample_net() -> dict:
    """Take a single network IO sample. Returns {adapter: {sent, recv}} in bytes/sec."""
    if not _PSUTIL:
        return {}

    try:
        counters = psutil.net_io_counters(pernic=True)
        now = time.time()
        result = {}

        for nic, stats in counters.items():
            if nic in _prev_counters:
                prev, prev_time = _prev_counters[nic]
                dt = max(now - prev_time, 0.001)
                sent_rate = max(0, (stats.bytes_sent - prev.bytes_sent) / dt)
                recv_rate = max(0, (stats.bytes_recv - prev.bytes_recv) / dt)
                result[nic] = {
                    "sent_rate": sent_rate,
                    "recv_rate": recv_rate,
                    "sent_rate_str": _fmt_bytes(sent_rate) + "/s",
                    "recv_rate_str": _fmt_bytes(recv_rate) + "/s",
                    "total_sent": stats.bytes_sent,
                    "total_recv": stats.bytes_recv,
                }
            _prev_counters[nic] = (stats, now)

        return result
    except Exception:
        return {}


def _monitor_loop():
    """Background thread sampling network every second."""
    global _prev_counters
    # Prime the counters
    if _PSUTIL:
        try:
            counters = psutil.net_io_counters(pernic=True)
            now = time.time()
            for nic, stats in counters.items():
                _prev_counters[nic] = (stats, now)
        except Exception:
            pass

    while not _stop_event.is_set():
        sample = _sample_net()
        if sample:
            with _history_lock:
                _net_history.append((time.time(), sample))
        _stop_event.wait(1)


def start_monitor() -> bool:
    """Start background network monitoring. Returns True if started."""
    global _monitor_thread
    if not _PSUTIL:
        return False
    if _monitor_thread and _monitor_thread.is_alive():
        return True
    _stop_event.clear()
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    return True


def stop_monitor():
    _stop_event.set()


def get_current_rates() -> dict:
    """Return latest network rates per adapter."""
    with _history_lock:
        if not _net_history:
            return {}
        _, latest = _net_history[-1]
        return latest


def get_history(adapter: str = None, seconds: int = 60) -> list[dict]:
    """Return rate history for charting. Each entry: {time, sent_rate, recv_rate}."""
    with _history_lock:
        recent = list(_net_history)[-seconds:]

    result = []
    for ts, sample in recent:
        if adapter:
            data = sample.get(adapter, {})
            result.append({
                "time": ts,
                "sent_rate": data.get("sent_rate", 0),
                "recv_rate": data.get("recv_rate", 0),
            })
        else:
            # Sum all adapters
            total_sent = sum(v.get("sent_rate", 0) for v in sample.values())
            total_recv = sum(v.get("recv_rate", 0) for v in sample.values())
            result.append({
                "time": ts,
                "sent_rate": total_sent,
                "recv_rate": total_recv,
            })
    return result


_proc_io_prev: dict[int, tuple[float, int, int]] = {}
_proc_io_lock = threading.Lock()


def get_top_processes(n: int = 10) -> list[dict]:
    """Return top N processes by I/O bandwidth (read+write bytes/sec).

    Uses psutil's per-process io_counters as a proxy for bandwidth. This
    captures all I/O (network + disk) but is the best available without ETW.
    Filters to processes with active network connections to bias toward
    network activity.
    """
    if not _PSUTIL:
        return []

    now = time.time()
    results = []
    with _proc_io_lock:
        prev = dict(_proc_io_prev)
        new_state: dict[int, tuple[float, int, int]] = {}

    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = proc.pid
                # Filter: only processes with at least one connection
                conns = proc.connections(kind="inet")
                established = sum(1 for c in conns if c.status == "ESTABLISHED")
                if not conns:
                    continue
                try:
                    io = proc.io_counters()
                except (psutil.AccessDenied, AttributeError):
                    continue

                read_bytes = getattr(io, "read_bytes", 0)
                write_bytes = getattr(io, "write_bytes", 0)
                new_state[pid] = (now, read_bytes, write_bytes)

                rate_bps = 0.0
                if pid in prev:
                    prev_t, prev_r, prev_w = prev[pid]
                    dt = max(now - prev_t, 0.001)
                    delta = max(0, (read_bytes + write_bytes) - (prev_r + prev_w))
                    rate_bps = delta / dt

                results.append({
                    "pid": pid,
                    "name": proc.name(),
                    "connections": established,
                    "total_connections": len(conns),
                    "io_rate_bps": rate_bps,
                    "io_rate_str": _fmt_bytes(rate_bps) + "/s",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

    with _proc_io_lock:
        _proc_io_prev.clear()
        _proc_io_prev.update(new_state)

    return sorted(results,
                   key=lambda x: (x["io_rate_bps"], x["connections"]),
                   reverse=True)[:n]


def get_adapters() -> list[str]:
    """Return list of active network adapter names."""
    if not _PSUTIL:
        return []
    try:
        stats = psutil.net_if_stats()
        return [name for name, s in stats.items() if s.isup]
    except Exception:
        return []


def _fmt_bytes(b: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"
