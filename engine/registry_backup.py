"""Registry Backup — export and restore Windows registry before cleaning."""

import os
import subprocess
import winreg
from datetime import datetime
from pathlib import Path

_BACKUP_DIR = Path(os.environ.get("TEMP", "C:\\Temp")) / "FreeSystemDoctor" / "registry_backups"

_BACKUP_KEYS = [
    (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run",     "HKCU_Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run",     "HKLM_Run"),
    (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU_RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM_RunOnce"),
]

# Full hive exports via reg.exe
_HIVE_EXPORTS = [
    ("HKCU", "HKCU_full"),
    ("HKLM\\SOFTWARE", "HKLM_SOFTWARE"),
]


def get_backup_dir() -> Path:
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return _BACKUP_DIR


def list_backups() -> list[dict]:
    """Return list of existing backups sorted newest first."""
    dir_ = get_backup_dir()
    backups = []
    for f in dir_.glob("*.reg"):
        try:
            stat = f.stat()
            backups.append({
                "name": f.stem,
                "path": str(f),
                "size": stat.st_size,
                "size_str": _fmt_bytes(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
            })
        except OSError:
            pass
    return sorted(backups, key=lambda x: x["created"], reverse=True)


def create_backup(label: str = "before_clean") -> dict:
    """Create a .reg backup of critical registry keys.
    Returns {path, size, error}."""
    dir_ = get_backup_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{label}.reg"
    out_path = dir_ / filename

    try:
        result = subprocess.run(
            ["reg", "export", "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion",
             str(out_path), "/y"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000)
        if out_path.exists():
            size = out_path.stat().st_size
            return {"path": str(out_path), "size": size, "error": None}
        return {"path": "", "size": 0, "error": result.stderr.strip() or "Export failed"}
    except Exception as e:
        return {"path": "", "size": 0, "error": str(e)}


def create_full_backup(label: str = "full") -> dict:
    """Export HKCU and HKLM\\SOFTWARE to .reg files."""
    dir_ = get_backup_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []

    for hive, suffix in _HIVE_EXPORTS:
        filename = f"{ts}_{label}_{suffix}.reg"
        out_path = dir_ / filename
        try:
            subprocess.run(
                ["reg", "export", hive, str(out_path), "/y"],
                capture_output=True, text=True, timeout=60, creationflags=0x08000000)
            if out_path.exists():
                results.append(str(out_path))
        except Exception:
            pass

    total_size = sum(Path(p).stat().st_size for p in results if Path(p).exists())
    return {
        "paths": results,
        "count": len(results),
        "size": total_size,
        "size_str": _fmt_bytes(total_size),
        "error": None if results else "No backups created",
    }


def restore_backup(backup_path: str) -> tuple[bool, str]:
    """Restore a .reg backup file. Returns (success, message)."""
    path = Path(backup_path)
    if not path.exists():
        return False, "Backup file not found"
    try:
        result = subprocess.run(
            ["reg", "import", str(path)],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000)
        if result.returncode == 0:
            return True, "Registry restored successfully. Restart may be required."
        return False, result.stderr.strip() or "Import failed"
    except Exception as e:
        return False, str(e)


def delete_backup(backup_path: str) -> bool:
    try:
        Path(backup_path).unlink()
        return True
    except Exception:
        return False


def auto_backup_before_clean() -> str:
    """Quick backup called automatically before registry cleaning. Returns path or ''."""
    result = create_backup("auto_before_clean")
    return result.get("path", "")


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"
