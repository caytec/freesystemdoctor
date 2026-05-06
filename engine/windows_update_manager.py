"""Windows Update Manager — control, schedule, and optimize Windows Updates."""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

_CONFIG_DIR = Path(os.environ.get("TEMP", ".")) / "FreeSystemDoctor"
_UPDATE_CONFIG = _CONFIG_DIR / "windows_update_config.json"


def _ensure_config_dir():
    """Ensure config directory exists."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_update_status() -> dict:
    """Get current Windows Update status."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-WmiObject -Namespace \"root\\cimv2\" -Class Win32_WindowsUpdate | Select-Object -Property Status,Description"],
            capture_output=True,
            text=True,
            timeout=10
        )

        pending_updates = result.stdout.count("Status")
        return {
            "pending_updates": pending_updates,
            "status": "Updates available" if pending_updates > 0 else "System up to date",
            "last_check": _get_last_update_time(),
        }
    except Exception:
        return {"pending_updates": 0, "status": "Unable to check", "last_check": None}


def _get_last_update_time() -> str:
    """Get timestamp of last Windows Update check."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update' | Select-Object -ExpandProperty 'LastSuccessfulRun'"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() if result.stdout else "Unknown"
    except Exception:
        return "Unknown"


def get_update_config() -> dict:
    """Load or create update configuration."""
    _ensure_config_dir()

    if _UPDATE_CONFIG.exists():
        try:
            with open(_UPDATE_CONFIG) as f:
                return json.load(f)
        except Exception:
            pass

    default_config = {
        "auto_install": True,
        "install_time": "03:00",  # 3 AM
        "restart_behavior": "auto",  # "auto", "manual", "never"
        "notify_before_restart": True,
        "defer_updates_days": 0,
        "excluded_kb": [],  # KBxxxx numbers to exclude
        "last_check": None,
        "check_frequency_hours": 24,
    }

    save_update_config(default_config)
    return default_config


def save_update_config(config: dict):
    """Save update configuration."""
    _ensure_config_dir()
    try:
        with open(_UPDATE_CONFIG, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def install_available_updates() -> dict:
    """Install all available Windows Updates."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Install-WindowsUpdate -MicrosoftUpdate -AcceptAll -AutoReboot"],
            capture_output=True,
            text=True,
            timeout=3600
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def schedule_update_check(hour: int = 3) -> bool:
    """Schedule automatic update check at specified hour."""
    config = get_update_config()
    config["install_time"] = f"{hour:02d}:00"
    config["last_check"] = datetime.now().isoformat()
    save_update_config(config)
    return True


def defer_updates(days: int = 7) -> bool:
    """Defer Windows Updates for N days."""
    if days < 0 or days > 30:
        return False

    config = get_update_config()
    config["defer_updates_days"] = days
    save_update_config(config)

    # Also set Windows registry
    try:
        subprocess.run(
            ["reg", "add", "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate",
             "/v", "DeferUpgrade", "/t", "REG_DWORD", "/d", str(days), "/f"],
            capture_output=True,
            timeout=10
        )
        return True
    except Exception:
        return False


def get_update_history() -> list[dict]:
    """Get Windows Update history."""
    updates = []

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-HotFix | Select-Object -Property HotFixID, Description, InstalledOn | ConvertTo-Json"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                if isinstance(data, list):
                    updates = data[:20]  # Last 20 updates
            except json.JSONDecodeError:
                pass
    except Exception:
        pass

    return updates


def exclude_update(kb_number: str) -> bool:
    """Exclude a KB update from installation."""
    config = get_update_config()

    if kb_number not in config["excluded_kb"]:
        config["excluded_kb"].append(kb_number)
        save_update_config(config)
        return True

    return False


def get_update_recommendations() -> list[str]:
    """Get recommendations for update management."""
    recommendations = []
    status = get_update_status()
    config = get_update_config()

    if status["pending_updates"] > 5:
        recommendations.append(f"Install {status['pending_updates']} pending Windows Updates to ensure security")

    if not config["auto_install"]:
        recommendations.append("Enable automatic Windows Updates to ensure your system stays secure")

    if config["defer_updates_days"] > 0:
        recommendations.append(f"Resume Windows Updates (currently deferred for {config['defer_updates_days']} days)")

    if config["restart_behavior"] == "never":
        recommendations.append("Enable automatic restart after updates to complete the installation")

    return recommendations
