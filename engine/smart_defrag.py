"""Smart Defragmentation — optimize SSD/HDD with intelligent scheduling."""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_CONFIG_DIR = Path(os.environ.get("TEMP", ".")) / "FreeSystemDoctor"
_DEFRAG_CONFIG = _CONFIG_DIR / "defrag_config.json"


def _ensure_config_dir():
    """Ensure config directory exists."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_drives() -> list[dict]:
    """Get list of drives with optimization stats."""
    if not _PSUTIL:
        return []

    drives = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            drives.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
                "total_str": _fmt_bytes(usage.total),
                "free_str": _fmt_bytes(usage.free),
                "used_str": _fmt_bytes(usage.used),
                "is_ssd": _detect_ssd(partition.mountpoint),
            })
        except Exception:
            pass

    return drives


def _detect_ssd(drive: str) -> bool:
    """Detect if drive is SSD or HDD."""
    try:
        result = subprocess.run(
            ["fsutil", "fsinfo", "ntfsinfo", f"{drive}\\"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # SSDs typically show different characteristics
        # For now, assume all are HDD unless proven otherwise
        return False
    except Exception:
        return False


def optimize_drive(drive: str, progress_cb=None) -> dict:
    """Optimize a drive (defrag HDD, trim SSD)."""
    is_ssd = _detect_ssd(drive)

    try:
        if is_ssd:
            return _optimize_ssd(drive, progress_cb)
        else:
            return _optimize_hdd(drive, progress_cb)
    except Exception as e:
        return {"success": False, "error": str(e), "drive": drive}


def _optimize_ssd(drive: str, progress_cb=None) -> dict:
    """Optimize SSD with TRIM command."""
    if progress_cb:
        progress_cb(10, "Running TRIM on SSD...")

    try:
        result = subprocess.run(
            ["optimize-volume", "-DriveLetter", drive[0], "-Defrag", "-TrimOnly"],
            capture_output=True,
            text=True,
            timeout=300
        )

        if progress_cb:
            progress_cb(100, "SSD TRIM complete")

        return {
            "success": result.returncode == 0,
            "type": "ssd",
            "drive": drive,
            "method": "TRIM",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "drive": drive, "type": "ssd"}


def _optimize_hdd(drive: str, progress_cb=None) -> dict:
    """Optimize HDD with defragmentation."""
    if progress_cb:
        progress_cb(10, "Starting HDD defragmentation...")

    try:
        result = subprocess.run(
            ["defrag", f"{drive}\\", "/U", "/V"],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        if progress_cb:
            progress_cb(100, "HDD defragmentation complete")

        return {
            "success": result.returncode == 0,
            "type": "hdd",
            "drive": drive,
            "method": "Defrag",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "drive": drive, "type": "hdd"}


def get_optimization_schedule() -> dict:
    """Get drive optimization schedule."""
    _ensure_config_dir()

    if _DEFRAG_CONFIG.exists():
        try:
            with open(_DEFRAG_CONFIG) as f:
                return json.load(f)
        except Exception:
            pass

    default_schedule = {
        "enabled": False,
        "ssd_trim_interval_days": 30,
        "hdd_defrag_interval_days": 7,
        "preferred_time": "02:00",  # 2 AM
        "last_optimization": {},
    }

    save_optimization_schedule(default_schedule)
    return default_schedule


def save_optimization_schedule(schedule: dict):
    """Save optimization schedule."""
    _ensure_config_dir()
    try:
        with open(_DEFRAG_CONFIG, "w") as f:
            json.dump(schedule, f, indent=2)
    except Exception:
        pass


def should_optimize(drive: str) -> bool:
    """Check if drive needs optimization based on schedule."""
    schedule = get_optimization_schedule()
    if not schedule.get("enabled"):
        return False

    is_ssd = _detect_ssd(drive)
    interval_days = schedule.get("ssd_trim_interval_days" if is_ssd else "hdd_defrag_interval_days")

    last_opt = schedule.get("last_optimization", {}).get(drive)
    if not last_opt:
        return True

    try:
        last_date = datetime.fromisoformat(last_opt)
        next_date = last_date + timedelta(days=interval_days)
        return datetime.now() >= next_date
    except Exception:
        return True


def optimize_all_drives(progress_cb=None) -> list[dict]:
    """Optimize all drives that need it."""
    results = []
    drives = get_drives()

    for i, drive_info in enumerate(drives):
        if should_optimize(drive_info["mountpoint"]):
            if progress_cb:
                pct = int((i / len(drives)) * 100)
                progress_cb(pct, f"Optimizing {drive_info['device']}...")

            result = optimize_drive(drive_info["mountpoint"], progress_cb)
            results.append(result)

    # Update last optimization time
    schedule = get_optimization_schedule()
    for drive in [d["mountpoint"] for d in drives]:
        schedule["last_optimization"][drive] = datetime.now().isoformat()
    save_optimization_schedule(schedule)

    return results


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
