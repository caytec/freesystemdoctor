"""
FreeSystemDoctor — License Manager (client-side)
Handles CD-key validation, offline cache (30-day JWT), tier detection
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import logging
import os
import platform
import subprocess
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger("fsd.license")

# ─────────────────────────────────────────────────────────────
# Pro feature registry — hybrid FREE/PRO model
# ─────────────────────────────────────────────────────────────
# HARD_LOCKED  → Free has NO access (full-page upsell wall).
# LIMITED      → Free gets a capped/teaser version; Pro removes the cap.
#                Enforcement happens inside each page via the limit helpers below.

# Fully walled for Free — the premium value (paid APIs, ML predictor, real-time
# monitoring, incremental backup) isn't separable from a teaser, so it's
# all-or-nothing.
HARD_LOCKED: frozenset[str] = frozenset({
    "ai_agent",
    "system_backup",
    "deep_clean",
    "disk_analyzer",
})

# Free gets a usable but capped version; Pro removes the cap.
LIMITED_FEATURES: frozenset[str] = frozenset({
    "advanced_scheduler",
    "performance_profiles",
    "turbo_mode",
    "idle_maintenance",
    "autopilot",
    "health_timeline",
})

# Union — anything that is gated in any way.
PRO_FEATURES: frozenset[str] = HARD_LOCKED | LIMITED_FEATURES

# Numeric Free-tier quotas for count-based limits.
# Absent  → the limit is qualitative (banner only, e.g. "weekly schedule").
FREE_LIMITS: dict[str, int] = {
    "advanced_scheduler":   3,   # max scheduled tasks
    "performance_profiles": 3,   # usable profiles (rest are Pro)
    "autopilot":            1,   # runs per day
    "health_timeline":      7,   # days of history visible
}

# Short human-readable description of each Free limit (for inline banners).
FREE_LIMIT_LABELS: dict[str, str] = {
    "advanced_scheduler":   "Free: up to 3 scheduled tasks",
    "performance_profiles": "Free: 3 profiles (more in Pro)",
    "turbo_mode":           "Free: basic turbo — per-app profiles are Pro",
    "idle_maintenance":     "Free: weekly schedule — continuous idle care is Pro",
    "autopilot":            "Free: 1 Auto-Pilot run per day",
    "health_timeline":      "Free: last 7 days — full history is Pro",
}

# ─────────────────────────────────────────────────────────────
# LicenseManager
# ─────────────────────────────────────────────────────────────
class LicenseManager:
    # SECURITY: default is plain HTTP (the VPS has no TLS on this port). Keys are
    # HMAC-signed + device-bound so a MITM cannot forge a usable key, but set
    # FSD_LICENSE_API_URL to an https://… proxy to also encrypt the channel.
    API_URL      = os.environ.get("FSD_LICENSE_API_URL",
                                  "http://frog02.mikr.us:21187/api/v1")
    CACHE_TTL_S  = 30 * 24 * 3600          # 30 days offline grace

    def __init__(self):
        self._cache_dir  = Path(os.path.expanduser("~")) / ".fsd"
        self._cache_file = self._cache_dir / "license.json"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Optional[Dict[str, Any]] = self._load_cache()
        # Environment override for testing
        self._override = os.getenv("OVERRIDE_TIER")

    # ── Public API ──────────────────────────────────────────

    def get_tier(self) -> str:
        """Return 'free', 'pro', or 'lifetime'."""
        if self._override:
            return self._override
        if self._cache_valid():
            return self._cache.get("tier", "free")          # type: ignore[union-attr]
        return "free"

    def is_pro(self) -> bool:
        return self.get_tier() in ("pro", "lifetime")

    def is_feature_available(self, feature_id: str) -> bool:
        """True if the page may build its normal UI.

        Non-Pro features and LIMITED features always build (the limited pages
        enforce their own quotas inline). Only HARD_LOCKED features are walled
        off entirely for Free users.
        """
        if feature_id not in HARD_LOCKED:
            return True
        return self.is_pro()

    # ── graduated-limit helpers ─────────────────────────────

    def feature_mode(self, feature_id: str) -> str:
        """Return 'full', 'limited', or 'locked' for the current tier."""
        if feature_id not in PRO_FEATURES or self.is_pro():
            return "full"
        return "locked" if feature_id in HARD_LOCKED else "limited"

    def effective_limit(self, feature_id: str) -> Optional[int]:
        """Numeric cap for the current tier. None = unlimited (Pro or uncapped)."""
        if self.is_pro():
            return None
        return FREE_LIMITS.get(feature_id)

    def is_within_limit(self, feature_id: str, current_count: int) -> bool:
        """True if creating one more item is allowed at the current tier."""
        lim = self.effective_limit(feature_id)
        return lim is None or current_count < lim

    def limit_label(self, feature_id: str) -> str:
        return FREE_LIMIT_LABELS.get(feature_id, "Free tier limit")

    def get_cd_key(self) -> Optional[str]:
        return self._cache.get("cd_key") if self._cache else None

    def get_email(self) -> Optional[str]:
        return self._cache.get("email") if self._cache else None

    def get_expires(self) -> Optional[str]:
        return self._cache.get("expires_at") if self._cache else None

    def activate(self, cd_key: str) -> tuple[bool, str]:
        """
        Validate CD-key with server and cache the result.
        Returns (success, message).
        """
        cd_key = cd_key.strip().upper()
        if not cd_key.startswith("FSD-"):
            return False, "Invalid CD-key format. Must start with FSD-"
        try:
            resp = requests.post(
                f"{self.API_URL}/validate",
                json={"cd_key": cd_key, "device_id": self._device_id()},
                timeout=8,
            )
            if resp.status_code == 200:
                data = resp.json()
                self._save_cache(data)
                logger.info("License activated: %s tier=%s", cd_key[:12], data.get("tier"))
                return True, f"Pro Edition activated! Expires: {data.get('expires_at','')[:10]}"
            elif resp.status_code == 402:
                return False, "License expired or subscription cancelled."
            else:
                detail = resp.json().get("detail", "Unknown error")
                return False, f"Server rejected key: {detail}"
        except requests.exceptions.RequestException as e:
            logger.warning("Server unreachable during activate: %s", e)
            return False, "Cannot reach license server. Check your internet connection."

    def sync_background(self):
        """Non-blocking server sync — called at startup."""
        if not self._cache or not self._cache.get("cd_key"):
            return
        t = threading.Thread(target=self._sync, daemon=True)
        t.start()

    def deactivate(self):
        """Remove local license cache (deactivate)."""
        if self._cache_file.exists():
            self._cache_file.unlink()
        self._cache = None
        logger.info("License deactivated locally")

    # ── Private ─────────────────────────────────────────────

    def _sync(self):
        cd_key = self._cache.get("cd_key")   # type: ignore
        if not cd_key:
            return
        try:
            resp = requests.post(
                f"{self.API_URL}/validate",
                json={"cd_key": cd_key, "device_id": self._device_id()},
                timeout=6,
            )
            if resp.status_code == 200:
                self._save_cache(resp.json())
                logger.info("License synced from server")
            elif resp.status_code in (401, 402):
                # Key revoked — evict cache
                self.deactivate()
                logger.warning("License revoked by server")
        except Exception:
            pass   # Stay offline — cache still valid

    def _cache_valid(self) -> bool:
        if not self._cache:
            return False
        try:
            # 1. Check 30-day offline TTL
            cached_at = datetime.fromisoformat(self._cache.get("cached_at", ""))
            if (datetime.utcnow() - cached_at).total_seconds() > self.CACHE_TTL_S:
                return False
            # 2. Check license expiry
            exp = self._cache.get("expires_at", "")
            if exp and datetime.fromisoformat(exp) < datetime.utcnow():
                return False
            return True
        except Exception:
            return False

    def _load_cache(self) -> Optional[Dict]:
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _save_cache(self, data: Dict):
        payload = {
            "cd_key":     data.get("cd_key", ""),
            "tier":       data.get("tier", "free"),
            "email":      data.get("email", ""),
            "expires_at": data.get("expires_at", ""),
            "days_left":  data.get("days_left", 0),
            "cached_at":  datetime.utcnow().isoformat(),
        }
        with open(self._cache_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        self._cache = payload

    def _device_id(self) -> str:
        try:
            parts = []
            if platform.system() == "Windows":
                for cmd in [
                    "wmic cpu get processorid /value",
                    "wmic diskdrive get serialnumber /value",
                ]:
                    out = subprocess.check_output(
                        cmd, shell=True, stderr=subprocess.DEVNULL
                    ).decode(errors="ignore")
                    parts.append(out.strip())
            parts.append(str(uuid.getnode()))
            combined = "|".join(parts)
            return hashlib.sha256(combined.encode()).hexdigest()[:20]
        except Exception:
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:20]


# ─────────────────────────────────────────────────────────────
# Singleton helpers
# ─────────────────────────────────────────────────────────────
_mgr: Optional[LicenseManager] = None

def get_manager() -> LicenseManager:
    global _mgr
    if _mgr is None:
        _mgr = LicenseManager()
    return _mgr

def is_pro() -> bool:
    return get_manager().is_pro()

def is_feature_available(feature_id: str) -> bool:
    return get_manager().is_feature_available(feature_id)

def get_tier() -> str:
    return get_manager().get_tier()

def feature_mode(feature_id: str) -> str:
    return get_manager().feature_mode(feature_id)

def effective_limit(feature_id: str) -> Optional[int]:
    return get_manager().effective_limit(feature_id)

def is_within_limit(feature_id: str, current_count: int) -> bool:
    return get_manager().is_within_limit(feature_id, current_count)

def limit_label(feature_id: str) -> str:
    return get_manager().limit_label(feature_id)
