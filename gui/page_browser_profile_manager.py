"""Browser Profile Manager page — manage extensions, homepage, and settings."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import browser_profile_manager as bpm


class BrowserProfileManagerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Browser Profile Manager", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Manage extensions, homepage, and browser settings",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_browser_selector(body)
        self._build_extensions_card(body)
        self._build_recommendations_card(body)

    def _build_browser_selector(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Select Browser").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row, text="Browser:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left", padx=10)

        self._browser_var = tk.StringVar()
        browser_combo = ttk.Combobox(row, textvariable=self._browser_var, state="readonly", width=20)
        browser_combo.pack(side="left", padx=10, fill="x", expand=True)
        browser_combo.bind("<<ComboboxSelected>>", lambda e: self._on_browser_changed())

        ActionButton(row, text="Refresh",
                     command=self._on_refresh).pack(side="left", padx=(10, 0))

        self._detected_label = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._detected_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_extensions_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Extensions").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._ext_tree = ttk.Treeview(tree_frame, columns=("id", "status"), height=10)
        self._ext_tree.column("#0", width=250)
        self._ext_tree.column("id", width=200)
        self._ext_tree.column("status", width=80)
        self._ext_tree.heading("#0", text="Extension Name")
        self._ext_tree.heading("id", text="ID")
        self._ext_tree.heading("status", text="Status")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._ext_tree.yview)
        self._ext_tree.configure(yscrollcommand=sb.set)
        self._ext_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_row, text="Remove Selected Extension",
                     command=self._on_remove_extension).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Remove All Suspicious",
                     command=self._on_remove_suspicious).pack(side="left")

        self._ext_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._ext_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_recommendations_card(self, parent):
        card = Card(parent)
        card.pack(fill="x")

        SectionLabel(card, "Browser Recommendations").pack(anchor="w", padx=10, pady=8)

        self._rec_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                 height=4, bd=0, padx=8, pady=6,
                                 state="disabled", wrap="word")
        self._rec_text.pack(fill="x", padx=10, pady=(0, 8))

    def _on_browser_changed(self):
        self._load_extensions()

    def _on_refresh(self):
        # Refresh browser list and extensions
        browsers = bpm.detect_installed_browsers()
        self._browser_var.set(browsers[0] if browsers else "")
        self._detected_label.config(text=f"Detected: {', '.join(browsers)}")
        self._load_extensions()

    def _load_extensions(self):
        browser = self._browser_var.get()
        if not browser:
            return

        def load():
            extensions = bpm.list_extensions(browser)
            malicious = bpm.detect_malicious_extensions(browser)
            recommendations = bpm.get_browser_recommendations()
            self.after(0, self._display_extensions, browser, extensions, malicious, recommendations)

        threading.Thread(target=load, daemon=True).start()

    def _display_extensions(self, browser, extensions, malicious, recommendations):
        # Update extensions tree
        self._ext_tree.delete(*self._ext_tree.get_children())
        for ext in extensions:
            suspicious = ext in malicious
            status = "SUSPICIOUS" if suspicious else "OK"
            color = T.DANGER if suspicious else T.SUCCESS
            self._ext_tree.insert("", "end", iid=ext.id, text=ext.name,
                                 values=(ext.id, status), tags=("suspicious" if suspicious else "ok",))

        self._ext_tree.tag_configure("suspicious", foreground=T.DANGER)
        self._ext_tree.tag_configure("ok", foreground=T.SUCCESS)

        # Update status
        suspicious_count = len(malicious)
        self._ext_status.config(
            text=f"Total: {len(extensions)} extension(s), {suspicious_count} suspicious"
        )

        # Update recommendations
        self._rec_text.config(state="normal")
        self._rec_text.delete("1.0", "end")
        if recommendations:
            self._rec_text.insert("end", "\n".join(f"• {r}" for r in recommendations))
        else:
            self._rec_text.insert("end", "Browser configuration looks good!")
        self._rec_text.config(state="disabled")

    def _on_remove_extension(self):
        browser = self._browser_var.get()
        if not browser:
            messagebox.showwarning("No Browser", "Select a browser first")
            return

        selection = self._ext_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select an extension to remove")
            return

        ext_id = selection[0]
        ext_name = self._ext_tree.item(ext_id)["text"]

        if not messagebox.askyesno("Remove Extension",
                f"Remove '{ext_name}' from {browser}?"):
            return

        def remove():
            if bpm.remove_extension(browser, ext_id):
                self.after(0, lambda: messagebox.showinfo("Success",
                    f"Removed '{ext_name}' from {browser}"))
            else:
                self.after(0, lambda: messagebox.showerror("Error",
                    f"Failed to remove '{ext_name}'"))
            self._load_extensions()

        threading.Thread(target=remove, daemon=True).start()

    def _on_remove_suspicious(self):
        browser = self._browser_var.get()
        if not browser:
            messagebox.showwarning("No Browser", "Select a browser first")
            return

        def remove():
            malicious = bpm.detect_malicious_extensions(browser)
            removed = 0
            for ext in malicious:
                if bpm.remove_extension(browser, ext.id):
                    removed += 1

            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Removed {removed} suspicious extension(s) from {browser}"))
            self._load_extensions()

        threading.Thread(target=remove, daemon=True).start()

    def on_activate(self):
        self._on_refresh()
