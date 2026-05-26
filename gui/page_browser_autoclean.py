"""Browser Auto-Clean page — automatic cleanup when browser exits."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import browser_autoclean as bac


class BrowserAutoCleanPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._enabled_var = tk.BooleanVar(value=bac.is_enabled())
        self._cat_vars = {}   # (process, cat) → BooleanVar
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🌐  Browser Auto-Clean", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Automatically clean browsers when they exit",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Master toggle
        toggle_card = Card(body)
        toggle_card.pack(fill="x", pady=(0, 12))

        row = tk.Frame(toggle_card, bg=T.PANEL)
        row.pack(fill="x", padx=12, pady=12)

        tk.Label(row, text="Auto-Clean Daemon",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_H2).pack(side="left")
        ToggleSwitch(row, variable=self._enabled_var,
                      command=self._on_toggle).pack(side="left", padx=12)

        self._status_lbl = tk.Label(row,
                                      text="● Active" if bac.is_enabled() else "○ Inactive",
                                      bg=T.PANEL,
                                      fg=T.SUCCESS if bac.is_enabled() else T.FG2,
                                      font=T.FONT_BODY)
        self._status_lbl.pack(side="left", padx=12)

        tk.Label(toggle_card,
                 text="When enabled, FSD watches selected browsers in the "
                      "background.\nAs soon as one is closed, the chosen categories "
                      "are wiped from disk.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 justify="left", anchor="w").pack(fill="x", padx=12, pady=(0, 12))

        # Browser cards
        scroll_card = Card(body)
        scroll_card.pack(fill="both", expand=True)
        SectionLabel(scroll_card, "Browsers & Cleanup Categories").pack(
            anchor="w", padx=12, pady=8)

        canvas = tk.Canvas(scroll_card, bg=T.PANEL, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        scrollbar = ttk.Scrollbar(scroll_card, orient="vertical",
                                    command=canvas.yview)
        scrollbar.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))
        canvas.configure(yscrollcommand=scrollbar.set)

        inner = tk.Frame(canvas, bg=T.PANEL)
        win_id = canvas.create_window(0, 0, window=inner, anchor="nw")

        def _conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _conf_canvas(e):
            canvas.itemconfig(win_id, width=e.width)
        inner.bind("<Configure>", _conf)
        canvas.bind("<Configure>", _conf_canvas)

        # Build per-browser blocks
        cfg = bac.get_config()
        saved = cfg.get("browsers", {})

        for b in bac.list_browsers():
            self._build_browser_block(inner, b, saved.get(b["process"], []))

    def _build_browser_block(self, parent, browser_info, current_cats):
        block = tk.Frame(parent, bg=T.lerp_color(T.PANEL, T.ACCENT, 0.4),
                          padx=12, pady=10)
        block.pack(fill="x", pady=4, padx=4)

        # Header
        hdr = tk.Frame(block, bg=block.cget("bg"))
        hdr.pack(fill="x")

        status = "✓ Detected" if browser_info["installed"] else "✕ Not installed"
        status_c = T.SUCCESS if browser_info["installed"] else T.FG2

        tk.Label(hdr, text=browser_info["label"],
                 bg=block.cget("bg"), fg=T.FG,
                 font=T.FONT_BOLD).pack(side="left")
        tk.Label(hdr, text=f"  {status}",
                 bg=block.cget("bg"), fg=status_c,
                 font=T.FONT_SMALL).pack(side="left")

        # Manual clean button
        ActionButton(hdr, text="Clean Now",
                      command=lambda b=browser_info: self._manual_clean(b),
                      width=100, secondary=True).pack(side="right")

        # Categories
        cats_row = tk.Frame(block, bg=block.cget("bg"))
        cats_row.pack(fill="x", pady=(8, 0))

        for cat in browser_info["categories"]:
            var = tk.BooleanVar(value=cat in current_cats)
            self._cat_vars[(browser_info["process"], cat)] = var

            cb = tk.Checkbutton(cats_row, text=cat,
                                 variable=var,
                                 bg=block.cget("bg"), fg=T.FG,
                                 selectcolor=T.ACCENT,
                                 activebackground=block.cget("bg"),
                                 activeforeground=T.HIGHLIGHT,
                                 font=T.FONT_BODY,
                                 command=lambda b=browser_info: self._save_cats(b))
            cb.pack(side="left", padx=(0, 12))

    def _save_cats(self, browser_info):
        proc = browser_info["process"]
        cats = [c for c in browser_info["categories"]
                if self._cat_vars.get((proc, c)) and self._cat_vars[(proc, c)].get()]
        bac.set_browser_categories(proc, cats)

    def _on_toggle(self):
        if self._enabled_var.get():
            bac.enable()
            self._status_lbl.config(text="● Active", fg=T.SUCCESS)
        else:
            bac.disable()
            self._status_lbl.config(text="○ Inactive", fg=T.FG2)

    def _manual_clean(self, browser_info):
        proc = browser_info["process"]
        cats = [c for c in browser_info["categories"]
                if self._cat_vars.get((proc, c)) and self._cat_vars[(proc, c)].get()]
        if not cats:
            messagebox.showinfo("Clean Now",
                                  "Select at least one category first.")
            return

        def work():
            r = bac.clean_browser(proc, cats)
            if r.get("ok"):
                msg = f"Cleaned {r['removed']} items, freed {r['freed'] / 1024**2:.1f} MB"
                self.after(0, lambda: messagebox.showinfo("Done", msg))
            else:
                self.after(0, lambda: messagebox.showwarning("Clean failed",
                                                                r.get("error", "")))

        threading.Thread(target=work, daemon=True).start()

    def on_activate(self):
        pass
