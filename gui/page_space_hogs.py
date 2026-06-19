"""Space Hogs page — WinDirStat-style largest files & folders finder."""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import space_hogs as sh


class SpaceHogsPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._cancel = None
        self._scanning = False
        self._drives = []
        self._build_ui()
        self._load_drives()

    # ── Layout ────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🗂  Space Hogs", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Find the biggest files and folders eating your disk",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_controls(body)
        self._build_tabs(body)

    def _build_controls(self, parent):
        ctrl = Card(parent)
        ctrl.pack(fill="x", pady=(0, 10))

        row = tk.Frame(ctrl, bg=T.PANEL)
        row.pack(fill="x", padx=12, pady=10)

        tk.Label(row, text="Scan location:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", padx=(0, 6))

        self._drive_var = tk.StringVar()
        self._drive_combo = ttk.Combobox(row, textvariable=self._drive_var,
                                          state="readonly", width=44)
        self._drive_combo.pack(side="left", padx=(0, 6))

        ActionButton(row, text="Pick Folder…",
                     command=self._on_pick_folder).pack(side="left", padx=(0, 6))

        tk.Label(row, text="  Min file size:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left")
        self._min_size_var = tk.StringVar(value="10 MB")
        ttk.Combobox(row, textvariable=self._min_size_var,
                      values=["100 KB", "1 MB", "10 MB", "100 MB", "1 GB"],
                      state="readonly", width=9).pack(side="left", padx=(4, 6))

        tk.Label(row, text="  Top N:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left")
        self._top_n_var = tk.StringVar(value="500")
        ttk.Combobox(row, textvariable=self._top_n_var,
                      values=["100", "200", "500", "1000", "2000"],
                      state="readonly", width=6).pack(side="left", padx=(4, 6))

        self._scan_btn = ActionButton(row, text="🔍 Scan",
                                       command=self._on_scan)
        self._scan_btn.pack(side="left", padx=(8, 4))
        self._cancel_btn = ActionButton(row, text="Cancel", danger=True,
                                         command=self._on_cancel)
        self._cancel_btn.pack(side="left")

        self._progress = ProgressBar(ctrl)
        self._progress.pack(fill="x", padx=12, pady=(0, 6))
        self._status = tk.Label(ctrl, text="Ready.", bg=T.PANEL, fg=T.FG2,
                                 font=T.FONT_SMALL, anchor="w")
        self._status.pack(fill="x", padx=12, pady=(0, 10))

    def _build_tabs(self, parent):
        # Use ttk.Notebook for two views: files / folders
        style = ttk.Style()
        try:
            style.configure("SpaceHogs.TNotebook", background=T.BG, borderwidth=0)
            style.configure("SpaceHogs.TNotebook.Tab",
                            padding=(14, 6), background=T.PANEL, foreground=T.FG)
            style.map("SpaceHogs.TNotebook.Tab",
                      background=[("selected", T.ACCENT)],
                      foreground=[("selected", T.HIGHLIGHT)])
        except Exception:
            pass

        nb = ttk.Notebook(parent, style="SpaceHogs.TNotebook")
        nb.pack(fill="both", expand=True)

        # ── Largest files tab ────────────────────────────────────────────
        files_frame = tk.Frame(nb, bg=T.BG)
        nb.add(files_frame, text="  Largest Files  ")

        apply_treeview_style()
        ft = tk.Frame(files_frame, bg=T.PANEL)
        ft.pack(fill="both", expand=True, padx=2, pady=2)

        self._files_tree = ttk.Treeview(
            ft, columns=("size", "ext", "folder"), show="tree headings", height=18)
        self._files_tree.column("#0", width=300)
        self._files_tree.column("size", width=110, anchor="e")
        self._files_tree.column("ext", width=70)
        self._files_tree.column("folder", width=500)
        self._files_tree.heading("#0", text="File Name")
        self._files_tree.heading("size", text="Size")
        self._files_tree.heading("ext", text="Type")
        self._files_tree.heading("folder", text="Folder")

        fsb = ttk.Scrollbar(ft, orient="vertical", command=self._files_tree.yview)
        self._files_tree.configure(yscrollcommand=fsb.set)
        self._files_tree.pack(side="left", fill="both", expand=True)
        fsb.pack(side="right", fill="y")

        self._files_tree.bind("<Double-1>", lambda e: self._reveal_selected("files"))
        self._files_menu = self._build_context_menu("files")
        self._files_tree.bind("<Button-3>",
                              lambda e: self._popup_menu(e, self._files_menu))

        # ── Largest folders tab ──────────────────────────────────────────
        folders_frame = tk.Frame(nb, bg=T.BG)
        nb.add(folders_frame, text="  Largest Folders  ")

        gt = tk.Frame(folders_frame, bg=T.PANEL)
        gt.pack(fill="both", expand=True, padx=2, pady=2)

        self._folders_tree = ttk.Treeview(
            gt, columns=("size", "percent"), show="tree headings", height=18)
        self._folders_tree.column("#0", width=620)
        self._folders_tree.column("size", width=110, anchor="e")
        self._folders_tree.column("percent", width=90, anchor="e")
        self._folders_tree.heading("#0", text="Folder Path")
        self._folders_tree.heading("size", text="Size")
        self._folders_tree.heading("percent", text="% of Root")

        gsb = ttk.Scrollbar(gt, orient="vertical", command=self._folders_tree.yview)
        self._folders_tree.configure(yscrollcommand=gsb.set)
        self._folders_tree.pack(side="left", fill="both", expand=True)
        gsb.pack(side="right", fill="y")

        self._folders_tree.bind("<Double-1>", lambda e: self._reveal_selected("folders"))
        self._folders_menu = self._build_context_menu("folders")
        self._folders_tree.bind("<Button-3>",
                                lambda e: self._popup_menu(e, self._folders_menu))

    def _build_context_menu(self, kind: str) -> tk.Menu:
        menu = tk.Menu(self, tearoff=0, bg=T.PANEL, fg=T.FG,
                        activebackground=T.ACCENT, activeforeground=T.HIGHLIGHT)
        menu.add_command(label="Reveal in Explorer",
                         command=lambda: self._reveal_selected(kind))
        menu.add_command(label="Copy path",
                         command=lambda: self._copy_path(kind))
        menu.add_separator()
        menu.add_command(label="Move to Recycle Bin",
                         command=lambda: self._delete_selected(kind))
        return menu

    # ── Data loading ──────────────────────────────────────────────────────
    def _load_drives(self):
        def work():
            try:
                drives = sh.list_drives()
                self.after(0, self._apply_drives, drives)
            except Exception as e:
                self.after(0, self._set_status, f"Drive list error: {e}")
        threading.Thread(target=work, daemon=True).start()

    def _apply_drives(self, drives):
        self._drives = drives
        labels = [d["label"] for d in drives]
        self._drive_combo.config(values=labels)
        if labels:
            self._drive_combo.current(0)

    def _on_pick_folder(self):
        folder = filedialog.askdirectory(title="Select folder to scan")
        if folder:
            # Append the picked folder to the dropdown for visibility
            label = f"📁  {folder}"
            values = list(self._drive_combo["values"])
            if label not in values:
                values.append(label)
                self._drive_combo.config(values=values)
            self._drive_var.set(label)

    # ── Scan logic ────────────────────────────────────────────────────────
    def _resolve_scan_path(self) -> str:
        sel = self._drive_var.get()
        if sel.startswith("📁  "):
            return sel[len("📁  "):]
        for d in self._drives:
            if d["label"] == sel:
                return d["mountpoint"]
        return ""

    def _parse_min_size(self) -> int:
        s = (self._min_size_var.get() or "10 MB").strip().upper()
        try:
            num, unit = s.split()
            n = float(num)
        except Exception:
            return 10 * 1024 * 1024
        mult = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}.get(unit, 1024**2)
        return int(n * mult)

    def _on_scan(self):
        if self._scanning:
            return
        path = self._resolve_scan_path()
        if not path or not os.path.exists(path):
            messagebox.showwarning("No location", "Pick a drive or folder first.")
            return
        try:
            top_n = int(self._top_n_var.get())
        except ValueError:
            top_n = 500
        min_size = self._parse_min_size()

        self._scanning = True
        self._cancel = sh.CancelFlag()
        self._files_tree.delete(*self._files_tree.get_children())
        self._folders_tree.delete(*self._folders_tree.get_children())
        self._progress.indeterminate(True)
        self._set_status(f"Scanning {path}…")

        def work():
            try:
                def cb(scanned, total_bytes, cur):
                    if self._cancel and self._cancel.cancelled:
                        return
                    short = cur if len(cur) < 80 else "…" + cur[-78:]
                    self.after(0, self._set_status,
                              f"Scanned {scanned:,} files • {sh.fmt_bytes(total_bytes)} • {short}")

                files = sh.find_largest_files(
                    path, top_n=top_n, min_size_bytes=min_size,
                    progress_cb=cb, cancel_flag=self._cancel,
                )
                if self._cancel and self._cancel.cancelled:
                    self.after(0, self._scan_done, files, [], path, True)
                    return

                folders = sh.find_largest_folders(
                    path, top_n=min(top_n, 200), depth=5,
                    progress_cb=cb, cancel_flag=self._cancel,
                )
                self.after(0, self._scan_done, files, folders, path, False)
            except Exception as e:
                self.after(0, self._scan_error, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_cancel(self):
        if self._cancel:
            self._cancel.cancel()
            self._set_status("Cancelling…")

    def _scan_done(self, files, folders, path, cancelled):
        self._scanning = False
        self._progress.indeterminate(False)

        for f in files:
            self._files_tree.insert(
                "", "end", text=f["name"],
                values=(f["size_str"], f["ext"] or "—", f["folder"]),
                tags=(f["path"],),
            )

        for fl in folders:
            self._folders_tree.insert(
                "", "end", text=fl["path"],
                values=(fl["size_str"], f'{fl["percent"]:.1f}%'),
                tags=(fl["path"],),
            )

        suffix = " (cancelled)" if cancelled else ""
        self._set_status(
            f"✓ Found {len(files):,} large files, {len(folders):,} folders under {path}{suffix}"
        )

    def _scan_error(self, msg: str):
        self._scanning = False
        self._progress.indeterminate(False)
        self._set_status(f"✗ Scan error: {msg}")
        messagebox.showerror("Scan failed", msg)

    def _set_status(self, msg: str):
        self._status.config(text=msg)

    # ── Selection actions ─────────────────────────────────────────────────
    def _selected_path(self, kind: str) -> str:
        tree = self._files_tree if kind == "files" else self._folders_tree
        sel = tree.selection()
        if not sel:
            return ""
        tags = tree.item(sel[0], "tags")
        return tags[0] if tags else ""

    def _reveal_selected(self, kind: str):
        path = self._selected_path(kind)
        if path:
            sh.reveal_in_explorer(path)

    def _copy_path(self, kind: str):
        path = self._selected_path(kind)
        if path:
            try:
                self.clipboard_clear()
                self.clipboard_append(path)
                self._set_status(f"Copied: {path}")
            except Exception:
                pass

    def _delete_selected(self, kind: str):
        path = self._selected_path(kind)
        if not path:
            return
        if not messagebox.askyesno("Recycle Bin",
                                    f"Move to Recycle Bin?\n\n{path}"):
            return
        if sh.send_to_recycle_bin(path):
            tree = self._files_tree if kind == "files" else self._folders_tree
            for iid in tree.selection():
                tree.delete(iid)
            self._set_status(f"Moved to Recycle Bin: {path}")
        else:
            messagebox.showerror("Failed", f"Could not delete:\n{path}")

    def _popup_menu(self, event, menu: tk.Menu):
        tree = (self._files_tree if menu is self._files_menu
                else self._folders_tree)
        row = tree.identify_row(event.y)
        if row:
            tree.selection_set(row)
            menu.tk_popup(event.x_root, event.y_root)

    def on_activate(self):
        if not self._drives:
            self._load_drives()
