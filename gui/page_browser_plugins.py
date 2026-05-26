"""Browser Plugin Manager page — list and toggle browser extensions."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import browser_plugin_manager as bpm


class BrowserPluginsPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._extensions = []
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Browser Plugin Manager", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Enable and disable extensions in Chrome, Edge and Firefox",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_info_card(body)
        self._build_controls(body)
        self._build_list_card(body)

    def _build_info_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        tk.Label(card,
                 text="Note: Changes to Chrome/Edge require the browser to be closed before editing. Restart the browser to apply changes.",
                 bg=T.PANEL, fg=T.WARNING, font=T.FONT_SMALL, wraplength=650, justify="left",
                 ).pack(anchor="w", padx=10, pady=8)

        self._browsers_label = tk.Label(card, text="Detecting browsers...",
                                        bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._browsers_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_controls(self, parent):
        ctrl = tk.Frame(parent, bg=T.BG)
        ctrl.pack(fill="x", pady=(0, 12))

        ActionButton(ctrl, text="Refresh",
                     command=self._on_refresh).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Enable Selected",
                     command=self._on_enable).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="Disable Selected",
                     command=self._on_disable).pack(side="left")

        tk.Label(ctrl, text="Filter browser:", bg=T.BG, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left", padx=(20, 4))

        self._filter_var = tk.StringVar(value="All")
        self._filter_cb = ttk.Combobox(ctrl, textvariable=self._filter_var,
                                       values=["All", "Chrome", "Edge", "Firefox"],
                                       state="readonly", width=10)
        self._filter_cb.pack(side="left")
        self._filter_cb.bind("<<ComboboxSelected>>", lambda _: self._apply_filter())

    def _build_list_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Extensions").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame,
                                  columns=("browser", "version", "status"),
                                  height=16)
        self._tree.column("#0", width=260)
        self._tree.column("browser", width=80)
        self._tree.column("version", width=80)
        self._tree.column("status", width=80)
        self._tree.heading("#0", text="Extension Name")
        self._tree.heading("browser", text="Browser")
        self._tree.heading("version", text="Version")
        self._tree.heading("status", text="Status")

        self._tree.tag_configure("enabled", foreground=T.SUCCESS)
        self._tree.tag_configure("disabled", foreground=T.DANGER)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        self._summary = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._summary.pack(anchor="w", padx=10, pady=(0, 8))

    def _load(self):
        def load():
            browsers = bpm.get_installed_browsers()
            exts = bpm.get_all_extensions()
            self.after(0, self._populate, exts, browsers)

        threading.Thread(target=load, daemon=True).start()

    def _populate(self, exts: list, browsers: list):
        self._extensions = exts
        browser_str = ", ".join(browsers) if browsers else "None detected"
        self._browsers_label.config(text=f"Detected: {browser_str}")

        # Update filter combobox
        opts = ["All"] + browsers
        self._filter_cb["values"] = opts

        self._render_tree(exts)

    def _render_tree(self, exts: list):
        self._tree.delete(*self._tree.get_children())

        for i, ext in enumerate(exts):
            tag = "enabled" if ext["enabled"] else "disabled"
            status = "Enabled" if ext["enabled"] else "Disabled"
            self._tree.insert("", "end", iid=str(i), text=ext["name"],
                             values=(ext["browser"], ext["version"], status),
                             tags=(tag,))

        enabled_count = sum(1 for e in exts if e["enabled"])
        self._summary.config(text=f"{len(exts)} extensions — {enabled_count} enabled")

    def _apply_filter(self):
        flt = self._filter_var.get()
        if flt == "All":
            filtered = self._extensions
        else:
            filtered = [e for e in self._extensions if e["browser"] == flt]
        self._render_tree(filtered)

    def _on_refresh(self):
        self._summary.config(text="Loading...")
        self._tree.delete(*self._tree.get_children())
        self._load()

    def _on_enable(self):
        self._toggle_selected(enabled=True)

    def _on_disable(self):
        self._toggle_selected(enabled=False)

    def _toggle_selected(self, enabled: bool):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select extensions first")
            return

        indices = [int(iid) for iid in sel]
        exts = [self._extensions[i] for i in indices if i < len(self._extensions)]

        if not exts:
            return

        action = "enable" if enabled else "disable"
        if not messagebox.askyesno("Confirm",
                f"{action.capitalize()} {len(exts)} extension(s)?\n\nClose the browser before applying changes."):
            return

        def toggle():
            messages = []
            for ext in exts:
                ok, msg = bpm.set_extension_enabled(ext, enabled)
                ext["enabled"] = enabled if ok else ext["enabled"]
                if not ok:
                    messages.append(f"{ext['name']}: {msg}")

            if messages:
                self.after(0, lambda: messagebox.showwarning("Some failed",
                    "\n".join(messages[:5])))
            else:
                status = "enabled" if enabled else "disabled"
                self.after(0, lambda: messagebox.showinfo("Done",
                    f"{len(exts)} extension(s) {status}.\nRestart the browser to apply."))

            self.after(0, self._apply_filter)

        threading.Thread(target=toggle, daemon=True).start()

    def on_activate(self):
        if not self._extensions:
            self._load()
