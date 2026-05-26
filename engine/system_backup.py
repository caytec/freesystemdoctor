"""System Backup — create system snapshots and recovery points."""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

_CONFIG_DIR = Path(os.environ.get("TEMP", ".")) / "FreeSystemDoctor"
_BACKUP_LIST = _CONFIG_DIR / "system_backups.json"


def _ensure_config_dir():
    """Ensure config directory exists."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def create_system_restore_point(name: str = None) -> dict:
    """Create a Windows System Restore Point."""
    if not name:
        name = f"FreeSystemDoctor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        result = subprocess.run(
            ["wmic", "os", "call", "CreateRestorePoint", f"'{name}'", "0"],
            capture_output=True,
            text=True,
            timeout=120, creationflags=0x08000000)

        if result.returncode == 0:
            return {
                "success": True,
                "type": "system_restore",
                "name": name,
                "timestamp": datetime.now().isoformat(),
                "message": "Restore point created successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to create restore point",
                "stderr": result.stderr
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_restore_points() -> list[dict]:
    """Get list of system restore points."""
    points = []

    try:
        result = subprocess.run(
            ["wmic", "path", "win32_shadowcopy", "get", "ID,InstallDate"],
            capture_output=True,
            text=True,
            timeout=10, creationflags=0x08000000)

        lines = result.stdout.strip().split("\n")
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    points.append({
                        "id": parts[0],
                        "timestamp": parts[1] if len(parts) > 1 else "Unknown",
                    })
    except Exception:
        pass

    return points


def list_backup_history() -> list[dict]:
    """List all FreeSystemDoctor backups created."""
    _ensure_config_dir()

    if _BACKUP_LIST.exists():
        try:
            with open(_BACKUP_LIST) as f:
                return json.load(f)
        except Exception:
            return []

    return []


def add_backup_record(backup_type: str, name: str, description: str = ""):
    """Record a backup in history."""
    _ensure_config_dir()

    record = {
        "type": backup_type,
        "name": name,
        "description": description,
        "timestamp": datetime.now().isoformat(),
        "size_mb": 0,
    }

    backups = list_backup_history()
    backups.append(record)

    try:
        with open(_BACKUP_LIST, "w") as f:
            json.dump(backups, f, indent=2)
    except Exception:
        pass


def backup_driver_list() -> dict:
    """Backup list of installed drivers."""
    try:
        backup_name = f"drivers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = _CONFIG_DIR / backup_name

        result = subprocess.run(
            ["driverquery", "/format:list"],
            capture_output=True,
            text=True,
            timeout=30, creationflags=0x08000000)

        with open(backup_path, "w") as f:
            f.write(result.stdout)

        add_backup_record("driver_list", backup_name, "Installed drivers snapshot")

        return {
            "success": True,
            "backup_name": backup_name,
            "path": str(backup_path),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_network_config() -> dict:
    """Backup network configuration."""
    try:
        backup_name = f"network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = _CONFIG_DIR / backup_name

        configs = {
            "ip_config": subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=10, creationflags=0x08000000).stdout,
            "dns_config": subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=10, creationflags=0x08000000).stdout,
            "route_table": subprocess.run(["route", "print"], capture_output=True, text=True, timeout=10, creationflags=0x08000000).stdout,
        }

        with open(backup_path, "w") as f:
            json.dump(configs, f, indent=2)

        add_backup_record("network_config", backup_name, "Network configuration snapshot")

        return {
            "success": True,
            "backup_name": backup_name,
            "path": str(backup_path),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_backup_size_mb(backup_name: str) -> float:
    """Get size of a backup in MB."""
    try:
        path = _CONFIG_DIR / backup_name
        if path.exists():
            return path.stat().st_size / (1024 * 1024)
    except Exception:
        pass
    return 0


def delete_backup(backup_name: str) -> bool:
    """Delete a backup file."""
    try:
        path = _CONFIG_DIR / backup_name
        if path.exists():
            path.unlink()

            backups = list_backup_history()
            backups = [b for b in backups if b["name"] != backup_name]
            with open(_BACKUP_LIST, "w") as f:
                json.dump(backups, f, indent=2)

            return True
    except Exception:
        pass
    return False
