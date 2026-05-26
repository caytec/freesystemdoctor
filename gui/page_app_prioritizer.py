"""App Priority Manager page — adjust CPU scheduling priority for running processes."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import app_prioritizer as ap


class AppPrioritizerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._procs = []
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="App Priority", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Adjust CPU scheduling priority for running applications",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Warning card
        self._build_warning_card(body)

        # Controls
        self._build_controls(body)

        # Process list
        self._build_process_list(body)

    def _build_warning_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False, pady=(0, 12))

        SectionLabel(card, "Priority Management").pack(anchor="w", padx=10, pady=8)

        tk.Label(card, text="⚠  Boosting to HIGH may cause system instability. ABOVE_NORMAL is safe for most workloads.",
                 bg=T.PANEL, fg=T.WARNING, font=T.FONT_SMALL, wraplength=600,
                 justify="left").pack(anchor="w", padx=10, pady=(0, 8))

    def _build_controls(self, parent):
        ctrl = tk.Frame(parent, bg=T.BG)
        ctrl.pack(fill="x", pady=(0, 12))

        ActionButton(ctrl, text="Refresh",
                     command=self._on_refresh).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Boost Selected",
                     command=self._on_boost).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Set Normal",
                     command=self._on_normal).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Set High",
                     command=self._on_high).pack(side="left")

    def _build_process_list(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Running Processes").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("pid", "cpu", "ram", "priority"), height=14)
        self._tree.column("#0", width=220)
        self._tree.column("pid", width=70)
        self._tree.column("cpu", width=70)
        self._tree.column("ram", width=70)
        self._tree.column("priority", width=120)
        self._tree.heading("#0", text="Process Name")
        self._tree.heading("pid", text="PID")
        self._tree.heading("cpu", text="CPU%")
        self._tree.heading("ram", text="RAM%")
        self._tree.heading("priority", text="Priority")

        # Color tags for priority levels
        self._tree.tag_configure("high", foreground=T.WARNING)
        self._tree.tag_configure("above_normal", foreground=T.SUCCESS)
        self._tree.tag_configure("realtime", foreground=T.DANGER)
        self._tree.tag_configure("idle", foreground=T.FG2)
        self._tree.tag_configure("normal", foreground=T.FG)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=0)
        sb.pack(side="right", fill="y", pady=0)

        self._summary = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._summary.pack(anchor="w", padx=10, pady=(0, 8))

    def _load(self):
        """Load process list in background thread."""
        def load():
            procs = ap.get_running_processes()
            self.after(0, self._populate, procs)

        threading.Thread(target=load, daemon=True).start()

    def _populate(self, procs):
        """Populate treeview with process data."""
        self._procs = procs
        self._tree.delete(*self._tree.get_children())

        for p in procs:
            priority = p["priority"].lower()
            # Determine tag
            tag = priority if priority in ("high", "above_normal", "realtime", "idle", "normal") else "normal"

            self._tree.insert("", "end", iid=str(p["pid"]), text=p["name"],
                             values=(p["pid"], f"{p['cpu_percent']:.1f}%", f"{p['memory_percent']:.1f}%", p["priority"]),
                             tags=(tag,))

        self._summary.config(text=f"Loaded {len(procs)} process(es)")

    def _on_refresh(self):
        self._load()

    def _on_boost(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select processes to boost")
            return

        pids = [int(iid) for iid in sel]

        def boost():
            success = 0
            for pid in pids:
                if ap.boost_process(pid):
                    success += 1
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Boosted {success}/{len(pids)} process(es) to ABOVE_NORMAL"))
            self._load()

        threading.Thread(target=boost, daemon=True).start()

    def _on_normal(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select processes to reset")
            return

        pids = [int(iid) for iid in sel]

        def reset():
            success = 0
            for pid in pids:
                if ap.set_normal_priority(pid):
                    success += 1
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Reset {success}/{len(pids)} process(es) to NORMAL"))
            self._load()

        threading.Thread(target=reset, daemon=True).start()

    def _on_high(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select processes to set HIGH")
            return

        if not messagebox.askyesno("Set High Priority",
                "Set HIGH priority? This may cause system instability.\n\nContinue?"):
            return

        pids = [int(iid) for iid in sel]

        def set_high():
            success = 0
            for pid in pids:
                if ap.set_high_priority(pid):
                    success += 1
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Set {success}/{len(pids)} process(es) to HIGH priority"))
            self._load()

        threading.Thread(target=set_high, daemon=True).start()

    def on_activate(self):
        if not self._procs:
            self._load()
