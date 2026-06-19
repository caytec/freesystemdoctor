"""
Command Palette (Ctrl+K) — fuzzy search & launch any of the ~56 tools.

A borderless, centered overlay with a search field and a keyboard-navigable result
list. Reads the live nav registry (gui/nav_registry.py) so it never duplicates the menu.
"""

from __future__ import annotations

import tkinter as tk

from . import theme as T
from . import nav_registry

_WIDTH       = 580
_TOP_OFFSET  = 120
_ROW_H       = 40
_MAX_VISIBLE = 8


class CommandPalette(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self._app = app
        self._registry = nav_registry.get_registry()
        self._results: list[nav_registry.NavEntry] = []
        self._rows: list[dict] = []          # [{frame, bar, icon, label, cat, entry}]
        self._sel = 0
        self._closed = False

        self.overrideredirect(True)
        self.configure(bg=T.BORDER)          # 1px border feel via padding frame
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.0)   # fade in
        except tk.TclError:
            pass

        self._build()
        self._bind_keys()

    # ── construction ─────────────────────────────────────────────────────────
    def _build(self):
        # Outer 1px border → inner panel
        outer = tk.Frame(self, bg=T.BORDER)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        body = tk.Frame(outer, bg=T.PANEL)
        body.pack(fill="both", expand=True)

        # Left accent strip
        tk.Frame(body, bg=T.HIGHLIGHT, width=3).pack(side="left", fill="y")

        inner = tk.Frame(body, bg=T.PANEL)
        inner.pack(side="left", fill="both", expand=True)

        # ── Search row ──
        search_row = tk.Frame(inner, bg=T.PANEL)
        search_row.pack(fill="x", padx=14, pady=(12, 8))

        tk.Label(search_row, text="🔍", bg=T.PANEL, fg=T.HIGHLIGHT,
                 font=(T.FONT_FAMILY, 14)).pack(side="left", padx=(0, 8))

        self._var = tk.StringVar()
        self._entry = tk.Entry(
            search_row, textvariable=self._var,
            bg=T.ACCENT, fg=T.FG, insertbackground=T.HIGHLIGHT,
            relief="flat", font=T.FONT_TITLE,
        )
        self._entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._var.trace_add("write", lambda *_: self._on_query_change())

        tk.Label(search_row, text="Esc", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_MICRO).pack(side="right", padx=(8, 0))

        tk.Frame(inner, bg=T.BORDER, height=1).pack(fill="x")

        # ── Results (scrollable canvas) ──
        self._list_wrap = tk.Frame(inner, bg=T.PANEL)
        self._list_wrap.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._list_wrap, bg=T.PANEL,
                                 highlightthickness=0, bd=0,
                                 height=_ROW_H * _MAX_VISIBLE)
        self._canvas.pack(side="left", fill="both", expand=True)

        self._sb = tk.Scrollbar(self._list_wrap, orient="vertical",
                                command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._sb.set)

        self._inner = tk.Frame(self._canvas, bg=T.PANEL)
        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._win, width=e.width))

        # Hint footer
        foot = tk.Frame(inner, bg=T.PANEL)
        foot.pack(fill="x", padx=14, pady=(4, 8))
        tk.Label(foot, text="↑↓ navigate   ⏎ open   Esc close",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_MICRO).pack(side="left")

    def _bind_keys(self):
        for seq, fn in (
            ("<Down>",   lambda e: self._move(+1)),
            ("<Up>",     lambda e: self._move(-1)),
            ("<Return>", lambda e: self._launch()),
            ("<Escape>", lambda e: self._close()),
            ("<Tab>",    lambda e: self._move(+1)),
        ):
            self._entry.bind(seq, fn)
        self.bind("<FocusOut>", self._on_focus_out)

    # ── show / close ─────────────────────────────────────────────────────────
    def show(self):
        self._app.update_idletasks()
        ax = self._app.winfo_rootx()
        aw = self._app.winfo_width()
        ay = self._app.winfo_rooty()
        x = ax + max(0, (aw - _WIDTH) // 2)
        y = ay + _TOP_OFFSET
        self.geometry(f"{_WIDTH}x340+{x}+{y}")
        self._render()
        self.deiconify()
        self.lift()
        self.focus_force()
        self._entry.focus_set()
        self._fade_in()

    def _fade_in(self, step: int = 0):
        if self._closed:
            return
        try:
            a = min(1.0, step * 0.18)
            self.attributes("-alpha", a)
            if a < 1.0:
                self.after(16, lambda: self._fade_in(step + 1))
        except tk.TclError:
            pass

    def _on_focus_out(self, _e=None):
        # Close when focus leaves the palette entirely.
        self.after(120, self._maybe_close_on_blur)

    def _maybe_close_on_blur(self):
        if self._closed:
            return
        try:
            foc = self.focus_get()
        except Exception:
            foc = None
        if foc is None or (str(foc) != str(self) and not str(foc).startswith(str(self))):
            self._close()

    def _close(self, _e=None):
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        except tk.TclError:
            pass

    # ── query / render ───────────────────────────────────────────────────────
    def _on_query_change(self):
        self._render()

    def _render(self):
        for w in self._inner.winfo_children():
            w.destroy()
        self._rows.clear()

        self._results = nav_registry.search(self._var.get(), self._registry)
        self._sel = 0

        if not self._results:
            tk.Label(self._inner, text="No matching tools",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY,
                     anchor="w").pack(fill="x", padx=14, pady=14)
            return

        for i, entry in enumerate(self._results):
            self._rows.append(self._make_row(i, entry))
        self._highlight()

    def _make_row(self, idx: int, entry: nav_registry.NavEntry) -> dict:
        row = tk.Frame(self._inner, bg=T.PANEL, height=_ROW_H)
        row.pack(fill="x")
        row.pack_propagate(False)

        bar = tk.Frame(row, bg=entry.color, width=3)
        bar.pack(side="left", fill="y")

        icon = tk.Label(row, text=entry.icon, bg=T.PANEL, fg=entry.color,
                        font=(T.FONT_FAMILY, 13), width=3)
        icon.pack(side="left", padx=(8, 4))

        label = tk.Label(row, text=entry.label, bg=T.PANEL, fg=T.FG,
                         font=T.FONT_BODY, anchor="w")
        label.pack(side="left", fill="x", expand=True)

        cat = tk.Label(row, text=entry.category_label, bg=T.PANEL, fg=T.FG2,
                       font=T.FONT_MICRO, anchor="e")
        cat.pack(side="right", padx=(4, 12))

        data = {"frame": row, "bar": bar, "icon": icon,
                "label": label, "cat": cat, "entry": entry}

        for w in (row, icon, label, cat):
            w.bind("<Button-1>", lambda e, k=idx: self._click(k))
            w.bind("<Enter>", lambda e, k=idx: self._hover(k))
        return data

    def _click(self, idx: int):
        self._sel = idx
        self._launch()

    def _hover(self, idx: int):
        if idx != self._sel:
            self._sel = idx
            self._highlight()

    def _highlight(self):
        for i, r in enumerate(self._rows):
            entry = r["entry"]
            sel = (i == self._sel)
            bg = T.lerp_color(T.PANEL, entry.color, 0.22) if sel else T.PANEL
            r["frame"].config(bg=bg)
            r["icon"].config(bg=bg)
            r["label"].config(bg=bg, fg=(T.FG if sel else T.FG))
            r["cat"].config(bg=bg)
        self._scroll_into_view()

    def _scroll_into_view(self):
        if not self._rows:
            return
        total = len(self._rows)
        if total <= _MAX_VISIBLE:
            return
        frac = max(0.0, min(1.0, (self._sel - _MAX_VISIBLE + 1) / total))
        if self._sel < _MAX_VISIBLE:
            frac = 0.0
        self._canvas.yview_moveto(frac)

    def _move(self, delta: int):
        if not self._results:
            return "break"
        self._sel = (self._sel + delta) % len(self._results)
        self._highlight()
        return "break"

    def _launch(self):
        if not self._results:
            return "break"
        entry = self._results[self._sel]
        key = entry.key
        self._close()
        try:
            self._app.activate_key(key)
        except Exception:
            pass
        return "break"
