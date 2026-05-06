"""Cloud Drive Cleaner page — Google Drive and OneDrive cleanup."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import cloud_drive_cleaner as cdc
from engine import onedrive_cleaner as odc


class CloudCleanerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._gdrive_files = []
        self._onedrive_files = []
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Cloud Drive Cleaner", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Clean up Google Drive and OneDrive duplicates and old files",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        gdrive_frame = tk.Frame(nb, bg=T.BG)
        nb.add(gdrive_frame, text="  Google Drive  ")
        self._build_gdrive_tab(gdrive_frame)

        onedrive_frame = tk.Frame(nb, bg=T.BG)
        nb.add(onedrive_frame, text="  OneDrive  ")
        self._build_onedrive_tab(onedrive_frame)

    # ── Google Drive tab ───────────────────────────────────────────────────────

    def _build_gdrive_tab(self, parent):
        body = tk.Frame(parent, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        auth_card = Card(body)
        auth_card.pack(fill="x", pady=(0, 12))
        SectionLabel(auth_card, "Google Drive Connection").pack(anchor="w", padx=10, pady=8)
        self._gdrive_status = tk.Label(auth_card, text="Not connected", bg=T.PANEL,
                                       fg=T.WARNING, font=T.FONT_BODY)
        self._gdrive_status.pack(anchor="w", padx=10, pady=(0, 8))
        btn_row = tk.Frame(auth_card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row, text="Connect to Google Drive",
                     command=self._gdrive_auth).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="List Files",
                     command=self._gdrive_list).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Duplicates",
                     command=self._gdrive_duplicates).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Old Files (90d)",
                     command=self._gdrive_old).pack(side="left")

        usage_card = Card(body)
        usage_card.pack(fill="x", pady=(0, 12))
        SectionLabel(usage_card, "Drive Usage").pack(anchor="w", padx=10, pady=8)
        self._gdrive_bar = ProgressBar(usage_card)
        self._gdrive_bar.pack(fill="x", padx=10, pady=(0, 4))
        self._gdrive_usage_text = tk.Label(usage_card, text="Not loaded", bg=T.PANEL,
                                           fg=T.FG2, font=T.FONT_SMALL)
        self._gdrive_usage_text.pack(anchor="w", padx=10, pady=(0, 8))

        results_card = Card(body)
        results_card.pack(fill="both", expand=True)
        SectionLabel(results_card, "Files").pack(anchor="w", padx=10, pady=8)
        self._gdrive_progress = ProgressBar(results_card)
        self._gdrive_progress.pack(fill="x", padx=10, pady=(0, 8))
        tree_frame = tk.Frame(results_card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        apply_treeview_style()
        self._gdrive_tree = ttk.Treeview(tree_frame, columns=("size", "modified"), height=10)
        self._gdrive_tree.column("#0", width=300)
        self._gdrive_tree.column("size", width=100)
        self._gdrive_tree.column("modified", width=120)
        self._gdrive_tree.heading("#0", text="Filename")
        self._gdrive_tree.heading("size", text="Size")
        self._gdrive_tree.heading("modified", text="Modified")
        self._gdrive_tree.pack(fill="both", expand=True)
        btn_row2 = tk.Frame(results_card, bg=T.PANEL)
        btn_row2.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row2, text="Delete Selected", danger=True,
                     command=self._gdrive_delete).pack(side="left")
        self._gdrive_summary = tk.Label(results_card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._gdrive_summary.pack(anchor="w", padx=10, pady=(0, 8))

    def _gdrive_auth(self):
        messagebox.showinfo("Google Drive",
            "To use Google Drive Cleaner:\n\n"
            "1. Set environment variables:\n"
            "   GOOGLE_DRIVE_CLIENT_ID=...\n"
            "   GOOGLE_DRIVE_CLIENT_SECRET=...\n\n"
            "2. Restart the application\n\n"
            "OAuth flow will run automatically on first connection.")
        self._gdrive_status.config(text="Ready (configure credentials)", fg=T.WARNING)

    def _gdrive_list(self):
        self._gdrive_progress.set_value(0)
        self._gdrive_tree.delete(*self._gdrive_tree.get_children())

        def load():
            try:
                self._gdrive_files = cdc.list_files()
                usage = cdc.get_drive_usage()
                if usage:
                    self.after(0, lambda: self._gdrive_bar.set_value(usage.get("percent_used", 0)))
                    txt = f"{usage['used_str']} / {usage['total_str']} ({usage['percent_used']:.1f}%)"
                    self.after(0, lambda: self._gdrive_usage_text.config(text=txt))
                self.after(0, self._gdrive_populate, self._gdrive_files)
                self.after(0, lambda: self._gdrive_status.config(text="Connected", fg=T.SUCCESS))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed: {e}"))
                self.after(0, lambda: self._gdrive_progress.set_value(0))

        threading.Thread(target=load, daemon=True).start()

    def _gdrive_populate(self, files):
        self._gdrive_tree.delete(*self._gdrive_tree.get_children())
        for f in files[:500]:
            date = f["modified"].split("T")[0] if "T" in f["modified"] else "—"
            self._gdrive_tree.insert("", "end", text=f["name"], values=(f["size_str"], date))
        self._gdrive_progress.set_value(100)
        self._gdrive_summary.config(text=f"Loaded {len(files)} files")

    def _gdrive_duplicates(self):
        if not self._gdrive_files:
            messagebox.showwarning("No Files", "List files first")
            return

        def find():
            dups = cdc.find_duplicates(self._gdrive_files)
            all_dups = [f for lst, _ in dups for f in lst]
            self.after(0, self._gdrive_populate_dups, all_dups, len(dups))

        threading.Thread(target=find, daemon=True).start()

    def _gdrive_populate_dups(self, files, n_sets):
        self._gdrive_tree.delete(*self._gdrive_tree.get_children())
        for f in files:
            date = f["modified"].split("T")[0] if "T" in f["modified"] else "—"
            self._gdrive_tree.insert("", "end", text=f"{f['name']} (DUP)", values=(f["size_str"], date))
        self._gdrive_summary.config(text=f"Found {len(files)} duplicates in {n_sets} sets")

    def _gdrive_old(self):
        if not self._gdrive_files:
            messagebox.showwarning("No Files", "List files first")
            return

        def find():
            old = cdc.find_old_files(self._gdrive_files, days=90)
            self.after(0, self._gdrive_populate, old)
            total = sum(f["size"] for f in old)
            self.after(0, lambda: self._gdrive_summary.config(
                text=f"Found {len(old)} old files ({cdc._fmt_bytes(total)})"))

        threading.Thread(target=find, daemon=True).start()

    def _gdrive_delete(self):
        sel = self._gdrive_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select files to delete")
            return
        names = {self._gdrive_tree.item(i, "text").replace(" (DUP)", "") for i in sel}
        ids = [f["id"] for f in self._gdrive_files if f["name"] in names]
        if not ids:
            messagebox.showerror("Error", "Files not found")
            return
        if not messagebox.askyesno("Confirm Delete", f"Delete {len(ids)} file(s) from Google Drive?"):
            return

        def delete():
            ok = sum(1 for fid in ids if cdc.delete_file(fid))
            self.after(0, lambda: messagebox.showinfo("Done", f"Deleted {ok}/{len(ids)} files"))

        threading.Thread(target=delete, daemon=True).start()

    # ── OneDrive tab ───────────────────────────────────────────────────────────

    def _build_onedrive_tab(self, parent):
        body = tk.Frame(parent, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        auth_card = Card(body)
        auth_card.pack(fill="x", pady=(0, 12))
        SectionLabel(auth_card, "OneDrive Connection").pack(anchor="w", padx=10, pady=8)
        self._od_status = tk.Label(auth_card, text="Not connected", bg=T.PANEL,
                                   fg=T.WARNING, font=T.FONT_BODY)
        self._od_status.pack(anchor="w", padx=10, pady=(0, 4))
        self._od_code_label = tk.Label(auth_card, text="", bg=T.PANEL,
                                       fg=T.FG, font=T.FONT_BODY, wraplength=500, justify="left")
        self._od_code_label.pack(anchor="w", padx=10, pady=(0, 8))
        btn_row = tk.Frame(auth_card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row, text="Connect to OneDrive",
                     command=self._od_auth).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="List Files",
                     command=self._od_list).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Duplicates",
                     command=self._od_duplicates).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Old Files (90d)",
                     command=self._od_old).pack(side="left")

        usage_card = Card(body)
        usage_card.pack(fill="x", pady=(0, 12))
        SectionLabel(usage_card, "OneDrive Usage").pack(anchor="w", padx=10, pady=8)
        self._od_bar = ProgressBar(usage_card)
        self._od_bar.pack(fill="x", padx=10, pady=(0, 4))
        self._od_usage_text = tk.Label(usage_card, text="Not loaded", bg=T.PANEL,
                                       fg=T.FG2, font=T.FONT_SMALL)
        self._od_usage_text.pack(anchor="w", padx=10, pady=(0, 8))

        results_card = Card(body)
        results_card.pack(fill="both", expand=True)
        SectionLabel(results_card, "Files").pack(anchor="w", padx=10, pady=8)
        self._od_progress = ProgressBar(results_card)
        self._od_progress.pack(fill="x", padx=10, pady=(0, 8))
        tree_frame = tk.Frame(results_card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        apply_treeview_style()
        self._od_tree = ttk.Treeview(tree_frame, columns=("size", "modified"), height=10)
        self._od_tree.column("#0", width=300)
        self._od_tree.column("size", width=100)
        self._od_tree.column("modified", width=120)
        self._od_tree.heading("#0", text="Filename")
        self._od_tree.heading("size", text="Size")
        self._od_tree.heading("modified", text="Modified")
        self._od_tree.pack(fill="both", expand=True)
        btn_row2 = tk.Frame(results_card, bg=T.PANEL)
        btn_row2.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row2, text="Delete Selected", danger=True,
                     command=self._od_delete).pack(side="left")
        self._od_summary = tk.Label(results_card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._od_summary.pack(anchor="w", padx=10, pady=(0, 8))

    def _od_auth(self):
        if not odc._CLIENT_ID:
            messagebox.showinfo("OneDrive Setup",
                "To use OneDrive Cleaner:\n\n"
                "1. Register an app at portal.azure.com\n"
                "   (or set ONEDRIVE_CLIENT_ID env var)\n\n"
                "2. Enable 'Files.ReadWrite' permission\n\n"
                "3. Restart the application and click Connect again.")
            return

        def auth():
            result = odc.start_device_auth()
            if "error" in result:
                self.after(0, lambda: messagebox.showerror("Error", result["error"]))
                return

            code = result.get("user_code", "")
            url = result.get("verification_uri", "")
            device_code = result.get("device_code", "")
            interval = result.get("interval", 5)

            self.after(0, lambda: self._od_code_label.config(
                text=f"Go to: {url}\nEnter code: {code}\n(Waiting for authentication...)"))

            import webbrowser
            webbrowser.open(url)

            for _ in range(60):
                if odc.poll_device_auth(device_code, interval):
                    self.after(0, lambda: self._od_status.config(text="Connected", fg=T.SUCCESS))
                    self.after(0, lambda: self._od_code_label.config(text=""))
                    return
                import time
                time.sleep(interval)

            self.after(0, lambda: self._od_code_label.config(text="Authentication timed out. Try again."))

        threading.Thread(target=auth, daemon=True).start()

    def _od_list(self):
        if not odc.is_connected():
            messagebox.showwarning("Not Connected", "Connect to OneDrive first")
            return

        self._od_progress.set_value(0)
        self._od_tree.delete(*self._od_tree.get_children())

        def load():
            try:
                self._onedrive_files = odc.list_files()
                usage = odc.get_drive_usage()
                if usage:
                    self.after(0, lambda: self._od_bar.set_value(usage.get("percent_used", 0)))
                    txt = f"{usage['used_str']} / {usage['total_str']} ({usage['percent_used']:.1f}%)"
                    self.after(0, lambda: self._od_usage_text.config(text=txt))
                self.after(0, self._od_populate, self._onedrive_files)
                self.after(0, lambda: self._od_status.config(text="Connected", fg=T.SUCCESS))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed: {e}"))

        threading.Thread(target=load, daemon=True).start()

    def _od_populate(self, files):
        self._od_tree.delete(*self._od_tree.get_children())
        for f in files:
            date = f["modified"].split("T")[0] if "T" in f["modified"] else "—"
            self._od_tree.insert("", "end", text=f["name"], values=(f["size_str"], date))
        self._od_progress.set_value(100)
        self._od_summary.config(text=f"Loaded {len(files)} files")

    def _od_duplicates(self):
        if not self._onedrive_files:
            messagebox.showwarning("No Files", "List files first")
            return

        def find():
            dups = odc.find_duplicates(self._onedrive_files)
            all_dups = [f for lst, _ in dups for f in lst]
            self.after(0, self._od_populate, all_dups)
            self.after(0, lambda: self._od_summary.config(
                text=f"Found {len(all_dups)} duplicates in {len(dups)} sets"))

        threading.Thread(target=find, daemon=True).start()

    def _od_old(self):
        if not self._onedrive_files:
            messagebox.showwarning("No Files", "List files first")
            return

        def find():
            old = odc.find_old_files(self._onedrive_files, days=90)
            self.after(0, self._od_populate, old)
            total = sum(f["size"] for f in old)
            self.after(0, lambda: self._od_summary.config(
                text=f"Found {len(old)} old files ({odc._fmt_bytes(total)})"))

        threading.Thread(target=find, daemon=True).start()

    def _od_delete(self):
        sel = self._od_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select files to delete")
            return
        names = {self._od_tree.item(i, "text").replace(" (DUP)", "") for i in sel}
        ids = [f["id"] for f in self._onedrive_files if f["name"] in names]
        if not ids:
            messagebox.showerror("Error", "Files not found")
            return
        if not messagebox.askyesno("Confirm Delete", f"Delete {len(ids)} file(s) from OneDrive?"):
            return

        def delete():
            ok = sum(1 for fid in ids if odc.delete_file(fid))
            self.after(0, lambda: messagebox.showinfo("Done", f"Deleted {ok}/{len(ids)} files"))

        threading.Thread(target=delete, daemon=True).start()

    def on_activate(self):
        if odc.is_connected():
            self._od_status.config(text="Connected", fg=T.SUCCESS)
