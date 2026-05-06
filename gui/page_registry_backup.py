"""Registry Backup page — create, restore and manage registry backups."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import registry_backup as rb


class RegistryBackupPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._backups = []
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Registry Backup", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Backup and restore Windows registry before cleaning",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        info_card = Card(body)
        info_card.pack(fill="x", pady=(0, 12))
        SectionLabel(info_card, "Create Backup").pack(anchor="w", padx=10, pady=8)
        tk.Label(info_card,
                 text="Backups are stored in %TEMP%\\FreeSystemDoctor\\registry_backups\\  as .reg files.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", padx=10, pady=(0, 4))

        btn_row = tk.Frame(info_card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row, text="Quick Backup (CurrentVersion)",
                     command=self._on_quick_backup).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Full Backup (HKCU + HKLM\\SOFTWARE)",
                     command=self._on_full_backup).pack(side="left")

        self._backup_status = tk.Label(info_card, text="", bg=T.PANEL,
                                       fg=T.FG2, font=T.FONT_SMALL)
        self._backup_status.pack(anchor="w", padx=10, pady=(0, 8))

        list_card = Card(body)
        list_card.pack(fill="both", expand=True)

        hdr2 = tk.Frame(list_card, bg=T.PANEL)
        hdr2.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(hdr2, "Existing Backups").pack(side="left")
        ActionButton(hdr2, text="Refresh", command=self._load_backups).pack(side="right")

        tree_frame = tk.Frame(list_card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("created", "size"), height=12)
        self._tree.column("#0", width=300)
        self._tree.column("created", width=150)
        self._tree.column("size", width=80)
        self._tree.heading("#0", text="Backup Name")
        self._tree.heading("created", text="Created")
        self._tree.heading("size", text="Size")
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        action_row = tk.Frame(list_card, bg=T.PANEL)
        action_row.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(action_row, text="Restore Selected",
                     command=self._on_restore).pack(side="left", padx=(0, 6))
        ActionButton(action_row, text="Delete Selected", danger=True,
                     command=self._on_delete).pack(side="left")

    def _load_backups(self):
        self._backups = rb.list_backups()
        self._tree.delete(*self._tree.get_children())
        for b in self._backups:
            self._tree.insert("", "end", iid=b["path"], text=b["name"],
                              values=(b["created"], b["size_str"]))

    def _on_quick_backup(self):
        self._backup_status.config(text="Creating backup...", fg=T.FG2)

        def backup():
            result = rb.create_backup("manual")
            if result.get("error"):
                self.after(0, lambda: self._backup_status.config(
                    text=f"Error: {result['error']}", fg=T.DANGER))
            else:
                self.after(0, lambda: self._backup_status.config(
                    text=f"Backup created: {result['size_str'] if 'size_str' in result else rb._fmt_bytes(result['size'])}",
                    fg=T.SUCCESS))
                self.after(0, self._load_backups)

        threading.Thread(target=backup, daemon=True).start()

    def _on_full_backup(self):
        if not messagebox.askyesno("Full Backup",
                "Create a full registry backup? This may take a minute."):
            return
        self._backup_status.config(text="Creating full backup...", fg=T.FG2)

        def backup():
            result = rb.create_full_backup("manual_full")
            if result.get("error"):
                self.after(0, lambda: self._backup_status.config(
                    text=f"Error: {result['error']}", fg=T.DANGER))
            else:
                self.after(0, lambda: self._backup_status.config(
                    text=f"Full backup created: {result['count']} files, {result['size_str']}",
                    fg=T.SUCCESS))
                self.after(0, self._load_backups)

        threading.Thread(target=backup, daemon=True).start()

    def _on_restore(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a backup to restore")
            return
        path = sel[0]
        if not messagebox.askyesno("Confirm Restore",
                "Restore this registry backup?\n\nA system restart may be required."):
            return

        def restore():
            ok, msg = rb.restore_backup(path)
            self.after(0, lambda: messagebox.showinfo("Restored" if ok else "Error", msg))

        threading.Thread(target=restore, daemon=True).start()

    def _on_delete(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a backup to delete")
            return
        if not messagebox.askyesno("Delete", f"Delete {len(sel)} backup(s)?"):
            return
        for path in sel:
            rb.delete_backup(path)
        self._load_backups()

    def on_activate(self):
        self._load_backups()
