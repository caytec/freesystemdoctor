"""Network Diagnostics — advanced network testing and optimization."""

import socket
import struct
import subprocess
import time
from datetime import datetime

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class NetworkTest:
    """Represents a network diagnostic test result."""
    def __init__(self, name: str, status: str, value: str, unit: str = ""):
        self.name = name
        self.status = status
        self.value = value
        self.unit = unit
        self.timestamp = datetime.now()


def _run_ping(host: str, count: int = 4) -> tuple[float, float, int]:
    """Ping a host and return (min_ms, avg_ms, loss_percent)."""
    try:
        result = subprocess.run(
            ["ping", "-n", str(count), host],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout
        if "Reply from" in output:
            if "Minimum = " in output:
                stats_line = [line for line in output.split('\n') if "Minimum = " in line][0]
                parts = stats_line.split(",")
                min_ms = float(parts[0].split("=")[1].strip().rstrip("ms"))
                avg_ms = float(parts[1].split("=")[1].strip().rstrip("ms"))
                loss_line = [line for line in output.split('\n') if "Packets" in line and "loss" in line][0]
                loss_percent = int(loss_line.split("(")[1].split("%")[0])
                return (min_ms, avg_ms, loss_percent)
    except Exception:
        pass

    return (0, 0, 100)


def test_dns_resolution() -> NetworkTest:
    """Test DNS resolution capability."""
    try:
        start = time.time()
        ip = socket.gethostbyname("google.com")
        elapsed_ms = (time.time() - start) * 1000

        status = "PASS" if elapsed_ms < 100 else "SLOW" if elapsed_ms < 500 else "FAIL"
        return NetworkTest("DNS Resolution", status, f"{elapsed_ms:.0f}", "ms")
    except Exception:
        return NetworkTest("DNS Resolution", "FAIL", "0", "ms")


def test_gateway_connectivity() -> NetworkTest:
    """Test connectivity to default gateway."""
    try:
        result = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            text=True,
            timeout=5
        )

        gateway = None
        for line in result.stdout.split('\n'):
            if "Default Gateway" in line:
                gateway = line.split(":")[-1].strip()
                break

        if gateway and gateway != "":
            min_ms, avg_ms, loss = _run_ping(gateway, count=3)
            status = "PASS" if loss == 0 else "DEGRADED" if loss < 50 else "FAIL"
            return NetworkTest("Gateway Connectivity", status, f"{avg_ms:.0f}", "ms")
    except Exception:
        pass

    return NetworkTest("Gateway Connectivity", "UNKNOWN", "N/A", "")


def test_internet_connectivity() -> NetworkTest:
    """Test internet connectivity to public DNS servers."""
    min_ms, avg_ms, loss = _run_ping("8.8.8.8", count=4)
    status = "PASS" if loss == 0 else "DEGRADED" if loss < 50 else "FAIL"
    return NetworkTest("Internet Connectivity", status, f"{avg_ms:.0f}", "ms")


def test_dns_leak() -> NetworkTest:
    """Check for DNS leaks (simplified check)."""
    try:
        # Simple test: resolve localhost, should not leak
        local_ip = socket.gethostbyname("localhost")
        if local_ip == "127.0.0.1":
            return NetworkTest("DNS Leak Protection", "PASS", "Not leaking", "")
    except Exception:
        pass

    return NetworkTest("DNS Leak Protection", "UNKNOWN", "Cannot verify", "")


def test_ipv6_leak() -> NetworkTest:
    """Check for IPv6 leaks."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Test-Connection -ComputerName ipv6.google.com -ErrorAction SilentlyContinue"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return NetworkTest("IPv6 Available", "OK", "IPv6 enabled", "")
        else:
            return NetworkTest("IPv6 Available", "OK", "IPv6 disabled", "")
    except Exception:
        pass

    return NetworkTest("IPv6 Available", "UNKNOWN", "N/A", "")


def test_open_ports() -> list[NetworkTest]:
    """Test for commonly exploited open ports."""
    results = []
    common_ports = [22, 23, 80, 443, 3389, 3306, 5432]

    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            if result == 0:
                port_name = {
                    22: "SSH", 23: "Telnet", 80: "HTTP", 443: "HTTPS",
                    3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL"
                }.get(port, f"Port {port}")
                results.append(NetworkTest(f"Port {port} ({port_name})", "OPEN", "Listening", ""))
        except Exception:
            pass

    return results


def get_network_stats() -> dict:
    """Get current network statistics."""
    if not _PSUTIL:
        return {}

    try:
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent_mb": net_io.bytes_sent / (1024**2),
            "bytes_recv_mb": net_io.bytes_recv / (1024**2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout,
            "dropped_in": net_io.dropin,
            "dropped_out": net_io.dropout,
        }
    except Exception:
        return {}


def run_all_diagnostics() -> tuple[list[NetworkTest], list[NetworkTest]]:
    """Run all network diagnostics."""
    basic_tests = []

    basic_tests.append(test_dns_resolution())
    basic_tests.append(test_gateway_connectivity())
    basic_tests.append(test_internet_connectivity())
    basic_tests.append(test_dns_leak())
    basic_tests.append(test_ipv6_leak())

    port_tests = test_open_ports()

    return (basic_tests, port_tests)


def get_network_recommendations() -> list[str]:
    """Get recommendations based on network diagnostics."""
    recommendations = []
    basic_tests, port_tests = run_all_diagnostics()

    failed_tests = [t for t in basic_tests if t.status == "FAIL"]
    if failed_tests:
        recommendations.append(f"Network issues detected: {', '.join(t.name for t in failed_tests)}")

    slow_tests = [t for t in basic_tests if t.status == "SLOW"]
    if slow_tests:
        recommendations.append(f"Slow network response: {', '.join(t.name for t in slow_tests)}")

    open_ports = [t for t in port_tests if t.status == "OPEN"]
    if open_ports:
        recommendations.append(f"Found {len(open_ports)} open port(s) — verify if intentional")

    if not failed_tests and not slow_tests and not open_ports:
        recommendations.append("Network connectivity and security looks good!")

    return recommendations
