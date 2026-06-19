"""Idle Maintenance page — configure automatic cleanup during idle time."""

import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import idle_maintenance as im


from ._pro_gate import limit_banner


class IdleMaintenancePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._enabled_var = tk.BooleanVar(value=False)
        self._disk_clean_var = tk.BooleanVar(value=True)
        self._registry_clean_var = tk.BooleanVar(value=True)
        self._privacy_clean_var = tk.BooleanVar(value=True)
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Idle Maintenance", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Automatic cleanup when your PC is idle",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        banner = limit_banner(body, "idle_maintenance")
        if banner:
            banner.pack(fill="x", pady=(0, 10))

        # Enable toggle
        self._build_enable_card(body)

        # Configuration card
        self._build_config_card(body)

        # Status card
        self._build_status_card(body)

    def _build_enable_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Automatic Maintenance").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row, text="Enable idle-time auto-maintenance:",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")

        ToggleSwitch(row, variable=self._enabled_var,
                     command=self._on_enable_toggle).pack(side="left", padx=12)

        tk.Label(card,
                 text="When enabled, FreeSystemDoctor will automatically run selected cleanups when your PC is idle (no mouse/keyboard for 5+ minutes, CPU/disk not busy).",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 wraplength=550, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

    def _build_config_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Maintenance Tasks").pack(anchor="w", padx=10, pady=8)

        tk.Label(card, text="Select which cleanups to run automatically:",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", padx=10, pady=(0, 8))

        for label, var in [
            ("Disk Cleaner (remove junk files)", self._disk_clean_var),
            ("Registry Cleaner (fix errors)", self._registry_clean_var),
            ("Privacy Cleaner (remove tracking data)", self._privacy_clean_var),
        ]:
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=2)

            tk.Checkbutton(row, text=label, variable=var, bg=T.PANEL, fg=T.FG,
                          font=T.FONT_BODY, activebackground=T.PANEL,
                          activeforeground=T.FG).pack(anchor="w")

        tk.Frame(card, bg=T.PANEL, height=4).pack()

        ActionButton(card, text="Save Configuration",
                     command=self._on_save_config).pack(anchor="w", padx=10, pady=(0, 8))

    def _build_status_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False)

        SectionLabel(card, "Status").pack(anchor="w", padx=10, pady=8)

        self._status_text = tk.Label(card, text="Loading status...", bg=T.PANEL, fg=T.FG2,
                                     font=T.FONT_SMALL, wraplength=550, justify="left")
        self._status_text.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_enable_toggle(self):
        enabled = self._enabled_var.get()
        if enabled:
            im.enable_idle_maintenance(True)
            messagebox.showinfo("Idle Maintenance",
                              "Idle maintenance enabled. Cleanups will run when your PC is idle.")
        else:
            im.enable_idle_maintenance(False)
            messagebox.showinfo("Idle Maintenance", "Idle maintenance disabled.")

        self._update_status()

    def _on_save_config(self):
        config = im.get_maintenance_config()
        config["run_disk_clean"] = self._disk_clean_var.get()
        config["run_registry_clean"] = self._registry_clean_var.get()
        config["run_privacy_clean"] = self._privacy_clean_var.get()
        im.set_maintenance_config(config)
        messagebox.showinfo("Settings Saved", "Idle maintenance configuration updated.")

    def _update_status(self):
        enabled = im.is_maintenance_enabled()
        next_time = im.get_next_maintenance_time()

        status = f"Status: {'Enabled' if enabled else 'Disabled'}\n"
        status += f"Next maintenance: {next_time}"

        self._status_text.config(text=status)

    def on_activate(self):
        config = im.get_maintenance_config()
        self._enabled_var.set(config.get("enabled", False))
        self._disk_clean_var.set(config.get("run_disk_clean", True))
        self._registry_clean_var.set(config.get("run_registry_clean", True))
        self._privacy_clean_var.set(config.get("run_privacy_clean", True))
        self._update_status()
