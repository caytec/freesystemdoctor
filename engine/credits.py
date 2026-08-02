"""
credits.py — in-app credit economy (an alternative to the Pro subscription).

Model (decided with the product owner):
  • Pro subscription ($9.99/yr) stays the primary offer and unlocks EVERYTHING.
  • Credits are an *additional*, subscription-free path: spend credits to unlock
    an individual Pro tool permanently.

Earning credits:
  • Daily / streak bonus for regular use — works offline, no third party.
  • Rewarded ads — plumbing is ready but only pays out when a real ad was
    actually served by a configured provider. If no provider is configured we
    say so instead of granting fake credits (see reward_available()).
  • Credit packs bought via Stripe (one-time payment).

Storage is ``~/.fsd/credits.json`` — deliberately NOT under %TEMP%, because the
app's own Turbo Clean wipes temp and would otherwise erase the user's balance.
Writes are atomic (.tmp + os.replace) and guarded by a lock.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(os.path.expanduser("~")) / ".fsd"
_CREDITS_FILE = _CONFIG_DIR / "credits.json"

_VERSION = 1
_lock = threading.RLock()
_cache: dict[str, Any] | None = None

# ── economy tuning ───────────────────────────────────────────────────────────
# Credit cost to permanently unlock one Pro tool.
UNLOCK_COST = 20

# Free earning
DAILY_BONUS = 5          # credits for opening the app on a new day
STREAK_BONUS = 5         # extra when the streak keeps going (capped)
STREAK_BONUS_MAX = 15
AD_REWARD = 5            # credits per rewarded ad actually watched
AD_DAILY_CAP = 4         # max rewarded ads per day

# Credit packs sold via Stripe (one-time payment). Price in USD cents.
PACKS: list[dict] = [
    {"id": "small",  "credits": 100, "price_cents": 299,  "label": "100 credits"},
    {"id": "medium", "credits": 250, "price_cents": 599,  "label": "250 credits"},
    {"id": "large",  "credits": 600, "price_cents": 1199, "label": "600 credits"},
]

# Tools that can be unlocked with credits (mirrors license_manager.HARD_LOCKED).
UNLOCKABLE: dict[str, str] = {
    "ai_agent":      "AI Agent",
    "system_backup": "System Backup",
    "deep_clean":    "Deep Clean",
    "disk_analyzer": "Disk Analyzer",
}


# ── storage ──────────────────────────────────────────────────────────────────

def _defaults() -> dict[str, Any]:
    return {
        "version": _VERSION,
        "balance": 0,
        "unlocked": [],          # feature_ids permanently unlocked with credits
        "ledger": [],            # recent transactions (capped)
        "last_daily": "",        # ISO date of last daily bonus
        "streak": 0,
        "ads_today": 0,
        "ads_date": "",
    }


def _load() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    data = _defaults()
    try:
        if _CREDITS_FILE.exists():
            raw = json.loads(_CREDITS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data.update({k: v for k, v in raw.items() if k in data})
    except Exception:
        pass   # corrupt/missing → clean defaults, never raise
    _cache = data
    return _cache


def _save() -> bool:
    with _lock:
        data = _load()
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = _CREDITS_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(tmp, _CREDITS_FILE)
            return True
        except Exception:
            return False


def _log(kind: str, amount: int, reason: str):
    data = _load()
    data.setdefault("ledger", []).append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "kind": kind, "amount": amount, "reason": reason,
        "balance": data.get("balance", 0),
    })
    data["ledger"] = data["ledger"][-100:]


# ── balance ──────────────────────────────────────────────────────────────────

def balance() -> int:
    with _lock:
        return int(_load().get("balance", 0))


def earn(amount: int, reason: str = "") -> int:
    """Add credits. Returns the new balance."""
    amount = max(0, int(amount))
    with _lock:
        data = _load()
        data["balance"] = int(data.get("balance", 0)) + amount
        _log("earn", amount, reason)
        _save()
        return data["balance"]


def spend(amount: int, reason: str = "") -> bool:
    """Deduct credits if affordable. Returns True on success."""
    amount = max(0, int(amount))
    with _lock:
        data = _load()
        if int(data.get("balance", 0)) < amount:
            return False
        data["balance"] = int(data["balance"]) - amount
        _log("spend", -amount, reason)
        _save()
        return True


def ledger(n: int = 20) -> list[dict]:
    with _lock:
        return list(_load().get("ledger", []))[-n:][::-1]


# ── unlocks ──────────────────────────────────────────────────────────────────

def _is_pro() -> bool:
    try:
        from engine import license_manager as lm
        return lm.is_pro()
    except Exception:
        return False


def is_unlocked(feature_id: str) -> bool:
    """True if the user may use *feature_id* (Pro covers everything)."""
    if _is_pro():
        return True
    with _lock:
        return feature_id in _load().get("unlocked", [])


def unlock_cost(feature_id: str) -> int:
    return UNLOCK_COST


def unlock_feature(feature_id: str) -> tuple[bool, str]:
    """Spend credits to permanently unlock one tool."""
    if feature_id not in UNLOCKABLE:
        return False, "This tool cannot be unlocked with credits."
    if is_unlocked(feature_id):
        return True, "Already unlocked."
    cost = unlock_cost(feature_id)
    if balance() < cost:
        return False, (f"You need {cost} credits ({balance()} available). "
                       f"Earn credits free or top up.")
    if not spend(cost, f"unlock:{feature_id}"):
        return False, "Could not deduct credits."
    with _lock:
        data = _load()
        data.setdefault("unlocked", []).append(feature_id)
        _save()
    return True, f"{UNLOCKABLE[feature_id]} unlocked permanently."


def unlocked_features() -> list[str]:
    with _lock:
        return list(_load().get("unlocked", []))


# ── free earning: daily / streak bonus ───────────────────────────────────────

def daily_bonus_available() -> bool:
    with _lock:
        return _load().get("last_daily", "") != date.today().isoformat()


def claim_daily_bonus() -> tuple[bool, int, str]:
    """Claim the once-per-day bonus. Returns (ok, credits_granted, message)."""
    today = date.today().isoformat()
    with _lock:
        data = _load()
        if data.get("last_daily", "") == today:
            return False, 0, "Daily bonus already claimed — come back tomorrow."
        # streak: consecutive days
        try:
            last = date.fromisoformat(data.get("last_daily", ""))
            consecutive = (date.today() - last).days == 1
        except Exception:
            consecutive = False
        data["streak"] = (int(data.get("streak", 0)) + 1) if consecutive else 1
        data["last_daily"] = today
        bonus = DAILY_BONUS + min(STREAK_BONUS * (data["streak"] - 1),
                                  STREAK_BONUS_MAX)
        _save()
    earn(bonus, f"daily bonus (streak {streak()})")
    return True, bonus, f"+{bonus} credits — day {streak()} streak!"


def streak() -> int:
    with _lock:
        return int(_load().get("streak", 0))


# ── free earning: rewarded ads (requires a configured provider) ──────────────

def reward_available() -> tuple[bool, str]:
    """Can we serve a rewarded ad right now?

    HONESTY: we never grant credits for an ad that was not actually served.
    Windows desktop has no mainstream rewarded-video network (AdMob/Unity/
    ironSource are mobile SDKs), so this returns False until an ad provider is
    configured and reachable — the UI then explains that instead of paying out.
    """
    try:
        from engine import ad_network
        if not ad_network.is_enabled():
            return False, "Enable partner recommendations in Settings → Monetization first."
    except Exception:
        return False, "Ad module unavailable."
    if ads_left_today() <= 0:
        return False, f"Daily limit reached ({AD_DAILY_CAP} ads). Come back tomorrow."
    try:
        from engine import ad_network
        if ad_network.fetch_ad("reward") is None:
            return False, "No rewarded ad available right now."
    except Exception:
        return False, "No rewarded ad available right now."
    return True, ""


def ads_left_today() -> int:
    today = date.today().isoformat()
    with _lock:
        data = _load()
        if data.get("ads_date", "") != today:
            return AD_DAILY_CAP
        return max(0, AD_DAILY_CAP - int(data.get("ads_today", 0)))


def grant_ad_reward() -> tuple[bool, int, str]:
    """Grant credits for a rewarded ad that was ACTUALLY served and watched.

    Call only after a real ad impression completed. Returns (ok, credits, msg).
    """
    ok, why = reward_available()
    if not ok:
        return False, 0, why
    today = date.today().isoformat()
    with _lock:
        data = _load()
        if data.get("ads_date", "") != today:
            data["ads_date"] = today
            data["ads_today"] = 0
        data["ads_today"] = int(data.get("ads_today", 0)) + 1
        _save()
    earn(AD_REWARD, "rewarded ad")
    return True, AD_REWARD, f"+{AD_REWARD} credits for watching an ad."


# ── purchased packs ──────────────────────────────────────────────────────────

def get_pack(pack_id: str) -> dict | None:
    return next((p for p in PACKS if p["id"] == pack_id), None)


def credit_pack_purchased(pack_id: str) -> tuple[bool, int]:
    """Apply a successfully purchased credit pack. Returns (ok, new_balance)."""
    pack = get_pack(pack_id)
    if not pack:
        return False, balance()
    return True, earn(pack["credits"], f"purchase:{pack_id}")


def reset_all() -> bool:
    """Wipe the wallet (used by tests / 'reset' in settings)."""
    global _cache
    with _lock:
        _cache = _defaults()
        return _save()
