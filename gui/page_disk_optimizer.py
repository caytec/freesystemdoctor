"""Disk Optimizer page — Defragmentation, SSD TRIM, health monitoring."""

import threading
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import disk_optimizer as do


class DiskOptimizerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Disk Optimizer", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Defragmentation, TRIM optimization, and health check",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Drives section
        self._build_drives_section(body)

    def _build_drives_section(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))
        SectionLabel(card, "Drives").pack(anchor="w", padx=10, pady=8)

        # Frame for drive list
        list_frame = tk.Frame(card, bg=T.PANEL)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._drives_label = tk.Label(list_frame, text="Loading drives...",
                                      bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY)
        self._drives_label.pack(anchor="w", pady=8)

        # Action buttons frame
        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Scan Drives",
                     command=self._on_scan).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Defragment Selected",
                     command=self._on_defrag).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Run TRIM",
                     command=self._on_trim).pack(side="left", padx=0)

        # Progress bar
        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        # Output text
        self._output = tk.Text(card, height=8, bg=T.ACCENT, fg=T.FG,
                               font=("Courier", 9), wrap="word")
        self._output.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._output.config(state="disabled")

        # Load initial drives
        self._load_drives()

    def _load_drives(self):
        def load():
            try:
                drives = do.get_drives()
                text = "Available Drives:\n\n"
                for drive in drives:
                    text += f"  • {drive['letter']}: {drive['label']} ({drive['type']}) — {drive['size_gb']:.1f} GB\n"
                self._drives_label.config(text=text)
            except Exception as e:
                self._drives_label.config(text=f"Error loading drives: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _on_scan(self):
        self._output.config(state="normal")
        self._output.delete("1.0", "end")
        self._output.config(state="disabled")
        self._update_output("Scanning drives...")

    def _on_defrag(self):
        self._output.config(state="normal")
        self._output.delete("1.0", "end")
        self._output.config(state="disabled")
        self._update_output("Defragmentation started...\n")

        def defrag():
            try:
                drives = do.get_drives()
                for drive in drives:
                    if drive['type'] != 'SSD':
                        self._update_output(f"\nDefragmenting {drive['letter']}...\n")
                        for line in do.defrag_drive(drive['letter']):
                            self._update_output(line + "\n")
            except Exception as e:
                self._update_output(f"Error: {e}\n")

        threading.Thread(target=defrag, daemon=True).start()

    def _on_trim(self):
        self._output.config(state="normal")
        self._output.delete("1.0", "end")
        self._output.config(state="disabled")
        self._update_output("TRIM optimization started...\n")

        def trim():
            try:
                drives = do.get_drives()
                for drive in drives:
                    if drive['type'] == 'SSD':
                        self._update_output(f"\nTRIMming {drive['letter']}...\n")
                        for line in do.trim_drive(drive['letter']):
                            self._update_output(line + "\n")
            except Exception as e:
                self._update_output(f"Error: {e}\n")

        threading.Thread(target=trim, daemon=True).start()

    def _update_output(self, text):
        def update():
            try:
                self._output.config(state="normal")
                self._output.insert("end", text)
                self._output.see("end")
                self._output.config(state="disabled")
            except tk.TclError:
                pass

        self._app.after(0, update)

    def on_activate(self):
        self._load_drives()
