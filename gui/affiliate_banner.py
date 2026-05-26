"""
Native tkinter widgets for monetization:
- SponsoredBanner: subtle 1-line affiliate recommendation
- ProUpgradePrompt: in-app upsell to FSD Pro tier

Both are explicitly labeled, hover-aware, and respect the user's
'Hide sponsored recommendations' toggle in Settings.
"""

import tkinter as tk
import webbrowser

from . import theme as T
from engine import affiliate


PRO_URL = "https://caytec.github.io/freesystemdoctor-pro"


class SponsoredBanner(tk.Frame):
    """One-line sponsored placement, 36 px tall, dismissible per-session."""

    def __init__(self, parent, page_key: str, **kw):
        super().__init__(parent, bg=T.PANEL, height=44, **kw)
        self.pack_propagate(False)
        self._page_key = page_key
        self._offer = affiliate.pick_offer_for_page(page_key)
        if self._offer is None:
            # Either disabled by user or no offer for this page → render empty
            self.config(height=1)
            return
        self._build()

    def _build(self):
        o = self._offer

        # Subtle border-top accent
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x", side="top")

        inner = tk.Frame(self, bg=T.PANEL)
        inner.pack(fill="both", expand=True, padx=12, pady=4)

        # "✦ Sponsored" tag
        tag = tk.Label(
            inner, text="✦ Sponsored",
            bg=T.PANEL, fg=T.FG2,
            font=(T.FONT_FAMILY, 8, "bold"),
        )
        tag.pack(side="left", padx=(0, 10))

        # Title + tagline
        text_frame = tk.Frame(inner, bg=T.PANEL)
        text_frame.pack(side="left", fill="x", expand=True)

        tk.Label(
            text_frame,
            text=f"{o['title']} — {o['tagline']}",
            bg=T.PANEL, fg=T.FG,
            font=(T.FONT_FAMILY, 9),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        # CTA button
        cta = tk.Button(
            inner, text=o["cta"],
            bg=T.HIGHLIGHT, fg="white",
            activebackground=T.lerp_color(T.HIGHLIGHT, "#ffffff", 0.1),
            activeforeground="white",
            bd=0, padx=14, pady=4,
            font=(T.FONT_FAMILY, 9, "bold"),
            cursor="hand2",
            command=self._on_click,
        )
        cta.pack(side="right", padx=(8, 0))

        # Hide-X button (per-session dismiss, not permanent)
        x = tk.Label(
            inner, text="✕",
            bg=T.PANEL, fg=T.FG2,
            font=(T.FONT_FAMILY, 10),
            cursor="hand2",
        )
        x.pack(side="right", padx=(0, 4))
        x.bind("<Button-1>", lambda e: self.destroy())
        x.bind("<Enter>", lambda e: x.config(fg=T.DANGER))
        x.bind("<Leave>", lambda e: x.config(fg=T.FG2))

    def _on_click(self):
        affiliate.record_click(self._offer["id"])


class ProUpgradePrompt(tk.Frame):
    """Bigger native card promoting FSD Pro features. Shown post-scan."""

    def __init__(self, parent, context: str = "post-scan", **kw):
        super().__init__(parent, bg=T.PANEL,
                          highlightthickness=1,
                          highlightbackground=T.HIGHLIGHT,
                          **kw)
        self._context = context
        self._build()

    def _build(self):
        # Gold-ish accent strip on top
        tk.Frame(self, bg="#ffc857", height=3).pack(fill="x", side="top")

        inner = tk.Frame(self, bg=T.PANEL)
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        # Title
        title_row = tk.Frame(inner, bg=T.PANEL)
        title_row.pack(fill="x", pady=(0, 6))
        tk.Label(
            title_row, text="💎  Polub FSD Pro",
            bg=T.PANEL, fg="#ffc857",
            font=(T.FONT_FAMILY, 12, "bold"),
        ).pack(side="left")

        tk.Label(
            title_row, text="od 99 zł/rok · lifetime 199 zł",
            bg=T.PANEL, fg=T.FG2,
            font=(T.FONT_FAMILY, 9),
        ).pack(side="right")

        # Context-specific message
        msg = self._message_for_context()
        tk.Label(
            inner, text=msg,
            bg=T.PANEL, fg=T.FG,
            font=T.FONT_BODY,
            justify="left", anchor="w", wraplength=520,
        ).pack(fill="x", pady=(0, 10))

        # Button row
        btns = tk.Frame(inner, bg=T.PANEL)
        btns.pack(fill="x")

        cta = tk.Button(
            btns, text="Zobacz Pro →",
            bg="#ffc857", fg="#1a1207",
            activebackground=T.lerp_color("#ffc857", "#ffffff", 0.1),
            activeforeground="#1a1207",
            bd=0, padx=18, pady=6,
            font=(T.FONT_FAMILY, 10, "bold"),
            cursor="hand2",
            command=lambda: webbrowser.open(PRO_URL),
        )
        cta.pack(side="left")

        skip = tk.Label(
            btns, text="Później",
            bg=T.PANEL, fg=T.FG2,
            font=(T.FONT_FAMILY, 9),
            cursor="hand2",
        )
        skip.pack(side="left", padx=12)
        skip.bind("<Button-1>", lambda e: self.destroy())
        skip.bind("<Enter>", lambda e: skip.config(fg=T.FG))
        skip.bind("<Leave>", lambda e: skip.config(fg=T.FG2))

    def _message_for_context(self) -> str:
        return {
            "post-scan": (
                "Cofnij ten skan co tydzień automatycznie. Cloud sync pomiędzy 3 PC.\n"
                "Discord/email alerts gdy znajdzie nowe problemy."
            ),
            "post-clean": (
                "Pro czyści to samo automatycznie co tydzień — bez Twojej interwencji.\n"
                "Branded raporty PDF dla klientów IT."
            ),
            "drivers": (
                "Pro: 8M+ driverów w bazie, równoległe pobieranie, bez kolejki.\n"
                "Plus auto-update 3000+ aplikacji."
            ),
            "game": (
                "Per-game profile dla 50+ tytułów. Auto-detect przy launch.\n"
                "Anti-cheat safe sandbox tester w Ultimate."
            ),
        }.get(self._context, (
            "Cloud sync · auto-scheduler · per-game profile · Discord alerts.\n"
            "Lifetime za 199 zł — bez auto-renewal."
        ))


class SidebarProBadge(tk.Frame):
    """Tiny clickable diamond in sidebar bottom area."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=T.SIDEBAR, **kw)
        lbl = tk.Label(
            self, text="💎 Pro",
            bg=T.SIDEBAR, fg="#ffc857",
            font=(T.FONT_FAMILY, 9, "bold"),
            cursor="hand2", pady=4,
        )
        lbl.pack()
        lbl.bind("<Button-1>", lambda e: webbrowser.open(PRO_URL))
        lbl.bind("<Enter>", lambda e: lbl.config(fg="#ffe9b5"))
        lbl.bind("<Leave>", lambda e: lbl.config(fg="#ffc857"))
