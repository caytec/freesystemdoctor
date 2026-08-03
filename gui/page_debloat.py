"""Debloat — remove preinstalled Windows Store (UWP) apps.

Covers what the classic uninstaller cannot see: Xbox, Bing News/Weather,
Solitaire, Copilot and friends. System-critical packages are never listed.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import (Card, SectionLabel, ActionButton, PageHeader,
                      ProgressBar, apply_treeview_style, Toast)
from engine import debloat as db


class DebloatPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._apps: list[dict] = []
        self._busy = False
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Debloat Windows",
                   subtitle="Remove preinstalled Store apps you never use",
                   icon="🧹", color=T.WARNING).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        tk.Label(body,
                 text="These are Microsoft Store apps bundled with Windows. "
                      "Removing them frees space and reduces background activity. "
                      "System-critical packages are never shown, and most apps can "
                      "be reinstalled from the Store later.",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=760).pack(anchor="w", pady=(0, 8))

        # controls
        ctl = tk.Frame(body, bg=T.BG)
        ctl.pack(fill="x", pady=(0, 8))
        ActionButton(ctl, text="🔍  Scan apps", width=140,
                     command=self._scan).pack(side="left", padx=(0, 8))
        ActionButton(ctl, text="Select recommended", width=170, secondary=True,
                     command=self._select_recommended).pack(side="left", padx=(0, 8))
        self._remove_btn = ActionButton(ctl, text="🗑  Remove selected", width=180,
                                        danger=True, command=self._remove)
        self._remove_btn.pack(side="left")

        self._show_all = tk.BooleanVar(value=False)
        tk.Checkbutton(ctl, text="Show all removable apps",
                       variable=self._show_all, command=self._render,
                       bg=T.BG, fg=T.FG2, selectcolor=T.ACCENT,
                       activebackground=T.BG, font=T.FONT_SMALL).pack(side="right")

        self._prog = ProgressBar(body)
        self._prog.pack(fill="x", pady=(0, 6))
        self._status = tk.Label(body, text="Click “Scan apps” to begin.",
                                bg=T.BG, fg=T.FG2, font=T.FONT_SMALL, anchor="w")
        self._status.pack(fill="x", pady=(0, 6))

        # list
        card = Card(body)
        card.pack(fill="both", expand=True)
        apply_treeview_style()
        self._tree = ttk.Treeview(card, columns=("desc", "pkg"),
                                  show="tree headings", height=14,
                                  selectmode="extended")
        self._tree.heading("#0", text="App")
        self._tree.heading("desc", text="What it is")
        self._tree.heading("pkg", text="Package")
        self._tree.column("#0", width=200)
        self._tree.column("desc", width=280)
        self._tree.column("pkg", width=250)
        self._tree.pack(fill="both", expand=True, padx=10, pady=10)
        self._tree.tag_configure("rec", foreground=T.WARNING)

    # ── actions ──────────────────────────────────────────────────────────────
    def _scan(self):
        if self._busy:
            return
        self._busy = True
        self._status.config(text="Scanning installed Store apps…")
        self._prog.indeterminate(True)

        def work():
            apps = db.list_removable_apps()
            self.after(0, lambda: self._scanned(apps))

        threading.Thread(target=work, daemon=True).start()

    def _scanned(self, apps: list[dict]):
        self._busy = False
        self._prog.indeterminate(False)
        self._apps = apps
        rec = sum(1 for a in apps if a["recommended"])
        self._status.config(
            text=f"Found {len(apps)} removable app(s) — {rec} recognised as bloat.")
        self._render()

    def _render(self):
        self._tree.delete(*self._tree.get_children())
        show_all = self._show_all.get()
        for a in self._apps:
            if not show_all and not a["recommended"]:
                continue
            self._tree.insert("", "end", iid=a["name"],
                              text=("★ " if a["recommended"] else "   ") + a["friendly"],
                              values=(a["description"], a["name"]),
                              tags=("rec",) if a["recommended"] else ())

    def _select_recommended(self):
        rec = [a["name"] for a in self._apps
               if a["recommended"] and self._tree.exists(a["name"])]
        self._tree.selection_set(rec)
        if not rec:
            messagebox.showinfo("Nothing to select", "Run a scan first.")

    def _remove(self):
        if self._busy:
            return
        sel = list(self._tree.selection())
        if not sel:
            messagebox.showinfo("Nothing selected",
                                "Select the apps you want to remove.")
            return

        names = [(a["name"], a["full_name"]) for a in self._apps if a["name"] in sel]
        friendly = ", ".join(a["friendly"] for a in self._apps
                             if a["name"] in sel)[:300]
        if not messagebox.askyesno(
                "Remove selected apps?",
                f"Remove {len(names)} app(s)?\n\n{friendly}\n\n"
                f"They are removed for your user account and can usually be "
                f"reinstalled from the Microsoft Store.\n\n"
                f"A restore point is created first."):
            return

        self._busy = True
        self._remove_btn.config(state="disabled")
        self._prog.set(0)

        def progress(msg, pct):
            self.after(0, lambda: (self._status.config(text=str(msg)),
                                   self._prog.set(pct)))

        def work():
            try:
                from engine import system_restore
                system_restore.ensure_checkpoint("removing Windows apps")
            except Exception:
                pass
            res = db.remove_apps(names, progress_cb=progress)
            self.after(0, lambda: self._removed(res))

        threading.Thread(target=work, daemon=True).start()

    def _removed(self, res: dict):
        self._busy = False
        self._remove_btn.config(state="normal")
        self._prog.set(100)
        removed, failed = res.get("removed", 0), res.get("failed", 0)
        self._status.config(text=f"Removed {removed}, failed {failed}.")
        if failed:
            fails = "\n".join(f"• {d['name']}: {d['msg']}"
                              for d in res.get("details", []) if not d["ok"])[:600]
            messagebox.showwarning("Finished with issues",
                                   f"Removed {removed} app(s).\n\nCould not remove:\n{fails}")
        else:
            try:
                Toast.show(self.winfo_toplevel(),
                           f"Removed {removed} app(s)", "success")
            except Exception:
                pass
        self._scan()

    def on_activate(self):
        pass
