"""Disk Analyzer page — visual folder size breakdown."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import disk_analyzer as da


class DiskAnalyzerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._current_analysis = None
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Disk Analyzer", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Visualize disk usage by folder",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Top controls
        ctrl = tk.Frame(body, bg=T.BG)
        ctrl.pack(fill="x", pady=(0, 8))

        tk.Label(ctrl, text="Analyze:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")

        self._drive_var = tk.StringVar()
        self._drive_combo = ttk.Combobox(ctrl, textvariable=self._drive_var,
                                         state="readonly", width=20)
        self._drive_combo.pack(side="left", padx=8)
        self._drive_combo.bind("<<ComboboxSelected>>", lambda e: self._on_drive_select())

        ActionButton(ctrl, text="Analyze", command=self._on_analyze).pack(side="left", padx=(0, 6))

        self._progress = ProgressBar(body)
        self._progress.pack(fill="x", pady=(0, 8))

        # Main card with tree
        card = Card(body)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Folder Breakdown").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("size", "percent"), height=15)
        self._tree.column("#0", width=400)
        self._tree.column("size", width=120)
        self._tree.column("percent", width=80)
        self._tree.heading("#0", text="Folder")
        self._tree.heading("size", text="Size")
        self._tree.heading("percent", text="% of Total")
        self._tree.pack(fill="both", expand=True)

        # Summary
        self._summary = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                font=T.FONT_SMALL)
        self._summary.pack(anchor="w", padx=10, pady=(0, 8))

        self._load_drives()

    def _load_drives(self):
        def load():
            try:
                analyses = da.analyze_all_drives()
                drive_labels = [a["drive"] for a in analyses]
                self._drive_combo.config(values=drive_labels)
                if drive_labels:
                    self._drive_var.set(drive_labels[0])
                    self._on_drive_select()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load drives: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _on_drive_select(self):
        drive = self._drive_var.get()
        if drive:
            self._on_analyze(drive)

    def _on_analyze(self, drive=None):
        target_drive = drive or self._drive_var.get()
        if not target_drive:
            messagebox.showwarning("No Drive", "Select a drive to analyze")
            return

        self._progress.set_value(0)
        self._tree.delete(*self._tree.get_children())

        def analyze():
            try:
                analysis = da.analyze_folder(target_drive)
                self._current_analysis = analysis

                self._tree.delete(*self._tree.get_children())
                for sub in analysis["subfolders"][:50]:  # Top 50
                    self._tree.insert("", "end", text=sub["name"],
                                     values=(sub["size_str"], f"{sub['percent']:.1f}%"))

                total = analysis["total_size_str"]
                count = len(analysis["subfolders"])
                self._summary.config(text=f"Total: {total} | Folders: {count}")
                self._progress.set_value(100)

            except Exception as e:
                messagebox.showerror("Error", f"Analysis failed: {e}")
                self._progress.set_value(0)

        threading.Thread(target=analyze, daemon=True).start()

    def on_activate(self):
        pass
