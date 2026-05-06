"""Scheduled Task Manager tab."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import task_scheduler as ts


class TasksTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._tasks: list[ts.ScheduledTask] = []
        self._build_ui()
        self.after(300, self._load)

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        SectionLabel(hdr, "Scheduled Task Manager").pack(side="left", padx=8, pady=8)
        tk.Label(hdr,
                 text="Highlighted rows can be safely disabled for privacy/performance",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=10)

        filter_row = tk.Frame(self, bg=T.BG)
        filter_row.pack(fill="x", padx=16, pady=4)
        tk.Label(filter_row, text="Filter:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(filter_row, textvariable=self._filter_var, width=26,
                 bg=T.PANEL, fg=T.FG, insertbackground=T.FG,
                 font=T.FONT_BODY).pack(side="left", padx=6)
        self._safe_only = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_row, text="Show recommended-to-disable only",
                       variable=self._safe_only, bg=T.BG, fg=T.FG,
                       selectcolor=T.ACCENT, activebackground=T.BG,
                       command=self._apply_filter).pack(side="left", padx=8)
        ActionButton(filter_row, "Refresh", command=self._load).pack(side="right")

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Enable Selected", command=self._enable_selected).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Disable Selected", command=self._disable_selected).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Disable All Recommended", command=self._disable_recommended).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Run Now", command=self._run_now).pack(side="left")

        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=2)

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Status", "Next Run", "Last Run", "Note")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",      text="Task Name",  anchor="w")
        self._tv.heading("Status",  text="Status",     anchor="w")
        self._tv.heading("Next Run",text="Next Run",   anchor="w")
        self._tv.heading("Last Run",text="Last Run",   anchor="w")
        self._tv.heading("Note",    text="Note",       anchor="w")
        self._tv.column("#0",       width=260)
        self._tv.column("Status",   width=75)
        self._tv.column("Next Run", width=140)
        self._tv.column("Last Run", width=140)
        self._tv.column("Note",     width=300)
        self._tv.tag_configure("safe",     foreground=T.WARNING)
        self._tv.tag_configure("enabled",  foreground=T.FG)
        self._tv.tag_configure("disabled", foreground=T.FG2)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _load(self):
        self._progress.indeterminate(True)
        self._status.set("Loading scheduled tasks (this may take a moment)...")
        threading.Thread(target=self._do_load, daemon=True).start()

    def _do_load(self):
        tasks = ts.list_tasks()
        self.after(0, self._show, tasks)

    def _show(self, tasks):
        self._progress.indeterminate(False)
        self._tasks = tasks
        self._apply_filter()
        self._status.set(f"Loaded {len(tasks)} scheduled tasks.")

    def _apply_filter(self):
        q = self._filter_var.get().lower()
        safe_only = self._safe_only.get()
        for item in self._tv.get_children():
            self._tv.delete(item)
        for task in self._tasks:
            if q and q not in task.name.lower() and q not in task.path.lower():
                continue
            if safe_only and not task.safe_to_disable:
                continue
            tag = "safe" if task.safe_to_disable else \
                  "disabled" if task.status == "Disabled" else "enabled"
            self._tv.insert("", "end", iid=task.path, text=task.name,
                            values=(task.status, task.next_run[:16],
                                    task.last_run[:16], task.note),
                            tags=(tag,))

    def _selected_paths(self) -> list[str]:
        return list(self._tv.selection())

    def _enable_selected(self):
        for path in self._selected_paths():
            ts.enable_task(path)
        self._load()
        self._status.set("Selected tasks enabled.")

    def _disable_selected(self):
        paths = self._selected_paths()
        if not paths:
            return
        if not messagebox.askyesno("Disable Tasks",
                                   f"Disable {len(paths)} selected task(s)?"):
            return
        for path in paths:
            ts.disable_task(path)
        self._load()
        self._status.set(f"Disabled {len(paths)} tasks.")

    def _disable_recommended(self):
        recommended = ts.get_safe_to_disable()
        if not messagebox.askyesno("Disable Recommended Tasks",
                                   f"Disable {len(recommended)} telemetry/tracking tasks?"):
            return
        def run():
            done = 0
            for path in recommended:
                if ts.disable_task(path):
                    done += 1
            self.after(0, lambda: self._load())
            self.after(0, self._status.set, f"Disabled {done} recommended tasks.")
        threading.Thread(target=run, daemon=True).start()

    def _run_now(self):
        for path in self._selected_paths():
            ts.run_task_now(path)
        self._status.set("Task(s) triggered.")
