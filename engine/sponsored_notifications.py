"""
sponsored_notifications.py — tip-of-the-day style sponsored content.

These are NOT toast popups. They surface as a small dismissible card on
the Home page when the user opens it (and only then). Hard rules:

  • Max 1 sponsored tip per 24 h, regardless of how many times the user
    opens Home.
  • Hard frequency cap also gates `sponsored=True` items so the same
    advertiser does not appear twice in a row.
  • Respects `engine.affiliate.is_enabled()` and global Settings flag.
  • No Windows toast / no balloon notification / no system tray push —
    rendering is fully in-process inside the GUI.

We blend our own product news (Pro features, changelog highlights) with
sponsored entries so the surface is genuinely useful regardless of who's
paying.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from . import affiliate


CONFIG_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "FreeSystemDoctor"
STATE_FILE = CONFIG_DIR / "tips_state.json"

MIN_HOURS_BETWEEN_TIPS = 20
MIN_HOURS_BETWEEN_SPONSORED = 48


# ── content pool ────────────────────────────────────────────────────────────

EDITORIAL_TIPS: list[dict] = [
    {
        "id": "ed-1",
        "icon": "💡",
        "title": "Wskazówka",
        "body": "Włącz auto-skan tygodniowy w Ustawieniach — FSD posprząta C:\\ "
                "bez Twojej interwencji.",
        "cta": None, "url": None, "sponsored": False,
    },
    {
        "id": "ed-2",
        "icon": "🚀",
        "title": "Czy wiesz, że…",
        "body": "Tryb TURBO zamyka zbędne usługi Windows i potrafi dodać 2–4 FPS w grach.",
        "cta": "Włącz TURBO", "url": "#turbo", "sponsored": False,
    },
    {
        "id": "ed-3",
        "icon": "🔒",
        "title": "Prywatność",
        "body": "Cotygodniowy Browser Auto-Clean wymazuje historię, ciasteczka i cache "
                "Chrome/Edge/Firefox/Brave automatycznie.",
        "cta": "Skonfiguruj", "url": "#browser_autoclean", "sponsored": False,
    },
    {
        "id": "ed-pro-1",
        "icon": "💎",
        "title": "FSD Pro",
        "body": "Cloud sync ustawień między 3 PC, harmonogram tygodniowy bez pytania, "
                "branded raporty PDF — od 99 zł/rok.",
        "cta": "Zobacz Pro", "url": "https://caytec.github.io/freesystemdoctor-pro",
        "sponsored": False,
    },
    {
        "id": "ed-pro-2",
        "icon": "🎮",
        "title": "Gamer?",
        "body": "FSD Pro zna 50+ tytułów (CS2, Valorant, ABI, EFT) i tworzy per-game "
                "profile boost automatycznie.",
        "cta": "Pro dla graczy", "url": "https://caytec.github.io/freesystemdoctor-pro",
        "sponsored": False,
    },
]


# ── state ────────────────────────────────────────────────────────────────────

def _load() -> dict:
    if not STATE_FILE.exists():
        return {"shown": {}, "last_tip_at": None, "last_sponsored_at": None,
                "dismissed_ids": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"shown": {}, "last_tip_at": None, "last_sponsored_at": None,
                "dismissed_ids": []}


def _save(state: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def _hours_since(iso: Optional[str]) -> float:
    if not iso:
        return 9999.0
    try:
        then = datetime.fromisoformat(iso)
        return (datetime.now() - then).total_seconds() / 3600
    except ValueError:
        return 9999.0


# ── sponsored entries built from affiliate registry ─────────────────────────

def _build_sponsored_pool() -> list[dict]:
    if not affiliate.is_enabled():
        return []
    pool: list[dict] = []
    for offer in affiliate.OFFERS:
        if offer["category"] in affiliate.disabled_categories():
            continue
        pool.append({
            "id": f"spn-{offer['id']}",
            "icon": "✦",
            "title": f"Polecane: {offer['title']}",
            "body": offer["tagline"],
            "cta": offer["cta"],
            "url": offer["url"],
            "sponsored": True,
            "offer_id": offer["id"],
            "category": offer["category"],
        })
    return pool


# ── public API ───────────────────────────────────────────────────────────────

def get_tip_of_the_day() -> Optional[dict]:
    """Return one tip card (sponsored or editorial), or None if too soon."""
    state = _load()

    # Global frequency cap
    if _hours_since(state.get("last_tip_at")) < MIN_HOURS_BETWEEN_TIPS:
        # Re-show today's tip if we still remember it
        last_id = state.get("last_id")
        if last_id and last_id not in state.get("dismissed_ids", []):
            for tip in EDITORIAL_TIPS + _build_sponsored_pool():
                if tip["id"] == last_id:
                    return tip
        return None

    dismissed = set(state.get("dismissed_ids", []))
    editorial = [t for t in EDITORIAL_TIPS if t["id"] not in dismissed]

    sponsored = []
    if _hours_since(state.get("last_sponsored_at")) >= MIN_HOURS_BETWEEN_SPONSORED:
        sponsored = [t for t in _build_sponsored_pool() if t["id"] not in dismissed]

    # 60% editorial, 40% sponsored when both available
    pool: list[dict]
    if sponsored and editorial and random.random() < 0.4:
        pool = sponsored
    else:
        pool = editorial or sponsored
    if not pool:
        return None

    tip = random.choice(pool)
    state["last_tip_at"] = datetime.now().isoformat()
    state["last_id"] = tip["id"]
    if tip.get("sponsored"):
        state["last_sponsored_at"] = datetime.now().isoformat()
    _save(state)
    return tip


def dismiss(tip_id: str) -> None:
    state = _load()
    dismissed = set(state.get("dismissed_ids", []))
    dismissed.add(tip_id)
    state["dismissed_ids"] = sorted(dismissed)
    _save(state)


def reset() -> None:
    """For QA / 'Resetuj wskazówki' button in Settings."""
    if STATE_FILE.exists():
        try:
            STATE_FILE.unlink()
        except OSError:
            pass
