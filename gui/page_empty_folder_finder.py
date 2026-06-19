"""Empty Folder Finder page — Scan and remove empty directories."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import empty_folder_finder as eff


def _fmt_size(num_bytes: int) -> str:
    """Human-readable size from a byte count."""
    try:
        n = float(num_bytes)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


class EmptyFolderFinderPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Empty Folder Finder", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Find and remove empty directories",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Main card
        card = Card(body)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Empty Folders").pack(anchor="w", padx=10, pady=8)

        # Stats
        self._stats = tk.Label(card, text="Ready to scan", bg=T.PANEL, fg=T.FG2,
                              font=T.FONT_SMALL)
        self._stats.pack(anchor="w", padx=10, pady=(0, 8))

        # Progress
        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        # Tree
        tree_frame = tk.Frame(card, bg=T.ACCENT)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("size",), height=10)
        self._tree.column("#0", width=400)
        self._tree.column("size", width=100)
        self._tree.heading("#0", text="Folder Path")
        self._tree.heading("size", text="Size")
        self._tree.pack(fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Scan for Empty Folders",
                     command=self._on_scan).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Delete Selected",
                     command=self._on_delete).pack(side="left", padx=0)

    def _on_scan(self):
        self._progress.set_value(0)
        self._tree.delete(*self._tree.get_children())
        self._stats.config(text="Scanning...")

        def scan():
            try:
                folders = eff.scan_empty_folders()

                def _show():
                    self._tree.delete(*self._tree.get_children())
                    for folder in folders[:1000]:
                        path = folder.get("path", "")
                        size_b = folder.get("size_on_disk", 0)
                        self._tree.insert("", "end", text=path,
                                          values=(_fmt_size(size_b),))
                    self._progress.set_value(100)
                    self._stats.config(text=f"Found {len(folders)} empty folder(s)")

                self.after(0, _show)
            except Exception as e:
                self.after(0, lambda e=e: (self._stats.config(text=f"Error: {e}"),
                                           self._progress.set_value(0)))

        threading.Thread(target=scan, daemon=True).start()

    def _on_delete(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select folder(s) to delete")
            return

        paths = [self._tree.item(item)["text"] for item in selected]
        if messagebox.askyesno("Confirm", f"Delete {len(paths)} folder(s)?\n\nThis cannot be undone."):
            self._progress.set_value(0)

            def delete():
                try:
                    eff.delete_folders(paths)
                    self._progress.set_value(100)
                    messagebox.showinfo("Success", f"Deleted {len(paths)} folder(s)")
                    self._on_scan()
                except Exception as e:
                    messagebox.showerror("Error", f"Delete failed: {e}")
                    self._progress.set_value(0)

            threading.Thread(target=delete, daemon=True).start()

    def on_activate(self):
        pass
