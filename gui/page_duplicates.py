"""Duplicate & similar files — content-based scan grouped by file type.

Surfaces the enhanced_duplicates engine, which had no UI at all. Unlike the
legacy Duplicates tab this groups by type (photos, videos, documents…) and can
also find *similar* files, not just byte-identical ones.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import theme as T
from .widgets import (Card, SectionLabel, ActionButton, PageHeader,
                      ProgressBar, apply_treeview_style, Toast)
from engine import enhanced_duplicates as ed


def _fmt(num_bytes) -> str:
    try:
        n = float(num_bytes)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


class DuplicatesPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._paths = [os.path.expanduser("~")]
        self._groups: list[dict] = []
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Duplicate Files",
                   subtitle="Find identical and similar files by content",
                   icon="🗂", color=T.WARNING).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # folder + controls
        top = tk.Frame(body, bg=T.BG)
        top.pack(fill="x", pady=(0, 6))
        tk.Label(top, text="Folder:", bg=T.BG, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._path_lbl = tk.Label(top, text=self._paths[0], bg=T.BG, fg=T.FG2,
                                  font=T.FONT_SMALL)
        self._path_lbl.pack(side="left", padx=8)
        ActionButton(top, text="Choose…", width=110, secondary=True,
                     command=self._choose).pack(side="left")

        ctl = tk.Frame(body, bg=T.BG)
        ctl.pack(fill="x", pady=(0, 8))
        tk.Label(ctl, text="Type:", bg=T.BG, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._type = tk.StringVar(value="all")
        ttk.Combobox(ctl, textvariable=self._type, width=12, state="readonly",
                     values=("all", "image", "video", "audio", "document",
                             "archive")).pack(side="left", padx=(6, 12))
        ActionButton(ctl, text="🔍  Find duplicates", width=170,
                     command=lambda: self._scan(False)).pack(side="left",
                                                             padx=(0, 8))
        ActionButton(ctl, text="≈  Find similar", width=150, secondary=True,
                     command=lambda: self._scan(True)).pack(side="left")
        self._del_btn = ActionButton(ctl, text="🗑  Delete selected", width=170,
                                     danger=True, command=self._delete)
        self._del_btn.pack(side="right")

        self._prog = ProgressBar(body)
        self._prog.pack(fill="x", pady=(0, 4))
        self._status = tk.Label(body, text="Pick a folder and start a scan.",
                                bg=T.BG, fg=T.FG2, font=T.FONT_SMALL, anchor="w")
        self._status.pack(fill="x", pady=(0, 6))

        card = Card(body)
        card.pack(fill="both", expand=True)
        apply_treeview_style()
        self._tree = ttk.Treeview(card, columns=("size", "path"),
                                  show="tree headings", height=14,
                                  selectmode="extended")
        self._tree.heading("#0", text="Group / file")
        self._tree.heading("size", text="Size")
        self._tree.heading("path", text="Location")
        self._tree.column("#0", width=240)
        self._tree.column("size", width=90)
        self._tree.column("path", width=420)
        self._tree.pack(fill="both", expand=True, padx=10, pady=10)
        self._tree.tag_configure("group", foreground=T.HIGHLIGHT)
        self._tree.tag_configure("keep", foreground=T.SUCCESS)

    # ── actions ──────────────────────────────────────────────────────────────
    def _choose(self):
        folder = filedialog.askdirectory(initialdir=self._paths[0])
        if folder:
            self._paths = [folder]
            self._path_lbl.config(text=folder)

    def _scan(self, similar: bool):
        if self._busy:
            return
        self._busy = True
        self._tree.delete(*self._tree.get_children())
        self._prog.indeterminate(True)
        self._status.config(text="Scanning… this can take a while on big folders.")

        ftype = None if self._type.get() == "all" else self._type.get()

        def progress(msg, pct=0):
            # engine calls progress_cb(message, percent)
            self.after(0, lambda: self._status.config(text=str(msg)[:110]))

        def work():
            try:
                if similar:
                    groups = ed.find_similar_files(self._paths,
                                                   progress_cb=progress)
                else:
                    groups = ed.find_duplicates_by_type(self._paths,
                                                        file_type=ftype,
                                                        progress_cb=progress)
            except Exception as exc:
                groups = []
                self.after(0, lambda: messagebox.showerror("Scan failed", str(exc)))
            self.after(0, lambda: self._scanned(groups, similar))

        threading.Thread(target=work, daemon=True).start()

    def _scanned(self, groups: list, similar: bool):
        self._busy = False
        self._prog.indeterminate(False)
        self._groups = groups or []

        wasted = 0
        for gi, group in enumerate(self._groups):
            files = group.get("files") or group.get("paths") or []
            if not isinstance(files, list) or len(files) < 2:
                continue
            label = (group.get("file_type") or group.get("note")
                     or f"Group {gi + 1}")
            size = group.get("size") or group.get("primary_size") or 0
            wasted += group.get("wasted") or 0
            parent = self._tree.insert(
                "", "end", text=f"{label}  ({len(files)} files)",
                values=(_fmt(size), ""), tags=("group",), open=False)
            for fi, f in enumerate(files):
                path = f if isinstance(f, str) else (f.get("path") or "")
                fsize = size if isinstance(f, str) else (f.get("size") or size)
                self._tree.insert(
                    parent, "end", iid=path,
                    text=("✓ keep  " if fi == 0 else "     ") + os.path.basename(path),
                    values=(_fmt(fsize), os.path.dirname(path)),
                    tags=("keep",) if fi == 0 else ())

        kind = "similar" if similar else "duplicate"
        if self._groups:
            self._status.config(
                text=f"Found {len(self._groups)} {kind} group(s) — up to "
                     f"{_fmt(wasted)} could be reclaimed. The first file in each "
                     f"group is marked “keep”.")
        else:
            self._status.config(text=f"No {kind} files found.")

    def _delete(self):
        sel = [i for i in self._tree.selection() if os.path.isfile(i)]
        if not sel:
            messagebox.showinfo("Nothing selected",
                                "Select the individual files you want to delete.\n\n"
                                "Tip: keep at least one file from each group.")
            return
        if not messagebox.askyesno(
                "Delete files?",
                f"Permanently delete {len(sel)} selected file(s)?\n\n"
                f"This cannot be undone."):
            return

        deleted = freed = 0
        errors = []
        for path in sel:
            try:
                freed += os.path.getsize(path)
                os.remove(path)
                deleted += 1
                if self._tree.exists(path):
                    self._tree.delete(path)
            except Exception as exc:
                errors.append(f"{os.path.basename(path)}: {exc}")

        self._status.config(text=f"Deleted {deleted} file(s), freed {_fmt(freed)}.")
        if errors:
            messagebox.showwarning("Some files could not be deleted",
                                   "\n".join(errors[:8]))
        else:
            try:
                Toast.show(self.winfo_toplevel(),
                           f"Freed {_fmt(freed)}", "success")
            except Exception:
                pass

    def on_activate(self):
        pass
