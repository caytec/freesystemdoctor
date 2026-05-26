"""
native_ad_widgets.py — extra GUI surfaces for Option D monetization.

All widgets here are TKINTER NATIVE — no embedded WebView, no Image
downloader, no JS bridge. They're indistinguishable from regular FSD
panels except for an explicit "✦ Sponsored" or "💡 Tip" label.

Widgets:
  • TipCard            — Home page sponsored / editorial tip card.
  • NewsletterCard     — Email capture with explicit GDPR consent box.
  • InlineRecommendation — Compact 1-line recommendation row that fits
                          inside a result list (e.g. software updater).
  • PartnerGrid        — Settings → Monetization preview of all partners.

(File is `gui/native_ad_widgets.py` because `gui/widgets.py` already
owns the `gui.widgets` module name for primitives like Card/ActionButton.)
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from typing import Optional

from . import theme as T
from engine import affiliate, sponsored_notifications, email_capture


# ────────────────────────────────────────────────────────────────────────────
# TipCard
# ────────────────────────────────────────────────────────────────────────────

class TipCard(tk.Frame):
    """A 1-row dismissible card used on Home and post-action pages."""

    def __init__(self, parent, tip: Optional[dict] = None, **kw):
        super().__init__(parent, bg=T.PANEL,
                         highlightthickness=1,
                         highlightbackground=T.BORDER, **kw)
        self._tip = tip or sponsored_notifications.get_tip_of_the_day()
        if not self._tip:
            self.config(height=1)
            return
        self._build()

    def _build(self):
        t = self._tip
        is_spn = t.get("sponsored", False)

        inner = tk.Frame(self, bg=T.PANEL)
        inner.pack(fill="both", expand=True, padx=14, pady=10)

        tk.Label(
            inner, text=t.get("icon", "💡"),
            bg=T.PANEL, fg=T.HIGHLIGHT,
            font=(T.FONT_FAMILY, 18),
        ).pack(side="left", padx=(0, 12))

        text_frame = tk.Frame(inner, bg=T.PANEL)
        text_frame.pack(side="left", fill="both", expand=True)

        title_row = tk.Frame(text_frame, bg=T.PANEL)
        title_row.pack(fill="x")
        tk.Label(
            title_row, text=t.get("title", ""),
            bg=T.PANEL, fg=T.FG,
            font=T.FONT_H3, anchor="w",
        ).pack(side="left")
        if is_spn:
            tk.Label(
                title_row, text="  ✦ Sponsored",
                bg=T.PANEL, fg=T.FG2,
                font=T.FONT_MICRO,
            ).pack(side="left")

        tk.Label(
            text_frame, text=t.get("body", ""),
            bg=T.PANEL, fg=T.FG2,
            font=T.FONT_SMALL, justify="left", anchor="w",
            wraplength=460,
        ).pack(fill="x", pady=(2, 0))

        if t.get("cta") and t.get("url"):
            cta = tk.Button(
                inner, text=t["cta"],
                bg=T.HIGHLIGHT, fg="white",
                activebackground=T.lighten(T.HIGHLIGHT),
                activeforeground="white",
                bd=0, padx=14, pady=4,
                font=(T.FONT_FAMILY, 9, "bold"),
                cursor="hand2",
                command=self._on_click,
            )
            cta.pack(side="right", padx=(8, 0))

        x = tk.Label(
            inner, text="✕",
            bg=T.PANEL, fg=T.FG2,
            font=(T.FONT_FAMILY, 10), cursor="hand2",
        )
        x.pack(side="right", padx=(0, 8))
        x.bind("<Button-1>", lambda e: self._dismiss())
        x.bind("<Enter>", lambda e: x.config(fg=T.DANGER))
        x.bind("<Leave>", lambda e: x.config(fg=T.FG2))

    def _on_click(self):
        url = self._tip.get("url", "")
        if url.startswith("#"):
            return
        if self._tip.get("sponsored") and self._tip.get("offer_id"):
            affiliate.record_click(self._tip["offer_id"])
        else:
            try:
                webbrowser.open(url)
            except Exception:
                pass

    def _dismiss(self):
        if self._tip:
            sponsored_notifications.dismiss(self._tip["id"])
        self.destroy()


# ────────────────────────────────────────────────────────────────────────────
# NewsletterCard
# ────────────────────────────────────────────────────────────────────────────

class NewsletterCard(tk.Frame):
    """Explicit-consent email capture. Renders nothing once subscribed
    or dismissed."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=T.PANEL,
                         highlightthickness=1,
                         highlightbackground=T.BORDER, **kw)
        if email_capture.is_subscribed() or email_capture.is_dismissed():
            self.config(height=1)
            return
        self._consent = tk.BooleanVar(value=False)
        self._email = tk.StringVar()
        self._build()

    def _build(self):
        inner = tk.Frame(self, bg=T.PANEL)
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        tk.Label(
            inner, text="📬  Newsletter FSD",
            bg=T.PANEL, fg=T.HIGHLIGHT,
            font=T.FONT_H2, anchor="w",
        ).pack(fill="x")

        tk.Label(
            inner,
            text=("1 e-mail/tydzień: nowe funkcje, poradniki czyszczenia "
                  "Windows, kupony partnerów. Bez spamu, wypisujesz się "
                  "1 kliknięciem."),
            bg=T.PANEL, fg=T.FG2,
            font=T.FONT_SMALL, justify="left", anchor="w",
            wraplength=520,
        ).pack(fill="x", pady=(4, 10))

        entry = tk.Entry(
            inner, textvariable=self._email,
            bg=T.BG, fg=T.FG, insertbackground=T.FG,
            bd=0, relief="flat",
            font=T.FONT_BODY,
        )
        entry.pack(fill="x", ipady=6, padx=1)
        tk.Frame(inner, bg=T.BORDER, height=1).pack(fill="x", pady=(0, 8))

        consent_row = tk.Frame(inner, bg=T.PANEL)
        consent_row.pack(fill="x", pady=(0, 10))
        tk.Checkbutton(
            consent_row,
            variable=self._consent,
            text=("Wyrażam zgodę na otrzymywanie newslettera FSD na podany e-mail. "
                  "Mogę wypisać się w każdej chwili (RODO)."),
            bg=T.PANEL, fg=T.FG2,
            activebackground=T.PANEL, activeforeground=T.FG,
            selectcolor=T.BG,
            font=T.FONT_MICRO, anchor="w", justify="left",
            wraplength=520,
        ).pack(side="left", fill="x", expand=True)

        btns = tk.Frame(inner, bg=T.PANEL)
        btns.pack(fill="x")

        tk.Button(
            btns, text="Zapisz mnie",
            bg=T.HIGHLIGHT, fg="white",
            activebackground=T.lighten(T.HIGHLIGHT),
            activeforeground="white",
            bd=0, padx=16, pady=6,
            font=(T.FONT_FAMILY, 9, "bold"),
            cursor="hand2",
            command=self._on_submit,
        ).pack(side="left")

        skip = tk.Label(
            btns, text="Nie, dziękuję",
            bg=T.PANEL, fg=T.FG2,
            font=T.FONT_SMALL, cursor="hand2",
        )
        skip.pack(side="left", padx=12)
        skip.bind("<Button-1>", lambda e: self._on_dismiss())
        skip.bind("<Enter>", lambda e: skip.config(fg=T.FG))
        skip.bind("<Leave>", lambda e: skip.config(fg=T.FG2))

        self._status = tk.Label(
            inner, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_MICRO,
            anchor="w", justify="left",
        )
        self._status.pack(fill="x", pady=(8, 0))

    def _on_submit(self):
        if not self._consent.get():
            self._status.config(text="✗ Zaznacz zgodę RODO przed wysłaniem.",
                                fg=T.DANGER)
            return
        result = email_capture.subscribe(self._email.get().strip(), source="card")
        if result["ok"] and not result["queued"]:
            self._status.config(text="✓ Zapisano! Sprawdź swoją skrzynkę.", fg=T.SUCCESS)
            self.after(2200, self.destroy)
        elif result["queued"]:
            self._status.config(
                text="⏳ Brak internetu — wyślemy zapis przy następnym uruchomieniu.",
                fg=T.WARNING,
            )
            self.after(2600, self.destroy)
        else:
            if result["reason"] == "invalid_email":
                self._status.config(text="✗ Niepoprawny adres e-mail.", fg=T.DANGER)
            else:
                self._status.config(text="✗ Nie udało się zapisać.", fg=T.DANGER)

    def _on_dismiss(self):
        email_capture.dismiss_prompt()
        self.destroy()


# ────────────────────────────────────────────────────────────────────────────
# InlineRecommendation
# ────────────────────────────────────────────────────────────────────────────

class InlineRecommendation(tk.Frame):
    """A subtle single-row recommendation that fits inside a list view
    (e.g. between rows in the software updater). Renders nothing if
    monetization is off or no offer fits."""

    def __init__(self, parent, page_key: str, **kw):
        super().__init__(parent, bg=T.ACCENT, **kw)
        self._offer = affiliate.pick_offer_for_page(page_key)
        if not self._offer:
            self.config(height=1)
            return
        self._build()

    def _build(self):
        o = self._offer
        inner = tk.Frame(self, bg=T.ACCENT)
        inner.pack(fill="both", expand=True, padx=10, pady=6)

        tk.Label(
            inner, text="✦",
            bg=T.ACCENT, fg=T.FG2,
            font=(T.FONT_FAMILY, 9),
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            inner,
            text=f"{o['title']} — {o['tagline']}",
            bg=T.ACCENT, fg=T.FG2,
            font=T.FONT_SMALL, anchor="w",
        ).pack(side="left", fill="x", expand=True)

        link = tk.Label(
            inner, text=f"{o['cta']} →",
            bg=T.ACCENT, fg=T.HIGHLIGHT,
            font=(T.FONT_FAMILY, 9, "bold"),
            cursor="hand2",
        )
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: affiliate.record_click(o["id"]))
        link.bind("<Enter>", lambda e: link.config(fg=T.lighten(T.HIGHLIGHT, 0.2)))
        link.bind("<Leave>", lambda e: link.config(fg=T.HIGHLIGHT))


# ────────────────────────────────────────────────────────────────────────────
# PartnerGrid
# ────────────────────────────────────────────────────────────────────────────

class PartnerGrid(tk.Frame):
    """Settings → 'Nasi partnerzy' transparent grid of every offer with
    per-category toggles."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=T.PANEL, **kw)
        self._build()

    def _build(self):
        tk.Label(
            self, text="Nasi partnerzy afiliacyjni",
            bg=T.PANEL, fg=T.FG, font=T.FONT_H2, anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 4))

        tk.Label(
            self,
            text=("Klikając poniższe linki pomagasz utrzymać FSD w pełni "
                  "darmowym — otrzymujemy małą prowizję, Ty nie płacisz nic "
                  "więcej. Możesz wyłączyć całą kategorię w jednym kliknięciu."),
            bg=T.PANEL, fg=T.FG2,
            font=T.FONT_SMALL, justify="left", anchor="w",
            wraplength=620,
        ).pack(fill="x", padx=14, pady=(0, 10))

        disabled = set(affiliate.disabled_categories())
        grouped: dict[str, list[dict]] = {}
        for o in affiliate.OFFERS:
            grouped.setdefault(o["category"], []).append(o)

        for cat, offers in sorted(grouped.items()):
            self._render_category(cat, offers, cat in disabled)

    def _render_category(self, category: str, offers: list[dict], cat_disabled: bool):
        block = tk.Frame(self, bg=T.PANEL)
        block.pack(fill="x", padx=14, pady=(8, 4))

        header = tk.Frame(block, bg=T.PANEL)
        header.pack(fill="x")
        tk.Label(
            header, text=category,
            bg=T.PANEL, fg=T.FG, font=T.FONT_H3, anchor="w",
        ).pack(side="left")

        var = tk.BooleanVar(value=not cat_disabled)
        tk.Checkbutton(
            header, text="Pokazuj", variable=var,
            bg=T.PANEL, fg=T.FG2,
            activebackground=T.PANEL, activeforeground=T.FG,
            selectcolor=T.BG,
            font=T.FONT_MICRO,
            command=lambda: affiliate.set_category_enabled(category, var.get()),
        ).pack(side="right")

        for o in offers:
            row = tk.Frame(block, bg=T.PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(
                row, text=f"• {o['title']}",
                bg=T.PANEL, fg=T.FG, font=T.FONT_SMALL, anchor="w",
            ).pack(side="left")
            tk.Label(
                row, text=o["tagline"],
                bg=T.PANEL, fg=T.FG2, font=T.FONT_MICRO, anchor="w",
            ).pack(side="left", padx=(8, 0), fill="x", expand=True)
            link = tk.Label(
                row, text="otwórz →",
                bg=T.PANEL, fg=T.HIGHLIGHT,
                font=T.FONT_MICRO, cursor="hand2",
            )
            link.pack(side="right")
            link.bind("<Button-1>", lambda e, oid=o["id"]: affiliate.record_click(oid))
