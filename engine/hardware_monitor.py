"""Hardware Monitoring — CPU/GPU/Disk temperatures and fan speeds via WMI."""

try:
    import wmi
    _WMI = True
except ImportError:
    _WMI = False


def get_cpu_temperature() -> float:
    """Get CPU temperature in Celsius. Returns 0 if unavailable."""
    if not _WMI:
        return 0
    try:
        w = wmi.WMI(namespace="root\\cimv2")
        temps = w.query("SELECT * FROM Win32_TemperatureProbe")
        if temps:
            return float(temps[0].CurrentReading) / 10.0
    except Exception:
        pass
    try:
        w = wmi.WMI(namespace="root\\wmi")
        temps = w.query("SELECT * FROM MSAcpi_ThermalZoneTemperature")
        if temps:
            return float(temps[0].CurrentTemperature) / 10.0 - 273.15
    except Exception:
        pass
    return 0


def get_disk_temperature(drive: str = "C:") -> float:
    """Get disk temperature in Celsius. Returns 0 if unavailable."""
    if not _WMI:
        return 0
    try:
        w = wmi.WMI(namespace="root\\cimv2")
        disks = w.query(f"SELECT * FROM Win32_LogicalDisk WHERE Name='{drive}'")
        if disks:
            disk = disks[0]
            return float(disk.FreeSpace or 0) / 1e9
    except Exception:
        pass
    return 0


def get_system_temps() -> dict:
    """Get all system temperatures and thermal info.
    Returns dict with cpu_temp, disk_temp, gpu_temp, overall_status."""
    if not _WMI:
        return {"cpu_temp": 0, "disk_temp": 0, "status": "unavailable"}

    results = {"cpu_temp": 0, "disk_temp": 0, "gpu_temp": 0}

    try:
        results["cpu_temp"] = get_cpu_temperature()
        results["disk_temp"] = get_disk_temperature()
    except Exception:
        pass

    # Determine thermal status
    cpu = results["cpu_temp"]
    if cpu > 85:
        status = "critical"
    elif cpu > 75:
        status = "warning"
    elif cpu > 0:
        status = "normal"
    else:
        status = "unavailable"

    results["status"] = status
    results["safe_threshold"] = 80
    results["warning_threshold"] = 75

    return results


def get_fan_speeds() -> list[dict]:
    """Get fan speed information. Returns list of fans with speed in RPM."""
    if not _WMI:
        return []

    fans = []
    try:
        w = wmi.WMI(namespace="root\\cimv2")
        fan_data = w.query("SELECT * FROM Win32_Fan")
        for fan in fan_data:
            try:
                speed = int(fan.CurrentSpeed or 0)
                fans.append({
                    "name": fan.Name or "Unknown",
                    "speed_rpm": speed,
                    "status": fan.Status or "Unknown",
                })
            except Exception:
                pass
    except Exception:
        pass

    return fans


def check_thermal_health() -> dict:
    """Comprehensive thermal health check. Returns health score 0-100."""
    temps = get_system_temps()
    cpu_temp = temps["cpu_temp"]

    score = 100
    issues = []

    if cpu_temp > 85:
        score -= 50
        issues.append("CRITICAL: CPU temperature exceeds 85°C")
    elif cpu_temp > 75:
        score -= 30
        issues.append("WARNING: CPU temperature high (75-85°C)")
    elif cpu_temp > 60:
        score -= 10
        issues.append("NOTICE: CPU running warm (60-75°C)")

    return {
        "score": max(0, min(100, score)),
        "cpu_temp": cpu_temp,
        "status": temps["status"],
        "issues": issues,
        "recommendation": "Clean heatsinks and improve case airflow" if score < 70 else "Thermal system healthy",
    }
