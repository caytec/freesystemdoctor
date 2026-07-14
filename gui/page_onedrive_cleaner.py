"""OneDrive Cleaner page — manage cloud storage and remove duplicates."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import onedrive_cleaner as oc


class OneDriveCleanerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="OneDrive Cleaner", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Manage cloud storage and reclaim space",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_auth_card(body)
        self._build_quota_card(body)
        self._build_duplicates_card(body)
        self._build_old_files_card(body)
        self._build_recommendations_card(body)

    def _build_auth_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "OneDrive Authorization").pack(anchor="w", padx=10, pady=8)

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        self._auth_status = tk.Label(btn_row, text="Not authorized", bg=T.PANEL, fg=T.DANGER,
                                     font=T.FONT_BODY)
        self._auth_status.pack(side="left", padx=10)

        ActionButton(btn_row, text="Authorize OneDrive",
                     command=self._on_authorize).pack(side="left", padx=(10, 0))

    def _build_quota_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Storage Quota").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row, text="Total:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._quota_total = tk.Label(row, text="–", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY)
        self._quota_total.pack(side="left", padx=10)

        tk.Label(row, text="Used:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left", padx=(20, 0))
        self._quota_used = tk.Label(row, text="–", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY)
        self._quota_used.pack(side="left", padx=10)

        tk.Label(row, text="Free:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left", padx=(20, 0))
        self._quota_free = tk.Label(row, text="–", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY)
        self._quota_free.pack(side="left", padx=10)

    def _build_duplicates_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=False, pady=(0, 12))

        SectionLabel(card, "Duplicate Files").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._dup_tree = ttk.Treeview(tree_frame, columns=("count", "recoverable"), height=6)
        self._dup_tree.column("#0", width=200)
        self._dup_tree.column("count", width=60)
        self._dup_tree.column("recoverable", width=120)
        self._dup_tree.heading("#0", text="Filename")
        self._dup_tree.heading("count", text="Copies")
        self._dup_tree.heading("recoverable", text="Recoverable")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._dup_tree.yview)
        self._dup_tree.configure(yscrollcommand=sb.set)
        self._dup_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_row, text="Delete Selected Duplicates",
                     command=self._on_delete_duplicates).pack(side="left")

    def _build_old_files_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Old Files (90+ days)").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._old_tree = ttk.Treeview(tree_frame, columns=("modified", "days_old"), height=8)
        self._old_tree.column("#0", width=200)
        self._old_tree.column("modified", width=120)
        self._old_tree.column("days_old", width=80)
        self._old_tree.heading("#0", text="Filename")
        self._old_tree.heading("modified", text="Last Modified")
        self._old_tree.heading("days_old", text="Days Old")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._old_tree.yview)
        self._old_tree.configure(yscrollcommand=sb.set)
        self._old_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_row, text="Delete Selected Old Files",
                     command=self._on_delete_old).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Refresh Scan",
                     command=self._on_refresh).pack(side="left")

    def _build_recommendations_card(self, parent):
        card = Card(parent)
        card.pack(fill="x")

        SectionLabel(card, "Recommendations").pack(anchor="w", padx=10, pady=8)

        self._rec_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                 height=3, bd=0, padx=8, pady=6,
                                 state="disabled", wrap="word")
        self._rec_text.pack(fill="x", padx=10, pady=(0, 8))

    def _on_authorize(self):
        messagebox.showinfo("OneDrive Authorization",
            "Visit https://login.microsoft.com/common/oauth2/v2.0/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8080/callback&response_type=code&scope=files.readwrite.all\n\n"
            "Paste authorization code when prompted.")
        # In production, would open browser and handle callback

    def _on_delete_duplicates(self):
        selection = self._dup_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select duplicate files to delete")
            return

        if not messagebox.askyesno("Delete Duplicates",
                f"Delete {len(selection)} duplicate file(s)?"):
            return

        def delete_dups():
            deleted = 0
            for iid in selection:
                item = self._dup_tree.item(iid)
                if oc.delete_file(iid):
                    deleted += 1
            self.after(0, lambda: messagebox.showinfo("Complete", f"Deleted {deleted} file(s)"))
            self._on_refresh()

        threading.Thread(target=delete_dups, daemon=True).start()

    def _on_delete_old(self):
        selection = self._old_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select old files to delete")
            return

        if not messagebox.askyesno("Delete Old Files",
                f"Delete {len(selection)} old file(s)?"):
            return

        def delete_old():
            deleted = 0
            for iid in selection:
                if oc.delete_file(iid):
                    deleted += 1
            self.after(0, lambda: messagebox.showinfo("Complete", f"Deleted {deleted} file(s)"))
            self._on_refresh()

        threading.Thread(target=delete_old, daemon=True).start()

    def _on_refresh(self):
        self._load_data()

    def _load_data(self):
        def load():
            # Not signed in → show an empty, honest state instead of crashing.
            if not oc.is_connected():
                self.after(0, self._display_data, {}, [], [], [])
                return

            files = oc.list_files()
            usage = oc.get_drive_usage()
            quota = {}
            if usage:
                quota = {
                    "total_gb": usage.get("total", 0) / (1024**3),
                    "used_gb": usage.get("used", 0) / (1024**3),
                    "remaining_gb": usage.get("free", 0) / (1024**3),
                }

            # Adapt find_duplicates() tuples -> the shape _display_data expects.
            duplicates = []
            for group, total_size in oc.find_duplicates(files):
                keep = group[0]["size"] if group else 0
                duplicates.append({
                    "name": group[0]["name"] if group else "",
                    "count": len(group),
                    "files": group,
                    "recoverable_size": max(0, total_size - keep),
                })

            # Old files + a computed days_old field.
            import datetime as _dt
            now = _dt.datetime.utcnow()
            old_files = []
            for f in oc.find_old_files(files, days=90):
                days_old = 0
                try:
                    mod = _dt.datetime.strptime(
                        f.get("modified", "")[:10], "%Y-%m-%d")
                    days_old = (now - mod).days
                except Exception:
                    pass
                old_files.append({**f, "days_old": days_old})

            recommendations = []
            if duplicates:
                recommendations.append(
                    f"{len(duplicates)} duplicate set(s) found — free up space by removing copies.")
            if old_files:
                recommendations.append(
                    f"{len(old_files)} file(s) untouched for 90+ days — consider archiving.")
            if usage and usage.get("percent_used", 0) > 85:
                recommendations.append("OneDrive is over 85% full.")

            self.after(0, self._display_data, quota, duplicates, old_files, recommendations)

        threading.Thread(target=load, daemon=True).start()

    def _display_data(self, quota, duplicates, old_files, recommendations):
        # Update quota
        if quota:
            self._quota_total.config(text=f"{quota.get('total_gb', 0):.2f} GB")
            self._quota_used.config(text=f"{quota.get('used_gb', 0):.2f} GB")
            self._quota_free.config(text=f"{quota.get('remaining_gb', 0):.2f} GB")
            self._auth_status.config(text="Authorized", fg=T.SUCCESS)

        # Update duplicates
        self._dup_tree.delete(*self._dup_tree.get_children())
        for dup in duplicates:
            recoverable_mb = dup["recoverable_size"] / (1024**2)
            self._dup_tree.insert("", "end", iid=dup["files"][0]["id"],
                                 text=dup["name"],
                                 values=(dup["count"], f"{recoverable_mb:.1f} MB"))

        # Update old files
        self._old_tree.delete(*self._old_tree.get_children())
        for old in old_files:
            self._old_tree.insert("", "end", iid=old["id"],
                                 text=old["name"],
                                 values=(old["modified"][:10], old["days_old"]))

        # Update recommendations
        self._rec_text.config(state="normal")
        self._rec_text.delete("1.0", "end")
        if recommendations:
            self._rec_text.insert("end", "\n".join(f"• {r}" for r in recommendations))
        else:
            self._rec_text.insert("end", "Your OneDrive is well organized!")
        self._rec_text.config(state="disabled")

    def on_activate(self):
        self._load_data()
