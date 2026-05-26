"""Hardware Monitoring — CPU/GPU/Disk temperatures and fan speeds.

Multi-source strategy (tries in order, uses first that works):
1. nvidia-smi          — GPU temp, no admin needed (NVIDIA only)
2. LibreHardwareMonitor — most complete (WMI namespace if LHM running)
3. OpenHardwareMonitor  — older alternative (WMI namespace)
4. MSAcpi_ThermalZoneTemperature — ACPI thermal zones (some desktops)
5. Win32_TemperatureProbe — rarely populated but try
6. SMART data via WMI for disk temps

Returns 0 if everything fails. The GUI should treat 0 as 'N/A'.
"""

from __future__ import annotations

import subprocess
import sys

try:
    import wmi
    _WMI = True
except ImportError:
    _WMI = False

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=timeout, creationflags=_CREATE_NO_WINDOW)
        return r.returncode, (r.stdout or "").strip()
    except Exception:
        return -1, ""


# ── source 1: nvidia-smi (GPU only) ──────────────────────────────────────────

def _gpu_temp_nvidia() -> float:
    rc, out = _run([
        "nvidia-smi", "--query-gpu=temperature.gpu",
        "--format=csv,noheader,nounits",
    ], timeout=3)
    if rc == 0 and out:
        try:
            return float(out.split("\n")[0])
        except ValueError:
            pass
    return 0


# ── source 2: LibreHardwareMonitor (if running) ──────────────────────────────

def _temps_lhm() -> dict:
    """Query LibreHardwareMonitor WMI namespace. User must have LHM running."""
    result = {"cpu": 0, "gpu": 0, "disk": 0}
    if not _WMI:
        return result
    try:
        c = wmi.WMI(namespace="root\\LibreHardwareMonitor")
        for s in c.Sensor():
            if s.SensorType != "Temperature":
                continue
            name_l = (s.Name or "").lower()
            parent_l = (s.Parent or "").lower()
            v = float(s.Value or 0)
            if not result["cpu"] and ("cpu package" in name_l or "core (tctl/tdie)" in name_l):
                result["cpu"] = v
            elif not result["gpu"] and ("gpu core" in name_l or "/gpu/" in parent_l):
                result["gpu"] = v
            elif not result["disk"] and "temperature" in name_l and "hdd" in parent_l:
                result["disk"] = v
    except Exception:
        pass
    return result


def _temps_ohm() -> dict:
    """Query OpenHardwareMonitor — older naming convention."""
    result = {"cpu": 0, "gpu": 0, "disk": 0}
    if not _WMI:
        return result
    try:
        c = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        for s in c.Sensor():
            if s.SensorType != "Temperature":
                continue
            name_l = (s.Name or "").lower()
            v = float(s.Value or 0)
            if not result["cpu"] and "cpu" in name_l:
                result["cpu"] = max(result["cpu"], v)
            elif not result["gpu"] and "gpu" in name_l:
                result["gpu"] = max(result["gpu"], v)
            elif not result["disk"] and any(k in name_l for k in ("hdd", "ssd", "nvme")):
                result["disk"] = max(result["disk"], v)
    except Exception:
        pass
    return result


# ── source 3: ACPI thermal zones (admin + supported hardware) ────────────────

def _temps_acpi() -> float:
    """MSAcpi_ThermalZoneTemperature — works on some desktops with admin."""
    if not _WMI:
        return 0
    try:
        c = wmi.WMI(namespace="root\\wmi")
        zones = c.MSAcpi_ThermalZoneTemperature()
        if zones:
            # Returns deci-Kelvin
            return float(zones[0].CurrentTemperature) / 10.0 - 273.15
    except Exception:
        pass
    return 0


# ── source 4: SMART disk temp ────────────────────────────────────────────────

def _disk_temp_smart() -> float:
    """Read SMART attribute 0xC2 (194) or 0xBE (190) — temperature."""
    if not _WMI:
        return 0
    try:
        c = wmi.WMI(namespace="root\\wmi")
        for drv in c.MSStorageDriver_ATAPISmartData():
            data = list(drv.VendorSpecific or [])
            for i in range(30):
                base = 2 + i * 12
                if base + 6 >= len(data):
                    break
                if data[base] in (0xC2, 0xBE):
                    raw = data[base + 5]
                    if 0 < raw < 120:
                        return float(raw)
    except Exception:
        pass

    # PowerShell Get-StorageReliabilityCounter fallback
    rc, out = _run([
        "powershell", "-NoProfile", "-Command",
        "Get-PhysicalDisk | Get-StorageReliabilityCounter | "
        "Select-Object -ExpandProperty Temperature -First 1",
    ], timeout=8)
    if rc == 0 and out:
        try:
            return float(out.split("\n")[0])
        except ValueError:
            pass
    return 0


# ── public API ───────────────────────────────────────────────────────────────

def get_cpu_temperature() -> float:
    """CPU temperature in °C. Returns 0 if unavailable."""
    # Try LHM first
    lhm = _temps_lhm()
    if lhm["cpu"] > 0:
        return lhm["cpu"]
    # OHM second
    ohm = _temps_ohm()
    if ohm["cpu"] > 0:
        return ohm["cpu"]
    # ACPI third (requires admin + hardware support)
    return _temps_acpi()


def get_gpu_temperature() -> float:
    """GPU temperature in °C. Returns 0 if unavailable."""
    # nvidia-smi is fastest and most reliable
    t = _gpu_temp_nvidia()
    if t > 0:
        return t
    # LHM / OHM for AMD/Intel
    lhm = _temps_lhm()
    if lhm["gpu"] > 0:
        return lhm["gpu"]
    return _temps_ohm()["gpu"]


def get_disk_temperature(drive: str = "C:") -> float:
    """Disk temperature in °C. Returns 0 if unavailable."""
    # LHM first
    lhm = _temps_lhm()
    if lhm["disk"] > 0:
        return lhm["disk"]
    ohm = _temps_ohm()
    if ohm["disk"] > 0:
        return ohm["disk"]
    # SMART direct
    return _disk_temp_smart()


def get_system_temps() -> dict:
    """All temperatures + status. Values of 0 mean 'unavailable'."""
    cpu = get_cpu_temperature()
    gpu = get_gpu_temperature()
    disk = get_disk_temperature()

    all_zero = (cpu == 0 and gpu == 0 and disk == 0)
    status = "unavailable" if all_zero else "ok"

    return {
        "cpu_temp": cpu,
        "gpu_temp": gpu,
        "disk_temp": disk,
        "status": status,
        "safe_threshold": 80,
        "warning_threshold": 75,
        "available_sources": _list_available_sources(),
    }


def _list_available_sources() -> list[str]:
    """Diagnostic: which temp sources are usable on this system."""
    found = []
    if not _WMI:
        return ["wmi-module-missing"]
    # nvidia
    if _gpu_temp_nvidia() > 0:
        found.append("nvidia-smi")
    # LHM
    try:
        if wmi.WMI(namespace="root\\LibreHardwareMonitor").Sensor():
            found.append("LibreHardwareMonitor")
    except Exception:
        pass
    # OHM
    try:
        if wmi.WMI(namespace="root\\OpenHardwareMonitor").Sensor():
            found.append("OpenHardwareMonitor")
    except Exception:
        pass
    # ACPI
    if _temps_acpi() > 0:
        found.append("ACPI-thermal-zones")
    return found or ["none"]


def get_fan_speeds() -> list[dict]:
    """Fan speeds via WMI / LHM. Returns empty list if unavailable."""
    fans = []
    if not _WMI:
        return fans

    # LHM is the most reliable
    try:
        c = wmi.WMI(namespace="root\\LibreHardwareMonitor")
        for s in c.Sensor():
            if s.SensorType == "Fan":
                rpm = int(s.Value or 0)
                fans.append({
                    "name": s.Name or "Fan",
                    "speed_rpm": rpm,
                    "status": "OK" if rpm > 0 else "stopped",
                })
    except Exception:
        pass

    if fans:
        return fans

    # WMI Win32_Fan (rarely returns anything useful)
    try:
        c = wmi.WMI(namespace="root\\cimv2")
        for f in c.Win32_Fan():
            speed = getattr(f, "DesiredSpeed", 0) or 0
            fans.append({
                "name": f.Name or "Fan",
                "speed_rpm": int(speed),
                "status": "OK" if speed > 0 else "unknown",
            })
    except Exception:
        pass

    return fans


def check_thermal_health() -> dict:
    """Score the thermal situation."""
    temps = get_system_temps()
    cpu = temps["cpu_temp"]
    gpu = temps["gpu_temp"]
    disk = temps["disk_temp"]

    if temps["status"] == "unavailable":
        return {
            "score": 0,
            "cpu_temp": 0, "gpu_temp": 0, "disk_temp": 0,
            "status": "unavailable",
            "issues": ["Brak źródła temperatury"],
            "recommendation": (
                "Zainstaluj LibreHardwareMonitor (free, open source) i uruchom "
                "go w tle. Po starcie FSD pokaże CPU/GPU/disk temp. "
                "Download: github.com/LibreHardwareMonitor/LibreHardwareMonitor"
            ),
            "sources_tried": temps.get("available_sources", []),
        }

    score = 100
    issues = []
    if cpu > 0:
        if cpu > 85:
            score -= 40; issues.append(f"CPU bardzo gorący ({cpu:.0f}°C)")
        elif cpu > 75:
            score -= 20; issues.append(f"CPU ciepły ({cpu:.0f}°C)")
    if gpu > 0:
        if gpu > 85:
            score -= 30; issues.append(f"GPU bardzo gorące ({gpu:.0f}°C)")
        elif gpu > 78:
            score -= 15; issues.append(f"GPU ciepłe ({gpu:.0f}°C)")
    if disk > 0:
        if disk > 60:
            score -= 20; issues.append(f"Dysk bardzo gorący ({disk:.0f}°C)")
        elif disk > 50:
            score -= 10; issues.append(f"Dysk ciepły ({disk:.0f}°C)")

    score = max(0, score)
    if score >= 80:
        status = "normal"
        rec = "System termiczny w dobrej kondycji"
    elif score >= 50:
        status = "warning"
        rec = "Rozważ wyczyszczenie wentylatorów / poprawienie airflow"
    else:
        status = "critical"
        rec = "PILNIE: thermal throttling. Wyczyść kurz, sprawdź pasty termoprzewodzącej, otwórz boczny panel"

    return {
        "score": score,
        "cpu_temp": cpu, "gpu_temp": gpu, "disk_temp": disk,
        "status": status,
        "issues": issues,
        "recommendation": rec,
        "sources_tried": temps.get("available_sources", []),
    }
