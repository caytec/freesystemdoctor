"""Scheduled Cleaner page — Automatic background cleaning tasks."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import scheduled_cleaner as sc


class ScheduledCleanerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Scheduled Cleaner", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Automatic background cleaning and maintenance",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Daily cleaning card
        self._build_schedule_card(body, "Daily Cleanup", "daily", "Runs daily at 2 AM")

        # Weekly deep clean card
        self._build_schedule_card(body, "Weekly Deep Clean", "weekly", "Runs every Sunday at 3 AM")

        # Manual cleanup card
        self._build_manual_card(body)

    def _build_schedule_card(self, parent, title, schedule_type, description):
        card = Card(parent)
        card.pack(fill="both", expand=False, pady=(0, 12))
        SectionLabel(card, title).pack(anchor="w", padx=10, pady=8)

        desc = tk.Label(card, text=description, bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        desc.pack(anchor="w", padx=10, pady=(0, 8))

        # Toggle
        toggle_frame = tk.Frame(card, bg=T.PANEL)
        toggle_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(toggle_frame, text="Enable", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")

        var = tk.BooleanVar(value=False)
        toggle = ToggleSwitch(toggle_frame, variable=var,
                             command=lambda: self._on_schedule_toggle(schedule_type, var))
        toggle.pack(side="right")

        # Status label
        status = tk.Label(card, text="Disabled", bg=T.PANEL, fg=T.FG2,
                         font=T.FONT_SMALL)
        status.pack(anchor="w", padx=10, pady=(0, 8))

        setattr(self, f"_{schedule_type}_toggle", toggle)
        setattr(self, f"_{schedule_type}_var", var)
        setattr(self, f"_{schedule_type}_status", status)

    def _build_manual_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=False)
        SectionLabel(card, "Run Cleanup Now").pack(anchor="w", padx=10, pady=8)

        desc = tk.Label(card, text="Execute cleaning immediately with all enabled modules",
                       bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, wraplength=400)
        desc.pack(anchor="w", padx=10, pady=(0, 8))

        ActionButton(card, text="Start Cleanup",
                     command=self._on_run_now).pack(anchor="w", padx=10, pady=(0, 8))

    # frequency, time, and modules for each schedule card
    _SCHEDULES = {
        "daily":  ("daily",  "02:00", ["disk_cleaner", "registry_cleaner"]),
        "weekly": ("weekly", "03:00", ["disk_cleaner", "registry_cleaner",
                                       "empty_folder_finder"]),
    }

    def _on_schedule_toggle(self, schedule_type, var):
        status_label = getattr(self, f"_{schedule_type}_status")
        if var.get():
            freq, time_str, modules = self._SCHEDULES[schedule_type]

            def enable():
                try:
                    ok = sc.set_schedule(True, freq, time_str, modules)
                    if ok:
                        self.after(0, lambda: status_label.config(
                            text="✓ Enabled", fg=T.SUCCESS))
                    else:
                        raise RuntimeError(
                            "Could not create the scheduled task (admin rights required).")
                except Exception as e:
                    self.after(0, lambda e=e: (
                        var.set(False),
                        status_label.config(text="Disabled", fg=T.FG2),
                        messagebox.showerror("Error", f"Failed to enable: {e}")))

            threading.Thread(target=enable, daemon=True).start()
        else:
            def disable():
                try:
                    sc.delete_schedule()
                except Exception:
                    pass
                self.after(0, lambda: status_label.config(text="Disabled", fg=T.FG2))

            threading.Thread(target=disable, daemon=True).start()

    def _on_run_now(self):
        def run():
            try:
                summary = sc.run_auto_clean(
                    modules=["disk_cleaner", "registry_cleaner"])
                fixed = summary.get("issues_fixed", 0)
                errors = summary.get("errors", [])
                if errors:
                    self.after(0, lambda: messagebox.showwarning(
                        "Completed with warnings",
                        f"Cleaned {fixed} item(s).\n\nIssues:\n" + "\n".join(errors[:5])))
                else:
                    self.after(0, lambda: messagebox.showinfo(
                        "Success", f"Cleanup completed — {fixed} item(s) cleaned."))
            except Exception as e:
                self.after(0, lambda e=e: messagebox.showerror(
                    "Error", f"Cleanup failed: {e}"))

        threading.Thread(target=run, daemon=True).start()

    def on_activate(self):
        pass
