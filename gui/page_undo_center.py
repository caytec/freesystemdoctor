"""Undo Center — every change this app made, in one list, each one revertible.

Optimizers change dozens of settings and then forget which. This page is the
receipt: a chronological record of every tweak applied, with per-item undo and
a single button to put everything back.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, PageHeader, ProgressBar
from .widgets import apply_treeview_style
from engine import change_ledger as ledger


class UndoCenterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._entries: list[dict] = []
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Undo Center",
                   subtitle="Every change we made — and one click to undo any of it",
                   icon="↩", color=T.SUCCESS).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        card = Card(body)
        card.pack(fill="both", expand=True)

        head = tk.Frame(card, bg=T.PANEL)
        head.pack(fill="x", padx=16, pady=(12, 2))
        SectionLabel(head, "Change history").pack(side="left")
        ActionButton(head, text="Refresh", width=100,
                     command=self._refresh).pack(side="right")

        tk.Label(card,
                 text="Only changes made through FreeSystemDoctor appear here. "
                      "Each row can be undone on its own — the original value "
                      "was saved before the change was applied.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=820).pack(fill="x", padx=16)

        self._only_active = tk.BooleanVar(value=True)
        tk.Checkbutton(card, text="Show only changes that are still active",
                       variable=self._only_active, bg=T.PANEL, fg=T.FG2,
                       activebackground=T.PANEL, activeforeground=T.FG,
                       selectcolor=T.BG, font=T.FONT_SMALL,
                       command=self._refresh).pack(anchor="w", padx=16,
                                                   pady=(6, 2))

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(4, 6))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame,
                                  columns=("when", "area", "status"),
                                  height=14)
        self._tree.column("#0", width=300)
        self._tree.column("when", width=140)
        self._tree.column("area", width=130)
        self._tree.column("status", width=120)
        self._tree.heading("#0", text="Change")
        self._tree.heading("when", text="When")
        self._tree.heading("area", text="Area")
        self._tree.heading("status", text="Status")
        self._tree.tag_configure("active", foreground=T.SUCCESS)
        self._tree.tag_configure("reverted", foreground=T.FG2)
        self._tree.tag_configure("failed", foreground=T.DANGER)

        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        btns = tk.Frame(card, bg=T.PANEL)
        btns.pack(fill="x", padx=16, pady=(0, 6))
        ActionButton(btns, text="↩ Undo selected", width=160,
                     command=self._undo_selected).pack(side="left",
                                                       padx=(0, 8))
        ActionButton(btns, text="Undo everything", width=150, danger=True,
                     command=self._undo_all).pack(side="left", padx=(0, 8))
        ActionButton(btns, text="Clear history", width=130, secondary=True,
                     command=self._clear).pack(side="left")

        self._prog = ProgressBar(card)
        self._prog.pack(fill="x", padx=16, pady=(2, 4))
        self._status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                font=T.FONT_SMALL, anchor="w")
        self._status.pack(fill="x", padx=16, pady=(0, 14))

    # ── data ────────────────────────────────────────────────────────────────
    def _refresh(self):
        def work():
            try:
                entries = ledger.get_entries(
                    limit=300, only_active=bool(self._only_active.get()))
                self.after(0, self._render, entries)
            except Exception as e:
                self.after(0, lambda: self._status.config(text=f"Error: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _render(self, entries: list[dict]):
        self._entries = entries
        self._tree.delete(*self._tree.get_children())
        for i, e in enumerate(entries):
            if not e.get("ok"):
                status, tag = "failed", "failed"
            elif e.get("reverted"):
                status, tag = "undone", "reverted"
            else:
                status, tag = "active", "active"
            self._tree.insert("", "end", iid=str(i), text=e.get("name", "?"),
                              values=(e.get("ts", ""), e.get("module_label", ""),
                                      status),
                              tags=(tag,))
        if not entries:
            self._status.config(
                text="No changes recorded yet. Anything you apply from Deep "
                     "Optimize, GPU Boost, CPU Optimizer or RAM Master will "
                     "show up here.")
        else:
            active = sum(1 for e in entries
                         if e.get("ok") and not e.get("reverted"))
            self._status.config(text=f"{len(entries)} change(s) recorded, "
                                     f"{active} still active.")

    # ── actions ─────────────────────────────────────────────────────────────
    def _undo_selected(self):
        if self._busy:
            return
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Nothing selected",
                                   "Pick the change you want to undo.")
            return
        picked = [self._entries[int(i)] for i in sel
                  if i.isdigit() and int(i) < len(self._entries)]
        if not picked:
            return
        if not messagebox.askyesno(
                "Undo change",
                f"Undo {len(picked)} change(s) and restore the previous "
                f"settings?"):
            return
        self._busy = True

        def work():
            done, failed = 0, []
            for e in picked:
                ok, msg = ledger.revert_entry(e)
                if ok:
                    done += 1
                else:
                    failed.append(f"{e.get('name', '?')}: {msg}")
            self.after(0, self._after_undo, done, failed)

        threading.Thread(target=work, daemon=True).start()

    def _undo_all(self):
        if self._busy:
            return
        if not messagebox.askyesno(
                "Undo everything",
                "Undo every change that is still active and restore your "
                "previous settings?\n\nSome changes need a reboot to fully "
                "take effect."):
            return
        self._busy = True
        self._prog.set(0)

        def progress(msg, pct):
            self.after(0, lambda: (self._status.config(text=str(msg)),
                                   self._prog.set(int(pct))))

        def work():
            try:
                rep = ledger.revert_all(progress_cb=progress)
                self.after(0, self._after_undo, rep["reverted"], rep["failed"])
            except Exception as e:
                self.after(0, self._after_undo, 0, [str(e)])

        threading.Thread(target=work, daemon=True).start()

    def _after_undo(self, done: int, failed: list):
        self._busy = False
        self._prog.set(100)
        if failed:
            messagebox.showwarning(
                "Finished with issues",
                f"Undid {done} change(s).\n\n" + "\n".join(failed[:6]))
        else:
            messagebox.showinfo("Done", f"Undid {done} change(s).")
        self._refresh()

    def _clear(self):
        if not messagebox.askyesno(
                "Clear history",
                "Forget the change history?\n\nThis does NOT undo anything — "
                "the saved original values stay intact, you just stop seeing "
                "the list."):
            return
        ledger.clear_history()
        self._refresh()

    def on_activate(self):
        self._refresh()
