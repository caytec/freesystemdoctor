"""Service Manager tab."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import service_manager as sm


_SAFETY_COLORS = {
    "Safe":    "#4caf50",
    "Caution": "#ff9800",
    "System":  "#f44336",
    "Unknown": "#808080",
}


class ServicesTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._services: list[sm.WinService] = []
        self._build_ui()
        self.after(300, self._load)

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        SectionLabel(hdr, "Windows Service Manager").pack(side="left", padx=8, pady=8)
        tk.Label(hdr, text="Green=Safe to disable  |  Orange=Use caution  |  Red=System/Do not disable",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=10)

        filter_row = tk.Frame(self, bg=T.BG)
        filter_row.pack(fill="x", padx=16, pady=4)
        tk.Label(filter_row, text="Filter:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(filter_row, textvariable=self._filter_var, width=24,
                 bg=T.PANEL, fg=T.FG, insertbackground=T.FG, font=T.FONT_BODY).pack(side="left", padx=6)
        self._show_safe_only = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_row, text="Show safe-to-disable only",
                       variable=self._show_safe_only, bg=T.BG, fg=T.FG,
                       selectcolor=T.ACCENT, activebackground=T.BG,
                       command=self._apply_filter).pack(side="left", padx=8)
        ActionButton(filter_row, "Refresh", command=self._load).pack(side="right")

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Start", command=self._start_selected).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Stop", command=self._stop_selected).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Set Auto", command=lambda: self._set_start("auto")).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Set Manual", command=lambda: self._set_start("manual")).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Disable", command=lambda: self._set_start("disabled"), danger=True).pack(side="left")

        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=2)

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Status", "Start", "Safety", "Note")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",     text="Service Name",   anchor="w")
        self._tv.heading("Status", text="Status",         anchor="w")
        self._tv.heading("Start",  text="Startup",        anchor="w")
        self._tv.heading("Safety", text="Safety",         anchor="w")
        self._tv.heading("Note",   text="Note",           anchor="w")
        self._tv.column("#0",     width=200)
        self._tv.column("Status", width=80)
        self._tv.column("Start",  width=80)
        self._tv.column("Safety", width=75)
        self._tv.column("Note",   width=350)
        self._tv.tag_configure("Safe",    foreground=T.SUCCESS)
        self._tv.tag_configure("Caution", foreground=T.WARNING)
        self._tv.tag_configure("System",  foreground=T.DANGER)
        self._tv.tag_configure("Unknown", foreground=T.FG2)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._tv.bind("<Double-1>", self._on_double_click)

        self._detail = tk.Label(self, text="", bg=T.BG, fg=T.FG2, font=T.FONT_SMALL,
                                anchor="w", wraplength=900)
        self._detail.pack(fill="x", padx=20, pady=(0, 8))

    def _load(self):
        self._progress.indeterminate(True)
        self._status.set("Loading services...")
        threading.Thread(target=self._do_load, daemon=True).start()

    def _do_load(self):
        def cb(n):
            if n % 20 == 0:
                self.after(0, self._status.set, f"Loading services... ({n})")
        services = sm.list_services(progress_cb=cb)
        self.after(0, self._show, services)

    def _show(self, services):
        self._progress.indeterminate(False)
        self._services = services
        self._apply_filter()
        self._status.set(f"Loaded {len(services)} services.")

    def _apply_filter(self):
        q = self._filter_var.get().lower()
        safe_only = self._show_safe_only.get()
        for item in self._tv.get_children():
            self._tv.delete(item)
        for svc in self._services:
            if q and q not in svc.name.lower() and q not in svc.display_name.lower():
                continue
            if safe_only and svc.safety != "Safe":
                continue
            self._tv.insert("", "end", iid=svc.name, text=svc.display_name or svc.name,
                            values=(svc.status, svc.start_type, svc.safety, svc.note),
                            tags=(svc.safety,))

    def _selected_names(self) -> list[str]:
        return list(self._tv.selection())

    def _start_selected(self):
        self._op_on_selected(sm.start_service, "start")

    def _stop_selected(self):
        names = self._selected_names()
        if not names:
            return
        if not messagebox.askyesno("Stop Services",
                                   f"Stop {len(names)} service(s)?"):
            return
        self._op_on_selected(sm.stop_service, "stop")

    def _set_start(self, mode):
        names = self._selected_names()
        if not names:
            messagebox.showinfo("Select", "Select at least one service.")
            return
        if mode == "disabled":
            if not messagebox.askyesno("Disable Services",
                                       f"Disable {len(names)} service(s) at startup?"):
                return
        def run():
            for n in names:
                sm.set_service_startup(n, mode)
            self.after(0, self._load)
        threading.Thread(target=run, daemon=True).start()
        self._status.set(f"Setting {mode} on {len(names)} service(s)...")

    def _op_on_selected(self, func, verb):
        names = self._selected_names()
        if not names:
            return
        def run():
            for n in names:
                func(n)
            self.after(0, self._load)
        threading.Thread(target=run, daemon=True).start()
        self._status.set(f"Attempting to {verb} {len(names)} service(s)...")

    def _on_double_click(self, event):
        iid = self._tv.identify_row(event.y)
        if iid:
            self._detail.config(text=f"Service: {iid}  —  {sm.get_service_detail(iid)[:200]}")
