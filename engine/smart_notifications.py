"""Smart Notifications — background scanner with system tray alerts."""

import json
import os
import subprocess
import threading
import time
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("TEMP", "C:\\Temp")) / "FreeSystemDoctor"
_CONFIG_FILE = _CONFIG_DIR / "notifications_config.json"

_DEFAULT_CONFIG = {
    "enabled": True,
    "interval_minutes": 60,
    "notify_junk": True,
    "notify_startup": True,
    "notify_memory": True,
    "junk_threshold_mb": 500,
    "memory_threshold_pct": 85,
    "startup_threshold": 10,
}

_scan_thread: threading.Thread | None = None
_stop_event = threading.Event()


def get_config() -> dict:
    """Load notification config from JSON, falling back to defaults."""
    try:
        if _CONFIG_FILE.exists():
            with open(_CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return {**_DEFAULT_CONFIG, **cfg}
    except Exception:
        pass
    return dict(_DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def run_scan() -> list[dict]:
    """Run a quick scan and return list of issues found.
    Each issue: {type, title, message, severity}"""
    issues = []
    cfg = get_config()

    # Check junk files
    if cfg.get("notify_junk", True):
        try:
            from engine import disk_cleaner
            items = disk_cleaner.scan_junk()
            # ScanResult objects expose .size (bytes); fall back to dict if list of dicts
            total_bytes = sum(
                getattr(i, "size", None) if not isinstance(i, dict) else i.get("size", 0)
                or 0
                for i in items
            )
            threshold = cfg.get("junk_threshold_mb", 500) * 1024 * 1024
            if total_bytes >= threshold:
                mb = total_bytes / (1024 * 1024)
                issues.append({
                    "type": "junk",
                    "title": "Junk Files Detected",
                    "message": f"Found {mb:.0f} MB of junk files. Run Disk Cleaner to free space.",
                    "severity": "warning",
                })
        except Exception:
            pass

    # Check startup count
    if cfg.get("notify_startup", True):
        try:
            from engine import startup_manager
            entries = startup_manager.get_startup_entries_with_impact()
            high_impact = [e for e in entries if e.impact == "High" and e.enabled]
            threshold = cfg.get("startup_threshold", 10)
            if len(entries) >= threshold or len(high_impact) >= 3:
                issues.append({
                    "type": "startup",
                    "title": "Slow Startup Detected",
                    "message": f"{len(entries)} startup programs ({len(high_impact)} high impact). Consider disabling unused ones.",
                    "severity": "warning",
                })
        except Exception:
            pass

    # Check memory usage
    if cfg.get("notify_memory", True):
        try:
            import psutil
            mem = psutil.virtual_memory()
            threshold = cfg.get("memory_threshold_pct", 85)
            if mem.percent >= threshold:
                issues.append({
                    "type": "memory",
                    "title": "High Memory Usage",
                    "message": f"RAM usage is {mem.percent:.0f}%. Consider running Memory Optimizer.",
                    "severity": "critical",
                })
        except Exception:
            pass

    return issues


def show_toast(title: str, message: str) -> None:
    """Show a Windows toast notification via PowerShell."""
    try:
        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.ShowBalloonTip(5000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Milliseconds 5500
$notify.Dispose()
"""
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=0x08000000,
        )
    except Exception:
        pass


def _scanner_loop(interval_minutes: int) -> None:
    """Background loop that scans and shows notifications."""
    while not _stop_event.is_set():
        issues = run_scan()
        if issues:
            titles = [i["title"] for i in issues]
            title = "FreeSystemDoctor Alert"
            if len(issues) == 1:
                show_toast(issues[0]["title"], issues[0]["message"])
            else:
                show_toast(title, f"Found {len(issues)} issues: {', '.join(titles)}")
        _stop_event.wait(timeout=interval_minutes * 60)


def start_background_scanner() -> bool:
    """Start the background notification scanner thread. Returns True if started."""
    global _scan_thread, _stop_event

    cfg = get_config()
    if not cfg.get("enabled", True):
        return False

    if _scan_thread and _scan_thread.is_alive():
        return True

    _stop_event.clear()
    interval = cfg.get("interval_minutes", 60)
    _scan_thread = threading.Thread(target=_scanner_loop, args=(interval,), daemon=True)
    _scan_thread.start()
    return True


def stop_background_scanner() -> None:
    """Stop the background notification scanner."""
    _stop_event.set()


def is_scanner_running() -> bool:
    """Return True if background scanner thread is alive."""
    return _scan_thread is not None and _scan_thread.is_alive()


def scan_now_and_notify() -> list[dict]:
    """Run scan immediately and show notification if issues found."""
    issues = run_scan()
    if issues:
        if len(issues) == 1:
            show_toast(issues[0]["title"], issues[0]["message"])
        else:
            titles = [i["title"] for i in issues]
            show_toast("FreeSystemDoctor", f"{len(issues)} issues found: {', '.join(titles)}")
    return issues
