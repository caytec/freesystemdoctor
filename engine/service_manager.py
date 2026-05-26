"""Windows Service Manager — list, start, stop, enable, disable with safety ratings."""

import subprocess
import winreg
from dataclasses import dataclass, field


@dataclass
class WinService:
    name: str
    display_name: str
    status: str          # Running / Stopped / ...
    start_type: str      # Auto / Manual / Disabled
    description: str = ""
    pid: int = 0
    safety: str = "Unknown"   # Safe / Caution / System / Unknown
    note: str = ""


# ── safety database ───────────────────────────────────────────────────────────

_SAFETY = {
    # name: (safety, note)
    "DiagTrack":           ("Safe",    "Windows telemetry/diagnostics — can be disabled"),
    "dmwappushservice":    ("Safe",    "Diagnostic data push — not needed by most users"),
    "WSearch":             ("Safe",    "Windows Search indexer — disable if not using search"),
    "SCardSvr":            ("Safe",    "Smart Card reader — safe if no smart card"),
    "SSDPSRV":             ("Safe",    "UPnP discovery — safe to disable on desktops"),
    "upnphost":            ("Safe",    "UPnP device hosting — disable if unused"),
    "WinRM":               ("Safe",    "Remote management — disable if not using"),
    "RemoteRegistry":      ("Safe",    "Remote registry access — disable for security"),
    "Fax":                 ("Safe",    "Fax service — disable if no fax modem"),
    "TabletInputService":  ("Safe",    "Touch/pen input — safe to disable on desktop"),
    "XblAuthManager":      ("Safe",    "Xbox authentication — disable if not gaming"),
    "XblGameSave":         ("Safe",    "Xbox game save — disable if not gaming"),
    "XboxNetApiSvc":       ("Safe",    "Xbox networking — disable if not gaming"),
    "MapsBroker":          ("Safe",    "Maps service — disable if not using maps app"),
    "RetailDemo":          ("Safe",    "Retail demo — should be disabled"),
    "lfsvc":               ("Safe",    "Geolocation — disable for privacy"),
    "wuauserv":            ("Caution", "Windows Update — disabling prevents updates"),
    "WerSvc":              ("Caution", "Error reporting — impacts crash diagnostics"),
    "Superfetch":          ("Caution", "Prefetch/SysMain — may help or hurt on SSDs"),
    "SysMain":             ("Caution", "Superfetch alias — see above"),
    "Spooler":             ("Caution", "Print spooler — disable if no printer"),
    "LanmanServer":        ("Caution", "File sharing server — disable if no file sharing"),
    "LanmanWorkstation":   ("Caution", "Workstation/SMB client — needed for network files"),
    "EventLog":            ("System",  "Event logging — do not disable"),
    "RpcSs":               ("System",  "RPC — critical system service"),
    "lsass":               ("System",  "Security Authority — critical"),
    "svchost":             ("System",  "Service host — critical"),
    "System":              ("System",  "Windows kernel — critical"),
}


def _get_description(name: str) -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            f"SYSTEM\\CurrentControlSet\\Services\\{name}") as k:
            try:
                v, _ = winreg.QueryValueEx(k, "Description")
                return str(v)[:120]
            except OSError:
                pass
    except OSError:
        pass
    return ""


def _get_display_name(name: str) -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            f"SYSTEM\\CurrentControlSet\\Services\\{name}") as k:
            try:
                v, _ = winreg.QueryValueEx(k, "DisplayName")
                return str(v)
            except OSError:
                pass
    except OSError:
        pass
    return name


def list_services(progress_cb=None) -> list[WinService]:
    """Return all non-driver services."""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Service | Select-Object Name,DisplayName,Status,StartType "
         "| ConvertTo-Csv -NoTypeInformation"],
        capture_output=True, text=True, creationflags=0x08000000)

    services = []
    lines = r.stdout.strip().splitlines()
    if len(lines) < 2:
        return services

    headers = [h.strip('"') for h in lines[0].split(",")]
    for i, line in enumerate(lines[1:], 1):
        vals = [v.strip('"') for v in line.split(",")]
        if len(vals) != len(headers):
            continue
        d = dict(zip(headers, vals))
        name = d.get("Name", "")
        safety, note = _SAFETY.get(name, ("Unknown", ""))
        svc = WinService(
            name=name,
            display_name=d.get("DisplayName", name),
            status=d.get("Status", ""),
            start_type=d.get("StartType", ""),
            safety=safety,
            note=note,
        )
        services.append(svc)
        if progress_cb and i % 20 == 0:
            progress_cb(i)

    return services


def get_service_detail(name: str) -> str:
    r = subprocess.run(["sc", "query", name], capture_output=True, text=True, creationflags=0x08000000)
    r2 = subprocess.run(["sc", "qc", name], capture_output=True, text=True, creationflags=0x08000000)
    return (r.stdout + "\n" + r2.stdout).strip()


def start_service(name: str) -> bool:
    r = subprocess.run(["net", "start", name], capture_output=True, creationflags=0x08000000)
    return r.returncode == 0


def stop_service(name: str) -> bool:
    r = subprocess.run(["net", "stop", name], capture_output=True, creationflags=0x08000000)
    return r.returncode == 0


def set_service_startup(name: str, mode: str) -> bool:
    """mode: auto | manual | disabled"""
    r = subprocess.run(["sc", "config", name, f"start={mode}"], capture_output=True, creationflags=0x08000000)
    return r.returncode == 0


def restart_service(name: str) -> bool:
    stop_service(name)
    return start_service(name)
