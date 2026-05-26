"""File Shredder tab — multi-pass secure deletion."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import secure_delete as sd


def _fmt(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


class ShredderTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._queue: list[str] = []
        self._build_ui()

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        SectionLabel(hdr, "Secure File Shredder").pack(side="left", padx=8, pady=8)
        tk.Label(hdr,
                 text="Overwrites files with random data before deletion — prevents recovery",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=10)

        cfg = tk.Frame(self, bg=T.BG)
        cfg.pack(fill="x", padx=16, pady=4)
        tk.Label(cfg, text="Overwrite method:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._method_var = tk.StringVar(value=sd.DEFAULT_METHOD)
        method_cb = ttk.Combobox(cfg, textvariable=self._method_var,
                                  values=sd.get_methods(), state="readonly", width=26)
        method_cb.pack(side="left", padx=8)

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Add Files", command=self._add_files).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Add Folder", command=self._add_folder).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Remove Selected", command=self._remove_selected).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Clear Queue", command=self._clear_queue).pack(side="left", padx=(0, 12))
        self._shred_btn = ActionButton(btn_row, "SHRED FILES", command=self._shred, danger=True)
        self._shred_btn.pack(side="left")

        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        self._progress_detail = tk.Label(self, text="", bg=T.BG, fg=T.FG2, font=T.FONT_SMALL)
        self._progress_detail.pack(anchor="w", padx=16)

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        SectionLabel(card, "Files in Shred Queue").pack(anchor="w", padx=8, pady=(6, 2))
        cols = ("Size", "Type")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",   text="Path",      anchor="w")
        self._tv.heading("Size", text="Size",       anchor="w")
        self._tv.heading("Type", text="Type",       anchor="w")
        self._tv.column("#0",   width=500)
        self._tv.column("Size", width=90)
        self._tv.column("Type", width=70)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._summary = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._summary.pack(anchor="w", padx=8, pady=4)

    # ── queue management ──────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="Select files to shred")
        for p in paths:
            if p not in self._queue:
                self._queue.append(p)
        self._refresh_queue()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select folder to shred")
        if folder and folder not in self._queue:
            self._queue.append(folder)
        self._refresh_queue()

    def _remove_selected(self):
        for iid in self._tv.selection():
            path = self._tv.item(iid, "text")
            if path in self._queue:
                self._queue.remove(path)
        self._refresh_queue()

    def _clear_queue(self):
        self._queue = []
        self._refresh_queue()

    def _refresh_queue(self):
        for item in self._tv.get_children():
            self._tv.delete(item)
        total_size = 0
        for path in self._queue:
            try:
                if os.path.isfile(path):
                    sz = os.path.getsize(path)
                    total_size += sz
                    self._tv.insert("", "end", text=path,
                                    values=(_fmt(sz), "File"))
                elif os.path.isdir(path):
                    sz = sum(os.path.getsize(os.path.join(r, f))
                             for r, _, files in os.walk(path)
                             for f in files)
                    total_size += sz
                    self._tv.insert("", "end", text=path,
                                    values=(_fmt(sz), "Folder"))
            except OSError:
                self._tv.insert("", "end", text=path, values=("?", "?"))
        self._summary.config(text=f"{len(self._queue)} items  —  {_fmt(total_size)} total")

    # ── shred ─────────────────────────────────────────────────────────────────

    def _shred(self):
        if not self._queue:
            messagebox.showinfo("Empty queue", "Add files or folders to the queue first.")
            return
        method = self._method_var.get()
        total = len(self._queue)
        warn = (
            f"PERMANENTLY DESTROY {total} item(s) using:\n{method}\n\n"
            "Files overwritten with this method are UNRECOVERABLE.\n\n"
            "Are you absolutely sure?"
        )
        if not messagebox.askyesno("Confirm Shred", warn, icon="warning"):
            return
        self._shred_btn.config(state="disabled")
        self._progress.indeterminate(True)
        self._status.set("Shredding files...")
        threading.Thread(target=self._do_shred, args=(list(self._queue), method),
                         daemon=True).start()

    def _do_shred(self, queue, method):
        done = errors = 0

        def file_cb(pass_num, total_passes, done_bytes, total_bytes):
            pct = int(done_bytes / max(total_bytes, 1) * 100)
            self.after(0, self._progress.set, pct)
            self.after(0, self._progress_detail.config,
                       {"text": f"Pass {pass_num}/{total_passes}  {pct}%"})

        for path in queue:
            self.after(0, self._status.set, f"Shredding: {path[-60:]}")
            try:
                if os.path.isfile(path):
                    ok = sd.shred_file(path, method=method, progress_cb=file_cb)
                elif os.path.isdir(path):
                    shredded, errs = sd.shred_folder(path, method=method,
                                                      progress_cb=lambda p: None)
                    ok = errs == 0
                    done += shredded
                    errors += errs
                    path = None  # prevent double-counting
                else:
                    ok = True
                if path is not None:
                    if ok:
                        done += 1
                    else:
                        errors += 1
            except Exception:
                errors += 1

        self.after(0, self._shred_done, done, errors)

    def _shred_done(self, done, errors):
        self._progress.indeterminate(False)
        self._progress.set(100)
        self._shred_btn.config(state="normal")
        self._queue = [p for p in self._queue if os.path.exists(p)]
        self._refresh_queue()
        self._status.set(f"Shredded {done} file(s) — {errors} error(s).")
        messagebox.showinfo("Shred Complete",
                            f"Shredded: {done} file(s)\nErrors: {errors}")
        self._progress.set(0)
        self._progress_detail.config(text="")
