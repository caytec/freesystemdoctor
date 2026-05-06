"""Startup Manager tab."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import startup_manager


class StartupTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._entries: list[startup_manager.StartupEntry] = []
        self._build_ui()
        self.after(200, self._load)

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Startup Manager").pack(side="left", padx=8, pady=8)
        tk.Label(hdr, text="Click a row to toggle Enabled/Disabled",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=10)

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Refresh", command=self._load).pack(side="left", padx=(0, 8))
        self._toggle_btn = ActionButton(btn_row, "Toggle Selected", command=self._toggle_selected)
        self._toggle_btn.pack(side="left")

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        cols = ("Source", "Command", "Impact", "Status")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0", text="Name", anchor="w")
        self._tv.heading("Source", text="Source", anchor="w")
        self._tv.heading("Command", text="Command", anchor="w")
        self._tv.heading("Impact", text="Impact", anchor="w")
        self._tv.heading("Status", text="Status", anchor="w")
        self._tv.column("#0", width=180)
        self._tv.column("Source", width=110)
        self._tv.column("Command", width=290)
        self._tv.column("Impact", width=70)
        self._tv.column("Status", width=75)

        self._tv.tag_configure("enabled",  foreground=T.SUCCESS)
        self._tv.tag_configure("disabled", foreground=T.DANGER)
        self._tv.tag_configure("high",    foreground=T.DANGER)
        self._tv.tag_configure("medium",  foreground=T.WARNING)
        self._tv.tag_configure("low",     foreground=T.SUCCESS)

        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _load(self):
        self._status.set("Loading startup entries...")
        threading.Thread(target=self._do_load, daemon=True).start()

    def _do_load(self):
        entries = startup_manager.get_startup_entries_with_impact()
        self.after(0, self._show_entries, entries)

    def _show_entries(self, entries):
        self._entries = entries
        for item in self._tv.get_children():
            self._tv.delete(item)
        for i, e in enumerate(entries):
            status_tag = "enabled" if e.enabled else "disabled"
            impact_tag = e.impact.lower() if e.impact in ("High", "Medium", "Low") else "medium"
            status = "Enabled" if e.enabled else "Disabled"
            self._tv.insert("", "end", iid=str(i), text=e.name,
                            values=(e.source, e.command[:60], e.impact, status),
                            tags=(status_tag, impact_tag))
        high = sum(1 for e in entries if e.impact == "High")
        self._status.set(f"Found {len(entries)} startup entries — {high} high impact.")

    def _toggle_selected(self):
        sel = self._tv.selection()
        if not sel:
            messagebox.showinfo("Select entry", "Select a startup entry first.")
            return
        changed = 0
        for iid in sel:
            idx = int(iid)
            e = self._entries[idx]
            ok = startup_manager.toggle_entry(e)
            if ok:
                changed += 1
                status_tag = "enabled" if e.enabled else "disabled"
                impact_tag = e.impact.lower() if e.impact in ("High", "Medium", "Low") else "medium"
                status = "Enabled" if e.enabled else "Disabled"
                self._tv.item(iid, values=(e.source, e.command[:60], e.impact, status),
                              tags=(status_tag, impact_tag))
        self._status.set(f"Toggled {changed} entries.")
