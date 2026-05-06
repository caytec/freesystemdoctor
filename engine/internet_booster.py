"""
internet_booster.py — DNS benchmarking, TCP optimisation, and network utilities.
Part of FreeSystemDoctor engine.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import time
import winreg
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "internet_booster.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DNS_SERVERS: list[dict] = [
    {"ip": "8.8.8.8",         "name": "Google Primary"},
    {"ip": "8.8.4.4",         "name": "Google Secondary"},
    {"ip": "1.1.1.1",         "name": "Cloudflare Primary"},
    {"ip": "1.0.0.1",         "name": "Cloudflare Secondary"},
    {"ip": "9.9.9.9",         "name": "Quad9"},
    {"ip": "208.67.222.222",  "name": "OpenDNS Primary"},
    {"ip": "208.67.220.220",  "name": "OpenDNS Secondary"},
    {"ip": "94.140.14.14",    "name": "AdGuard Primary"},
    {"ip": "94.140.15.15",    "name": "AdGuard Secondary"},
]

_DEFAULT_TEST_DOMAINS: list[str] = [
    "google.com",
    "microsoft.com",
    "cloudflare.com",
    "github.com",
    "youtube.com",
]

# Registry path for TCP global params
_TCP_PARAMS_KEY = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
_TCP_IFACE_KEY  = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 30, encoding: str = "utf-8", errors: str = "replace") -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding=encoding,
            errors=errors,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return result.returncode, result.stdout or ""
    except subprocess.TimeoutExpired:
        return -1, "Timeout"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"
    except Exception as exc:
        logger.exception("_run error: %s", exc)
        return -1, str(exc)


def _run_powershell(script: str, timeout: int = 60) -> tuple[int, str]:
    return _run(
        ["powershell", "-NonInteractive", "-NoProfile", "-Command", script],
        timeout=timeout,
    )


def _reg_read(root, key_path: str, value_name: str, default=None):
    try:
        with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, value_name)
            return val
    except FileNotFoundError:
        return default
    except Exception as exc:
        logger.debug("_reg_read %s\\%s: %s", key_path, value_name, exc)
        return default


def _reg_write(root, key_path: str, value_name: str, value, reg_type=winreg.REG_DWORD) -> bool:
    try:
        with winreg.CreateKeyEx(root, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, value_name, 0, reg_type, value)
        return True
    except Exception as exc:
        logger.warning("_reg_write %s\\%s: %s", key_path, value_name, exc)
        return False


def _reg_delete_value(root, key_path: str, value_name: str) -> bool:
    try:
        with winreg.OpenKey(root, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, value_name)
        return True
    except FileNotFoundError:
        return True  # Already absent
    except Exception as exc:
        logger.debug("_reg_delete_value %s\\%s: %s", key_path, value_name, exc)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_dns() -> dict:
    """
    Return current DNS settings for all adapters.

    Returns:
        {adapters: list[{adapter, dns_servers: list[str]}]}
    """
    adapters: list[dict] = []
    try:
        rc, out = _run(["ipconfig", "/all"], timeout=15)
        if rc != 0:
            return {"adapters": adapters}

        current_adapter = None
        dns_servers: list[str] = []

        for line in out.splitlines():
            # New adapter section
            adapter_match = re.match(r"^[A-Za-z].*adapter (.+):$", line)
            if adapter_match:
                if current_adapter:
                    adapters.append({"adapter": current_adapter, "dns_servers": dns_servers})
                current_adapter = adapter_match.group(1).strip()
                dns_servers = []
                continue

            if current_adapter:
                # DNS Server lines
                dns_match = re.search(r"DNS Servers[^:]*:\s+(.+)", line, re.IGNORECASE)
                if dns_match:
                    dns_servers.append(dns_match.group(1).strip())
                    continue
                # Continuation lines (indented with spaces, no label)
                if re.match(r"^\s{20,}(\d{1,3}\.){3}\d{1,3}\s*$", line):
                    ip = line.strip()
                    if ip and ip not in dns_servers:
                        dns_servers.append(ip)

        if current_adapter:
            adapters.append({"adapter": current_adapter, "dns_servers": dns_servers})

    except Exception as exc:
        logger.exception("get_current_dns failed: %s", exc)

    return {"adapters": adapters}


def dns_benchmark(
    servers: Optional[list[str]] = None,
    test_domains: Optional[list[str]] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> list[dict]:
    """
    Benchmark DNS servers by timing resolution of several domains.

    Args:
        servers: List of IP strings to test. Defaults to well-known + system DNS.
        test_domains: Domains to resolve. Defaults to _DEFAULT_TEST_DOMAINS.
        progress_cb: Called with status strings during the test.

    Returns:
        List of {server, name, avg_ms, min_ms, max_ms, success_rate} sorted by avg_ms.
    """
    results: list[dict] = []
    try:
        if test_domains is None:
            test_domains = _DEFAULT_TEST_DOMAINS

        # Build server list
        server_defs: list[dict] = []
        seen: set[str] = set()
        for entry in _DEFAULT_DNS_SERVERS:
            if entry["ip"] not in seen:
                seen.add(entry["ip"])
                server_defs.append(entry.copy())

        # Add current system DNS servers
        current = get_current_dns()
        for adapter in current.get("adapters", []):
            for ip in adapter.get("dns_servers", []):
                ip = ip.strip()
                if ip and ip not in seen:
                    seen.add(ip)
                    server_defs.append({"ip": ip, "name": f"System DNS ({adapter['adapter']})"})

        # Override if explicit list provided
        if servers:
            server_defs = []
            for ip in servers:
                ip = ip.strip()
                server_defs.append({"ip": ip, "name": ip})

        for sd in server_defs:
            ip = sd["ip"]
            name = sd["name"]
            if progress_cb:
                try:
                    progress_cb(f"Testing {name} ({ip})...")
                except Exception:
                    pass

            times_ms: list[float] = []
            successes = 0

            for domain in test_domains:
                start = time.perf_counter()
                rc, out = _run(
                    ["nslookup", domain, ip],
                    timeout=10,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000
                if rc == 0 and "answer" in out.lower() or "name:" in out.lower() or "address" in out.lower():
                    times_ms.append(elapsed_ms)
                    successes += 1
                else:
                    # Still record the timing even on failure but don't count as success
                    times_ms.append(elapsed_ms)

            if times_ms:
                avg = round(sum(times_ms) / len(times_ms), 2)
                min_ms = round(min(times_ms), 2)
                max_ms = round(max(times_ms), 2)
            else:
                avg = min_ms = max_ms = 9999.0

            success_rate = round(successes / len(test_domains) * 100, 1) if test_domains else 0.0
            results.append({
                "server": ip,
                "name": name,
                "avg_ms": avg,
                "min_ms": min_ms,
                "max_ms": max_ms,
                "success_rate": success_rate,
            })

        results.sort(key=lambda x: (x["avg_ms"], -x["success_rate"]))

    except Exception as exc:
        logger.exception("dns_benchmark failed: %s", exc)

    return results


def set_dns(adapter: str, primary: str, secondary: str = "") -> bool:
    """
    Set DNS server(s) for a network adapter using netsh.

    Args:
        adapter: Adapter name (e.g. "Ethernet" or "Wi-Fi")
        primary: Primary DNS IP
        secondary: Secondary DNS IP (optional)

    Returns:
        True on success.
    """
    try:
        rc1, out1 = _run(
            ["netsh", "interface", "ip", "set", "dns", f"name={adapter}", "static", primary],
            timeout=30,
        )
        if rc1 != 0:
            logger.warning("set_dns primary failed: %s", out1)
            return False

        if secondary:
            rc2, out2 = _run(
                ["netsh", "interface", "ip", "add", "dns", f"name={adapter}", secondary, "index=2"],
                timeout=30,
            )
            if rc2 != 0:
                logger.warning("set_dns secondary failed: %s", out2)
                # Primary succeeded; don't fail entirely
        logger.info("set_dns %s -> %s / %s", adapter, primary, secondary)
        return True
    except Exception as exc:
        logger.exception("set_dns failed: %s", exc)
        return False


def reset_dns_to_auto(adapter: str) -> bool:
    """
    Reset DNS to DHCP-assigned (automatic) for the given adapter.

    Returns:
        True on success.
    """
    try:
        rc, out = _run(
            ["netsh", "interface", "ip", "set", "dns", f"name={adapter}", "dhcp"],
            timeout=30,
        )
        logger.info("reset_dns_to_auto %s: rc=%d", adapter, rc)
        return rc == 0
    except Exception as exc:
        logger.exception("reset_dns_to_auto failed: %s", exc)
        return False


def get_tcp_settings() -> dict:
    """
    Read current TCP optimisation settings from the registry.

    Returns:
        Dict of setting names to their current values.
    """
    settings: dict = {}
    try:
        root = winreg.HKEY_LOCAL_MACHINE
        key = _TCP_PARAMS_KEY

        # Global TCP/IP parameters
        for name, default in [
            ("DefaultTTL", 128),
            ("TcpTimedWaitDelay", 30),
            ("MaxUserPort", 65534),
            ("TcpNumConnections", None),
            ("Tcp1323Opts", 0),
            ("TCPNoDelay", 0),
            ("TcpAckFrequency", 2),
            ("GlobalMaxTcpWindowSize", None),
            ("TcpWindowSize", None),
        ]:
            settings[name] = _reg_read(root, key, name, default)

        # Nagle's algorithm: interface-level TcpAckFrequency / TCPNoDelay
        # Check first interface subkey for per-interface values
        try:
            with winreg.OpenKey(root, _TCP_IFACE_KEY) as ifaces_key:
                n = 0
                while True:
                    try:
                        guid = winreg.EnumKey(ifaces_key, n)
                        iface_path = f"{_TCP_IFACE_KEY}\\{guid}"
                        ack_freq = _reg_read(root, iface_path, "TcpAckFrequency", None)
                        no_delay  = _reg_read(root, iface_path, "TCPNoDelay", None)
                        if ack_freq is not None or no_delay is not None:
                            settings.setdefault("interfaces", []).append({
                                "guid": guid,
                                "TcpAckFrequency": ack_freq,
                                "TCPNoDelay": no_delay,
                            })
                        n += 1
                    except OSError:
                        break
        except Exception as exc:
            logger.debug("Interface TCP key enumeration: %s", exc)

    except Exception as exc:
        logger.exception("get_tcp_settings failed: %s", exc)

    return settings


def optimize_tcp(aggressive: bool = False) -> list[str]:
    """
    Apply TCP registry tweaks for lower latency and higher throughput.

    Args:
        aggressive: If True, applies more aggressive tweaks (may not suit all connections).

    Returns:
        List of changes made.
    """
    changes: list[str] = []
    root = winreg.HKEY_LOCAL_MACHINE
    key = _TCP_PARAMS_KEY

    tweaks = [
        # (name, value, description)
        ("DefaultTTL",       64,    "Set DefaultTTL to 64 (Linux-compatible)"),
        ("TcpTimedWaitDelay", 30,   "Reduce TIME_WAIT delay to 30s"),
        ("MaxUserPort",      65534, "Increase MaxUserPort to 65534"),
        ("Tcp1323Opts",      1,     "Enable TCP window scaling and timestamps"),
    ]
    if aggressive:
        tweaks += [
            ("GlobalMaxTcpWindowSize", 65535, "Set GlobalMaxTcpWindowSize to 65535"),
            ("TcpWindowSize",          65535, "Set TcpWindowSize to 65535"),
        ]

    for name, value, desc in tweaks:
        try:
            if _reg_write(root, key, name, value):
                changes.append(desc)
                logger.info("optimize_tcp: %s = %s", name, value)
        except Exception as exc:
            logger.warning("optimize_tcp tweak %s failed: %s", name, exc)

    # Disable Nagle's algorithm per interface (TCPNoDelay + TcpAckFrequency=1)
    try:
        with winreg.OpenKey(root, _TCP_IFACE_KEY) as ifaces_key:
            n = 0
            while True:
                try:
                    guid = winreg.EnumKey(ifaces_key, n)
                    iface_path = f"{_TCP_IFACE_KEY}\\{guid}"
                    _reg_write(root, iface_path, "TcpAckFrequency", 1)
                    _reg_write(root, iface_path, "TCPNoDelay", 1)
                    n += 1
                except OSError:
                    break
        changes.append("Disabled Nagle's algorithm on all interfaces (TcpAckFrequency=1, TCPNoDelay=1)")
    except Exception as exc:
        logger.warning("optimize_tcp Nagle disable failed: %s", exc)

    return changes


def reset_tcp() -> list[str]:
    """
    Revert TCP settings to Windows defaults.

    Returns:
        List of changes made.
    """
    changes: list[str] = []
    root = winreg.HKEY_LOCAL_MACHINE
    key = _TCP_PARAMS_KEY

    defaults = [
        ("DefaultTTL",             128),
        ("TcpTimedWaitDelay",       30),
        ("MaxUserPort",           5000),
        ("Tcp1323Opts",              0),
        ("GlobalMaxTcpWindowSize", None),  # Delete
        ("TcpWindowSize",          None),  # Delete
    ]

    for name, value in defaults:
        try:
            if value is None:
                if _reg_delete_value(root, key, name):
                    changes.append(f"Removed custom value {name}")
            else:
                if _reg_write(root, key, name, value):
                    changes.append(f"Reset {name} to {value}")
        except Exception as exc:
            logger.warning("reset_tcp %s failed: %s", name, exc)

    # Re-enable Nagle's algorithm per interface
    try:
        with winreg.OpenKey(root, _TCP_IFACE_KEY) as ifaces_key:
            n = 0
            while True:
                try:
                    guid = winreg.EnumKey(ifaces_key, n)
                    iface_path = f"{_TCP_IFACE_KEY}\\{guid}"
                    _reg_delete_value(root, iface_path, "TcpAckFrequency")
                    _reg_delete_value(root, iface_path, "TCPNoDelay")
                    n += 1
                except OSError:
                    break
        changes.append("Re-enabled Nagle's algorithm on all interfaces")
    except Exception as exc:
        logger.warning("reset_tcp Nagle restore failed: %s", exc)

    return changes


def get_network_adapters() -> list[dict]:
    """
    Return active network adapters with their properties.

    Returns:
        List of {name, description, ip, mac, speed_mbps, status}
    """
    adapters: list[dict] = []
    try:
        script = (
            "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed, MacAddress | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        rc, out = _run_powershell(script, timeout=30)
        if rc != 0 or not out.strip():
            return adapters

        import csv, io
        reader = csv.DictReader(io.StringIO(out))
        for row in reader:
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            # Get IP for this adapter
            ip = _get_adapter_ip(name)
            speed_raw = (row.get("LinkSpeed") or "").strip()
            speed_mbps = _parse_speed_mbps(speed_raw)
            adapters.append({
                "name": name,
                "description": (row.get("InterfaceDescription") or "").strip(),
                "ip": ip,
                "mac": (row.get("MacAddress") or "").strip(),
                "speed_mbps": speed_mbps,
                "status": (row.get("Status") or "").strip(),
            })
    except Exception as exc:
        logger.exception("get_network_adapters failed: %s", exc)
    return adapters


def _get_adapter_ip(adapter_name: str) -> str:
    try:
        script = (
            f"Get-NetIPAddress -InterfaceAlias '{adapter_name}' -AddressFamily IPv4 "
            f"| Select-Object -ExpandProperty IPAddress"
        )
        rc, out = _run_powershell(script, timeout=15)
        if rc == 0:
            return out.strip().splitlines()[0] if out.strip() else ""
    except Exception:
        pass
    return ""


def _parse_speed_mbps(speed_str: str) -> float:
    """Parse speed strings like '1 Gbps', '100 Mbps' into Mbps float."""
    try:
        match = re.search(r"([\d.]+)\s*(G|M|K)?bps", speed_str, re.IGNORECASE)
        if match:
            num = float(match.group(1))
            unit = (match.group(2) or "M").upper()
            if unit == "G":
                return num * 1000
            elif unit == "K":
                return num / 1000
            return num
    except Exception:
        pass
    return 0.0


def flush_dns() -> bool:
    """
    Flush the DNS resolver cache.

    Returns:
        True on success.
    """
    try:
        rc, out = _run(["ipconfig", "/flushdns"], timeout=15)
        logger.info("flush_dns: rc=%d", rc)
        return rc == 0
    except Exception as exc:
        logger.exception("flush_dns failed: %s", exc)
        return False
