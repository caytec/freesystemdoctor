"""
affiliate.py — native sponsored recommendations (Option D registry).

DESIGN RULES (anti-PUP / non-intrusive):
  1. ZERO outbound HTTP unless the user explicitly clicks a CTA.
  2. ZERO third-party tracking pixels, ZERO JS, ZERO iframes.
  3. ZERO bundled installers — every offer opens the partner's own site
     in the user's default browser.
  4. Global opt-out persists in %APPDATA%\\FreeSystemDoctor\\affiliate.json
     and is honoured by every selection call.
  5. Frequency cap: at most one impression per offer per N minutes per
     page, so no page is "spammy" even when enabled.
  6. Hand-picked partners only (browsers, VPNs, AV, productivity, cloud).
     No download-managers, no "registry cleaners", no toolbars, no PUP.

The local click/impression counters exist purely so the developer can
read `get_local_stats()` from the GUI. They are NEVER transmitted.
"""

from __future__ import annotations

import os
import json
import random
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta


CONFIG_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "FreeSystemDoctor"
CONFIG_FILE = CONFIG_DIR / "affiliate.json"

# Minimum minutes between two impressions of the same offer on the same page.
IMPRESSION_COOLDOWN_MIN = 45

# Categories the user can disable independently (granular opt-out).
CATEGORIES = [
    "Browser", "VPN", "Antywirus", "Adblocker", "Cloud Storage",
    "Password Manager", "Productivity", "Streaming", "Backup",
    "Email", "Hosting",
]


# ── offer registry (18 offers, hand-picked, all AV-clean) ────────────────────

OFFERS: list[dict] = [
    # ── Browsers ────────────────────────────────────────────────────────────
    {
        "id": "brave", "category": "Browser",
        "page_keys": ["software", "speedup", "privacy", "deep_clean", "home"],
        "title": "Brave Browser",
        "tagline": "3x szybsze ładowanie, blokuje reklamy i trackery natywnie",
        "cta": "Wypróbuj Brave",
        "url": "https://brave.com/freesystemdoctor",
        "commission": "$5 per install (Tier 1)",
        "weight": 30,
    },
    # ── VPNs ────────────────────────────────────────────────────────────────
    {
        "id": "protonvpn", "category": "VPN",
        "page_keys": ["internet", "privacy", "network_security", "dns_protector"],
        "title": "ProtonVPN",
        "tagline": "Szwajcarski VPN no-logs, darmowa wersja na zawsze",
        "cta": "Pobierz ProtonVPN",
        "url": "https://protonvpn.com/freesystemdoctor",
        "commission": "100% first month, 30% recurring",
        "weight": 25,
    },
    {
        "id": "nordvpn", "category": "VPN",
        "page_keys": ["internet", "privacy", "network_security", "dns_protector"],
        "title": "NordVPN",
        "tagline": "5500+ serwerów w 60 krajach, 6 urządzeń jednocześnie",
        "cta": "Spróbuj NordVPN",
        "url": "https://go.nordvpn.net/aff_c?offer_id=15&aff_id=freesystemdoctor",
        "commission": "100% first month (~$45)",
        "weight": 25,
    },
    {
        "id": "surfshark", "category": "VPN",
        "page_keys": ["internet", "privacy", "network_security"],
        "title": "Surfshark VPN",
        "tagline": "Nielimitowane urządzenia, CleanWeb adblocker w cenie",
        "cta": "Sprawdź Surfshark",
        "url": "https://get.surfshark.net/aff_c?offer_id=926&aff_id=freesystemdoctor",
        "commission": "40% per sale",
        "weight": 18,
    },
    # ── Antywirus ────────────────────────────────────────────────────────────
    {
        "id": "bitdefender", "category": "Antywirus",
        "page_keys": ["protect", "security", "deep_clean", "home"],
        "title": "Bitdefender Total Security",
        "tagline": "Najlepszy AV 2026 wg AV-TEST, 0% wpływu na wydajność",
        "cta": "Spróbuj 30 dni",
        "url": "https://www.bitdefender.com/freesystemdoctor",
        "commission": "30% per sale (~$30)",
        "weight": 22,
    },
    {
        "id": "malwarebytes", "category": "Antywirus",
        "page_keys": ["protect", "security", "deep_clean", "browser_protection"],
        "title": "Malwarebytes Premium",
        "tagline": "Anty-malware #1, działa obok Defendera bez konfliktów",
        "cta": "Skanuj za darmo",
        "url": "https://www.malwarebytes.com/affiliate/freesystemdoctor",
        "commission": "30% per sale (~$12)",
        "weight": 18,
    },
    {
        "id": "eset", "category": "Antywirus",
        "page_keys": ["protect", "security"],
        "title": "ESET HOME Security",
        "tagline": "Polski wybór #1 — lekki silnik, bankowość chroniona",
        "cta": "Pobierz ESET",
        "url": "https://www.eset.com/pl/freesystemdoctor",
        "commission": "20% per sale",
        "weight": 12,
    },
    # ── Adblocker ────────────────────────────────────────────────────────────
    {
        "id": "adguard", "category": "Adblocker",
        "page_keys": ["software", "privacy", "internet", "deep_clean", "browser_autoclean"],
        "title": "AdGuard",
        "tagline": "Blokuje reklamy systemowo — wszystkie aplikacje i przeglądarki",
        "cta": "Sprawdź AdGuard",
        "url": "https://adguard.com/freesystemdoctor",
        "commission": "30-40% per sale (~$15)",
        "weight": 15,
    },
    # ── Cloud storage ────────────────────────────────────────────────────────
    {
        "id": "pcloud", "category": "Cloud Storage",
        "page_keys": ["cloud_cleaner", "speedup", "settings", "system_backup"],
        "title": "pCloud Lifetime 500 GB",
        "tagline": "199 USD raz na zawsze — alternatywa dla subskrypcji Dropbox",
        "cta": "Zobacz pCloud",
        "url": "https://www.pcloud.com/freesystemdoctor",
        "commission": "20% per sale (~$40)",
        "weight": 12,
    },
    {
        "id": "internxt", "category": "Cloud Storage",
        "page_keys": ["cloud_cleaner", "privacy", "system_backup"],
        "title": "Internxt Drive",
        "tagline": "Post-quantum encrypted cloud z UE, 10 GB darmowe",
        "cta": "Załóż konto",
        "url": "https://internxt.com/freesystemdoctor",
        "commission": "30% per sale (~$20)",
        "weight": 8,
    },
    {
        "id": "backblaze", "category": "Backup",
        "page_keys": ["system_backup", "deep_clean", "drive_wipe"],
        "title": "Backblaze Personal Backup",
        "tagline": "Unlimited backup za $9/mc — set-and-forget",
        "cta": "15 dni za darmo",
        "url": "https://www.backblaze.com/freesystemdoctor",
        "commission": "$10 per signup",
        "weight": 10,
    },
    # ── Password managers ───────────────────────────────────────────────────
    {
        "id": "bitwarden", "category": "Password Manager",
        "page_keys": ["security", "privacy", "browser_autoclean", "browser_protection"],
        "title": "Bitwarden",
        "tagline": "Open-source menedżer haseł, darmowy plan w pełni funkcjonalny",
        "cta": "Pobierz Bitwarden",
        "url": "https://bitwarden.com/freesystemdoctor",
        "commission": "20% per Premium signup",
        "weight": 10,
    },
    {
        "id": "1password", "category": "Password Manager",
        "page_keys": ["security", "privacy", "settings"],
        "title": "1Password",
        "tagline": "Najlepszy UX wśród password managerów, Watchtower alerts",
        "cta": "14 dni za darmo",
        "url": "https://1password.com/freesystemdoctor",
        "commission": "30% first year",
        "weight": 9,
    },
    {
        "id": "nordpass", "category": "Password Manager",
        "page_keys": ["security", "browser_protection"],
        "title": "NordPass",
        "tagline": "Od twórców NordVPN, XChaCha20 encryption, data breach scanner",
        "cta": "Spróbuj NordPass",
        "url": "https://nordpass.com/aff/freesystemdoctor",
        "commission": "40% per sale",
        "weight": 8,
    },
    # ── Productivity ────────────────────────────────────────────────────────
    {
        "id": "notion", "category": "Productivity",
        "page_keys": ["home", "settings", "ai_agent"],
        "title": "Notion",
        "tagline": "All-in-one workspace: notatki, projekty, bazy danych, AI",
        "cta": "Zacznij za darmo",
        "url": "https://affiliate.notion.so/freesystemdoctor",
        "commission": "50% first year of Plus plan",
        "weight": 8,
    },
    {
        "id": "office365", "category": "Productivity",
        "page_keys": ["software", "home", "settings"],
        "title": "Microsoft 365 Personal",
        "tagline": "Word, Excel, Outlook + 1 TB OneDrive — 299 zł/rok",
        "cta": "Zobacz ofertę",
        "url": "https://www.microsoft.com/microsoft-365/freesystemdoctor",
        "commission": "5-10% per sale",
        "weight": 7,
    },
    # ── Streaming ────────────────────────────────────────────────────────────
    {
        "id": "spotify", "category": "Streaming",
        "page_keys": ["home", "speedup", "game"],
        "title": "Spotify Premium",
        "tagline": "3 miesiące za darmo dla nowych użytkowników",
        "cta": "Aktywuj promo",
        "url": "https://www.spotify.com/freesystemdoctor",
        "commission": "$5 per signup",
        "weight": 6,
    },
    # ── Email / hosting ─────────────────────────────────────────────────────
    {
        "id": "protonmail", "category": "Email",
        "page_keys": ["privacy", "email_security", "security"],
        "title": "Proton Mail",
        "tagline": "Szwajcarski zaszyfrowany e-mail, alternatywa dla Gmaila",
        "cta": "Załóż Proton Mail",
        "url": "https://proton.me/mail/freesystemdoctor",
        "commission": "Up to $30 per signup",
        "weight": 10,
    },
]


# ── state ────────────────────────────────────────────────────────────────────

def _default_state() -> dict:
    return {
        "disabled": False,
        "disabled_categories": [],
        "clicks": {},
        "impressions": {},
        "last_seen": {},
        "click_log": [],
    }


def _load() -> dict:
    if not CONFIG_FILE.exists():
        return _default_state()
    try:
        state = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        for k, v in _default_state().items():
            state.setdefault(k, v)
        return state
    except Exception:
        return _default_state()


def _save(state: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        # Never crash the app over an affiliate write
        pass


def is_enabled() -> bool:
    return not _load().get("disabled", False)


def set_enabled(enabled: bool) -> None:
    state = _load()
    state["disabled"] = not enabled
    _save(state)


def disabled_categories() -> list[str]:
    return _load().get("disabled_categories", [])


def set_category_enabled(category: str, enabled: bool) -> None:
    state = _load()
    disabled = set(state.get("disabled_categories", []))
    if enabled:
        disabled.discard(category)
    else:
        disabled.add(category)
    state["disabled_categories"] = sorted(disabled)
    _save(state)


# ── selection ────────────────────────────────────────────────────────────────

def _eligible(offer: dict, page_key: str, state: dict) -> bool:
    if offer["category"] in state.get("disabled_categories", []):
        return False
    if page_key not in offer["page_keys"]:
        return False
    last = state.get("last_seen", {}).get(offer["id"])
    if last:
        try:
            then = datetime.fromisoformat(last)
            if datetime.now() - then < timedelta(minutes=IMPRESSION_COOLDOWN_MIN):
                return False
        except ValueError:
            pass
    return True


def pick_offer_for_page(page_key: str) -> dict | None:
    """Pick a random offer eligible for this page (weighted, with cooldown).
    Returns None if monetization is globally off, or no offer is eligible."""
    state = _load()
    if state.get("disabled", False):
        return None

    candidates = [o for o in OFFERS if _eligible(o, page_key, state)]
    if not candidates:
        # fall back to any not-on-cooldown, ignoring page key — but still
        # honour disabled categories
        candidates = [
            o for o in OFFERS
            if o["category"] not in state.get("disabled_categories", [])
            and _eligible({**o, "page_keys": [page_key]}, page_key, state)
        ]
    if not candidates:
        return None

    weights = [o.get("weight", 10) for o in candidates]
    choice = random.choices(candidates, weights=weights, k=1)[0]

    state.setdefault("impressions", {})
    state["impressions"][choice["id"]] = state["impressions"].get(choice["id"], 0) + 1
    state.setdefault("last_seen", {})[choice["id"]] = datetime.now().isoformat()
    _save(state)
    return choice


def get_offer_by_id(offer_id: str) -> dict | None:
    for o in OFFERS:
        if o["id"] == offer_id:
            return o
    return None


def offers_for_category(category: str) -> list[dict]:
    return [o for o in OFFERS if o["category"] == category]


# ── click tracking (local only — never sent anywhere) ────────────────────────

def record_click(offer_id: str) -> bool:
    offer = get_offer_by_id(offer_id)
    if not offer:
        return False
    state = _load()
    state.setdefault("clicks", {})
    state["clicks"][offer_id] = state["clicks"].get(offer_id, 0) + 1
    state.setdefault("click_log", []).append({
        "offer_id": offer_id,
        "ts": datetime.now().isoformat(),
    })
    # Keep last 200 clicks max
    state["click_log"] = state["click_log"][-200:]
    _save(state)

    try:
        webbrowser.open(offer["url"])
    except Exception:
        pass
    return True


def get_local_stats() -> dict:
    state = _load()
    impressions = state.get("impressions", {})
    clicks = state.get("clicks", {})
    return {
        "enabled": not state.get("disabled", False),
        "disabled_categories": state.get("disabled_categories", []),
        "impressions": impressions,
        "clicks": clicks,
        "total_impressions": sum(impressions.values()),
        "total_clicks": sum(clicks.values()),
        "ctr_per_offer": {
            oid: round(clicks.get(oid, 0) / max(impressions.get(oid, 1), 1) * 100, 2)
            for oid in {**impressions, **clicks}
        },
    }
