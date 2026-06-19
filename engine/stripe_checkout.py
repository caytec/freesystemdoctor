"""
FreeSystemDoctor — Stripe Checkout Helper
Opens browser checkout, polls for CD-key, then activates locally
"""

from __future__ import annotations

import os
import threading
import time
import webbrowser
import logging
import requests
from typing import Callable, Optional

logger = logging.getLogger("fsd.stripe")

# License/activation API endpoint.
# SECURITY: the default endpoint is plain HTTP because the mikr.us VPS does not
# expose TLS on this port. CD-keys are HMAC-signed and device-bound, so a
# man-in-the-middle cannot forge a usable key, but the email/key are visible in
# transit. To harden, put an HTTPS terminator in front (Cloudflare Tunnel,
# Caddy/Let's Encrypt, or the mikr.us HTTPS proxy) and set FSD_LICENSE_API_URL
# to that https://… address — no rebuild required.
API_URL = os.environ.get("FSD_LICENSE_API_URL",
                         "http://frog02.mikr.us:21187/api/v1")


class CheckoutSession:
    """Manages one Stripe checkout lifecycle."""

    POLL_INTERVAL = 3   # seconds between status checks
    POLL_TIMEOUT  = 600 # 10-minute max wait

    def __init__(self, email: str, device_id: str = "*"):
        self.email      = email
        self.device_id  = device_id
        self.session_id : Optional[str] = None
        self.cd_key     : Optional[str] = None

    def start(
        self,
        on_success: Callable[[str, str], None],   # (cd_key, email)
        on_error:   Callable[[str], None],
    ) -> bool:
        """
        Create session, open browser, poll in background.
        Returns True if browser was opened successfully.
        """
        try:
            resp = requests.post(
                f"{API_URL}/create-checkout",
                json={"email": self.email, "device_id": self.device_id},
                timeout=10,
            )
            if resp.status_code != 200:
                on_error(f"Server error {resp.status_code}: {resp.text}")
                return False

            data            = resp.json()
            self.session_id = data["session_id"]
            checkout_url    = data["checkout_url"]

            logger.info("Stripe session %s — opening browser", self.session_id)
            webbrowser.open(checkout_url)

            # Poll in background daemon thread
            threading.Thread(
                target=self._poll,
                args=(on_success, on_error),
                daemon=True,
            ).start()
            return True

        except requests.exceptions.RequestException as e:
            on_error(f"Cannot reach server: {e}")
            return False

    def _poll(self, on_success, on_error):
        start = time.monotonic()
        while time.monotonic() - start < self.POLL_TIMEOUT:
            try:
                resp = requests.get(
                    f"{API_URL}/checkout-status/{self.session_id}",
                    timeout=5,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("paid") and data.get("cd_key"):
                        self.cd_key = data["cd_key"]
                        logger.info("Payment confirmed! CD-key: %s", self.cd_key)
                        on_success(self.cd_key, data.get("email", self.email))
                        return
            except Exception:
                pass
            time.sleep(self.POLL_INTERVAL)

        on_error("Payment confirmation timed out (10 min). "
                 "Check your email for the CD-key or contact support.")


def begin_checkout(
    email: str,
    device_id: str = "*",
    on_success: Optional[Callable[[str, str], None]] = None,
    on_error:   Optional[Callable[[str], None]] = None,
) -> bool:
    """Convenience wrapper — single call from Settings page."""
    sess = CheckoutSession(email, device_id)
    return sess.start(
        on_success=on_success or (lambda k, e: None),
        on_error=on_error   or (lambda m: None),
    )
