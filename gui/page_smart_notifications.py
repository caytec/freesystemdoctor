"""Smart Notifications page — configure background scanning and alerts."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import smart_notifications as sn


class SmartNotificationsPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._cfg = sn.get_config()
        self._enabled_var = tk.BooleanVar(value=self._cfg.get("enabled", True))
        self._junk_var = tk.BooleanVar(value=self._cfg.get("notify_junk", True))
        self._startup_var = tk.BooleanVar(value=self._cfg.get("notify_startup", True))
        self._memory_var = tk.BooleanVar(value=self._cfg.get("notify_memory", True))
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Smart Notifications", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Background scanning with automatic system alerts",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_master_card(body)
        self._build_settings_card(body)
        self._build_scan_card(body)
        self._build_results_card(body)

    def _build_master_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Background Scanner").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row, text="Enable automatic background scanning",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        ToggleSwitch(row, variable=self._enabled_var,
                     command=self._on_toggle_master).pack(side="left", padx=12)

        self._scanner_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._scanner_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_settings_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Alert Settings").pack(anchor="w", padx=10, pady=8)

        def toggle_row(parent, text, var, key):
            row = tk.Frame(parent, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=text, bg=T.PANEL, fg=T.FG, font=T.FONT_BODY,
                     width=35, anchor="w").pack(side="left")
            ToggleSwitch(row, variable=var,
                         command=lambda: self._save_setting(key, var.get())).pack(side="left")

        toggle_row(card, "Alert when junk files exceed 500 MB", self._junk_var, "notify_junk")
        toggle_row(card, "Alert when startup programs slow boot", self._startup_var, "notify_startup")
        toggle_row(card, "Alert when RAM usage exceeds 85%", self._memory_var, "notify_memory")

        interval_row = tk.Frame(card, bg=T.PANEL)
        interval_row.pack(fill="x", padx=10, pady=(8, 8))
        tk.Label(interval_row, text="Scan interval (minutes):",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")

        self._interval_var = tk.StringVar(value=str(self._cfg.get("interval_minutes", 60)))
        vcmd = self.register(lambda s: s.isdigit() or s == "")
        entry = tk.Entry(interval_row, textvariable=self._interval_var, width=6,
                         bg=T.ACCENT, fg=T.FG, insertbackground=T.FG,
                         font=T.FONT_BODY, validate="key", validatecommand=(vcmd, "%P"))
        entry.pack(side="left", padx=8)
        ActionButton(interval_row, text="Save", command=self._save_interval).pack(side="left")

    def _build_scan_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Manual Scan").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(row, text="Scan Now",
                     command=self._on_scan_now).pack(side="left", padx=(0, 8))
        self._scan_status = tk.Label(row, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._scan_status.pack(side="left")

    def _build_results_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Last Scan Results").pack(anchor="w", padx=10, pady=8)

        self._results_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                     height=8, bd=0, padx=8, pady=6,
                                     state="disabled", wrap="word")
        self._results_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _on_toggle_master(self):
        enabled = self._enabled_var.get()
        self._cfg["enabled"] = enabled
        sn.save_config(self._cfg)
        if enabled:
            sn.start_background_scanner()
            self._scanner_status.config(text="Scanner running in background", fg=T.SUCCESS)
        else:
            sn.stop_background_scanner()
            self._scanner_status.config(text="Scanner stopped", fg=T.FG2)

    def _save_setting(self, key: str, value):
        self._cfg[key] = value
        sn.save_config(self._cfg)

    def _save_interval(self):
        try:
            minutes = int(self._interval_var.get())
            if minutes < 5:
                minutes = 5
            self._cfg["interval_minutes"] = minutes
            sn.save_config(self._cfg)
            messagebox.showinfo("Saved", f"Scan interval set to {minutes} minutes.\nRestart scanner to apply.")
        except ValueError:
            messagebox.showerror("Invalid", "Enter a valid number of minutes (minimum 5)")

    def _on_scan_now(self):
        self._scan_status.config(text="Scanning...", fg=T.FG2)

        def scan():
            issues = sn.scan_now_and_notify()
            self.after(0, self._show_results, issues)

        threading.Thread(target=scan, daemon=True).start()

    def _show_results(self, issues: list):
        self._scan_status.config(text=f"Done — {len(issues)} issue(s) found", fg=T.SUCCESS if not issues else T.WARNING)

        self._results_text.config(state="normal")
        self._results_text.delete("1.0", "end")

        if not issues:
            self._results_text.insert("end", "No issues found. Your system looks good!")
        else:
            for issue in issues:
                self._results_text.insert("end", f"[{issue['severity'].upper()}] {issue['title']}\n")
                self._results_text.insert("end", f"  {issue['message']}\n\n")

        self._results_text.config(state="disabled")

    def _update_scanner_status(self):
        if sn.is_scanner_running():
            self._scanner_status.config(text="Scanner running in background", fg=T.SUCCESS)
        elif self._enabled_var.get():
            self._scanner_status.config(text="Scanner not running", fg=T.WARNING)
        else:
            self._scanner_status.config(text="Scanner disabled", fg=T.FG2)

    def on_activate(self):
        self._update_scanner_status()
        if self._enabled_var.get() and not sn.is_scanner_running():
            sn.start_background_scanner()
            self._update_scanner_status()
