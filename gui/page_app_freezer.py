"""App Freezer page — suspend and resume background processes."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import app_freezer as af


class AppFreezerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._procs = []
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="App Freezer", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Pause background processes to reclaim CPU and RAM",
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

        tk.Label(card, text="⚠  Freezing critical system processes may destabilize your system.",
                 bg=T.PANEL, fg=T.WARNING, font=T.FONT_SMALL, wraplength=600,
                 justify="left").pack(anchor="w", padx=10, pady=8)

    def _build_controls(self, parent):
        ctrl = tk.Frame(parent, bg=T.BG)
        ctrl.pack(fill="x", pady=(0, 12))

        ActionButton(ctrl, text="Refresh",
                     command=self._on_refresh).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Freeze Selected",
                     command=self._on_freeze).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Unfreeze Selected",
                     command=self._on_unfreeze).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Unfreeze All", danger=True,
                     command=self._on_unfreeze_all).pack(side="left")

    def _build_process_list(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Background Processes").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("pid", "cpu", "ram", "status"), height=14)
        self._tree.column("#0", width=220)
        self._tree.column("pid", width=70)
        self._tree.column("cpu", width=70)
        self._tree.column("ram", width=90)
        self._tree.column("status", width=90)
        self._tree.heading("#0", text="Process Name")
        self._tree.heading("pid", text="PID")
        self._tree.heading("cpu", text="CPU%")
        self._tree.heading("ram", text="RAM (MB)")
        self._tree.heading("status", text="Status")

        self._tree.tag_configure("frozen", foreground=T.WARNING)
        self._tree.tag_configure("running", foreground=T.SUCCESS)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=0)
        sb.pack(side="right", fill="y", pady=0)

        self._summary = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._summary.pack(anchor="w", padx=10, pady=(0, 8))

    def _load(self):
        """Load process list in background thread."""
        def load():
            procs = af.get_background_processes()
            self.after(0, self._populate, procs)

        threading.Thread(target=load, daemon=True).start()

    def _populate(self, procs):
        """Populate treeview with process data."""
        self._procs = procs
        self._tree.delete(*self._tree.get_children())

        for p in procs:
            tag = "frozen" if p["status"] == "Frozen" else "running"
            self._tree.insert("", "end", iid=str(p["pid"]), text=p["name"],
                             values=(p["pid"], f"{p['cpu_percent']:.1f}%", p["ram_mb"], p["status"]),
                             tags=(tag,))

        frozen_count = sum(1 for p in procs if p["status"] == "Frozen")
        self._summary.config(text=f"Loaded {len(procs)} process(es) — {frozen_count} frozen")

    def _on_refresh(self):
        self._load()

    def _on_freeze(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select processes to freeze")
            return

        pids = [int(iid) for iid in sel]

        def freeze():
            success = 0
            for pid in pids:
                if af.freeze_process(pid):
                    success += 1
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Froze {success}/{len(pids)} process(es)"))
            self._load()

        threading.Thread(target=freeze, daemon=True).start()

    def _on_unfreeze(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select processes to unfreeze")
            return

        pids = [int(iid) for iid in sel]

        def unfreeze():
            success = 0
            for pid in pids:
                if af.unfreeze_process(pid):
                    success += 1
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Unfroze {success}/{len(pids)} process(es)"))
            self._load()

        threading.Thread(target=unfreeze, daemon=True).start()

    def _on_unfreeze_all(self):
        if not messagebox.askyesno("Unfreeze All",
                "Resume all frozen processes?\n\nContinue?"):
            return

        def unfreeze():
            unfrozen, errors = af.unfreeze_all()
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Unfroze {unfrozen} process(es)" + (f" ({errors} error(s))" if errors else "")))
            self._load()

        threading.Thread(target=unfreeze, daemon=True).start()

    def on_activate(self):
        if not self._procs:
            self._load()
