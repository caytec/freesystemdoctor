"""
welcome_dialog.py — friendly first-run welcome for non-technical users.

Shown once (persisted via app_settings "welcome_seen"). Lets the user:
  • pick a view — Simple (only essential tools) or All tools (advanced),
  • jump straight into a safe first action (1-Click Auto-Pilot or Health Check),
  • learn the Ctrl+K search shortcut.

Nothing here changes the system; the action buttons just navigate to a page.
"""

import tkinter as tk

from . import theme as T
from .widgets import ActionButton

try:
    from engine import app_settings
except Exception:  # pragma: no cover
    app_settings = None


class WelcomeDialog(tk.Toplevel):
    W, H = 600, 540

    def __init__(self, app, on_close=None):
        super().__init__(app)
        self._app = app
        self._on_close = on_close
        self.title("Welcome to FreeSystemDoctor")
        self.configure(bg=T.BG)
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.transient(app)
        self._mode_btns = {}
        self._build_ui()

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.W) // 2
        y = (self.winfo_screenheight() - self.H) // 2
        self.geometry(f"+{x}+{y}")
        try:
            self.attributes("-topmost", True)
            self.after(300, lambda: self.attributes("-topmost", False))
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self._finish)

    # ── layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=88)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="👋  Welcome to FreeSystemDoctor",
                 bg=T.ACCENT, fg=T.FG,
                 font=(T.FONT_FAMILY, 17, "bold")).pack(anchor="w", padx=24, pady=(18, 0))
        tk.Label(hdr, text="Keep your Windows PC fast, clean, and healthy.",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_BODY).pack(anchor="w", padx=24)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=24, pady=18)

        # ── 1. Choose a view ────────────────────────────────────────────────
        tk.Label(body, text="1.  Choose how much you want to see",
                 bg=T.BG, fg=T.FG, font=T.FONT_H2, anchor="w").pack(fill="x")
        tk.Label(body,
                 text="New to PC tools? Start Simple — you can switch anytime in Settings.",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 8))

        mode_row = tk.Frame(body, bg=T.BG)
        mode_row.pack(fill="x", pady=(0, 16))
        self._make_mode_card(mode_row, "simple", "🌱  Simple",
                             "Only the essential, everyday tools")
        self._make_mode_card(mode_row, "advanced", "🛠  All tools",
                             "Everything, including advanced features")

        current = "advanced"
        if app_settings is not None:
            current = app_settings.get("ui_mode", "advanced")
        self._select_mode(current, persist=False)

        # ── 2. Quick start ──────────────────────────────────────────────────
        tk.Label(body, text="2.  Or jump straight in",
                 bg=T.BG, fg=T.FG, font=T.FONT_H2, anchor="w").pack(fill="x")
        tk.Label(body, text="Both are safe — they scan first and ask before changing anything.",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL, anchor="w").pack(fill="x", pady=(2, 8))

        qa = tk.Frame(body, bg=T.BG)
        qa.pack(fill="x")
        ActionButton(qa, text="🚀  1-Click Auto-Pilot",
                     command=lambda: self._go("autopilot"), width=250).pack(side="left", padx=(0, 10))
        ActionButton(qa, text="❤  Health Check",
                     command=lambda: self._go("health"), width=200, secondary=True).pack(side="left")

        # ── 3. Tip ──────────────────────────────────────────────────────────
        tip = tk.Frame(body, bg=T.PANEL)
        tip.pack(fill="x", pady=(18, 0))
        tk.Label(tip, text="💡  Tip: press  Ctrl + K  anytime to search every tool by name.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 padx=12, pady=10, anchor="w").pack(fill="x")

        # ── footer ──────────────────────────────────────────────────────────
        footer = tk.Frame(self, bg=T.BG)
        footer.pack(fill="x", side="bottom", padx=24, pady=(0, 16))
        ActionButton(footer, text="Start exploring  →",
                     command=self._finish, width=170).pack(side="right")

    def _make_mode_card(self, parent, mode, title, subtitle):
        card = tk.Frame(parent, bg=T.PANEL, highlightthickness=2,
                        highlightbackground=T.BORDER, cursor="hand2")
        card.pack(side="left", fill="both", expand=True,
                  padx=(0, 10) if mode == "simple" else (0, 0))
        title_lbl = tk.Label(card, text=title, bg=T.PANEL, fg=T.FG,
                             font=T.FONT_BOLD, anchor="w", padx=12)
        title_lbl.pack(fill="x", pady=(10, 0))
        sub_lbl = tk.Label(card, text=subtitle, bg=T.PANEL, fg=T.FG2,
                           font=T.FONT_SMALL, anchor="w", padx=12,
                           wraplength=230, justify="left")
        sub_lbl.pack(fill="x", pady=(0, 10))
        self._mode_btns[mode] = (card, title_lbl, sub_lbl)
        for w in (card, title_lbl, sub_lbl):
            w.bind("<Button-1>", lambda e, m=mode: self._select_mode(m))

    def _select_mode(self, mode, persist=True):
        for m, (card, title_lbl, sub_lbl) in self._mode_btns.items():
            active = (m == mode)
            edge = T.HIGHLIGHT if active else T.BORDER
            bg = T.lerp_color(T.PANEL, T.HIGHLIGHT, 0.12) if active else T.PANEL
            try:
                card.config(highlightbackground=edge, bg=bg)
                title_lbl.config(bg=bg, fg=T.HIGHLIGHT if active else T.FG)
                sub_lbl.config(bg=bg)
            except tk.TclError:
                pass
        if persist and app_settings is not None:
            try:
                app_settings.set_and_save("ui_mode", mode)
            except Exception:
                pass
            # Apply live so the sidebar reflects the choice immediately.
            try:
                self._app._sidebar.refresh_mode()
            except Exception:
                pass

    # ── actions ─────────────────────────────────────────────────────────────
    def _go(self, page_key):
        # User dove straight into a tool — don't interrupt with the tour.
        self._on_close = None
        self._finish()
        try:
            self._app._switch_page(page_key)
        except Exception:
            pass

    def _finish(self):
        if app_settings is not None:
            try:
                app_settings.set_and_save("welcome_seen", True)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
        # Hand off to whatever should run after the welcome (e.g. the tour).
        if self._on_close:
            cb, self._on_close = self._on_close, None
            try:
                self._app.after(150, cb)
            except Exception:
                pass


def maybe_show_welcome(app, on_close=None) -> bool:
    """Show the welcome dialog once on first run. Returns True if it will show.

    ``on_close`` is invoked after the dialog is dismissed via "Start exploring"
    (used to chain the interactive tour). It is NOT called if the user dives
    straight into a tool from a CTA.
    """
    if app_settings is None:
        return False
    try:
        if app_settings.get("welcome_seen", False):
            return False
    except Exception:
        return False
    app.after(700, lambda: WelcomeDialog(app, on_close=on_close))
    return True
