"""Memory & Performance optimizer — RAM trim, power plans, visual effects, process booster."""

import ctypes
import subprocess
import winreg
import os
import time

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ── RAM trim ─────────────────────────────────────────────────────────────────

def trim_working_sets(progress_cb=None) -> tuple[int, int]:
    """
    Trim working sets of all accessible processes.
    Returns (processes_trimmed, errors).
    """
    if not _PSUTIL:
        return 0, 0
    k32 = ctypes.windll.kernel32
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_QUERY_INFO = 0x0400

    trimmed = errors = 0
    pids = [p.pid for p in psutil.process_iter(["pid"])]
    for pid in pids:
        handle = None
        try:
            handle = k32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFO, False, pid)
            if handle:
                k32.SetProcessWorkingSetSize(handle, ctypes.c_size_t(-1), ctypes.c_size_t(-1))
                trimmed += 1
        except Exception:
            errors += 1
        finally:
            if handle:
                k32.CloseHandle(handle)
        if progress_cb:
            progress_cb(trimmed)
    return trimmed, errors


def get_memory_detail() -> dict:
    if not _PSUTIL:
        return {}
    m = psutil.virtual_memory()
    s = psutil.swap_memory()
    return {
        "ram_total":     _fmt(m.total),
        "ram_used":      _fmt(m.used),
        "ram_available": _fmt(m.available),
        "ram_pct":       m.percent,
        "swap_total":    _fmt(s.total),
        "swap_used":     _fmt(s.used),
        "swap_pct":      s.percent,
        "ram_total_bytes": m.total,
        "ram_avail_bytes": m.available,
    }


# ── power plans ───────────────────────────────────────────────────────────────

POWER_PLANS = {
    "High Performance": "8c5e7fda-e8bf-45a6-a6cc-4b0d644e0a0d",
    "Balanced":         "381b4222-f694-41f0-9685-ff5bb260df2e",
    "Power Saver":      "a1841308-3541-4fab-bc81-f71556f20b4a",
}


def get_active_power_plan() -> str:
    r = _run(["powercfg", "/getactivescheme"])
    line = r.stdout.strip()
    for name, guid in POWER_PLANS.items():
        if guid.lower() in line.lower():
            return name
    # Try to extract friendly name from output
    if "(" in line and ")" in line:
        return line.split("(")[-1].rstrip(")")
    return line or "Unknown"


def set_power_plan(name: str) -> bool:
    guid = POWER_PLANS.get(name)
    if not guid:
        return False
    r = _run(["powercfg", "/setactive", guid])
    return r.returncode == 0


def list_power_plans() -> list[dict]:
    r = _run(["powercfg", "/list"])
    plans = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if "GUID" in line or not line:
            continue
        # typical: Power Scheme GUID: <guid>  (<name>)
        if ":" in line:
            guid_part = line.split(":", 1)[1].strip()
            # guid_part looks like: abc-123  (Name)  *
            guid = guid_part.split()[0] if guid_part else ""
            name = ""
            if "(" in guid_part:
                name = guid_part.split("(", 1)[1].rstrip(")").rstrip(" *").strip()
            active = "*" in line
            if guid:
                plans.append({"guid": guid, "name": name or guid, "active": active})
    return plans


# ── visual effects ────────────────────────────────────────────────────────────

_VISUAL_FX_PATH = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
_PERF_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
_DESKTOP_KEY = r"Control Panel\Desktop"


def get_visual_effects_mode() -> str:
    """Returns 'best_performance', 'best_appearance', 'custom', or 'unknown'."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _VISUAL_FX_PATH) as k:
            val, _ = winreg.QueryValueEx(k, "VisualFXSetting")
            return {0: "best_appearance", 2: "best_performance", 3: "custom"}.get(val, "custom")
    except OSError:
        return "unknown"


def set_visual_effects(mode: str) -> bool:
    """mode: 'best_performance' | 'best_appearance' | 'custom'"""
    mapping = {"best_performance": 2, "best_appearance": 0, "custom": 3}
    val = mapping.get(mode, 2)
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _VISUAL_FX_PATH) as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, val)
    except OSError:
        return False

    if mode == "best_performance":
        _apply_performance_visual()
    elif mode == "best_appearance":
        _apply_appearance_visual()
    return True


def _apply_performance_visual():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _DESKTOP_KEY, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, "DragFullWindows", 0, winreg.REG_SZ, "0")
            winreg.SetValueEx(k, "MenuShowDelay",   0, winreg.REG_SZ, "0")
            winreg.SetValueEx(k, "UserPreferencesMask", 0, winreg.REG_BINARY,
                              b"\x90\x12\x03\x80\x10\x00\x00\x00")
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERF_KEY, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, "ListviewShadow", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(k, "TaskbarAnimations", 0, winreg.REG_DWORD, 0)
    except OSError:
        pass


def _apply_appearance_visual():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _DESKTOP_KEY, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, "DragFullWindows", 0, winreg.REG_SZ, "1")
            winreg.SetValueEx(k, "MenuShowDelay",   0, winreg.REG_SZ, "400")
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERF_KEY, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, "ListviewShadow", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "TaskbarAnimations", 0, winreg.REG_DWORD, 1)
    except OSError:
        pass


# ── process booster ───────────────────────────────────────────────────────────

HIGH_PRIORITY   = 0x00000080
ABOVE_NORMAL    = 0x00008000
NORMAL_PRIORITY = 0x00000020
BELOW_NORMAL    = 0x00004000
IDLE_PRIORITY   = 0x00000040

_PRIORITY_NAMES = {
    HIGH_PRIORITY:   "High",
    ABOVE_NORMAL:    "Above Normal",
    NORMAL_PRIORITY: "Normal",
    BELOW_NORMAL:    "Below Normal",
    IDLE_PRIORITY:   "Idle",
}


def get_running_processes() -> list[dict]:
    if not _PSUTIL:
        return []
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append({
                "pid":  p.info["pid"],
                "name": p.info["name"],
                "cpu":  round(p.info["cpu_percent"] or 0, 1),
                "ram":  round(p.info["memory_percent"] or 0, 2),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: x["ram"], reverse=True)


def boost_process(pid: int, priority: int = HIGH_PRIORITY) -> bool:
    k32 = ctypes.windll.kernel32
    PROCESS_SET_INFORMATION = 0x0200
    handle = k32.OpenProcess(PROCESS_SET_INFORMATION, False, pid)
    if not handle:
        return False
    ok = k32.SetPriorityClass(handle, priority)
    k32.CloseHandle(handle)
    return bool(ok)


def get_process_priority(pid: int) -> str:
    k32 = ctypes.windll.kernel32
    PROCESS_QUERY_INFORMATION = 0x0400
    handle = k32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        return "Unknown"
    val = k32.GetPriorityClass(handle)
    k32.CloseHandle(handle)
    return _PRIORITY_NAMES.get(val, f"0x{val:x}")


# ── disk defrag / TRIM ────────────────────────────────────────────────────────

def get_drive_type(drive_letter: str) -> str:
    """Returns 'SSD', 'HDD', or 'Unknown'."""
    r = _run(["powershell", "-Command",
               f"Get-PhysicalDisk | Where-Object {{$_.DeviceId -eq 0}} | "
               f"Select-Object -ExpandProperty MediaType"])
    t = r.stdout.strip()
    if "SSD" in t or "Solid" in t:
        return "SSD"
    if "HDD" in t or "Hard" in t or "Rotational" in t:
        return "HDD"
    # Fallback via volume
    r2 = _run(["powershell", "-Command",
                f"(New-Object -ComObject Microsoft.Update.SystemInfo).RebootRequired"])
    return "Unknown"


def optimize_drive(drive_letter: str, progress_cb=None) -> bool:
    if progress_cb:
        progress_cb(f"Optimizing drive {drive_letter}:...")
    r = _run(["powershell", "-Command",
               f"Optimize-Volume -DriveLetter {drive_letter} -Verbose"],
             timeout=300)
    return r.returncode == 0


def analyze_drive_fragmentation(drive_letter: str) -> str:
    r = _run(["powershell", "-Command",
               f"Optimize-Volume -DriveLetter {drive_letter} -Analyze -Verbose"],
             timeout=120)
    return r.stdout or r.stderr
