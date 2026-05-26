"""Secure Drive Wipe page — overwrite free space or entire drives."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import drive_wipe as dw


class DriveWipePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._drives = []
        self._running = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Secure Drive Wipe", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Overwrite free space to prevent data recovery",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        warn = Card(body)
        warn.pack(fill="x", pady=(0, 12))
        tk.Label(warn, text="WARNING: Wiping free space is irreversible. Do NOT wipe a drive containing your OS unless you intend to reinstall Windows.",
                 bg=T.PANEL, fg=T.DANGER, font=T.FONT_SMALL, wraplength=650, justify="left"
                 ).pack(anchor="w", padx=10, pady=8)

        drives_card = Card(body)
        drives_card.pack(fill="x", pady=(0, 12))
        SectionLabel(drives_card, "Select Drive").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(drives_card, bg=T.PANEL)
        tree_frame.pack(fill="x", padx=10, pady=(0, 8))
        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("total", "free", "pct"), height=5)
        self._tree.column("#0", width=100)
        self._tree.column("total", width=100)
        self._tree.column("free", width=100)
        self._tree.column("pct", width=80)
        self._tree.heading("#0", text="Drive")
        self._tree.heading("total", text="Total")
        self._tree.heading("free", text="Free")
        self._tree.heading("pct", text="Used %")
        self._tree.pack(fill="x")

        options_card = Card(body)
        options_card.pack(fill="x", pady=(0, 12))
        SectionLabel(options_card, "Wipe Method").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(options_card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(row, text="Method:", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._method_var = tk.StringVar(value="DoD 3-pass")
        methods = list(dw.WIPE_METHODS.keys()) + ["Windows cipher /w (recommended)"]
        ttk.Combobox(row, textvariable=self._method_var, values=methods,
                     state="readonly", width=30).pack(side="left", padx=8)

        action_card = Card(body)
        action_card.pack(fill="both", expand=True)
        SectionLabel(action_card, "Progress").pack(anchor="w", padx=10, pady=8)

        self._progress = ProgressBar(action_card)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        self._status_label = tk.Label(action_card, text="Select a drive and click Start Wipe",
                                      bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY)
        self._status_label.pack(anchor="w", padx=10, pady=(0, 8))

        btn_row = tk.Frame(action_card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row, text="Start Wipe Free Space", danger=True,
                     command=self._on_start).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Refresh Drives",
                     command=self._load_drives).pack(side="left")

    def _load_drives(self):
        self._drives = dw.get_drives()
        self._tree.delete(*self._tree.get_children())
        for d in self._drives:
            self._tree.insert("", "end", text=d["mountpoint"],
                              values=(d["total_str"], d["free_str"], f"{d['percent_used']:.0f}%"))

    def _on_start(self):
        if self._running:
            messagebox.showwarning("Running", "Wipe already in progress")
            return
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Drive", "Select a drive first")
            return
        mountpoint = self._tree.item(sel[0], "text")
        method = self._method_var.get()

        if not messagebox.askyesno("Confirm Wipe",
                f"Wipe free space on {mountpoint} using {method}?\n\nThis cannot be undone."):
            return

        self._running = True
        self._progress.set_value(0)

        def run():
            def cb(pct, msg):
                self.after(0, lambda: self._progress.set_value(pct))
                self.after(0, lambda: self._status_label.config(text=msg))

            if "cipher" in method:
                drive_letter = mountpoint.rstrip("\\").rstrip("/")
                result = dw.wipe_drive_windows(drive_letter, progress_cb=cb)
            else:
                result = dw.wipe_free_space(mountpoint, method=method, progress_cb=cb)

            self._running = False
            if result.get("error"):
                self.after(0, lambda: messagebox.showerror("Error", result["error"]))
            else:
                self.after(0, lambda: messagebox.showinfo("Done",
                    f"Wipe complete.\n{dw._fmt_bytes(result.get('bytes_wiped', 0))} written."))

        threading.Thread(target=run, daemon=True).start()

    def on_activate(self):
        if not self._drives:
            self._load_drives()
