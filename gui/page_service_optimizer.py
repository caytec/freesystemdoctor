"""Service Optimizer page — apply service profiles."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import service_optimizer as so


class ServiceOptimizerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._working = False
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Service Optimizer", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Apply preset profiles to optimize Windows services",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Profile picker card
        card = Card(body)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Service Profile").pack(anchor="w", padx=12, pady=8)

        notes = {
            "Default": "Windows defaults — safe baseline",
            "Optimal": "Disable telemetry & rarely used services",
            "Gaming":  "Maximum performance — search/superfetch off",
            "Bare":    "Minimal services — power users only",
        }

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=12, pady=4)

        self._profile_var = tk.StringVar(value="Optimal")
        for prof in ["Default", "Optimal", "Gaming", "Bare"]:
            rb = tk.Radiobutton(row, text=prof, value=prof,
                                 variable=self._profile_var,
                                 bg=T.PANEL, fg=T.FG,
                                 selectcolor=T.ACCENT,
                                 activebackground=T.PANEL,
                                 activeforeground=T.HIGHLIGHT,
                                 font=T.FONT_BOLD,
                                 command=self._on_profile_change)
            rb.pack(side="left", padx=(0, 16))

        self._note_lbl = tk.Label(card, text=notes["Optimal"],
                                   bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                   anchor="w")
        self._note_lbl.pack(fill="x", padx=12, pady=(4, 12))
        self._notes = notes

        # Action row
        action_row = tk.Frame(card, bg=T.PANEL)
        action_row.pack(fill="x", padx=12, pady=(0, 12))

        ActionButton(action_row, text="Apply Profile",
                     command=self._on_apply, width=140).pack(side="left", padx=(0, 8))
        ActionButton(action_row, text="↶ Restore Backup",
                     command=self._on_restore, width=140,
                     secondary=True).pack(side="left", padx=(0, 8))

        self._status_lbl = tk.Label(action_row, text="",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._status_lbl.pack(side="left", padx=12)

        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=12, pady=(0, 12))

        # Service list card
        list_card = Card(body)
        list_card.pack(fill="both", expand=True)
        SectionLabel(list_card, "Managed Services").pack(anchor="w", padx=12, pady=8)

        cols = ("name", "state")
        self._tv = ttk.Treeview(list_card, columns=cols, show="headings", height=12)
        self._tv.heading("name", text="Service Name")
        self._tv.heading("state", text="Start Type")
        self._tv.column("name", width=320, anchor="w")
        self._tv.column("state", width=140, anchor="w")
        self._tv.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        bot = tk.Frame(list_card, bg=T.PANEL)
        bot.pack(fill="x", padx=12, pady=(0, 12))
        ActionButton(bot, text="↻ Refresh", command=self._refresh,
                      secondary=True, width=100).pack(side="left")

    def _on_profile_change(self):
        self._note_lbl.config(text=self._notes.get(self._profile_var.get(), ""))

    def _on_apply(self):
        if self._working:
            return
        prof = self._profile_var.get()
        if not messagebox.askyesno("Confirm",
                                    f"Apply '{prof}' profile?\n\n"
                                    f"A backup will be created automatically.\n"
                                    f"You can restore at any time."):
            return

        self._working = True
        self._status_lbl.config(text="Working…", fg=T.FG2)
        self._progress.set(0)

        def work():
            def progress(i, total, name):
                pct = (i + 1) / total * 100
                self.after(0, lambda: self._progress.set(pct))
                self.after(0, lambda: self._status_lbl.config(text=f"  {name}…"))

            result = so.apply_profile(prof, progress=progress)
            self.after(0, lambda: self._on_done(prof, result))

        threading.Thread(target=work, daemon=True).start()

    def _on_done(self, profile, result):
        self._working = False
        self._progress.set(100)
        ok = len(result.get("ok", []))
        fail = len(result.get("fail", []))
        self._status_lbl.config(
            text=f"  '{profile}' applied — {ok} ok, {fail} failed",
            fg=T.SUCCESS if not fail else T.WARNING)
        self._refresh()

    def _on_restore(self):
        if not so.has_backup():
            messagebox.showinfo("Restore", "No backup snapshot available.")
            return
        if not messagebox.askyesno("Confirm",
                                    "Restore service settings from backup?"):
            return

        self._status_lbl.config(text="Restoring…", fg=T.FG2)

        def work():
            r = so.restore_backup()
            ok = len(r.get("ok", []))
            fail = len(r.get("fail", []))
            self.after(0, lambda: self._status_lbl.config(
                text=f"  Restored {ok} services ({fail} failed)",
                fg=T.SUCCESS if not fail else T.WARNING))
            self.after(0, self._refresh)

        threading.Thread(target=work, daemon=True).start()

    def _refresh(self):
        for item in self._tv.get_children():
            self._tv.delete(item)

        def fetch():
            services = so.list_managed_services()
            self.after(0, lambda: self._populate(services))

        threading.Thread(target=fetch, daemon=True).start()

    def _populate(self, services):
        for s in services:
            tag = "ok" if s["start_type"] in ("manual", "disabled", "auto") else "warn"
            self._tv.insert("", "end", values=(s["name"], s["start_type"]),
                             tags=(tag,))
        self._tv.tag_configure("ok", foreground=T.FG)
        self._tv.tag_configure("warn", foreground=T.WARNING)

    def on_activate(self):
        self._refresh()
