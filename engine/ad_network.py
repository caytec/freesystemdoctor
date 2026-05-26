"""
ad_network.py — opt-in native ad fetch (Carbon Ads / EthicalAds style).

ANTI-PUP GUARANTEES:
  • Network is OFF by default. The user must explicitly enable it in
    Settings → Monetization → "Wspieraj rozwój przez delikatne reklamy".
  • Fetched only when a page asks for an ad AND the user is connected.
  • Plain HTTPS JSON fetch — no JS execution, no cookies, no iframes,
    no impression pixels.
  • Hard 24 h disk cache so the same network call isn't repeated within
    a day even across restarts.
  • No request is made on app launch, on idle, or in the background.
    Only when a page is opened that wants to render an ad slot.
  • If a fetch fails or times out, we silently render nothing — no
    retries, no spinners, no error popups.

Endpoint contract (very small — we own the backend):

    GET https://ads.freesystemdoctor.pl/v1/native?slot=<key>&v=<app_ver>
    →   { "id": "...", "title": "...", "body": "...",
          "cta": "...", "url": "...", "advertiser": "...",
          "image_url": null, "expires_in": 86400 }

If the server returns 204 or { "ad": null } we render nothing.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "FreeSystemDoctor"
NETWORK_PREF_FILE = CONFIG_DIR / "ad_network.json"
CACHE_FILE = CONFIG_DIR / "ad_cache.json"

# Our own backend, no third party. (Set up later as a tiny FastAPI service
# in the Pro repo's `activation_server`.)
NETWORK_ENDPOINT = "https://ads.freesystemdoctor.pl/v1/native"
USER_AGENT = "FreeSystemDoctor/1.0 (+https://freesystemdoctor.pl)"
TIMEOUT_SECONDS = 3.0
CACHE_TTL_SECONDS = 24 * 60 * 60


# ── enable/disable persistence ───────────────────────────────────────────────

def _read_pref() -> dict:
    if not NETWORK_PREF_FILE.exists():
        return {"enabled": False, "asked": False}
    try:
        return json.loads(NETWORK_PREF_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"enabled": False, "asked": False}


def _write_pref(pref: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        NETWORK_PREF_FILE.write_text(json.dumps(pref, indent=2), encoding="utf-8")
    except Exception:
        pass


def is_enabled() -> bool:
    return _read_pref().get("enabled", False)


def set_enabled(enabled: bool) -> None:
    pref = _read_pref()
    pref["enabled"] = bool(enabled)
    pref["asked"] = True
    _write_pref(pref)


def was_user_asked() -> bool:
    return _read_pref().get("asked", False)


# ── cache ────────────────────────────────────────────────────────────────────

def _read_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_cache(cache: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── fetch ────────────────────────────────────────────────────────────────────

def _check_internet() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=1.5).close()
        return True
    except OSError:
        return False


def fetch_ad(slot: str, app_version: str = "1.0") -> Optional[dict]:
    """Fetch a native ad for a slot, or return None to render nothing.

    Caller must already know they want to show an ad — this is not gated
    by any timer or background task. The cache + opt-in flag are the
    only mechanisms protecting the user from chatty network behaviour.
    """
    if not is_enabled():
        return None

    cache = _read_cache()
    entry = cache.get(slot)
    now = time.time()
    if entry and entry.get("expires", 0) > now:
        return entry.get("ad")

    if not _check_internet():
        return None

    url = f"{NETWORK_ENDPOINT}?slot={slot}&v={app_version}"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })

    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS, context=ctx) as r:
            if r.status == 204:
                ad = None
            else:
                payload = json.loads(r.read().decode("utf-8"))
                ad = payload if payload and payload.get("title") else None
    except (urllib.error.URLError, TimeoutError, socket.timeout,
            ValueError, ConnectionError):
        return None

    cache[slot] = {
        "ad": ad,
        "expires": now + CACHE_TTL_SECONDS,
    }
    _write_cache(cache)
    return ad


def clear_cache() -> None:
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
    except OSError:
        pass
