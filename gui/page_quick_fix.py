"""Quick Fix — Simple mode's goal-oriented one-click actions.

Each card runs several Advanced-mode tools in one go, grouped by what the user
wants to achieve (Disk Health, Network Health, RAM Boost, Gaming Booster…).
The card states which Advanced tools it bundles, so switching to Advanced mode
is an obvious next step rather than a mystery.
"""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, ActionButton, ProgressBar, PageHeader, Toast
from engine import quick_fix as qf


class QuickFixPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Quick Fix",
                   subtitle="One click — runs several tools for you",
                   icon="✨", color=T.HIGHLIGHT).pack(fill="x")

        intro = tk.Frame(self, bg=T.BG)
        intro.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(intro,
                 text="Pick what you want to fix. Each action runs a whole set of "
                      "tools for you — no need to hunt through menus.",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=760).pack(anchor="w")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        # ── progress strip (hidden until a run starts) ──────────────────
        self._prog_frame = tk.Frame(body, bg=T.PANEL)
        self._prog_lbl = tk.Label(self._prog_frame, text="", bg=T.PANEL,
                                  fg=T.HIGHLIGHT, font=T.FONT_SMALL, anchor="w")
        self._prog_lbl.pack(fill="x", padx=12, pady=(8, 2))
        self._prog = ProgressBar(self._prog_frame)
        self._prog.pack(fill="x", padx=12, pady=(0, 10))

        # ── bundle cards (2 columns) ────────────────────────────────────
        grid = tk.Frame(body, bg=T.BG)
        grid.pack(fill="both", expand=True)
        self._grid = grid
        for c in range(2):
            grid.columnconfigure(c, weight=1)

        self._buttons = []
        for i, bundle in enumerate(qf.get_bundles()):
            self._build_card(grid, bundle, i // 2, i % 2)

        # ── results ─────────────────────────────────────────────────────
        self._result_card = Card(body)
        self._result_title = tk.Label(self._result_card, text="", bg=T.PANEL,
                                      fg=T.SUCCESS, font=T.FONT_H2, anchor="w")
        self._result_title.pack(fill="x", padx=12, pady=(10, 4))
        self._result_body = tk.Frame(self._result_card, bg=T.PANEL)
        self._result_body.pack(fill="x", padx=12, pady=(0, 10))

    def _build_card(self, parent, bundle: dict, row: int, col: int):
        card = Card(parent, hover_glow=True)
        card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

        head = tk.Frame(card, bg=T.PANEL)
        head.pack(fill="x", padx=12, pady=(12, 2))
        tk.Label(head, text=bundle["icon"], bg=T.PANEL, fg=T.HIGHLIGHT,
                 font=(T.FONT_FAMILY, 20)).pack(side="left", padx=(0, 8))
        tk.Label(head, text=bundle["title"], bg=T.PANEL, fg=T.FG,
                 font=(T.FONT_FAMILY, 13, "bold")).pack(side="left")

        tk.Label(card, text=bundle["desc"], bg=T.PANEL, fg=T.FG,
                 font=T.FONT_SMALL, anchor="w", justify="left",
                 wraplength=330).pack(fill="x", padx=12)
        tk.Label(card, text=bundle["does"], bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_MICRO, anchor="w", justify="left",
                 wraplength=330).pack(fill="x", padx=12, pady=(4, 6))

        # Which Advanced tools this bundles — makes Advanced mode discoverable
        tk.Label(card,
                 text="Advanced tools used:  " + " · ".join(bundle["advanced"]),
                 bg=T.PANEL, fg=T.lerp_color(T.FG2, T.HIGHLIGHT, 0.35),
                 font=T.FONT_MICRO, anchor="w", justify="left",
                 wraplength=330).pack(fill="x", padx=12, pady=(0, 8))

        btn = ActionButton(card, text=f"Run {bundle['title']}", width=190,
                           command=lambda b=bundle: self._run(b))
        btn.pack(anchor="w", padx=12, pady=(0, 12))
        self._buttons.append(btn)

    # ── run ──────────────────────────────────────────────────────────────────
    def _run(self, bundle: dict):
        if self._busy:
            return
        if bundle.get("destructive"):
            if not messagebox.askyesno(
                    f"Run {bundle['title']}?",
                    f"{bundle['does']}\n\n"
                    f"Files older than 24 hours are removed; files currently in "
                    f"use are left alone.\n\nContinue?"):
                return

        self._busy = True
        for b in self._buttons:
            b.config(state="disabled")
        self._prog_frame.pack(fill="x", pady=(0, 10), before=self._grid)
        self._prog.set(0)
        self._prog_lbl.config(text=f"Starting {bundle['title']}…")
        self._result_card.pack_forget()

        def progress(step, pct):
            self.after(0, lambda s=step, p=pct: self._on_progress(s, p))

        def work():
            result = qf.run_bundle(bundle["id"], progress_cb=progress)
            self.after(0, lambda: self._done(result))

        threading.Thread(target=work, daemon=True).start()

    def _on_progress(self, step: str, pct: int):
        try:
            self._prog_lbl.config(text=str(step))
            self._prog.set(max(0, min(100, int(pct))))
        except tk.TclError:
            pass

    def _done(self, result: dict):
        self._busy = False
        for b in self._buttons:
            b.config(state="normal")
        self._prog.set(100)
        self._prog_lbl.config(text="Finished")

        for w in self._result_body.winfo_children():
            w.destroy()
        self._result_title.config(text=f"✓  {result.get('title', '')} — "
                                       f"{result.get('summary', '')}")
        for step in result.get("steps", []):
            row = tk.Frame(self._result_body, bg=T.PANEL)
            row.pack(fill="x", pady=1)
            ok = step.get("ok")
            tk.Label(row, text="✓" if ok else "✗", bg=T.PANEL,
                     fg=T.SUCCESS if ok else T.DANGER,
                     font=T.FONT_BOLD, width=3).pack(side="left")
            tk.Label(row, text=step.get("name", ""), bg=T.PANEL, fg=T.FG,
                     font=T.FONT_SMALL, width=22, anchor="w").pack(side="left")
            tk.Label(row, text=step.get("detail", ""), bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, anchor="w").pack(side="left")
        self._result_card.pack(fill="x", pady=(8, 0))

        try:
            Toast.show(self.winfo_toplevel(),
                       f"{result.get('title','')} finished", "success")
        except Exception:
            pass

    def on_activate(self):
        pass
