"""Performance Profiles page — switch between Work/Gaming/Streaming/Battery modes."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton
from engine import performance_profiles as pp
from engine import license_manager as lm

from ._pro_gate import limit_banner, at_limit_dialog


class PerformanceProfilesPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Performance Profiles", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Switch between Work, Gaming, Streaming, and Battery modes",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        banner = limit_banner(body, "performance_profiles")
        if banner:
            banner.pack(fill="x", pady=(0, 10))

        # Status card
        self._build_status_card(body)

        # Profiles card
        self._build_profiles_card(body)

    def _build_status_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Current Power Plan").pack(anchor="w", padx=10, pady=8)

        self._power_plan = tk.Label(card, text="Loading...", bg=T.PANEL, fg=T.FG,
                                   font=(T.FONT_FAMILY, 14, "bold"))
        self._power_plan.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_profiles_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Available Profiles").pack(anchor="w", padx=10, pady=8)

        profiles_frame = tk.Frame(card, bg=T.PANEL)
        profiles_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._profile_buttons = {}
        profiles = pp.list_profiles()

        # Free tier: only the first N profiles are usable; the rest are Pro.
        limit = lm.effective_limit("performance_profiles")  # None = unlimited
        for idx, profile in enumerate(profiles):
            locked = limit is not None and idx >= limit
            self._build_profile_button(profiles_frame, profile, locked)

    def _build_profile_button(self, parent, profile, locked=False):
        frame = tk.Frame(parent, bg=T.ACCENT if profile["active"] else T.BORDER, height=80)
        frame.pack(fill="x", pady=4)
        frame.pack_propagate(False)

        inner = tk.Frame(frame, bg=T.PANEL)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        title = tk.Label(inner, text=profile["name"], bg=T.PANEL, fg=T.FG,
                        font=T.FONT_BOLD)
        title.pack(anchor="w", padx=10, pady=(6, 0))

        desc = tk.Label(inner, text=profile["description"], bg=T.PANEL, fg=T.FG2,
                       font=T.FONT_SMALL, wraplength=400)
        desc.pack(anchor="w", padx=10, pady=2)

        if locked:
            btn = tk.Button(inner, text="🔒 Pro", bg=T.ACCENT,
                            fg=T.HIGHLIGHT, font=T.FONT_BODY, padx=10, pady=4,
                            command=lambda: at_limit_dialog("performance_profiles"))
            btn.pack(anchor="e", padx=10, pady=(0, 6))
            return

        status = "ACTIVE" if profile["active"] else "Switch"

        btn = tk.Button(inner, text=status, bg=T.HIGHLIGHT if profile["active"] else T.ACCENT,
                       fg=T.FG, font=T.FONT_BODY, padx=10, pady=4,
                       command=lambda k=profile["key"]: self._on_activate(k),
                       state="disabled" if profile["active"] else "normal")
        btn.pack(anchor="e", padx=10, pady=(0, 6))

        self._profile_buttons[profile["key"]] = btn

    def _on_activate(self, profile_key):
        def activate():
            success = pp.activate_profile(profile_key)
            self.after(0, lambda: self._on_activated(success, profile_key))

        threading.Thread(target=activate, daemon=True).start()

    def _on_activated(self, success, profile_key):
        if success:
            messagebox.showinfo("Profile Activated",
                              f"Performance profile activated: {profile_key.title()}")
            self._refresh_ui()
        else:
            messagebox.showerror("Error", "Failed to activate profile")

    def _refresh_ui(self):
        power_plan = pp.get_power_plan()
        self._power_plan.config(text=f"Active: {power_plan['name']}")

        profiles = pp.list_profiles()
        for profile in profiles:
            if profile["key"] in self._profile_buttons:
                btn = self._profile_buttons[profile["key"]]
                if profile["active"]:
                    btn.config(state="disabled", text="ACTIVE")
                else:
                    btn.config(state="normal", text="Switch")

    def on_activate(self):
        self._refresh_ui()
