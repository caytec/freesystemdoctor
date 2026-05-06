"""Smart Defrag page — optimize SSD/HDD with intelligent scheduling."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import smart_defrag as sd


class SmartDefragPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._optimizing = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Smart Defragmentation", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Optimize SSD/HDD with intelligent scheduling",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Drives list
        self._build_drives_card(body)

        # Progress
        self._build_progress_card(body)

        # Actions
        ActionButton(body, text="Optimize All Drives",
                     command=self._on_optimize_all).pack(anchor="w", pady=(0, 12))

    def _build_drives_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Drives").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("fstype", "free", "used"), height=6)
        self._tree.column("#0", width=120)
        self._tree.column("fstype", width=80)
        self._tree.column("free", width=100)
        self._tree.column("used", width=100)
        self._tree.heading("#0", text="Drive")
        self._tree.heading("fstype", text="Type")
        self._tree.heading("free", text="Free")
        self._tree.heading("used", text="Used")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        self._load_drives()

    def _build_progress_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Optimization Progress").pack(anchor="w", padx=10, pady=8)

        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=10, pady=(0, 4))

        self._progress_label = tk.Label(card, text="Ready", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._progress_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _load_drives(self):
        """Load drives in background."""
        def load():
            drives = sd.get_drives()
            self.after(0, self._display_drives, drives)

        threading.Thread(target=load, daemon=True).start()

    def _display_drives(self, drives):
        """Display drives in tree."""
        self._tree.delete(*self._tree.get_children())

        for drive in drives:
            dtype = "SSD" if drive["is_ssd"] else "HDD"
            self._tree.insert("", "end", text=drive["device"],
                             values=(dtype, drive["free_str"], drive["used_str"]))

    def _on_optimize_all(self):
        if self._optimizing:
            return

        if not messagebox.askyesno("Optimize Drives",
                "This will optimize all drives. Continue?"):
            return

        self._optimizing = True

        def optimize():
            def progress_cb(pct, status):
                self.after(0, lambda: self._update_progress(pct, status))

            results = sd.optimize_all_drives(progress_cb)
            self.after(0, lambda: self._on_optimize_complete(results))

        threading.Thread(target=optimize, daemon=True).start()

    def _update_progress(self, pct, status):
        """Update progress display."""
        self._progress.set_value(pct)
        self._progress_label.config(text=status)

    def _on_optimize_complete(self, results):
        """Handle optimization completion."""
        self._optimizing = False
        success_count = sum(1 for r in results if r.get("success"))
        messagebox.showinfo("Optimization Complete",
                          f"Optimized {success_count}/{len(results)} drive(s)")
        self._load_drives()

    def on_activate(self):
        self._load_drives()
