"""Credits wallet — earn, spend and top up in-app credits.

Credits are the subscription-free way to unlock individual Pro tools.
Pro subscribers get everything anyway, so this page tells them so.
"""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, PageHeader
from engine import credits as cr


class CreditsPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Credits",
                   subtitle="Unlock Pro tools without a subscription",
                   icon="🎟", color=T.HIGHLIGHT).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_balance(body)
        self._build_earn(body)
        self._build_buy(body)
        self._build_unlocks(body)

    def _build_balance(self, parent):
        card = Card(parent, glow=True)
        card.pack(fill="x", pady=(0, 12))

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(row, text="🎟", bg=T.PANEL, fg=T.HIGHLIGHT,
                 font=(T.FONT_FAMILY, 26)).pack(side="left", padx=(0, 10))
        self._bal_lbl = tk.Label(row, text="0", bg=T.PANEL, fg=T.FG,
                                 font=("Segoe UI", 30, "bold"))
        self._bal_lbl.pack(side="left")
        tk.Label(row, text=" credits", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", pady=(14, 0))

        self._sub_lbl = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                 font=T.FONT_SMALL, anchor="w", justify="left",
                                 wraplength=600)
        self._sub_lbl.pack(anchor="w", padx=18, pady=(0, 14))

    def _build_earn(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Get credits free").pack(anchor="w", padx=14, pady=(10, 6))

        # Daily / streak bonus — works offline, no third party
        d = tk.Frame(card, bg=T.PANEL)
        d.pack(fill="x", padx=14, pady=(0, 6))
        self._daily_btn = ActionButton(d, text="🎁  Claim daily bonus", width=190,
                                       command=self._claim_daily)
        self._daily_btn.pack(side="left")
        self._daily_lbl = tk.Label(d, text="", bg=T.PANEL, fg=T.FG2,
                                   font=T.FONT_SMALL)
        self._daily_lbl.pack(side="left", padx=12)

        # Rewarded ad — only pays out when a real ad was served
        a = tk.Frame(card, bg=T.PANEL)
        a.pack(fill="x", padx=14, pady=(0, 10))
        self._ad_btn = ActionButton(a, text=f"📺  Watch an ad (+{cr.AD_REWARD})",
                                    width=190, secondary=True,
                                    command=self._watch_ad)
        self._ad_btn.pack(side="left")
        self._ad_lbl = tk.Label(a, text="", bg=T.PANEL, fg=T.FG2,
                                font=T.FONT_SMALL, wraplength=380,
                                justify="left")
        self._ad_lbl.pack(side="left", padx=12)

    def _build_buy(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Top up instantly").pack(anchor="w", padx=14, pady=(10, 2))
        tk.Label(card, text="One-time card payment via Stripe — no subscription.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(
                 anchor="w", padx=14, pady=(0, 8))

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=14, pady=(0, 10))
        for pack in cr.PACKS:
            price = f"${pack['price_cents'] / 100:.2f}"
            ActionButton(row, text=f"{pack['credits']} — {price}", width=140,
                         command=lambda p=pack: self._buy(p)).pack(side="left",
                                                                   padx=(0, 8))

        tk.Label(card,
                 text="💎  Prefer everything at once? Pro ($9.99/yr) unlocks all "
                      "tools — see Settings → License.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 wraplength=600, justify="left").pack(anchor="w", padx=14,
                                                      pady=(0, 10))

    def _build_unlocks(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, f"Unlock a tool — {cr.UNLOCK_COST} credits each").pack(
            anchor="w", padx=14, pady=(10, 6))

        self._unlock_rows = {}
        for fid, name in cr.UNLOCKABLE.items():
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=name, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BODY, width=20, anchor="w").pack(side="left")
            status = tk.Label(row, text="", bg=T.PANEL, fg=T.FG2,
                              font=T.FONT_SMALL)
            status.pack(side="left", padx=8)
            btn = ActionButton(row, text=f"Unlock ({cr.UNLOCK_COST})", width=140,
                               command=lambda f=fid: self._unlock(f))
            btn.pack(side="right")
            self._unlock_rows[fid] = (status, btn)

        tk.Frame(card, bg=T.PANEL, height=8).pack()

    # ── actions ──────────────────────────────────────────────────────────────
    def _claim_daily(self):
        ok, amount, msg = cr.claim_daily_bonus()
        messagebox.showinfo("Daily bonus" if ok else "Already claimed", msg)
        self._refresh()

    def _watch_ad(self):
        available, why = cr.reward_available()
        if not available:
            messagebox.showinfo(
                "Rewarded ads unavailable",
                f"{why}\n\nRewarded video is not available on Windows desktop "
                f"yet — we only pay out credits for ads that were actually "
                f"shown, never for nothing.")
            self._refresh()
            return
        ok, amount, msg = cr.grant_ad_reward()
        messagebox.showinfo("Thanks!" if ok else "Not available", msg)
        self._refresh()

    def _buy(self, pack):
        from engine import stripe_checkout
        if not hasattr(stripe_checkout, "begin_credits_checkout"):
            messagebox.showinfo("Coming soon",
                                "Credit purchases aren't enabled on the server yet.")
            return

        def on_success(pack_id):
            ok, bal = cr.credit_pack_purchased(pack_id)
            self.after(0, lambda: (
                messagebox.showinfo("Credits added",
                                    f"Payment successful — you now have {bal} credits."),
                self._refresh()))

        def on_error(msg):
            self.after(0, lambda: messagebox.showerror("Payment error", msg))

        ok = stripe_checkout.begin_credits_checkout(
            pack_id=pack["id"], on_success=on_success, on_error=on_error)
        if ok:
            messagebox.showinfo(
                "Browser opened",
                "Complete your payment in the browser.\n"
                "Your credits are added automatically once it's confirmed.")

    def _unlock(self, feature_id):
        ok, msg = cr.unlock_feature(feature_id)
        messagebox.showinfo("Unlocked" if ok else "Not enough credits", msg)
        self._refresh()

    # ── state ────────────────────────────────────────────────────────────────
    def _refresh(self):
        try:
            from engine import license_manager as lm
            is_pro = lm.is_pro()
        except Exception:
            is_pro = False

        bal = cr.balance()
        self._bal_lbl.config(text=str(bal))

        if is_pro:
            self._sub_lbl.config(
                text="You're on Pro — every tool is already unlocked. "
                     "Credits aren't needed on your account.")
        else:
            self._sub_lbl.config(
                text=f"Spend {cr.UNLOCK_COST} credits to unlock any single Pro "
                     f"tool permanently. Earn them free below, or top up once.")

        # daily bonus
        if cr.daily_bonus_available():
            self._daily_btn.config(state="normal")
            self._daily_lbl.config(
                text=f"+{cr.DAILY_BONUS} credits, once a day (streak adds more)")
        else:
            self._daily_btn.config(state="disabled")
            self._daily_lbl.config(
                text=f"Claimed today — streak: {cr.streak()} day(s)")

        # rewarded ad
        available, why = cr.reward_available()
        self._ad_btn.config(state="normal" if available else "disabled")
        self._ad_lbl.config(text=why if not available
                            else f"{cr.ads_left_today()} left today")

        # unlock rows
        for fid, (status, btn) in self._unlock_rows.items():
            if is_pro:
                status.config(text="✓ included in Pro", fg=T.SUCCESS)
                btn.config(state="disabled")
            elif cr.is_unlocked(fid):
                status.config(text="✓ unlocked", fg=T.SUCCESS)
                btn.config(state="disabled")
            else:
                status.config(text="locked", fg=T.FG2)
                btn.config(state="normal" if bal >= cr.UNLOCK_COST else "disabled")

    def on_activate(self):
        self._refresh()
