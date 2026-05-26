"""DNS Protector — locks DNS settings and detects unauthorized changes.

Inspired by IObit Advanced SystemCare DNS Protector. Pins user's chosen DNS
servers per active adapter and watches the registry for tampering.
"""

import os
import json
import threading
import time
import subprocess
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None


_CFG_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "FreeSystemDoctor"
_CFG_FILE = _CFG_DIR / "dns_protector.json"

# Common DNS providers
PROVIDERS = {
    "Cloudflare":   ("1.1.1.1", "1.0.0.1"),
    "Google":       ("8.8.8.8", "8.8.4.4"),
    "Quad9":        ("9.9.9.9", "149.112.112.112"),
    "OpenDNS":      ("208.67.222.222", "208.67.220.220"),
    "AdGuard":      ("94.140.14.14", "94.140.15.15"),
    "DHCP (auto)":  ("", ""),
}


def _load_cfg() -> dict:
    if _CFG_FILE.exists():
        try:
            return json.loads(_CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"locked": False, "primary": "", "secondary": "", "provider": ""}


def _save_cfg(cfg: dict):
    _CFG_DIR.mkdir(parents=True, exist_ok=True)
    _CFG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def list_adapters() -> list[dict]:
    """Return list of network adapters with their current DNS servers."""
    adapters = []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-DnsClientServerAddress -AddressFamily IPv4 | "
             "Select-Object InterfaceAlias,ServerAddresses | "
             "ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                alias = item.get("InterfaceAlias", "")
                servers = item.get("ServerAddresses") or []
                if isinstance(servers, str):
                    servers = [servers]
                if alias and not alias.lower().startswith(("loopback", "isatap")):
                    adapters.append({
                        "alias": alias,
                        "primary": servers[0] if len(servers) > 0 else "",
                        "secondary": servers[1] if len(servers) > 1 else "",
                    })
    except Exception:
        pass
    return adapters


def set_dns(alias: str, primary: str, secondary: str = "") -> tuple[bool, str]:
    """Set DNS servers for the named adapter. Empty primary resets to DHCP."""
    try:
        if not primary:
            cmd = ["netsh", "interface", "ipv4", "set", "dnsservers",
                   f"name={alias}", "source=dhcp"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                               creationflags=0x08000000)
            return (r.returncode == 0, r.stdout + r.stderr)

        cmd1 = ["netsh", "interface", "ipv4", "set", "dnsservers",
                f"name={alias}", "static", primary, "primary"]
        r1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=15,
                            creationflags=0x08000000)
        if r1.returncode != 0:
            return (False, r1.stdout + r1.stderr)
        if secondary:
            cmd2 = ["netsh", "interface", "ipv4", "add", "dnsservers",
                    f"name={alias}", secondary, "index=2"]
            subprocess.run(cmd2, capture_output=True, text=True, timeout=15,
                           creationflags=0x08000000)
        return (True, "DNS configured")
    except Exception as e:
        return (False, str(e))


def apply_to_all(primary: str, secondary: str = "") -> list[tuple[str, bool, str]]:
    """Apply DNS to every active adapter. Returns list of (alias, ok, msg)."""
    results = []
    for a in list_adapters():
        ok, msg = set_dns(a["alias"], primary, secondary)
        results.append((a["alias"], ok, msg))
    return results


def lock(primary: str, secondary: str = "", provider: str = "Custom"):
    """Persist desired DNS and start watcher."""
    cfg = {"locked": True, "primary": primary, "secondary": secondary,
           "provider": provider}
    _save_cfg(cfg)
    apply_to_all(primary, secondary)
    _Watcher.ensure_running()


def unlock():
    cfg = _load_cfg()
    cfg["locked"] = False
    _save_cfg(cfg)
    _Watcher.stop()


def is_locked() -> bool:
    return _load_cfg().get("locked", False)


def get_lock_state() -> dict:
    return _load_cfg()


def flush_dns() -> bool:
    try:
        r = subprocess.run(["ipconfig", "/flushdns"],
                           capture_output=True, text=True, timeout=10,
                           creationflags=0x08000000)
        return r.returncode == 0
    except Exception:
        return False


class _Watcher:
    _thread: threading.Thread = None
    _stop_event = threading.Event()
    _on_tamper = None

    @classmethod
    def ensure_running(cls, on_tamper=None):
        cls._on_tamper = on_tamper
        if cls._thread and cls._thread.is_alive():
            return
        cls._stop_event.clear()
        cls._thread = threading.Thread(target=cls._loop, daemon=True)
        cls._thread.start()

    @classmethod
    def stop(cls):
        cls._stop_event.set()

    @classmethod
    def _loop(cls):
        while not cls._stop_event.is_set():
            try:
                cfg = _load_cfg()
                if not cfg.get("locked"):
                    return
                want = cfg.get("primary", "")
                want2 = cfg.get("secondary", "")
                tampered = False
                for a in list_adapters():
                    if want and a["primary"] != want:
                        tampered = True
                        set_dns(a["alias"], want, want2)
                if tampered and cls._on_tamper:
                    try:
                        cls._on_tamper()
                    except Exception:
                        pass
            except Exception:
                pass
            cls._stop_event.wait(15)


def start_watcher_if_locked(on_tamper=None):
    if is_locked():
        _Watcher.ensure_running(on_tamper)
