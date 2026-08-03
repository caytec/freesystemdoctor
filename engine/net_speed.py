"""
net_speed.py — real internet speed test + Wi-Fi signal analyser.

Closes two gaps found in the competitive review:
  • we had no throughput test at all,
  • the existing "DNS benchmark" actually measured TCP reachability, not speed.

Everything here is a genuine measurement — download throughput is timed over
real bytes received, latency comes from real round-trips. Nothing is simulated.
"""

from __future__ import annotations

import re
import statistics
import subprocess
import time
import urllib.request
from typing import Callable, Optional

_NO_WINDOW = 0x08000000
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FreeSystemDoctor/2.2"}

# Public endpoints intended for throughput measurement, tried in order.
_DOWNLOAD_ENDPOINTS = (
    "https://speed.cloudflare.com/__down?bytes={bytes}",
    "https://proof.ovh.net/files/10Mb.dat",
)

ProgressCB = Optional[Callable[[str, int], None]]


def _emit(cb: ProgressCB, msg: str, pct: int):
    if cb:
        try:
            cb(msg, pct)
        except Exception:
            pass


# ── download throughput ──────────────────────────────────────────────────────

def measure_download(target_bytes: int = 15_000_000,
                     timeout: int = 40,
                     progress_cb: ProgressCB = None) -> dict:
    """Measure real download throughput.

    Returns {ok, mbps, mb, seconds, endpoint, error}.
    """
    last_err = ""
    for template in _DOWNLOAD_ENDPOINTS:
        url = template.format(bytes=target_bytes)
        try:
            _emit(progress_cb, "Connecting…", 5)
            req = urllib.request.Request(url, headers=_UA)
            received = 0
            start = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    received += len(chunk)
                    elapsed = time.time() - start
                    if elapsed > timeout:
                        break
                    if target_bytes:
                        _emit(progress_cb, "Downloading…",
                              min(95, int(received / target_bytes * 90) + 5))
            seconds = max(0.001, time.time() - start)
            if received < 100_000:          # too little to be meaningful
                last_err = "Not enough data received"
                continue
            _emit(progress_cb, "Done", 100)
            return {
                "ok": True,
                "mbps": round(received * 8 / seconds / 1_000_000, 1),
                "mb": round(received / 1_000_000, 1),
                "seconds": round(seconds, 2),
                "endpoint": url.split("/")[2],
                "error": "",
            }
        except Exception as exc:
            last_err = str(exc)
            continue
    return {"ok": False, "mbps": 0, "mb": 0, "seconds": 0,
            "endpoint": "", "error": last_err or "All endpoints failed"}


# ── latency / jitter ─────────────────────────────────────────────────────────

def measure_latency(host: str = "1.1.1.1", count: int = 6) -> dict:
    """Ping a host; return {ok, avg_ms, min_ms, max_ms, jitter_ms, loss_pct}."""
    try:
        r = subprocess.run(["ping", "-n", str(count), host],
                           capture_output=True, text=True, timeout=30,
                           creationflags=_NO_WINDOW)
        times = [float(m) for m in re.findall(r"[=<](\d+)ms", r.stdout or "")]
        sent = count
        received = len(times)
        if not times:
            return {"ok": False, "avg_ms": 0, "min_ms": 0, "max_ms": 0,
                    "jitter_ms": 0, "loss_pct": 100}
        return {
            "ok": True,
            "avg_ms": round(statistics.mean(times), 1),
            "min_ms": round(min(times), 1),
            "max_ms": round(max(times), 1),
            "jitter_ms": round(statistics.pstdev(times), 1) if received > 1 else 0.0,
            "loss_pct": round(max(0, (sent - received)) / sent * 100),
        }
    except Exception:
        return {"ok": False, "avg_ms": 0, "min_ms": 0, "max_ms": 0,
                "jitter_ms": 0, "loss_pct": 100}


# ── Wi-Fi analyser ───────────────────────────────────────────────────────────

def get_wifi_info() -> dict:
    """Current Wi-Fi connection details.

    Returns {connected, ssid, signal_pct, channel, radio, band, rx_mbps,
             tx_mbps, quality}. connected=False when on Ethernet / no adapter.
    """
    info = {"connected": False, "ssid": "", "signal_pct": 0, "channel": 0,
            "radio": "", "band": "", "rx_mbps": 0, "tx_mbps": 0, "quality": ""}
    try:
        r = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                           capture_output=True, text=True, timeout=15,
                           creationflags=_NO_WINDOW)
        out = r.stdout or ""
    except Exception:
        return info

    def grab(pattern: str) -> str:
        # MULTILINE matters: netsh prints one "Key : Value" per line, and the
        # SSID pattern must anchor per-line so it doesn't collide with BSSID.
        m = re.search(pattern + r"\s*:\s*(.+)", out,
                      re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else ""

    ssid = grab(r"^\s*SSID")
    if not ssid or "not connected" in out.lower():
        return info

    info["connected"] = True
    info["ssid"] = ssid
    sig = grab(r"Signal")
    try:
        info["signal_pct"] = int(sig.replace("%", "").strip())
    except ValueError:
        pass
    try:
        info["channel"] = int(grab(r"Channel") or 0)
    except ValueError:
        pass
    info["radio"] = grab(r"Radio type")
    for key, field in ((r"Receive rate \(Mbps\)", "rx_mbps"),
                       (r"Transmit rate \(Mbps\)", "tx_mbps")):
        try:
            info[field] = float(grab(key) or 0)
        except ValueError:
            pass

    ch = info["channel"]
    info["band"] = "5 GHz" if ch >= 32 else ("2.4 GHz" if ch else "")

    pct = info["signal_pct"]
    info["quality"] = ("Excellent" if pct >= 80 else "Good" if pct >= 60
                       else "Fair" if pct >= 40 else "Weak")
    return info


def get_wifi_recommendations(info: dict) -> list[str]:
    """Plain-language advice based on the current Wi-Fi state."""
    tips: list[str] = []
    if not info.get("connected"):
        return ["Not connected to Wi-Fi (wired connections are usually faster)."]
    pct = info.get("signal_pct", 0)
    if pct < 60:
        tips.append("Weak signal — move closer to the router or reduce obstacles.")
    if info.get("band") == "2.4 GHz":
        tips.append("You're on 2.4 GHz. The 5 GHz band is usually much faster "
                    "if your router offers it.")
    ch = info.get("channel", 0)
    if info.get("band") == "2.4 GHz" and ch not in (1, 6, 11) and ch:
        tips.append(f"Channel {ch} overlaps neighbours — channels 1, 6 or 11 "
                    f"are cleaner on 2.4 GHz.")
    radio = (info.get("radio") or "").lower()
    if "802.11n" in radio or "802.11g" in radio:
        tips.append("Your link uses an older Wi-Fi standard — a Wi-Fi 5/6 "
                    "router would be noticeably faster.")
    if not tips:
        tips.append("Wi-Fi looks healthy.")
    return tips
