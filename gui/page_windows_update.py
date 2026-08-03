"""Windows Update — check, defer, exclude and schedule Windows updates.

Surfaces the windows_update_manager engine, which previously had no UI at all.
Deferring updates and excluding a specific KB are features competitors charge
for; here they're free and reversible.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import (Card, SectionLabel, ActionButton, PageHeader,
                      ProgressBar, apply_treeview_style)
from engine import windows_update_manager as wu


class WindowsUpdatePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Windows Update",
                   subtitle="Check, defer and control Windows updates",
                   icon="🔄", color=T.INFO).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_status(body)
        self._build_controls(body)
        self._build_excluded(body)

    def _build_status(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=14, pady=(12, 4))
        self._status_lbl = tk.Label(row, text="Checking…", bg=T.PANEL, fg=T.FG,
                                    font=(T.FONT_FAMILY, 15, "bold"))
        self._status_lbl.pack(side="left")
        ActionButton(row, text="🔍  Check now", width=140,
                     command=self._check).pack(side="right")

        self._last_lbl = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                  font=T.FONT_SMALL, anchor="w")
        self._last_lbl.pack(fill="x", padx=14)

        self._prog = ProgressBar(card)
        self._prog.pack(fill="x", padx=14, pady=(6, 2))

        self._titles = tk.Text(card, height=5, bg=T.ACCENT, fg=T.FG,
                               font=T.FONT_SMALL, relief="flat", wrap="word",
                               state="disabled")
        self._titles.pack(fill="x", padx=14, pady=(4, 12))

    def _build_controls(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Control").pack(anchor="w", padx=14, pady=(10, 6))

        # Defer
        d = tk.Frame(card, bg=T.PANEL)
        d.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(d, text="Pause updates for:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")
        self._defer_days = tk.StringVar(value="7")
        ttk.Combobox(d, textvariable=self._defer_days, width=6, state="readonly",
                     values=("7", "14", "30")).pack(side="left", padx=(0, 8))
        ActionButton(d, text="Pause", width=110,
                     command=self._defer).pack(side="left")
        tk.Label(d, text="  days — useful before a deadline or a big game session",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=6)

        # Install
        i = tk.Frame(card, bg=T.PANEL)
        i.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(i, text="Install pending:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")
        ActionButton(i, text="⬇  Install updates", width=160,
                     command=self._install).pack(side="left")

        # Exclude a KB
        e = tk.Frame(card, bg=T.PANEL)
        e.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(e, text="Block a specific KB:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")
        self._kb_entry = tk.Entry(e, width=14, bg=T.ACCENT, fg=T.FG,
                                  insertbackground=T.FG, relief="flat")
        self._kb_entry.insert(0, "KB5030219")
        self._kb_entry.pack(side="left", padx=(0, 8))
        ActionButton(e, text="Block", width=100,
                     command=self._exclude).pack(side="left")

    def _build_excluded(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, "Blocked updates & history").pack(
            anchor="w", padx=14, pady=(10, 6))

        apply_treeview_style()
        self._tree = ttk.Treeview(card, columns=("info",), show="tree headings",
                                  height=8)
        self._tree.heading("#0", text="Item")
        self._tree.heading("info", text="Details")
        self._tree.column("#0", width=260)
        self._tree.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    # ── actions ──────────────────────────────────────────────────────────────
    def _check(self):
        if self._busy:
            return
        self._busy = True
        self._status_lbl.config(text="Checking Windows Update…", fg=T.FG2)
        self._prog.indeterminate(True)

        def work():
            status = wu.get_update_status()
            self.after(0, lambda: self._show_status(status))

        threading.Thread(target=work, daemon=True).start()

    def _show_status(self, status: dict):
        self._busy = False
        self._prog.indeterminate(False)
        n = status.get("pending_updates", 0)
        self._status_lbl.config(
            text=status.get("status", "Unknown"),
            fg=T.WARNING if n else T.SUCCESS)
        self._last_lbl.config(text=f"Last check: {status.get('last_check') or 'Unknown'}")

        self._titles.config(state="normal")
        self._titles.delete("1.0", "end")
        titles = status.get("titles") or []
        self._titles.insert("end", "\n".join(f"• {t}" for t in titles)
                            if titles else "No pending updates found.")
        self._titles.config(state="disabled")
        self._refresh_list()

    def _defer(self):
        try:
            days = int(self._defer_days.get())
        except ValueError:
            days = 7
        if not messagebox.askyesno(
                "Pause updates",
                f"Pause Windows updates for {days} days?\n\n"
                f"Security fixes will also be delayed — you can resume anytime."):
            return

        def work():
            ok = wu.defer_updates(days)
            self.after(0, lambda: (
                messagebox.showinfo("Updates paused" if ok else "Failed",
                                    f"Updates paused for {days} days." if ok else
                                    "Could not pause updates (admin rights required)."),
                self._refresh_list()))

        threading.Thread(target=work, daemon=True).start()

    def _install(self):
        if not messagebox.askyesno(
                "Install updates",
                "Install all pending Windows updates now?\n\n"
                "Your PC may need to restart afterwards."):
            return
        self._prog.indeterminate(True)

        def work():
            res = wu.install_available_updates()
            self.after(0, lambda: (
                self._prog.indeterminate(False),
                messagebox.showinfo("Windows Update", str(
                    res.get("message") or res.get("status") or "Finished.")),
                self._check()))

        threading.Thread(target=work, daemon=True).start()

    def _exclude(self):
        kb = self._kb_entry.get().strip().upper()
        if not kb.startswith("KB") or len(kb) < 4:
            messagebox.showwarning("Invalid KB", "Enter a KB number, e.g. KB5030219.")
            return
        ok = wu.exclude_update(kb)
        messagebox.showinfo("Blocked" if ok else "Failed",
                            f"{kb} will be skipped." if ok else
                            f"Could not block {kb}.")
        self._refresh_list()

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        try:
            cfg = wu.get_update_config()
            for kb in cfg.get("excluded_kb", []):
                self._tree.insert("", "end", text=f"🚫  {kb}",
                                  values=("blocked — will not install",))
            if cfg.get("defer_updates_days"):
                self._tree.insert("", "end", text="⏸  Updates paused",
                                  values=(f"{cfg['defer_updates_days']} day(s)",))
        except Exception:
            pass
        try:
            for item in (wu.get_update_history() or [])[:15]:
                title = str(item.get("title") or item.get("kb") or "Update")
                when = str(item.get("date") or item.get("installed_on") or "")
                self._tree.insert("", "end", text=f"✓  {title[:60]}", values=(when,))
        except Exception:
            pass

    def on_activate(self):
        self._refresh_list()
        self._check()
