"""Service Optimizer — preset profiles for Windows services.

Inspired by System Mechanic, Advanced SystemCare, Ashampoo WinOptimizer.
Provides one-click profile application: Default / Optimal / Gaming / Bare.
"""

import os
import json
import subprocess
from pathlib import Path

_CFG_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "FreeSystemDoctor"
_BACKUP_FILE = _CFG_DIR / "service_backup.json"

# Service profiles. Values: "auto", "manual", "disabled", "skip" (don't touch).
# Conservative recommendations — only services widely safe to change.
PROFILES = {
    "Default": {
        # Restores standard Windows defaults
        "DiagTrack":            "auto",       # Connected User Experiences and Telemetry
        "dmwappushservice":     "manual",
        "WSearch":              "auto",       # Windows Search
        "SysMain":              "auto",       # Superfetch
        "Fax":                  "manual",
        "WerSvc":               "manual",     # Error Reporting
        "RemoteRegistry":       "manual",
        "MapsBroker":           "manual",
        "RetailDemo":           "manual",
        "XblAuthManager":       "manual",
        "XblGameSave":          "manual",
        "XboxGipSvc":           "manual",
        "XboxNetApiSvc":        "manual",
        "WMPNetworkSvc":        "manual",     # Windows Media Player Net Sharing
        "TabletInputService":   "manual",
        "PrintNotify":          "manual",
        "Spooler":              "auto",
    },
    "Optimal": {
        # Disables telemetry and rarely-used services
        "DiagTrack":            "disabled",
        "dmwappushservice":     "disabled",
        "WerSvc":               "manual",
        "RemoteRegistry":       "disabled",
        "MapsBroker":           "manual",
        "RetailDemo":           "disabled",
        "WMPNetworkSvc":        "manual",
        "Fax":                  "disabled",
        "PrintNotify":          "manual",
        "TabletInputService":   "manual",
        "WSearch":              "auto",
        "SysMain":              "auto",
        "Spooler":              "auto",
    },
    "Gaming": {
        # Maximize performance — turn off background indexing/superfetch
        "DiagTrack":            "disabled",
        "dmwappushservice":     "disabled",
        "WSearch":              "disabled",
        "SysMain":              "disabled",
        "WerSvc":                "disabled",
        "RemoteRegistry":       "disabled",
        "MapsBroker":           "disabled",
        "Fax":                  "disabled",
        "RetailDemo":           "disabled",
        "WMPNetworkSvc":        "disabled",
        "TabletInputService":   "manual",
        "Spooler":              "manual",
        "PrintNotify":          "manual",
        "XblAuthManager":       "manual",      # keep Xbox stuff functional for game stores
        "XblGameSave":          "manual",
        "XboxGipSvc":           "manual",
        "XboxNetApiSvc":        "manual",
    },
    "Bare":   {
        # Minimal services — power users only. Same as Gaming but more aggressive.
        "DiagTrack":            "disabled",
        "dmwappushservice":     "disabled",
        "WSearch":              "disabled",
        "SysMain":              "disabled",
        "WerSvc":                "disabled",
        "RemoteRegistry":       "disabled",
        "MapsBroker":           "disabled",
        "RetailDemo":           "disabled",
        "Fax":                  "disabled",
        "WMPNetworkSvc":        "disabled",
        "PrintNotify":          "disabled",
        "Spooler":              "disabled",
        "TabletInputService":   "disabled",
        "XblAuthManager":       "disabled",
        "XblGameSave":          "disabled",
        "XboxGipSvc":           "disabled",
        "XboxNetApiSvc":        "disabled",
    },
}


def _query_service(name: str) -> tuple[str, str]:
    """Returns (start_type, current_state). Empty strings if not found."""
    try:
        r = subprocess.run(
            ["sc", "qc", name],
            capture_output=True, text=True, timeout=8,
            creationflags=0x08000000
        )
        start = ""
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("START_TYPE"):
                if "AUTO" in line.upper():
                    start = "auto"
                elif "DEMAND" in line.upper():
                    start = "manual"
                elif "DISABLED" in line.upper():
                    start = "disabled"
                elif "BOOT" in line.upper() or "SYSTEM" in line.upper():
                    start = "boot"
        return (start, "")
    except Exception:
        return ("", "")


def list_managed_services() -> list[dict]:
    """Return state of every service we know how to manage."""
    seen = {}
    for prof, mapping in PROFILES.items():
        for svc in mapping:
            seen.setdefault(svc, None)

    out = []
    for svc in sorted(seen):
        start, _ = _query_service(svc)
        out.append({"name": svc, "start_type": start or "(absent)"})
    return out


def _set_service(name: str, mode: str) -> bool:
    """mode = auto|manual|disabled. Returns True on success."""
    if mode == "skip":
        return True
    sc_modes = {"auto": "auto", "manual": "demand", "disabled": "disabled"}
    sc_mode = sc_modes.get(mode)
    if not sc_mode:
        return False
    try:
        r = subprocess.run(
            ["sc", "config", name, f"start=", sc_mode],
            capture_output=True, text=True, timeout=8,
            creationflags=0x08000000
        )
        # Some Windows builds need 'start= ' with space
        if r.returncode != 0:
            r = subprocess.run(
                ["sc", "config", name, f"start={sc_mode}"],
                capture_output=True, text=True, timeout=8,
                creationflags=0x08000000
            )
        return r.returncode == 0
    except Exception:
        return False


def backup_current_state():
    """Snapshot current start types of every managed service."""
    state = {svc["name"]: svc["start_type"] for svc in list_managed_services()}
    _CFG_DIR.mkdir(parents=True, exist_ok=True)
    _BACKUP_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def has_backup() -> bool:
    return _BACKUP_FILE.exists()


def apply_profile(profile: str, progress=None) -> dict:
    """Apply a profile. Returns {"ok": [...], "fail": [...]}."""
    if profile not in PROFILES:
        return {"ok": [], "fail": [], "error": f"Unknown profile: {profile}"}

    if not has_backup():
        backup_current_state()

    cfg = PROFILES[profile]
    ok, fail = [], []
    total = len(cfg)
    for i, (svc, mode) in enumerate(cfg.items()):
        if progress:
            try:
                progress(i, total, svc)
            except Exception:
                pass
        if _set_service(svc, mode):
            ok.append(svc)
        else:
            fail.append(svc)
    return {"ok": ok, "fail": fail}


def restore_backup() -> dict:
    """Restore services from the backup snapshot."""
    if not _BACKUP_FILE.exists():
        return {"ok": [], "fail": [], "error": "No backup found"}
    try:
        data = json.loads(_BACKUP_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": [], "fail": [], "error": str(e)}

    ok, fail = [], []
    for svc, mode in data.items():
        if mode in ("auto", "manual", "disabled"):
            if _set_service(svc, mode):
                ok.append(svc)
            else:
                fail.append(svc)
    return {"ok": ok, "fail": fail}
