"""Driver Updater page — Detect and update outdated drivers."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import driver_updater as du


class DriverUpdaterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Driver Updater", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Find and update outdated drivers",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Main card
        card = Card(body)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "System Drivers").pack(anchor="w", padx=10, pady=8)

        # Progress
        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        # Drivers tree
        tree_frame = tk.Frame(card, bg=T.ACCENT)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("status", "device"), height=10)
        self._tree.column("#0", width=250)
        self._tree.column("status", width=100)
        self._tree.column("device", width=200)
        self._tree.heading("#0", text="Driver")
        self._tree.heading("status", text="Status")
        self._tree.heading("device", text="Device")
        self._tree.pack(fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Scan for Updates",
                     command=self._on_scan).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Update Selected",
                     command=self._on_update).pack(side="left", padx=0)

    def _on_scan(self):
        self._progress.set_value(0)
        self._tree.delete(*self._tree.get_children())

        def scan():
            try:
                self._progress.set_value(20)
                drivers = du.get_installed_drivers()

                self._progress.set_value(50)
                problematic = du.find_problematic_drivers()

                self._progress.set_value(70)
                for driver in drivers[:20]:
                    status = "⚠ Problem" if driver in problematic else "✓ OK"
                    self._tree.insert("", "end", text=driver.get("name", "Unknown"),
                                    values=(status, driver.get("device", "")))

                self._progress.set_value(100)
            except Exception as e:
                messagebox.showerror("Error", f"Scan failed: {e}")
                self._progress.set_value(0)

        threading.Thread(target=scan, daemon=True).start()

    def _on_update(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a driver to update")
            return

        self._progress.set_value(0)

        def update():
            try:
                for item in selected:
                    driver_name = self._tree.item(item)["text"]
                    self._progress.set_value(50)
                    du.update_driver_winget(driver_name)
                    self._progress.set_value(100)
                messagebox.showinfo("Success", "Drivers updated successfully")
                self._on_scan()
            except Exception as e:
                messagebox.showerror("Error", f"Update failed: {e}")
                self._progress.set_value(0)

        threading.Thread(target=update, daemon=True).start()

    def on_activate(self):
        self._on_scan()
