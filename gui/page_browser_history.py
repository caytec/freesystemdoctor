"""Browser History Manager page — clear history, cookies, cache across all browsers."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import browser_history as bh


class BrowserHistoryPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._items = []
        self._check_vars: dict[int, tk.BooleanVar] = {}
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Browser History Manager", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Clear history, cookies and cache from all browsers",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        ctrl = tk.Frame(body, bg=T.BG)
        ctrl.pack(fill="x", pady=(0, 12))
        ActionButton(ctrl, text="Scan Browsers", command=self._on_scan).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Select All", command=self._select_all).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Deselect All", command=self._deselect_all).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Clear Selected", danger=True,
                     command=self._on_clear).pack(side="left")

        summary_card = Card(body)
        summary_card.pack(fill="x", pady=(0, 12))
        SectionLabel(summary_card, "Browser Summary").pack(anchor="w", padx=10, pady=8)
        self._summary_frame = tk.Frame(summary_card, bg=T.PANEL)
        self._summary_frame.pack(fill="x", padx=10, pady=(0, 8))
        self._summary_label = tk.Label(self._summary_frame,
                                       text="Click 'Scan Browsers' to start",
                                       bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY)
        self._summary_label.pack(anchor="w")

        results_card = Card(body)
        results_card.pack(fill="both", expand=True)
        SectionLabel(results_card, "Cleanable Items").pack(anchor="w", padx=10, pady=8)

        self._progress = ProgressBar(results_card)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        tree_frame = tk.Frame(results_card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("browser", "profile", "size"), height=14)
        self._tree.column("#0", width=180)
        self._tree.column("browser", width=90)
        self._tree.column("profile", width=80)
        self._tree.column("size", width=90)
        self._tree.heading("#0", text="Item")
        self._tree.heading("browser", text="Browser")
        self._tree.heading("profile", text="Profile")
        self._tree.heading("size", text="Size")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._total_label = tk.Label(results_card, text="", bg=T.PANEL,
                                     fg=T.FG2, font=T.FONT_SMALL)
        self._total_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_scan(self):
        self._progress.set_value(0)
        self._tree.delete(*self._tree.get_children())
        self._summary_label.config(text="Scanning...")

        def scan():
            items = bh.scan_browser_data()
            self.after(0, self._populate, items)

        threading.Thread(target=scan, daemon=True).start()

    def _populate(self, items):
        self._items = items
        self._tree.delete(*self._tree.get_children())

        total_size = 0
        for i, item in enumerate(items):
            if item["size"] == 0:
                continue
            self._tree.insert("", "end", iid=str(i), text=item["item"],
                              values=(item["browser"], item["profile"], item["size_str"]))
            total_size += item["size"]

        self._progress.set_value(100)

        # Summary per browser
        summary = bh.get_browser_summary()
        parts = [f"{b}: {bh._fmt_bytes(v['total_size'])}" for b, v in summary.items() if v["total_size"] > 0]
        self._summary_label.config(text="  |  ".join(parts) if parts else "No browser data found")
        self._total_label.config(text=f"Total cleanable: {bh._fmt_bytes(total_size)}")

        # Select all by default
        self._select_all()

    def _select_all(self):
        for item in self._tree.get_children():
            self._tree.selection_add(item)

    def _deselect_all(self):
        self._tree.selection_remove(*self._tree.get_children())

    def _on_clear(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select items to clear")
            return

        indices = [int(iid) for iid in sel]
        selected_items = [self._items[i] for i in indices if i < len(self._items)]
        for item in selected_items:
            item["selected"] = True

        total_size = sum(i["size"] for i in selected_items)
        if not messagebox.askyesno("Confirm Clear",
                f"Clear {len(selected_items)} item(s) ({bh._fmt_bytes(total_size)})?\n\nClose all browsers before clearing."):
            return

        def clear():
            freed, errors = bh.clear_selected(selected_items)
            self.after(0, lambda: messagebox.showinfo("Done",
                f"Cleared {bh._fmt_bytes(freed)}" +
                (f" ({errors} errors)" if errors else "")))
            self._on_scan()

        threading.Thread(target=clear, daemon=True).start()

    def on_activate(self):
        if not self._items:
            self._on_scan()
