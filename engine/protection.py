"""System Protection — Windows Defender and Firewall status/control."""

import subprocess
import json
import winreg


# ── Windows Defender ─────────────────────────────────────────────────────────

def get_defender_status() -> dict:
    """Query Windows Defender via PowerShell. Returns safe defaults on failure."""
    cmd = [
        "powershell", "-NoProfile", "-Command",
        "Get-MpComputerStatus | Select-Object "
        "RealTimeProtectionEnabled,AntivirusEnabled,"
        "AntivirusSignatureLastUpdated,AntivirusSignatureVersion,"
        "QuickScanStartTime,FullScanStartTime | ConvertTo-Json -Compress"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        data = json.loads(r.stdout)
        def _bool(k): return bool(data.get(k, False))
        def _str(k):  return str(data.get(k, "Unknown"))[:40]
        return {
            "available":       True,
            "enabled":         _bool("AntivirusEnabled"),
            "realtime":        _bool("RealTimeProtectionEnabled"),
            "last_scan":       _str("QuickScanStartTime").split("T")[0],
            "definition_ver":  _str("AntivirusSignatureVersion"),
            "definition_date": _str("AntivirusSignatureLastUpdated").split("T")[0],
        }
    except Exception:
        pass
    # Fallback: read registry
    return _get_defender_registry()


def _get_defender_registry() -> dict:
    result = {"available": False, "enabled": False, "realtime": False,
              "last_scan": "Unknown", "definition_ver": "Unknown", "definition_date": "Unknown"}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows Defender") as k:
            result["available"] = True
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows Defender\Real-Time Protection") as k:
            try:
                v, _ = winreg.QueryValueEx(k, "DisableRealtimeMonitoring")
                result["realtime"] = not bool(v)
                result["enabled"] = not bool(v)
            except OSError:
                result["realtime"] = True
                result["enabled"] = True
    except OSError:
        pass
    return result


def set_defender_realtime(enabled: bool) -> bool:
    """Toggle real-time protection (requires admin)."""
    val = "$false" if enabled else "$true"
    cmd = ["powershell", "-NoProfile", "-Command",
           f"Set-MpPreference -DisableRealtimeMonitoring {val}"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def start_defender_scan(full: bool = False) -> bool:
    scan_type = "FullScan" if full else "QuickScan"
    cmd = ["powershell", "-NoProfile", "-Command",
           f"Start-MpScan -ScanType {scan_type}"]
    try:
        subprocess.Popen(cmd)
        return True
    except Exception:
        return False


def update_defender_definitions() -> bool:
    cmd = ["powershell", "-NoProfile", "-Command", "Update-MpSignature"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


# ── Firewall ──────────────────────────────────────────────────────────────────

def get_firewall_status() -> dict:
    """Returns {Domain: {enabled: bool}, Private: ..., Public: ...}"""
    result = {p: {"enabled": False} for p in ("Domain", "Private", "Public")}
    try:
        r = subprocess.run(["netsh", "advfirewall", "show", "allprofiles"],
                           capture_output=True, text=True, timeout=8)
        current = None
        for line in r.stdout.splitlines():
            ls = line.strip()
            for profile in ("Domain", "Private", "Public"):
                if ls.lower().startswith(profile.lower()) and "profile settings" in ls.lower():
                    current = profile
            if current and "state" in ls.lower():
                result[current]["enabled"] = "on" in ls.lower()
                current = None
    except Exception:
        pass
    return result


def set_firewall_profile(profile: str, enabled: bool) -> bool:
    state = "on" if enabled else "off"
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "set",
             f"{profile.lower()}profile", "state", state],
            capture_output=True, timeout=8
        )
        return r.returncode == 0
    except Exception:
        return False


def set_all_firewall_profiles(enabled: bool) -> bool:
    state = "on" if enabled else "off"
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "set", "allprofiles", "state", state],
            capture_output=True, timeout=8
        )
        return r.returncode == 0
    except Exception:
        return False
