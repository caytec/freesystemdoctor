"""Disk Cleaner tab."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import disk_cleaner


class CleanerTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._scan_results: list[disk_cleaner.ScanResult] = []
        self._checks: dict[str, tk.BooleanVar] = {}
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Disk Cleaner").pack(side="left", padx=8, pady=8)
        self._rb_size_lbl = tk.Label(hdr, text="", bg=T.PANEL, fg=T.HIGHLIGHT,
                                     font=T.FONT_BOLD)
        self._rb_size_lbl.pack(side="right", padx=12)

        # Buttons
        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Scan for Junk", command=self._start_scan).pack(side="left", padx=(0, 8))
        self._clean_btn = ActionButton(btn_row, "Clean Selected", command=self._start_clean,
                                       danger=True)
        self._clean_btn.pack(side="left", padx=(0, 8))
        self._clean_btn.config(state="disabled")

        # Recycle Bin row
        rb_row = tk.Frame(self, bg=T.BG)
        rb_row.pack(fill="x", padx=16, pady=2)
        ActionButton(rb_row, "Empty Recycle Bin", command=self._empty_rb).pack(side="left")
        self._rb_info = tk.Label(rb_row, text="", bg=T.BG, fg=T.FG2, font=T.FONT_SMALL)
        self._rb_info.pack(side="left", padx=8)

        # Progress
        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        # Results treeview
        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Size", "Files")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0", text="Category / Path", anchor="w")
        self._tv.heading("Size", text="Size", anchor="w")
        self._tv.heading("Files", text="Files", anchor="w")
        self._tv.column("#0", width=420)
        self._tv.column("Size", width=90)
        self._tv.column("Files", width=70)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._update_rb_label()

    # ── actions ───────────────────────────────────────────────────────────────

    def _update_rb_label(self):
        sz = disk_cleaner.get_recycle_bin_size()
        if sz > 0:
            self._rb_info.config(text=f"Recycle Bin: {disk_cleaner._format_size(sz)}")
        else:
            self._rb_info.config(text="Recycle Bin: empty")

    def _start_scan(self):
        self._progress.indeterminate(True)
        self._status.set("Scanning for junk files...")
        self._clean_btn.config(state="disabled")
        for item in self._tv.get_children():
            self._tv.delete(item)
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        def cb(msg):
            self.after(0, self._status.set, msg)

        results = disk_cleaner.scan_junk(progress_cb=cb)
        self.after(0, self._show_scan, results)

    def _show_scan(self, results: list[disk_cleaner.ScanResult]):
        self._progress.indeterminate(False)
        self._scan_results = results
        self._checks.clear()

        for item in self._tv.get_children():
            self._tv.delete(item)

        total = 0
        for r in results:
            var = tk.BooleanVar(value=True)
            self._checks[r.path] = var
            # Checkbox-like toggle via tag
            tag = "checked"
            iid = self._tv.insert("", "end", text=f"[x] {r.label}",
                                  values=(r.size_str, r.file_count), tags=(tag,))
            self._tv.insert(iid, "end", text=r.path,
                            values=("", ""), tags=("path",))
            total += r.size

        self._tv.tag_configure("path", foreground=T.FG2)
        self._tv.tag_configure("checked", foreground=T.FG)

        self._tv.bind("<ButtonRelease-1>", self._on_tv_click)

        if results:
            self._clean_btn.config(state="normal")
            self._status.set(
                f"Found {len(results)} junk categories — "
                f"{disk_cleaner._format_size(total)} to clean."
            )
        else:
            self._status.set("No junk found. Your system is clean!")

    def _on_tv_click(self, event):
        """Toggle checkbox state when row clicked."""
        iid = self._tv.identify_row(event.y)
        if not iid:
            return
        parent = self._tv.parent(iid)
        if parent:
            return  # path sub-row
        current_text = self._tv.item(iid, "text")
        # find matching result
        for r in self._scan_results:
            label_checked = f"[x] {r.label}"
            label_unchecked = f"[ ] {r.label}"
            if current_text == label_checked:
                self._tv.item(iid, text=label_unchecked)
                self._checks[r.path].set(False)
                break
            elif current_text == label_unchecked:
                self._tv.item(iid, text=label_checked)
                self._checks[r.path].set(True)
                break

    def _start_clean(self):
        selected = [r for r in self._scan_results if self._checks.get(r.path, tk.BooleanVar(value=False)).get()]
        if not selected:
            messagebox.showinfo("Nothing selected", "Please select at least one category.")
            return
        total_size = sum(r.size for r in selected)
        if not messagebox.askyesno(
            "Confirm Clean",
            f"This will delete files in {len(selected)} categories "
            f"({disk_cleaner._format_size(total_size)}).\n\nProceed?"
        ):
            return
        self._progress.indeterminate(True)
        self._clean_btn.config(state="disabled")
        threading.Thread(target=self._do_clean, args=(selected,), daemon=True).start()

    def _do_clean(self, selected):
        total_freed = 0
        total_del = 0
        for r in selected:
            def cb(fp, _r=r):
                self.after(0, self._status.set, f"Deleting: {fp[-60:]}")
            freed, deleted = disk_cleaner.clean_folder(r.path, progress_cb=cb)
            total_freed += freed
            total_del += deleted
        self.after(0, self._clean_done, total_freed, total_del)

    def _clean_done(self, freed, deleted):
        self._progress.indeterminate(False)
        self._scan_results = []
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._clean_btn.config(state="disabled")
        self._update_rb_label()
        self._status.set(
            f"Cleaned {deleted} files — freed {disk_cleaner._format_size(freed)}."
        )
        messagebox.showinfo(
            "Clean Complete",
            f"Deleted {deleted} files\nFreed: {disk_cleaner._format_size(freed)}"
        )

    def _empty_rb(self):
        sz = disk_cleaner.get_recycle_bin_size()
        if sz == 0:
            messagebox.showinfo("Recycle Bin", "Recycle Bin is already empty.")
            return
        if messagebox.askyesno(
            "Empty Recycle Bin",
            f"Permanently delete all items in the Recycle Bin? ({disk_cleaner._format_size(sz)})"
        ):
            ok = disk_cleaner.empty_recycle_bin()
            if ok:
                self._status.set("Recycle Bin emptied.")
                self._update_rb_label()
            else:
                messagebox.showerror("Error", "Could not empty Recycle Bin.")
