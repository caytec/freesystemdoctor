"""Large File Finder tab."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import large_file_finder


class LargeFilesTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._results: list[dict] = []
        self._search_path = tk.StringVar(value=r"C:\\")
        self._build_ui()

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Large File Finder").pack(side="left", padx=8, pady=8)

        cfg = tk.Frame(self, bg=T.BG)
        cfg.pack(fill="x", padx=16, pady=4)
        tk.Label(cfg, text="Search path:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        tk.Entry(cfg, textvariable=self._search_path, width=30,
                 bg=T.PANEL, fg=T.FG, insertbackground=T.FG,
                 font=T.FONT_BODY).pack(side="left", padx=6)
        ActionButton(cfg, "Browse", command=self._browse).pack(side="left", padx=4)

        size_row = tk.Frame(self, bg=T.BG)
        size_row.pack(fill="x", padx=16, pady=4)
        tk.Label(size_row, text="Minimum size (MB):", bg=T.BG, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._min_size = tk.Entry(size_row, width=6, bg=T.PANEL, fg=T.FG,
                                  insertbackground=T.FG, font=T.FONT_BODY)
        self._min_size.insert(0, "50")
        self._min_size.pack(side="left", padx=6)

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Scan", command=self._start_scan).pack(side="left", padx=(0, 8))
        self._del_btn = ActionButton(btn_row, "Delete Selected",
                                     command=self._delete_selected, danger=True)
        self._del_btn.pack(side="left")
        self._del_btn.config(state="disabled")

        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        self._summary_lbl = tk.Label(self, text="", bg=T.BG, fg=T.HIGHLIGHT, font=T.FONT_BOLD)
        self._summary_lbl.pack(anchor="w", padx=16)

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Size", "Extension")
        self._tv = ttk.Treeview(card, columns=cols, show="headings tree")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",        text="File Path",  anchor="w")
        self._tv.heading("Size",      text="Size",       anchor="w")
        self._tv.heading("Extension", text="Extension",  anchor="w")
        self._tv.column("#0",        width=460)
        self._tv.column("Size",      width=100)
        self._tv.column("Extension", width=80)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._tv.bind("<Button-3>", self._show_context)

    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self._search_path.set(path)

    def _start_scan(self):
        path = self._search_path.get().strip()
        if not os.path.isdir(path):
            messagebox.showwarning("Invalid path", f"Path not found: {path}")
            return
        try:
            min_mb = float(self._min_size.get())
        except ValueError:
            min_mb = 50
        self._progress.indeterminate(True)
        self._summary_lbl.config(text="")
        self._del_btn.config(state="disabled")
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._status.set("Scanning for large files...")
        threading.Thread(target=self._do_scan, args=(path, min_mb), daemon=True).start()

    def _do_scan(self, path, min_mb):
        def cb(msg, count):
            self.after(0, self._status.set, f"{msg} ({count} found)")

        results = large_file_finder.find_large_files([path], min_size_mb=min_mb, progress_cb=cb)
        self.after(0, self._show_results, results)

    def _show_results(self, results):
        self._progress.indeterminate(False)
        self._results = results
        for item in self._tv.get_children():
            self._tv.delete(item)

        total = sum(r["size"] for r in results)
        self._summary_lbl.config(
            text=f"{len(results)} files — {self._fmt(total)} total"
        )

        for r in results:
            self._tv.insert("", "end", text=r["path"],
                            values=(r["size_str"], r["ext"]))

        self._status.set(
            f"Found {len(results)} large files ({self._fmt(total)})."
        )
        if results:
            self._del_btn.config(state="normal")

    def _delete_selected(self):
        sel = self._tv.selection()
        if not sel:
            messagebox.showinfo("Nothing selected", "Select files to delete.")
            return
        paths = [self._tv.item(i, "text") for i in sel]
        total = sum(os.path.getsize(p) for p in paths if os.path.exists(p))
        if not messagebox.askyesno(
            "Delete files",
            f"Permanently delete {len(paths)} file(s) ({self._fmt(total)})?\n\nThis cannot be undone."
        ):
            return
        deleted = freed = 0
        for path in paths:
            try:
                sz = os.path.getsize(path)
                os.remove(path)
                freed += sz
                deleted += 1
            except OSError:
                pass
        self._status.set(f"Deleted {deleted} files — freed {self._fmt(freed)}.")
        messagebox.showinfo("Done", f"Deleted {deleted} files\nFreed: {self._fmt(freed)}")
        self._start_scan()

    def _show_context(self, event):
        iid = self._tv.identify_row(event.y)
        if not iid:
            return
        path = self._tv.item(iid, "text")
        menu = tk.Menu(self, tearoff=0, bg=T.PANEL, fg=T.FG)
        menu.add_command(label="Open folder in Explorer",
                         command=lambda: os.startfile(os.path.dirname(path)))
        menu.add_command(label="Delete this file",
                         command=lambda: self._delete_one(iid, path))
        menu.post(event.x_root, event.y_root)

    def _delete_one(self, iid, path):
        if not messagebox.askyesno("Delete", f"Delete:\n{path}"):
            return
        try:
            os.remove(path)
            self._tv.delete(iid)
            self._status.set(f"Deleted: {path}")
        except OSError as e:
            messagebox.showerror("Error", str(e))

    @staticmethod
    def _fmt(b):
        for u in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} TB"
