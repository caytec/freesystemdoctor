"""Browser Protection — detect browsers, safe browsing checks, hosts-based ad blocking."""

import os
import winreg
import subprocess
from pathlib import Path


# ── browser detection ─────────────────────────────────────────────────────────

_BROWSER_REGISTRY = {
    "Chrome": (winreg.HKEY_LOCAL_MACHINE,
               r"SOFTWARE\Google\Chrome\BLBeacon", "version"),
    "Edge":   (winreg.HKEY_LOCAL_MACHINE,
               r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{56EB18F8-B008-4CBD-B6D2-8C97FE7E9062}",
               "pv"),
    "Firefox":(winreg.HKEY_LOCAL_MACHINE,
               r"SOFTWARE\Mozilla\Mozilla Firefox", "CurrentVersion"),
}

_BROWSER_EXE = {
    "Chrome":  Path(os.environ.get("LOCALAPPDATA","")) / "Google/Chrome/Application/chrome.exe",
    "Edge":    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    "Firefox": Path(r"C:\Program Files\Mozilla Firefox\firefox.exe"),
}


def detect_browsers() -> list[dict]:
    browsers = []
    for name, exe_path in _BROWSER_EXE.items():
        installed = exe_path.exists()
        version = _get_browser_version(name)
        if installed or version:
            browsers.append({
                "name": name,
                "installed": True,
                "version": version or "Unknown",
                "exe": str(exe_path),
            })
    return browsers


def _get_browser_version(name: str) -> str:
    hkey, path, value_name = _BROWSER_REGISTRY.get(name, (None, None, None))
    if hkey is None:
        return ""
    try:
        with winreg.OpenKey(hkey, path) as k:
            v, _ = winreg.QueryValueEx(k, value_name)
            return str(v)
    except OSError:
        pass
    # Try HKCU
    try:
        hkey2 = winreg.HKEY_CURRENT_USER
        with winreg.OpenKey(hkey2, path) as k:
            v, _ = winreg.QueryValueEx(k, value_name)
            return str(v)
    except OSError:
        return ""


# ── safe browsing ─────────────────────────────────────────────────────────────

_SAFE_BROWSING_KEYS = {
    "Chrome": (winreg.HKEY_LOCAL_MACHINE,
               r"SOFTWARE\Policies\Google\Chrome", "SafeBrowsingEnabled"),
    "Edge":   (winreg.HKEY_LOCAL_MACHINE,
               r"SOFTWARE\Policies\Microsoft\Edge", "SmartScreenEnabled"),
}


def get_safe_browsing_status(browser: str) -> str:
    """Returns 'enabled', 'disabled', or 'default' (no policy set)."""
    entry = _SAFE_BROWSING_KEYS.get(browser)
    if not entry:
        return "default"
    hkey, path, name = entry
    try:
        with winreg.OpenKey(hkey, path) as k:
            v, _ = winreg.QueryValueEx(k, name)
            return "enabled" if v else "disabled"
    except OSError:
        return "default"


def set_safe_browsing(browser: str, enabled: bool) -> bool:
    entry = _SAFE_BROWSING_KEYS.get(browser)
    if not entry:
        return False
    hkey, path, name = entry
    try:
        with winreg.CreateKey(hkey, path) as k:
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, 1 if enabled else 0)
        return True
    except OSError:
        return False


# ── ad blocking via hosts ─────────────────────────────────────────────────────

_HOSTS = Path(r"C:\Windows\System32\drivers\etc\hosts")
_MARKER_START = "# === FreeSystemDoctor AdBlock START ==="
_MARKER_END   = "# === FreeSystemDoctor AdBlock END ==="

AD_DOMAINS = [
    "ads.google.com", "doubleclick.net", "googleadservices.com",
    "googlesyndication.com", "adnxs.com", "adsymptotic.com",
    "scorecardresearch.com", "quantserve.com", "taboola.com",
    "outbrain.com", "amazon-adsystem.com", "advertising.com",
    "ad.doubleclick.net", "googletagmanager.com", "pagead2.googlesyndication.com",
    "ads.yahoo.com", "ads.twitter.com", "connect.facebook.net",
    "static.ads-twitter.com", "bat.bing.com", "c.microsoft.com",
    "telemetry.microsoft.com", "vortex.data.microsoft.com",
    "watson.microsoft.com", "settings-win.data.microsoft.com",
    "ads1.msn.com", "adservice.google.com", "adservice.google.co.uk",
    "pubmatic.com", "rubiconproject.com", "openx.net",
    "media.net", "criteo.com", "criteo.net",
    "casalemedia.com", "mopub.com", "smaato.net",
    "appnexus.com", "sizmek.com", "teads.tv",
    "moatads.com", "2mdn.net", "yieldmanager.com",
    "ad.turn.com", "bidswitch.net", "emxdgt.com",
    "spotxchange.com", "aniview.com", "indexww.com",
]


def get_ad_blocking_status() -> bool:
    try:
        content = _HOSTS.read_text(encoding="utf-8", errors="replace")
        return _MARKER_START in content
    except OSError:
        return False


def get_blocked_count() -> int:
    return len(AD_DOMAINS) if get_ad_blocking_status() else 0


def enable_ad_blocking() -> bool:
    try:
        content = _HOSTS.read_text(encoding="utf-8", errors="replace")
        if _MARKER_START in content:
            return True  # already enabled
        block_lines = [_MARKER_START]
        for domain in AD_DOMAINS:
            block_lines.append(f"0.0.0.0 {domain}")
        block_lines.append(_MARKER_END)
        new_content = content.rstrip() + "\n\n" + "\n".join(block_lines) + "\n"
        _HOSTS.write_text(new_content, encoding="utf-8")
        return True
    except PermissionError:
        # Try via elevated PowerShell
        block_text = "\\n".join([_MARKER_START] +
                                 [f"0.0.0.0 {d}" for d in AD_DOMAINS] +
                                 [_MARKER_END])
        r = subprocess.run(
            ["powershell", "-Command",
             f'Add-Content -Path "{_HOSTS}" -Value "{block_text}"'],
            capture_output=True, creationflags=0x08000000)
        return r.returncode == 0
    except OSError:
        return False


def disable_ad_blocking() -> bool:
    try:
        content = _HOSTS.read_text(encoding="utf-8", errors="replace")
        if _MARKER_START not in content:
            return True
        lines = content.splitlines(keepends=True)
        out = []
        inside = False
        for line in lines:
            if _MARKER_START in line:
                inside = True
                continue
            if _MARKER_END in line:
                inside = False
                continue
            if not inside:
                out.append(line)
        _HOSTS.write_text("".join(out), encoding="utf-8")
        return True
    except OSError:
        return False
