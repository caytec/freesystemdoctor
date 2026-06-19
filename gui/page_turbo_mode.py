"""Turbo Mode page — Performance and Gaming mode optimizer."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import turbo_mode as tm


from ._pro_gate import limit_banner


class TurboModePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._turbo_enabled = False
        self._gaming_enabled = False
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Turbo Mode", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Maximum performance and gaming optimization",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        banner = limit_banner(body, "turbo_mode")
        if banner:
            banner.pack(fill="x", pady=(0, 10))

        # Performance mode card
        self._build_performance_card(body)

        # Gaming mode card
        self._build_gaming_card(body)

    def _build_performance_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=False, pady=(0, 12))
        SectionLabel(card, "Performance Mode").pack(anchor="w", padx=10, pady=8)

        desc = tk.Label(card,
                       text="Disables visual effects, optimizes services, and tunes system for maximum CPU/RAM performance.",
                       bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, wraplength=400, justify="left")
        desc.pack(anchor="w", padx=10, pady=(0, 8))

        # Toggle
        toggle_frame = tk.Frame(card, bg=T.PANEL)
        toggle_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(toggle_frame, text="Enable Performance Mode", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._perf_var = tk.BooleanVar(value=self._turbo_enabled)
        self._perf_toggle = ToggleSwitch(toggle_frame, variable=self._perf_var,
                                         command=self._on_perf_toggled)
        self._perf_toggle.pack(side="right")

        # Status
        self._perf_status = tk.Label(card, text="Status: Disabled",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._perf_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_gaming_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=False, pady=0)
        SectionLabel(card, "Gaming Mode").pack(anchor="w", padx=10, pady=8)

        desc = tk.Label(card,
                       text="Optimizes for gaming: disables background tasks, prioritizes GPU, reduces input lag.",
                       bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, wraplength=400, justify="left")
        desc.pack(anchor="w", padx=10, pady=(0, 8))

        # Toggle
        toggle_frame = tk.Frame(card, bg=T.PANEL)
        toggle_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(toggle_frame, text="Enable Gaming Mode", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._game_var = tk.BooleanVar(value=self._gaming_enabled)
        self._game_toggle = ToggleSwitch(toggle_frame, variable=self._game_var,
                                         command=self._on_game_toggled)
        self._game_toggle.pack(side="right")

        # Status
        self._game_status = tk.Label(card, text="Status: Disabled",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._game_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_perf_toggled(self):
        if self._perf_var.get():
            def enable():
                try:
                    tm.enable_turbo(mode="performance")
                    self._turbo_enabled = True
                    self._perf_status.config(text="Status: ✓ Enabled", fg=T.SUCCESS)
                    messagebox.showinfo("Success", "Performance mode enabled")
                except Exception as e:
                    self._perf_var.set(False)
                    messagebox.showerror("Error", f"Failed: {e}")

            threading.Thread(target=enable, daemon=True).start()
        else:
            def disable():
                try:
                    tm.disable_turbo()
                    self._turbo_enabled = False
                    self._perf_status.config(text="Status: Disabled", fg=T.FG2)
                    messagebox.showinfo("Success", "Performance mode disabled")
                except Exception as e:
                    self._perf_var.set(True)
                    messagebox.showerror("Error", f"Failed: {e}")

            threading.Thread(target=disable, daemon=True).start()

    def _on_game_toggled(self):
        if self._game_var.get():
            def enable():
                try:
                    tm.enable_turbo(mode="gaming")
                    self._gaming_enabled = True
                    self._game_status.config(text="Status: ✓ Enabled", fg=T.SUCCESS)
                    messagebox.showinfo("Success", "Gaming mode enabled")
                except Exception as e:
                    self._game_var.set(False)
                    messagebox.showerror("Error", f"Failed: {e}")

            threading.Thread(target=enable, daemon=True).start()
        else:
            def disable():
                try:
                    tm.disable_turbo()
                    self._gaming_enabled = False
                    self._game_status.config(text="Status: Disabled", fg=T.FG2)
                    messagebox.showinfo("Success", "Gaming mode disabled")
                except Exception as e:
                    self._game_var.set(True)
                    messagebox.showerror("Error", f"Failed: {e}")

            threading.Thread(target=disable, daemon=True).start()

    def on_activate(self):
        pass
