"""Network optimizer — DNS flush, TCP tuning, adapter info, ping, DNS benchmark."""

import subprocess
import winreg
import socket
import time


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _rw(hkey, path, name, vtype, value) -> bool:
    try:
        with winreg.OpenKey(hkey, path, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, name, 0, vtype, value)
        return True
    except OSError:
        return False


# ── DNS ──────────────────────────────────────────────────────────────────────

def flush_dns() -> bool:
    r = _run(["ipconfig", "/flushdns"])
    return r.returncode == 0


def flush_arp() -> bool:
    r = _run(["netsh", "interface", "ip", "delete", "arpcache"])
    return r.returncode == 0


def get_dns_cache_lines() -> list[str]:
    r = _run(["ipconfig", "/displaydns"])
    return r.stdout.splitlines()[:100]


DNS_PRESETS = {
    "Google       (8.8.8.8 / 8.8.4.4)":        ("8.8.8.8",        "8.8.4.4"),
    "Cloudflare   (1.1.1.1 / 1.0.0.1)":        ("1.1.1.1",        "1.0.0.1"),
    "OpenDNS      (208.67.222.222)":            ("208.67.222.222",  "208.67.220.220"),
    "Quad9        (9.9.9.9 / 149.112.112.112)": ("9.9.9.9",        "149.112.112.112"),
    "Automatic (DHCP)":                         ("dhcp",           ""),
}


def set_dns(interface: str, primary: str, secondary: str = "") -> bool:
    if primary.lower() == "dhcp":
        r = _run(["netsh", "interface", "ip", "set", "dns",
                  f"name={interface}", "dhcp"])
        return r.returncode == 0
    r1 = _run(["netsh", "interface", "ip", "set", "dns",
               f"name={interface}", "static", primary])
    if secondary:
        _run(["netsh", "interface", "ip", "add", "dns",
              f"name={interface}", secondary, "index=2"])
    return r1.returncode == 0


def benchmark_dns(host: str = "www.google.com") -> dict:
    results = {}
    for label, (primary, _) in DNS_PRESETS.items():
        if primary == "dhcp":
            continue
        try:
            start = time.perf_counter()
            socket.getaddrinfo.__module__  # noop
            # Use a quick connect to measure
            s = socket.socket()
            s.settimeout(2)
            s.connect((primary, 53))
            s.close()
            ms = round((time.perf_counter() - start) * 1000, 1)
            results[label.split("(")[0].strip()] = ms
        except Exception:
            results[label.split("(")[0].strip()] = None
    return results


# ── TCP tweaks ────────────────────────────────────────────────────────────────

_TCP_REG = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"

_TWEAKS_PERFORMANCE = {
    "TcpMaxDataRetransmissions": 5,
    "DefaultTTL":                64,
    "EnablePMTUDiscovery":       1,
    "SackOpts":                  1,
    "Tcp1323Opts":               3,
    "TCPNoDelay":                1,
}

_TWEAKS_DEFAULT = {
    "TcpMaxDataRetransmissions": 5,
    "DefaultTTL":                128,
    "EnablePMTUDiscovery":       1,
    "SackOpts":                  1,
    "Tcp1323Opts":               0,
    "TCPNoDelay":                0,
}


def apply_tcp_tweaks() -> list[str]:
    done = []
    for name, val in _TWEAKS_PERFORMANCE.items():
        if _rw(winreg.HKEY_LOCAL_MACHINE, _TCP_REG, name, winreg.REG_DWORD, val):
            done.append(f"{name} = {val}")
    r = _run(["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"])
    if r.returncode == 0:
        done.append("TCP auto-tuning = normal")
    r2 = _run(["netsh", "int", "tcp", "set", "global", "ecncapability=enabled"])
    if r2.returncode == 0:
        done.append("ECN capability = enabled")
    return done


def reset_tcp_tweaks() -> list[str]:
    done = []
    for name, val in _TWEAKS_DEFAULT.items():
        if _rw(winreg.HKEY_LOCAL_MACHINE, _TCP_REG, name, winreg.REG_DWORD, val):
            done.append(f"{name} = {val}")
    _run(["netsh", "int", "ip", "reset"])
    done.append("TCP/IP stack reset")
    return done


def get_tcp_global() -> str:
    r = _run(["netsh", "int", "tcp", "show", "global"])
    return r.stdout


# ── adapters ─────────────────────────────────────────────────────────────────

def get_adapters() -> list[dict]:
    r = _run(["powershell", "-NoProfile", "-Command",
              "Get-NetAdapter | Select-Object Name,Status,LinkSpeed,MacAddress,"
              "InterfaceDescription | ConvertTo-Csv -NoTypeInformation"])
    adapters = []
    lines = r.stdout.strip().splitlines()
    if len(lines) < 2:
        return adapters
    headers = [h.strip('"') for h in lines[0].split(",")]
    for line in lines[1:]:
        vals = [v.strip('"') for v in line.split(",")]
        if len(vals) == len(headers):
            adapters.append(dict(zip(headers, vals)))
    return adapters


def get_active_adapters() -> list[str]:
    return [a["Name"] for a in get_adapters() if a.get("Status") == "Up"]


def get_ip_config() -> str:
    return _run(["ipconfig", "/all"]).stdout


# ── ping ──────────────────────────────────────────────────────────────────────

def ping(host: str = "8.8.8.8", count: int = 4) -> dict:
    r = _run(["ping", "-n", str(count), host])
    import re
    m = re.search(r"Average = (\d+)ms", r.stdout)
    avg = int(m.group(1)) if m else None
    lost_m = re.search(r"\((\d+)% loss\)", r.stdout)
    loss = int(lost_m.group(1)) if lost_m else None
    return {
        "host":      host,
        "reachable": r.returncode == 0,
        "avg_ms":    avg,
        "loss_pct":  loss,
        "output":    r.stdout,
    }


def get_current_dns_latency() -> float | None:
    try:
        start = time.perf_counter()
        socket.gethostbyname("www.google.com")
        return round((time.perf_counter() - start) * 1000, 1)
    except Exception:
        return None
