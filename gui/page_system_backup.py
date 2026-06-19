"""System Backup page — create and manage system snapshots."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import system_backup as sb


from ._pro_gate import gate_or_build


class SystemBackupPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._backing_up = False
        self._build_ui()

    def _build_ui(self):
        # Pro-feature gate — shows upsell for Free users
        if gate_or_build(self, "system_backup", "System Backup"):
            return
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="System Backup", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Create and manage system snapshots and recovery points",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Quick actions
        self._build_actions_card(body)

        # Backup history
        self._build_history_card(body)

    def _build_actions_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Quick Backups").pack(anchor="w", padx=10, pady=8)

        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(row1, text="Create System Restore Point",
                     command=self._on_create_restore).pack(side="left", padx=(0, 6))
        ActionButton(row1, text="Backup Drivers",
                     command=self._on_backup_drivers).pack(side="left", padx=(0, 6))
        ActionButton(row1, text="Backup Network Config",
                     command=self._on_backup_network).pack(side="left")

        self._action_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._action_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_history_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Backup History").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("type", "timestamp"), height=10)
        self._tree.column("#0", width=200)
        self._tree.column("type", width=150)
        self._tree.column("timestamp", width=180)
        self._tree.heading("#0", text="Backup Name")
        self._tree.heading("type", text="Type")
        self._tree.heading("timestamp", text="Created")

        sb_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb_scroll.pack(side="right", fill="y")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_row, text="Delete Selected",
                     command=self._on_delete).pack(side="left")

        self._history_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._history_status.pack(anchor="w", padx=10, pady=(0, 8))

        self._load_history()

    def _on_create_restore(self):
        if self._backing_up:
            return

        self._backing_up = True
        self._action_status.config(text="Creating restore point...")

        def create():
            result = sb.create_system_restore_point()
            self.after(0, lambda: self._on_backup_done(result))

        threading.Thread(target=create, daemon=True).start()

    def _on_backup_drivers(self):
        if self._backing_up:
            return

        self._backing_up = True
        self._action_status.config(text="Backing up drivers...")

        def backup():
            result = sb.backup_driver_list()
            self.after(0, lambda: self._on_backup_done(result))

        threading.Thread(target=backup, daemon=True).start()

    def _on_backup_network(self):
        if self._backing_up:
            return

        self._backing_up = True
        self._action_status.config(text="Backing up network config...")

        def backup():
            result = sb.backup_network_config()
            self.after(0, lambda: self._on_backup_done(result))

        threading.Thread(target=backup, daemon=True).start()

    def _on_backup_done(self, result):
        self._backing_up = False

        if result.get("success"):
            self._action_status.config(text="Backup completed successfully", fg=T.SUCCESS)
            self._load_history()
        else:
            self._action_status.config(text=f"Error: {result.get('error', 'Unknown')}", fg=T.DANGER)

    def _on_delete(self):
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select a backup to delete")
            return

        if not messagebox.askyesno("Delete Backup", "Delete selected backup?"):
            return

        item_id = selection[0]
        backup_name = self._tree.item(item_id)["text"]

        if sb.delete_backup(backup_name):
            messagebox.showinfo("Deleted", "Backup deleted successfully")
            self._load_history()
        else:
            messagebox.showerror("Error", "Failed to delete backup")

    def _load_history(self):
        """Load backup history in background."""
        def load():
            backups = sb.list_backup_history()
            self.after(0, self._display_history, backups)

        threading.Thread(target=load, daemon=True).start()

    def _display_history(self, backups):
        """Display backup history."""
        self._tree.delete(*self._tree.get_children())

        for backup in sorted(backups, key=lambda x: x["timestamp"], reverse=True):
            self._tree.insert("", "end", text=backup["name"],
                             values=(backup["type"], backup["timestamp"]))

        self._history_status.config(text=f"Total backups: {len(backups)}")

    def on_activate(self):
        self._load_history()
