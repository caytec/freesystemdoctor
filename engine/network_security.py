"""Network Security Scanner — identify devices on network and potential threats."""

import subprocess
import socket
import threading
from collections import defaultdict

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


def get_local_ip() -> str:
    """Get local machine's IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_network_subnet() -> str:
    """Get network subnet (e.g., 192.168.1.0/24)."""
    local_ip = get_local_ip()
    octets = local_ip.split(".")
    return f"{'.'.join(octets[:3])}.0/24"


def scan_network_devices(timeout_ms: int = 500) -> list[dict]:
    """Scan local /24 subnet in parallel using a thread pool.

    Each ping uses a short timeout (default 500 ms). Total scan ~6-10s.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    devices = []
    local_ip = get_local_ip()
    if not local_ip or local_ip.startswith("127."):
        return devices
    subnet_parts = local_ip.split(".")[:3]

    def probe(i: int):
        ip = f"{'.'.join(subnet_parts)}.{i}"
        if ip == local_ip:
            return None
        try:
            r = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout_ms), ip],
                capture_output=True, text=True, timeout=2,
                creationflags=0x08000000,
            )
            if r.returncode == 0:
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except Exception:
                    hostname = "Unknown"
                return {"ip": ip, "hostname": hostname,
                        "status": "active", "ping_success": True}
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=64) as ex:
        futures = [ex.submit(probe, i) for i in range(1, 255)]
        for f in as_completed(futures):
            try:
                result = f.result()
                if result:
                    devices.append(result)
            except Exception:
                pass

    devices.sort(key=lambda d: tuple(int(x) for x in d["ip"].split(".")))
    return devices


def get_open_ports() -> list[dict]:
    """Get list of open listening ports on local machine."""
    if not _PSUTIL:
        return []

    ports = []
    try:
        connections = psutil.net_connections()
        seen = set()

        for conn in connections:
            if conn.status == "LISTEN" and conn.laddr:
                port = conn.laddr[1]
                if port not in seen:
                    seen.add(port)
                    try:
                        service = socket.getservbyport(port)
                    except OSError:
                        service = "Unknown"

                    ports.append({
                        "port": port,
                        "service": service,
                        "status": "open",
                    })
    except Exception:
        pass

    return sorted(ports, key=lambda x: x["port"])


def check_port_security(port: int) -> dict:
    """Check if a port is potentially vulnerable."""
    known_vulnerable = {
        21: ("FTP", "high"),
        23: ("Telnet", "critical"),
        135: ("RPC", "high"),
        139: ("NetBIOS", "high"),
        445: ("SMB", "high"),
        3389: ("RDP", "medium"),
    }

    if port in known_vulnerable:
        name, risk = known_vulnerable[port]
        return {"port": port, "service": name, "risk": risk, "vulnerable": True}

    return {"port": port, "risk": "low", "vulnerable": False}


def get_network_security_status() -> dict:
    """Comprehensive network security audit."""
    status = {
        "open_ports": get_open_ports(),
        "vulnerable_ports": [],
        "network_devices": 0,
        "local_ip": get_local_ip(),
        "risk_level": "low",
    }

    # Check each port for vulnerabilities
    for port_info in status["open_ports"]:
        vuln = check_port_security(port_info["port"])
        if vuln["vulnerable"]:
            status["vulnerable_ports"].append(vuln)

    # Determine overall risk
    if any(p["risk"] == "critical" for p in status["vulnerable_ports"]):
        status["risk_level"] = "critical"
    elif any(p["risk"] == "high" for p in status["vulnerable_ports"]):
        status["risk_level"] = "high"
    elif any(p["risk"] == "medium" for p in status["vulnerable_ports"]):
        status["risk_level"] = "medium"

    return status


def identify_bandwidth_hogs() -> list[dict]:
    """Identify processes using significant bandwidth."""
    if not _PSUTIL:
        return []

    hogs = []
    try:
        for proc in psutil.process_iter(["pid", "name", "connections"]):
            try:
                conns = proc.connections(kind="inet")
                if len(conns) > 5:
                    hogs.append({
                        "pid": proc.pid,
                        "name": proc.name(),
                        "connection_count": len(conns),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

    return sorted(hogs, key=lambda x: x["connection_count"], reverse=True)[:10]


def get_firewall_status() -> dict:
    """Get Windows Firewall status — parses per-profile state from netsh."""
    profiles = {"Domain": None, "Private": None, "Public": None}
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles"],
            capture_output=True, text=True, timeout=8,
            creationflags=0x08000000,
        )
        current_profile = None
        for line in (result.stdout or "").splitlines():
            stripped = line.strip()
            for name in profiles:
                if stripped.lower().startswith(f"{name.lower()} profile settings"):
                    current_profile = name
                    break
            if current_profile and stripped.lower().startswith("state"):
                # "State                                 ON" or OFF
                parts = stripped.split()
                if len(parts) >= 2:
                    val = parts[-1].upper()
                    profiles[current_profile] = (val == "ON")
    except Exception:
        pass

    enabled_profiles = [k for k, v in profiles.items() if v is True]
    all_enabled = all(v for v in profiles.values() if v is not None) and any(profiles.values())

    return {
        "firewall_enabled": all_enabled,
        "status": "enabled" if all_enabled else
                  ("partial" if enabled_profiles else "disabled"),
        "profiles": profiles,
    }
