"""
email_capture.py — explicit opt-in newsletter (drip via Resend later).

CONSENT REQUIREMENTS:
  • The user must check an explicit checkbox AND click submit.
  • We store: email, locale, consent timestamp, app version.
  • We DO NOT phone home until the user submits.
  • The endpoint is our own (newsletter.freesystemdoctor.pl) and only
    receives `{ email, locale, source }` — no machine ID, no hostname.

If the network is offline at submit-time we queue locally and retry on
the next manual "Ulepsz" click. There's no background submission loop.
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
STATE_FILE = CONFIG_DIR / "newsletter.json"

ENDPOINT = "https://newsletter.freesystemdoctor.pl/v1/subscribe"
USER_AGENT = "FreeSystemDoctor/1.0 (+https://freesystemdoctor.pl)"
TIMEOUT_SECONDS = 4.0


# ── persistence ──────────────────────────────────────────────────────────────

def _load() -> dict:
    if not STATE_FILE.exists():
        return {"subscribed": False, "email": None, "consent_at": None,
                "pending": None, "dismissed": False}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"subscribed": False, "email": None, "consent_at": None,
                "pending": None, "dismissed": False}


def _save(state: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def is_subscribed() -> bool:
    return _load().get("subscribed", False)


def is_dismissed() -> bool:
    return _load().get("dismissed", False)


def dismiss_prompt() -> None:
    state = _load()
    state["dismissed"] = True
    _save(state)


# ── validation ───────────────────────────────────────────────────────────────

def _valid(email: str) -> bool:
    if not email or "@" not in email or len(email) > 320:
        return False
    local, _, domain = email.rpartition("@")
    return bool(local) and "." in domain and len(domain) >= 3


# ── submit ───────────────────────────────────────────────────────────────────

def _post(payload: dict) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=data, method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS, context=ctx) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError):
        return False


def _online() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=1.5).close()
        return True
    except OSError:
        return False


def subscribe(email: str, locale: str = "pl", source: str = "settings") -> dict:
    """Returns {'ok': bool, 'reason': str|None, 'queued': bool}."""
    email = (email or "").strip().lower()
    if not _valid(email):
        return {"ok": False, "reason": "invalid_email", "queued": False}

    payload = {
        "email": email,
        "locale": locale,
        "source": source,
        "ts": int(time.time()),
    }

    state = _load()
    state["email"] = email
    state["consent_at"] = payload["ts"]

    if not _online():
        state["pending"] = payload
        _save(state)
        return {"ok": True, "reason": None, "queued": True}

    if _post(payload):
        state["subscribed"] = True
        state["pending"] = None
        _save(state)
        return {"ok": True, "reason": None, "queued": False}

    state["pending"] = payload
    _save(state)
    return {"ok": False, "reason": "network", "queued": True}


def retry_pending() -> bool:
    state = _load()
    if state.get("subscribed"):
        return True
    pending = state.get("pending")
    if not pending:
        return False
    if not _online():
        return False
    if _post(pending):
        state["subscribed"] = True
        state["pending"] = None
        _save(state)
        return True
    return False


def unsubscribe() -> None:
    """Local-only unsubscribe (clears state). The newsletter unsubscribe
    link still controls the actual mailing list."""
    state = _load()
    state["subscribed"] = False
    state["pending"] = None
    _save(state)
