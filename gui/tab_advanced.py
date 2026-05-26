"""Advanced Tools tab — hosts file, env vars, event logs, thumbnail/font cache, context menu."""

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import advanced_tools as at


def _fmt(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


class AdvancedTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._env_system = False
        self._ctx_items = []
        self._build_ui()
        self.after(500, self._refresh_all)

    def _build_ui(self):
        # Use a notebook inside this tab for sub-sections
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self._hosts_frame   = self._make_hosts_tab(nb)
        self._env_frame     = self._make_env_tab(nb)
        self._cache_frame   = self._make_cache_tab(nb)
        self._eventlog_frame = self._make_eventlog_tab(nb)
        self._context_frame = self._make_context_tab(nb)

        nb.add(self._hosts_frame,    text="  Hosts File  ")
        nb.add(self._env_frame,      text="  Env Variables  ")
        nb.add(self._cache_frame,    text="  Caches  ")
        nb.add(self._eventlog_frame, text="  Event Logs  ")
        nb.add(self._context_frame,  text="  Context Menu  ")

    # ── hosts file ────────────────────────────────────────────────────────────

    def _make_hosts_tab(self, parent):
        f = tk.Frame(parent, bg=T.BG)
        hdr = tk.Frame(f, bg=T.BG)
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        SectionLabel(hdr, "Hosts File Editor  (C:\\Windows\\System32\\drivers\\etc\\hosts)").pack(side="left")
        ActionButton(hdr, "Save", command=self._save_hosts).pack(side="right", padx=4)
        ActionButton(hdr, "Reload", command=self._load_hosts).pack(side="right", padx=4)

        add_row = tk.Frame(f, bg=T.BG)
        add_row.pack(fill="x", padx=12, pady=4)
        tk.Label(add_row, text="IP:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._hosts_ip = tk.Entry(add_row, width=16, bg=T.PANEL, fg=T.FG,
                                  insertbackground=T.FG, font=T.FONT_BODY)
        self._hosts_ip.insert(0, "127.0.0.1")
        self._hosts_ip.pack(side="left", padx=4)
        tk.Label(add_row, text="Hostname:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left", padx=(6,0))
        self._hosts_name = tk.Entry(add_row, width=24, bg=T.PANEL, fg=T.FG,
                                    insertbackground=T.FG, font=T.FONT_BODY)
        self._hosts_name.pack(side="left", padx=4)
        ActionButton(add_row, "Add Entry", command=self._add_hosts).pack(side="left", padx=4)

        self._hosts_text = tk.Text(f, bg=T.PANEL, fg=T.FG, insertbackground=T.FG,
                                   font=("Consolas", 10), relief="flat", wrap="none")
        self._hosts_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        return f

    def _load_hosts(self):
        content = at.read_hosts()
        self._hosts_text.delete("1.0", "end")
        self._hosts_text.insert("end", content)

    def _save_hosts(self):
        content = self._hosts_text.get("1.0", "end")
        ok = at.write_hosts(content)
        if ok:
            self._status.set("Hosts file saved.")
        else:
            messagebox.showerror("Error", "Could not save hosts file.\n(Requires administrator rights)")

    def _add_hosts(self):
        ip = self._hosts_ip.get().strip()
        host = self._hosts_name.get().strip()
        if not ip or not host:
            return
        ok = at.add_hosts_entry(ip, host)
        if ok:
            self._load_hosts()
            self._status.set(f"Added hosts entry: {ip} -> {host}")
        else:
            messagebox.showinfo("Already exists", f"{host} is already in hosts file.")

    # ── environment variables ─────────────────────────────────────────────────

    def _make_env_tab(self, parent):
        f = tk.Frame(parent, bg=T.BG)
        hdr = tk.Frame(f, bg=T.BG)
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        SectionLabel(hdr, "Environment Variables").pack(side="left")
        self._env_scope = tk.StringVar(value="User")
        tk.Radiobutton(hdr, text="User", variable=self._env_scope, value="User",
                       bg=T.BG, fg=T.FG, selectcolor=T.ACCENT, activebackground=T.BG,
                       command=self._load_env).pack(side="left", padx=8)
        tk.Radiobutton(hdr, text="System", variable=self._env_scope, value="System",
                       bg=T.BG, fg=T.FG, selectcolor=T.ACCENT, activebackground=T.BG,
                       command=self._load_env).pack(side="left", padx=4)
        ActionButton(hdr, "Refresh", command=self._load_env).pack(side="right")

        add_row = tk.Frame(f, bg=T.BG)
        add_row.pack(fill="x", padx=12, pady=4)
        tk.Label(add_row, text="Name:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._env_name = tk.Entry(add_row, width=18, bg=T.PANEL, fg=T.FG,
                                  insertbackground=T.FG, font=T.FONT_BODY)
        self._env_name.pack(side="left", padx=4)
        tk.Label(add_row, text="Value:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left", padx=(6, 0))
        self._env_value = tk.Entry(add_row, width=34, bg=T.PANEL, fg=T.FG,
                                   insertbackground=T.FG, font=T.FONT_BODY)
        self._env_value.pack(side="left", padx=4)
        ActionButton(add_row, "Set", command=self._set_env).pack(side="left", padx=4)
        ActionButton(add_row, "Delete Selected", command=self._del_env, danger=True).pack(side="left", padx=4)

        cols = ("Value",)
        self._env_tv = ttk.Treeview(f, columns=cols, show="tree headings")
        apply_treeview_style(self._env_tv)
        self._env_tv.heading("#0",    text="Variable", anchor="w")
        self._env_tv.heading("Value", text="Value",    anchor="w")
        self._env_tv.column("#0",    width=200)
        self._env_tv.column("Value", width=500)
        sb = ttk.Scrollbar(f, orient="vertical", command=self._env_tv.yview)
        self._env_tv.configure(yscrollcommand=sb.set)
        self._env_tv.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(4, 10))
        sb.pack(side="right", fill="y", pady=(4, 10), padx=(0, 12))
        self._env_tv.bind("<<TreeviewSelect>>", self._on_env_select)
        return f

    def _load_env(self):
        system = self._env_scope.get() == "System"
        vars_ = at.get_env_vars(system=system)
        for item in self._env_tv.get_children():
            self._env_tv.delete(item)
        for k, v in sorted(vars_.items()):
            self._env_tv.insert("", "end", iid=k, text=k, values=(v,))

    def _on_env_select(self, event):
        sel = self._env_tv.selection()
        if sel:
            name = sel[0]
            val = self._env_tv.item(name, "values")
            self._env_name.delete(0, "end")
            self._env_name.insert(0, name)
            self._env_value.delete(0, "end")
            self._env_value.insert(0, val[0] if val else "")

    def _set_env(self):
        name = self._env_name.get().strip()
        value = self._env_value.get()
        if not name:
            return
        system = self._env_scope.get() == "System"
        ok = at.set_env_var(name, value, system=system)
        if ok:
            self._load_env()
            self._status.set(f"Set env var: {name}")
        else:
            messagebox.showerror("Error", "Could not set environment variable.")

    def _del_env(self):
        sel = self._env_tv.selection()
        if not sel:
            return
        if not messagebox.askyesno("Delete", f"Delete {len(sel)} variable(s)?"):
            return
        system = self._env_scope.get() == "System"
        for name in sel:
            at.delete_env_var(name, system=system)
        self._load_env()
        self._status.set(f"Deleted {len(sel)} variable(s).")

    # ── caches ────────────────────────────────────────────────────────────────

    def _make_cache_tab(self, parent):
        f = tk.Frame(parent, bg=T.BG)
        SectionLabel(f, "System Cache Cleaner").pack(anchor="w", padx=12, pady=(10, 4))

        self._cache_info = tk.Label(f, text="Scanning...", bg=T.BG, fg=T.FG,
                                    font=T.FONT_BODY, justify="left")
        self._cache_info.pack(anchor="w", padx=16, pady=4)

        btn_row = tk.Frame(f, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Clear Thumbnail Cache", command=self._clear_thumb).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Clear Font Cache", command=self._clear_font).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Optimize Drive C:", command=self._defrag).pack(side="left")

        self._cache_progress = ProgressBar(f, bg=T.BG)
        self._cache_progress.pack(fill="x", padx=16, pady=4)
        self._cache_result = tk.Label(f, text="", bg=T.BG, fg=T.HIGHLIGHT, font=T.FONT_BOLD)
        self._cache_result.pack(anchor="w", padx=16)
        return f

    def _refresh_cache_sizes(self):
        thumb = at.get_thumbnail_cache_size()
        font = at.get_font_cache_size()
        self._cache_info.config(text=(
            f"Thumbnail cache: {_fmt(thumb)}\n"
            f"Font cache:      {_fmt(font)}"
        ))

    def _clear_thumb(self):
        self._cache_progress.indeterminate(True)
        self._status.set("Clearing thumbnail cache...")
        def run():
            freed = at.clear_thumbnail_cache(
                progress_cb=lambda m: self.after(0, self._status.set, m))
            self.after(0, self._cache_done, freed, "Thumbnail cache cleared")
        threading.Thread(target=run, daemon=True).start()

    def _clear_font(self):
        self._cache_progress.indeterminate(True)
        self._status.set("Clearing font cache...")
        def run():
            freed = at.clear_font_cache(
                progress_cb=lambda m: self.after(0, self._status.set, m))
            self.after(0, self._cache_done, freed, "Font cache cleared")
        threading.Thread(target=run, daemon=True).start()

    def _defrag(self):
        self._cache_progress.indeterminate(True)
        self._status.set("Optimizing drive C: (may take a while)...")
        from engine.memory_optimizer import optimize_drive
        def run():
            ok = optimize_drive("C",
                                progress_cb=lambda m: self.after(0, self._status.set, m))
            self.after(0, self._cache_done, 0, "Drive optimized" if ok else "Optimization may have failed")
        threading.Thread(target=run, daemon=True).start()

    def _cache_done(self, freed, msg):
        self._cache_progress.indeterminate(False)
        text = msg + (f" — freed {_fmt(freed)}" if freed else "")
        self._cache_result.config(text=text)
        self._status.set(text)
        self._refresh_cache_sizes()

    # ── event logs ────────────────────────────────────────────────────────────

    def _make_eventlog_tab(self, parent):
        f = tk.Frame(parent, bg=T.BG)
        hdr = tk.Frame(f, bg=T.BG)
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        SectionLabel(hdr, "Windows Event Log Cleaner").pack(side="left")
        ActionButton(hdr, "Refresh", command=self._load_event_logs).pack(side="right", padx=4)
        ActionButton(hdr, "Clear Selected", command=self._clear_selected_logs).pack(side="right", padx=4)
        ActionButton(hdr, "Clear All", command=self._clear_all_logs, danger=True).pack(side="right", padx=4)

        self._log_progress = ProgressBar(f, bg=T.BG)
        self._log_progress.pack(fill="x", padx=12, pady=2)

        cols = ("Records", "Size")
        self._log_tv = ttk.Treeview(f, columns=cols, show="headings tree")
        apply_treeview_style(self._log_tv)
        self._log_tv.heading("#0",      text="Log Name", anchor="w")
        self._log_tv.heading("Records", text="Records",  anchor="w")
        self._log_tv.heading("Size",    text="Size",     anchor="w")
        self._log_tv.column("#0",      width=360)
        self._log_tv.column("Records", width=90)
        self._log_tv.column("Size",    width=90)
        sb = ttk.Scrollbar(f, orient="vertical", command=self._log_tv.yview)
        self._log_tv.configure(yscrollcommand=sb.set)
        self._log_tv.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(4, 10))
        sb.pack(side="right", fill="y", pady=(4, 10), padx=(0, 12))
        return f

    def _load_event_logs(self):
        self._log_progress.indeterminate(True)
        self._status.set("Loading event logs...")
        threading.Thread(target=self._do_load_logs, daemon=True).start()

    def _do_load_logs(self):
        logs = at.get_event_log_sizes()
        self.after(0, self._show_logs, logs)

    def _show_logs(self, logs):
        self._log_progress.indeterminate(False)
        for item in self._log_tv.get_children():
            self._log_tv.delete(item)
        for log in logs:
            if log["size"] > 0:
                self._log_tv.insert("", "end", iid=log["name"], text=log["name"],
                                    values=(log["records"], log["size_str"]))
        self._status.set(f"Loaded {len(logs)} event logs.")

    def _clear_selected_logs(self):
        sel = list(self._log_tv.selection())
        if not sel:
            return
        if not messagebox.askyesno("Clear Logs", f"Clear {len(sel)} event log(s)?"):
            return
        self._log_progress.indeterminate(True)
        def run():
            done = sum(1 for name in sel if at.clear_event_log(name))
            self.after(0, self._log_clear_done, done)
        threading.Thread(target=run, daemon=True).start()

    def _clear_all_logs(self):
        if not messagebox.askyesno("Clear ALL Logs",
                                   "Clear ALL Windows Event Logs?\n\nThis will erase diagnostic history."):
            return
        self._log_progress.indeterminate(True)
        def run():
            ok, fail = at.clear_all_event_logs(
                progress_cb=lambda n: self.after(0, self._status.set, f"Clearing: {n}"))
            self.after(0, self._log_clear_done, ok)
        threading.Thread(target=run, daemon=True).start()

    def _log_clear_done(self, done):
        self._log_progress.indeterminate(False)
        self._status.set(f"Cleared {done} event log(s).")
        self._load_event_logs()

    # ── context menu ─────────────────────────────────────────────────────────

    def _make_context_tab(self, parent):
        f = tk.Frame(parent, bg=T.BG)
        hdr = tk.Frame(f, bg=T.BG)
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        SectionLabel(hdr, "Right-Click Context Menu Manager").pack(side="left")
        ActionButton(hdr, "Refresh", command=self._load_context).pack(side="right", padx=4)
        tk.Label(hdr, text="Hide removes item from menu without deleting it",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=10)

        btn_row = tk.Frame(f, bg=T.BG)
        btn_row.pack(fill="x", padx=12, pady=4)
        ActionButton(btn_row, "Hide Selected", command=self._hide_selected).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Show Selected", command=self._show_selected).pack(side="left")

        cols = ("Category", "Hidden")
        self._ctx_tv = ttk.Treeview(f, columns=cols, show="tree headings")
        apply_treeview_style(self._ctx_tv)
        self._ctx_tv.heading("#0",       text="Item Name",  anchor="w")
        self._ctx_tv.heading("Category", text="Category",   anchor="w")
        self._ctx_tv.heading("Hidden",   text="Hidden",     anchor="w")
        self._ctx_tv.column("#0",       width=240)
        self._ctx_tv.column("Category", width=140)
        self._ctx_tv.column("Hidden",   width=70)
        self._ctx_tv.tag_configure("hidden",  foreground=T.FG2)
        self._ctx_tv.tag_configure("visible", foreground=T.FG)
        sb = ttk.Scrollbar(f, orient="vertical", command=self._ctx_tv.yview)
        self._ctx_tv.configure(yscrollcommand=sb.set)
        self._ctx_tv.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(4, 10))
        sb.pack(side="right", fill="y", pady=(4, 10), padx=(0, 12))
        return f

    def _load_context(self):
        threading.Thread(target=lambda: self.after(
            0, self._show_context, at.list_context_menu_items()), daemon=True).start()

    def _show_context(self, items):
        self._ctx_items = items
        for item in self._ctx_tv.get_children():
            self._ctx_tv.delete(item)
        for i, item in enumerate(items):
            hidden = at.is_context_item_hidden(item["hkey"], item["path"], item["name"])
            tag = "hidden" if hidden else "visible"
            self._ctx_tv.insert("", "end", iid=str(i),
                                text=item["label"] or item["name"],
                                values=(item["category"], "Yes" if hidden else "No"),
                                tags=(tag,))
        self._status.set(f"Found {len(items)} context menu items.")

    def _hide_selected(self):
        for iid in self._ctx_tv.selection():
            idx = int(iid)
            item = self._ctx_items[idx]
            at.hide_context_menu_item(item["hkey"], item["path"], item["name"])
        self._load_context()

    def _show_selected(self):
        for iid in self._ctx_tv.selection():
            idx = int(iid)
            item = self._ctx_items[idx]
            at.show_context_menu_item(item["hkey"], item["path"], item["name"])
        self._load_context()

    # ── combined refresh ──────────────────────────────────────────────────────

    def _refresh_all(self):
        self._load_hosts()
        self._load_env()
        self._refresh_cache_sizes()
        self._load_event_logs()
        self._load_context()
