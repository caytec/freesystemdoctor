"""Auto-Shutdown Scheduler page."""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton
from engine import auto_shutdown as ash


_ACTION_LABELS = {
    "shutdown":  ("⏻ Shutdown",   "Power off the computer"),
    "restart":   ("↻ Restart",    "Restart the computer"),
    "logoff":    ("⇤ Sign Out",   "Log off current user"),
    "sleep":     ("☾ Sleep",      "Put computer to sleep"),
    "hibernate": ("❄ Hibernate",  "Hibernate computer"),
}


class AutoShutdownPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._action_var = tk.StringVar(value="shutdown")
        self._mode_var   = tk.StringVar(value="in")
        self._build_ui()
        self._update_status()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⏻  Auto-Shutdown", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Schedule shutdown, restart, sleep or hibernate",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Action picker
        card = Card(body)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Action").pack(anchor="w", padx=12, pady=8)

        action_row = tk.Frame(card, bg=T.PANEL)
        action_row.pack(fill="x", padx=12, pady=4)
        for key, (label, _) in _ACTION_LABELS.items():
            tk.Radiobutton(action_row, text=label, value=key,
                            variable=self._action_var,
                            bg=T.PANEL, fg=T.FG,
                            selectcolor=T.ACCENT,
                            activebackground=T.PANEL,
                            activeforeground=T.HIGHLIGHT,
                            font=T.FONT_BOLD).pack(side="left", padx=(0, 12))

        # When picker
        when_card = Card(body)
        when_card.pack(fill="x", pady=(0, 12))
        SectionLabel(when_card, "When").pack(anchor="w", padx=12, pady=8)

        in_row = tk.Frame(when_card, bg=T.PANEL)
        in_row.pack(fill="x", padx=12, pady=4)
        tk.Radiobutton(in_row, text="In:", value="in",
                        variable=self._mode_var,
                        bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                        activebackground=T.PANEL,
                        font=T.FONT_BOLD).pack(side="left")
        self._mins = tk.Spinbox(in_row, from_=1, to=720, width=6,
                                  bg=T.ACCENT, fg=T.FG,
                                  font=T.FONT_BODY,
                                  insertbackground=T.FG)
        self._mins.pack(side="left", padx=8)
        self._mins.delete(0, tk.END)
        self._mins.insert(0, "60")
        tk.Label(in_row, text="minutes", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left")

        for q in [(15, "15 min"), (30, "30 min"), (60, "1 h"), (120, "2 h")]:
            ActionButton(in_row, text=q[1],
                          command=lambda m=q[0]: self._set_minutes(m),
                          width=70, secondary=True).pack(side="left", padx=4)

        at_row = tk.Frame(when_card, bg=T.PANEL)
        at_row.pack(fill="x", padx=12, pady=(8, 12))
        tk.Radiobutton(at_row, text="At:", value="at",
                        variable=self._mode_var,
                        bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                        activebackground=T.PANEL,
                        font=T.FONT_BOLD).pack(side="left")
        self._time_entry = tk.Entry(at_row, bg=T.ACCENT, fg=T.FG,
                                      font=T.FONT_BODY, width=10,
                                      insertbackground=T.FG)
        self._time_entry.pack(side="left", padx=8)
        self._time_entry.insert(0, datetime.now().replace(
            hour=23, minute=0).strftime("%H:%M"))
        tk.Label(at_row, text="HH:MM (today, or tomorrow if past)",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=8)

        # Action buttons
        btn_row = tk.Frame(body, bg=T.BG)
        btn_row.pack(fill="x", pady=(0, 12))
        ActionButton(btn_row, text="Schedule",
                      command=self._on_schedule, width=140).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, text="Cancel",
                      command=self._on_cancel, width=140,
                      secondary=True).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, text="Execute Now",
                      command=self._on_now, width=140,
                      danger=True).pack(side="left")

        # Status
        status_card = Card(body)
        status_card.pack(fill="both", expand=True)
        SectionLabel(status_card, "Status").pack(anchor="w", padx=12, pady=8)

        self._status_lbl = tk.Label(status_card, text="—",
                                      bg=T.PANEL, fg=T.FG,
                                      font=(T.FONT_FAMILY, 16, "bold"),
                                      anchor="w", padx=12, pady=8)
        self._status_lbl.pack(fill="x")

        self._countdown_lbl = tk.Label(status_card, text="",
                                         bg=T.PANEL, fg=T.HIGHLIGHT,
                                         font=(T.FONT_FAMILY, 28, "bold"),
                                         anchor="w", padx=12, pady=4)
        self._countdown_lbl.pack(fill="x")

    def _set_minutes(self, m):
        self._mode_var.set("in")
        self._mins.delete(0, tk.END)
        self._mins.insert(0, str(m))

    def _on_schedule(self):
        action = self._action_var.get()
        try:
            if self._mode_var.get() == "in":
                mins = float(self._mins.get())
                if mins <= 0:
                    raise ValueError("Must be > 0")
                ash.schedule_in(action, mins)
                self._status_lbl.config(text=f"Scheduled '{action}' in {mins:.0f} minutes",
                                         fg=T.SUCCESS)
            else:
                t = self._time_entry.get().strip()
                hh, mm = map(int, t.split(":"))
                target = datetime.now().replace(hour=hh, minute=mm,
                                                 second=0, microsecond=0)
                if target <= datetime.now():
                    target += timedelta(days=1)
                ash.schedule(action, target)
                self._status_lbl.config(
                    text=f"Scheduled '{action}' at {target.strftime('%H:%M')}",
                    fg=T.SUCCESS)
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return
        self._update_status()

    def _on_cancel(self):
        ash.cancel()
        self._status_lbl.config(text="Cancelled", fg=T.FG2)
        self._countdown_lbl.config(text="")

    def _on_now(self):
        action = self._action_var.get()
        if not messagebox.askyesno("Confirm",
                                    f"Execute '{action}' immediately?"):
            return
        ash.execute_now(action)

    def _update_status(self):
        state = ash.get_state()
        if state.get("active"):
            r = state.get("remaining_seconds", 0)
            h = r // 3600
            m = (r % 3600) // 60
            s = r % 60
            self._countdown_lbl.config(text=f"{h:02d}:{m:02d}:{s:02d}")
            self._status_lbl.config(
                text=f"Pending: {state.get('action')}", fg=T.WARNING)
        else:
            self._countdown_lbl.config(text="")
        self.after(1000, self._update_status)

    def on_activate(self):
        self._update_status()
