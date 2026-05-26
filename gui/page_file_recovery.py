"""File Recovery page — recover deleted files from Recycle Bin and NTFS."""

import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import file_recovery as fr


class FileRecoveryPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._recoverable_files = []
        self._recovery_dir = None
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="File Recovery", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Recover deleted files from Recycle Bin and disk",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Info card
        self._build_info_card(body)

        # Recovery destination card
        self._build_destination_card(body)

        # Filter card
        self._build_filter_card(body)

        # Results card
        self._build_results_card(body)

    def _build_info_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False, pady=(0, 12))

        SectionLabel(card, "Recycle Bin Status").pack(anchor="w", padx=10, pady=8)

        frame = tk.Frame(card, bg=T.PANEL)
        frame.pack(fill="x", padx=10, pady=(0, 8))

        self._rb_size = tk.Label(frame, text="Scanning...", bg=T.PANEL,
                                fg=T.FG2, font=T.FONT_BODY)
        self._rb_size.pack(anchor="w")

        ActionButton(card, text="Scan Recycle Bin",
                     command=self._on_scan).pack(anchor="w", padx=10, pady=(0, 8))

        self._load_rb_size()

    def _load_rb_size(self):
        def load():
            try:
                size = fr.get_recycle_bin_size()
                self.after(0, lambda: self._rb_size.config(
                    text=f"Total items: {fr._fmt_bytes(size)}"))
            except Exception:
                self.after(0, lambda: self._rb_size.config(text="Unable to scan"))

        threading.Thread(target=load, daemon=True).start()

    def _build_destination_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False, pady=(0, 12))

        SectionLabel(card, "Recovery Destination").pack(anchor="w", padx=10, pady=8)

        frame = tk.Frame(card, bg=T.PANEL)
        frame.pack(fill="x", padx=10, pady=(0, 8))

        self._dest_label = tk.Label(frame, text="Not selected", bg=T.PANEL,
                                    fg=T.FG2, font=T.FONT_BODY, wraplength=400)
        self._dest_label.pack(anchor="w", fill="x")

        ActionButton(card, text="Choose Destination Folder",
                     command=self._on_choose_dest).pack(anchor="w", padx=10, pady=(0, 8))

    def _build_filter_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False, pady=(0, 12))

        SectionLabel(card, "Filters").pack(anchor="w", padx=10, pady=8)

        frame = tk.Frame(card, bg=T.PANEL)
        frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(frame, text="File type:", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")

        self._filter_var = tk.StringVar(value="all")
        options = ["all", "images", "documents", "videos", "archives"]
        combo = ttk.Combobox(frame, textvariable=self._filter_var, values=options,
                            state="readonly", width=15)
        combo.pack(side="left", padx=8)

    def _build_results_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Recoverable Files").pack(anchor="w", padx=10, pady=8)

        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("size", "type"), height=12)
        self._tree.column("#0", width=300)
        self._tree.column("size", width=100)
        self._tree.column("type", width=80)
        self._tree.heading("#0", text="Filename")
        self._tree.heading("size", text="Size")
        self._tree.heading("type", text="Type")
        self._tree.pack(fill="both", expand=True)

        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Recover Selected",
                     command=self._on_recover).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Select All",
                     command=self._on_select_all).pack(side="left")

        self._summary = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                font=T.FONT_SMALL)
        self._summary.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_choose_dest(self):
        dest = filedialog.askdirectory(title="Select Recovery Destination")
        if dest:
            self._recovery_dir = dest
            self._dest_label.config(text=f"✓ {dest}", fg=T.SUCCESS)

    def _on_scan(self):
        if not self._recovery_dir:
            messagebox.showwarning("No Destination", "Choose recovery destination first")
            return

        self._progress.set_value(0)
        self._tree.delete(*self._tree.get_children())
        self._summary.config(text="Scanning...")

        def scan():
            try:
                files = fr.scan_recoverable_files(max_results=1000)
                self._recoverable_files = files

                self._tree.delete(*self._tree.get_children())
                for f in files:
                    ext = f.get("extension", "")
                    self._tree.insert("", "end", text=f["name"],
                                     values=(f["size_str"], ext))

                self._progress.set_value(100)
                self._summary.config(text=f"Found {len(files)} recoverable file(s)")

            except Exception as e:
                messagebox.showerror("Error", f"Scan failed: {e}")
                self._progress.set_value(0)

        threading.Thread(target=scan, daemon=True).start()

    def _on_select_all(self):
        for item in self._tree.get_children():
            self._tree.selection_add(item)

    def _on_recover(self):
        if not self._recovery_dir:
            messagebox.showwarning("No Destination", "Choose recovery destination first")
            return

        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select files to recover")
            return

        names = [self._tree.item(item, "text") for item in sel]
        files = [f for f in self._recoverable_files if f["name"] in names]

        if not files:
            messagebox.showerror("Error", "Files not found")
            return

        msg = f"Recover {len(files)} file(s) to:\n{self._recovery_dir}\n\nContinue?"
        if not messagebox.askyesno("Confirm Recovery", msg):
            return

        self._progress.set_value(0)

        def recover():
            try:
                success, total = fr.recover_multiple(
                    [f["path"] for f in files],
                    self._recovery_dir
                )
                self.after(0, lambda: messagebox.showinfo("Complete",
                    f"Recovered {success}/{total} file(s)"))
                self._progress.set_value(100)
                self._summary.config(text=f"Recovery complete: {success}/{total} files")

            except Exception as e:
                messagebox.showerror("Error", f"Recovery failed: {e}")
                self._progress.set_value(0)

        threading.Thread(target=recover, daemon=True).start()

    def on_activate(self):
        pass
