"""Duplicate File Finder tab."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine.duplicate_finder import find_duplicates


class DuplicatesTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._results: list[dict] = []
        self._search_paths: list[str] = []
        self._build_ui()

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Duplicate File Finder").pack(side="left", padx=8, pady=8)

        cfg = tk.Frame(self, bg=T.BG)
        cfg.pack(fill="x", padx=16, pady=4)

        tk.Label(cfg, text="Search Paths:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._path_lbl = tk.Label(cfg, text="(none selected)", bg=T.BG,
                                   fg=T.FG2, font=T.FONT_SMALL)
        self._path_lbl.pack(side="left", padx=8)
        ActionButton(cfg, "Add Folder", command=self._add_folder).pack(side="left", padx=4)
        ActionButton(cfg, "Clear", command=self._clear_paths).pack(side="left", padx=4)

        size_row = tk.Frame(self, bg=T.BG)
        size_row.pack(fill="x", padx=16, pady=4)
        tk.Label(size_row, text="Min file size (KB):", bg=T.BG, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._min_size = tk.Entry(size_row, width=6, bg=T.PANEL, fg=T.FG,
                                  insertbackground=T.FG, font=T.FONT_BODY)
        self._min_size.insert(0, "1")
        self._min_size.pack(side="left", padx=6)

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Find Duplicates", command=self._start_scan).pack(side="left", padx=(0, 8))
        self._del_btn = ActionButton(btn_row, "Delete Selected Duplicates",
                                     command=self._delete_selected, danger=True)
        self._del_btn.pack(side="left")
        self._del_btn.config(state="disabled")

        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        self._summary_lbl = tk.Label(self, text="", bg=T.BG, fg=T.HIGHLIGHT, font=T.FONT_BOLD)
        self._summary_lbl.pack(anchor="w", padx=16)

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Size", "Copies", "Wasted")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0", text="File / Path", anchor="w")
        self._tv.heading("Size",   text="File Size", anchor="w")
        self._tv.heading("Copies", text="Copies",    anchor="w")
        self._tv.heading("Wasted", text="Wasted",    anchor="w")
        self._tv.column("#0",     width=350)
        self._tv.column("Size",   width=90)
        self._tv.column("Copies", width=70)
        self._tv.column("Wasted", width=90)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # context menu
        self._tv.bind("<Button-3>", self._show_context)

    def _add_folder(self):
        path = filedialog.askdirectory(title="Select folder to search")
        if path:
            self._search_paths.append(path)
            self._path_lbl.config(text="; ".join(self._search_paths))

    def _clear_paths(self):
        self._search_paths = []
        self._path_lbl.config(text="(none selected)")

    def _start_scan(self):
        if not self._search_paths:
            messagebox.showinfo("No path", "Add at least one folder to search.")
            return
        try:
            min_kb = int(self._min_size.get())
        except ValueError:
            min_kb = 1
        self._progress.indeterminate(True)
        self._summary_lbl.config(text="")
        self._del_btn.config(state="disabled")
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._status.set("Scanning for duplicates...")
        threading.Thread(target=self._do_scan, args=(min_kb,), daemon=True).start()

    def _do_scan(self, min_kb):
        def cb(msg, pct):
            self.after(0, self._status.set, msg)
            if pct:
                self.after(0, self._progress.set, pct)

        results = find_duplicates(self._search_paths, min_size_kb=min_kb, progress_cb=cb)
        self.after(0, self._show_results, results)

    def _show_results(self, results):
        self._progress.indeterminate(False)
        self._results = results
        for item in self._tv.get_children():
            self._tv.delete(item)

        total_wasted = sum(g["wasted"] for g in results)
        self._summary_lbl.config(
            text=f"{len(results)} duplicate groups — {self._fmt(total_wasted)} wasted"
        )

        for i, g in enumerate(results):
            parent = self._tv.insert("", "end",
                text=f"Group {i+1}  ({g['size_str']} each, {len(g['files'])} copies)",
                values=(g["size_str"], len(g["files"]), g["wasted_str"]),
                tags=("group",),
            )
            for fp in g["files"]:
                self._tv.insert(parent, "end", text=fp,
                                values=("", "", ""), tags=("file",))

        self._tv.tag_configure("group", foreground=T.HIGHLIGHT)
        self._tv.tag_configure("file",  foreground=T.FG2)

        self._status.set(
            f"Found {len(results)} groups — {self._fmt(total_wasted)} can be freed."
        )
        if results:
            self._del_btn.config(state="normal")

    def _delete_selected(self):
        sel = self._tv.selection()
        to_delete = []
        for iid in sel:
            # if a file row is selected, add it; if a group row, add all but first
            parent = self._tv.parent(iid)
            if parent:
                # it's a file row
                path = self._tv.item(iid, "text")
                to_delete.append(path)
            else:
                # group row — queue all but the first child
                children = self._tv.get_children(iid)
                for child in children[1:]:
                    to_delete.append(self._tv.item(child, "text"))

        if not to_delete:
            messagebox.showinfo("Nothing to delete",
                "Select file rows or group rows. "
                "Selecting a group deletes all copies except the first.")
            return

        if not messagebox.askyesno(
            "Delete duplicates",
            f"Permanently delete {len(to_delete)} file(s)?\n\nThis cannot be undone."
        ):
            return

        deleted = 0
        freed = 0
        for path in to_delete:
            try:
                sz = os.path.getsize(path)
                os.remove(path)
                freed += sz
                deleted += 1
            except OSError:
                pass

        self._status.set(f"Deleted {deleted} files — freed {self._fmt(freed)}.")
        messagebox.showinfo("Done", f"Deleted {deleted} files\nFreed: {self._fmt(freed)}")
        self._start_scan()  # re-scan

    def _show_context(self, event):
        iid = self._tv.identify_row(event.y)
        if not iid:
            return
        parent = self._tv.parent(iid)
        if not parent:
            return  # group row
        path = self._tv.item(iid, "text")
        menu = tk.Menu(self, tearoff=0, bg=T.PANEL, fg=T.FG)
        menu.add_command(label="Open in Explorer",
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
