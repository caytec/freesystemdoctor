"""System information and real-time health monitoring."""

import os
import platform
import subprocess
from datetime import datetime, timedelta

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


# ── static info ───────────────────────────────────────────────────────────────

def get_static_info() -> dict:
    info = {
        "OS": platform.platform(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor() or "N/A",
        "Hostname": platform.node(),
        "Python": platform.python_version(),
    }

    if _PSUTIL:
        cpu_freq = psutil.cpu_freq()
        info["CPU Cores (Physical)"] = str(psutil.cpu_count(logical=False))
        info["CPU Cores (Logical)"] = str(psutil.cpu_count(logical=True))
        if cpu_freq:
            info["CPU Max Freq"] = f"{cpu_freq.max:.0f} MHz"

        mem = psutil.virtual_memory()
        info["RAM Total"] = _fmt_bytes(mem.total)

        boot_ts = psutil.boot_time()
        boot_dt = datetime.fromtimestamp(boot_ts)
        uptime = datetime.now() - boot_dt
        info["Boot Time"] = boot_dt.strftime("%Y-%m-%d %H:%M")
        info["Uptime"] = str(timedelta(seconds=int(uptime.total_seconds())))

    return info


def get_disk_info() -> list[dict]:
    if not _PSUTIL:
        return []
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "Drive": part.device,
                "Mount": part.mountpoint,
                "FS": part.fstype,
                "Total": _fmt_bytes(usage.total),
                "Used": _fmt_bytes(usage.used),
                "Free": _fmt_bytes(usage.free),
                "Used %": f"{usage.percent:.1f}%",
                "used_pct": usage.percent,
            })
        except PermissionError:
            pass
    return disks


# ── live metrics ──────────────────────────────────────────────────────────────

def get_live_metrics() -> dict:
    if not _PSUTIL:
        return {}

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=0.3)

    metrics = {
        "cpu_pct": cpu,
        "ram_pct": mem.percent,
        "ram_used_str": _fmt_bytes(mem.used),
        "ram_total_str": _fmt_bytes(mem.total),
        "swap_pct": swap.percent,
        "swap_used_str": _fmt_bytes(swap.used),
    }

    battery = psutil.sensors_battery()
    if battery:
        metrics["battery_pct"] = battery.percent
        metrics["battery_plugged"] = battery.power_plugged

    return metrics


def get_top_processes(n: int = 15) -> list[dict]:
    if not _PSUTIL:
        return []
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "status"]):
        try:
            procs.append({
                "PID": p.info["pid"],
                "Name": p.info["name"],
                "CPU %": round(p.info["cpu_percent"] or 0, 1),
                "RAM %": round(p.info["memory_percent"] or 0, 2),
                "Status": p.info["status"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: x["RAM %"], reverse=True)[:n]


# ── health score ──────────────────────────────────────────────────────────────

def get_health_score() -> tuple[int, list[str]]:
    """Return (0-100 score, list-of-issue-strings)."""
    if not _PSUTIL:
        return 50, ["psutil not installed"]

    score = 100
    issues = []

    mem = psutil.virtual_memory()
    if mem.percent > 90:
        score -= 25
        issues.append(f"Critical RAM usage: {mem.percent:.0f}%")
    elif mem.percent > 75:
        score -= 10
        issues.append(f"High RAM usage: {mem.percent:.0f}%")

    cpu = psutil.cpu_percent(interval=0.5)
    if cpu > 90:
        score -= 20
        issues.append(f"Critical CPU usage: {cpu:.0f}%")
    elif cpu > 70:
        score -= 8
        issues.append(f"High CPU usage: {cpu:.0f}%")

    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            if usage.percent > 95:
                score -= 20
                issues.append(f"Disk {part.device} almost full ({usage.percent:.0f}%)")
            elif usage.percent > 85:
                score -= 8
                issues.append(f"Disk {part.device} running low ({usage.percent:.0f}%)")
        except PermissionError:
            pass

    battery = psutil.sensors_battery()
    if battery and not battery.power_plugged and battery.percent < 15:
        score -= 10
        issues.append(f"Low battery: {battery.percent:.0f}%")

    return max(0, score), issues
