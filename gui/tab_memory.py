"""Memory & Performance tab — RAM trim, power plans, visual effects, process booster."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import memory_optimizer as mo


class MemoryTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._procs = []
        self._build_ui()
        self.after(300, self._refresh_all)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Row 1: RAM gauge + trim card ──────────────────────────────────────
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(12, 4))

        # RAM stats card
        ram_card = Card(top)
        ram_card.pack(side="left", fill="y", padx=(0, 8))
        SectionLabel(ram_card, "RAM Status").pack(anchor="w", padx=8, pady=(6, 2))
        self._ram_info = tk.Label(ram_card, text="Loading...", bg=T.PANEL, fg=T.FG,
                                  font=T.FONT_BODY, justify="left", anchor="w")
        self._ram_info.pack(padx=12, pady=(0, 8), anchor="w")

        # Trim card
        trim_card = Card(top)
        trim_card.pack(side="left", fill="both", expand=True)
        SectionLabel(trim_card, "RAM Optimizer").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(trim_card,
                 text="Trim unused memory from all processes (frees RAM without closing apps)",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, wraplength=320, justify="left"
                 ).pack(padx=10, anchor="w")
        btn_row = tk.Frame(trim_card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=8, pady=6)
        ActionButton(btn_row, "Optimize RAM Now", command=self._trim_ram).pack(side="left")
        self._trim_result = tk.Label(btn_row, text="", bg=T.PANEL, fg=T.HIGHLIGHT,
                                     font=T.FONT_BOLD)
        self._trim_result.pack(side="left", padx=10)
        self._trim_progress = ProgressBar(trim_card, bg=T.PANEL)
        self._trim_progress.pack(fill="x", padx=8, pady=(0, 8))

        # ── Row 2: Power plans + Visual effects ───────────────────────────────
        mid = tk.Frame(self, bg=T.BG)
        mid.pack(fill="x", padx=16, pady=4)

        # Power plans
        pp_card = Card(mid)
        pp_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(pp_card, "Power Plan").pack(anchor="w", padx=8, pady=(6, 2))
        self._pp_var = tk.StringVar(value="Balanced")
        for name in mo.POWER_PLANS:
            tk.Radiobutton(pp_card, text=name, variable=self._pp_var, value=name,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL, font=T.FONT_BODY
                           ).pack(anchor="w", padx=12)
        self._pp_cur = tk.Label(pp_card, text="Current: ...", bg=T.PANEL,
                                fg=T.FG2, font=T.FONT_SMALL)
        self._pp_cur.pack(anchor="w", padx=12, pady=2)
        ActionButton(pp_card, "Apply Power Plan", command=self._apply_power_plan
                     ).pack(padx=8, pady=(4, 8), anchor="w")

        # Visual effects
        ve_card = Card(mid)
        ve_card.pack(side="left", fill="both", expand=True)
        SectionLabel(ve_card, "Visual Effects").pack(anchor="w", padx=8, pady=(6, 2))
        self._ve_var = tk.StringVar(value="custom")
        for label, val in [("Best appearance", "best_appearance"),
                            ("Custom / Default", "custom"),
                            ("Best performance", "best_performance")]:
            tk.Radiobutton(ve_card, text=label, variable=self._ve_var, value=val,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL, font=T.FONT_BODY
                           ).pack(anchor="w", padx=12)
        self._ve_cur = tk.Label(ve_card, text="Current: ...", bg=T.PANEL,
                                fg=T.FG2, font=T.FONT_SMALL)
        self._ve_cur.pack(anchor="w", padx=12, pady=2)
        ActionButton(ve_card, "Apply Visual Effects", command=self._apply_ve
                     ).pack(padx=8, pady=(4, 8), anchor="w")

        # ── Row 3: Process booster ────────────────────────────────────────────
        bot = Card(self)
        bot.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        hdr = tk.Frame(bot, bg=T.PANEL)
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(hdr, "Process Priority Booster").pack(side="left")
        ActionButton(hdr, "Refresh Processes", command=self._load_procs).pack(side="right")
        tk.Label(hdr, text="Select process → set priority →",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=6)

        self._prio_var = tk.StringVar(value="High")
        prio_row = tk.Frame(bot, bg=T.PANEL)
        prio_row.pack(fill="x", padx=8, pady=2)
        for label in ("High", "Above Normal", "Normal", "Below Normal", "Idle"):
            tk.Radiobutton(prio_row, text=label, variable=self._prio_var, value=label,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL, font=T.FONT_SMALL
                           ).pack(side="left", padx=6)
        ActionButton(prio_row, "Set Priority", command=self._boost_selected).pack(side="right", padx=4)

        cols = ("PID", "CPU %", "RAM %")
        self._proc_tv = ttk.Treeview(bot, columns=cols, show="tree headings", height=8)
        apply_treeview_style(self._proc_tv)
        self._proc_tv.heading("#0",    text="Process Name", anchor="w")
        self._proc_tv.heading("PID",   text="PID",   anchor="w")
        self._proc_tv.heading("CPU %", text="CPU %", anchor="w")
        self._proc_tv.heading("RAM %", text="RAM %", anchor="w")
        self._proc_tv.column("#0",    width=200)
        self._proc_tv.column("PID",   width=70)
        self._proc_tv.column("CPU %", width=70)
        self._proc_tv.column("RAM %", width=70)
        sb = ttk.Scrollbar(bot, orient="vertical", command=self._proc_tv.yview)
        self._proc_tv.configure(yscrollcommand=sb.set)
        self._proc_tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

    # ── actions ───────────────────────────────────────────────────────────────

    def _refresh_all(self):
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        detail = mo.get_memory_detail()
        pp = mo.get_active_power_plan()
        ve = mo.get_visual_effects_mode()
        procs = mo.get_running_processes()
        self.after(0, self._apply_refresh, detail, pp, ve, procs)

    def _apply_refresh(self, detail, pp, ve, procs):
        if detail:
            self._ram_info.config(text=(
                f"Total:     {detail['ram_total']}\n"
                f"Used:      {detail['ram_used']}\n"
                f"Available: {detail['ram_available']}\n"
                f"Usage:     {detail['ram_pct']:.0f}%\n"
                f"Swap Used: {detail['swap_used']} / {detail['swap_total']}"
            ))
        self._pp_var.set(pp if pp in mo.POWER_PLANS else "Balanced")
        self._pp_cur.config(text=f"Current: {pp}")
        self._ve_var.set(ve)
        self._ve_cur.config(text=f"Current: {ve.replace('_', ' ').title()}")
        self._procs = procs
        self._populate_procs(procs)

    def _populate_procs(self, procs):
        for item in self._proc_tv.get_children():
            self._proc_tv.delete(item)
        for p in procs[:50]:
            self._proc_tv.insert("", "end", text=p["name"],
                                 values=(p["pid"], p["cpu"], p["ram"]))

    def _load_procs(self):
        threading.Thread(target=lambda: self.after(
            0, self._populate_procs, mo.get_running_processes()), daemon=True).start()

    def _trim_ram(self):
        self._trim_result.config(text="Optimizing...")
        self._trim_progress.indeterminate(True)
        self._status.set("Trimming RAM working sets...")
        threading.Thread(target=self._do_trim, daemon=True).start()

    def _do_trim(self):
        count = [0]
        def cb(n):
            count[0] = n
        trimmed, errors = mo.trim_working_sets(progress_cb=cb)
        self.after(0, self._trim_done, trimmed, errors)

    def _trim_done(self, trimmed, errors):
        self._trim_progress.indeterminate(False)
        self._trim_result.config(text=f"Trimmed {trimmed} processes")
        self._status.set(f"RAM optimized — {trimmed} processes trimmed, {errors} errors.")
        self._refresh_all()

    def _apply_power_plan(self):
        name = self._pp_var.get()
        ok = mo.set_power_plan(name)
        if ok:
            self._pp_cur.config(text=f"Current: {name}")
            self._status.set(f"Power plan set to: {name}")
        else:
            messagebox.showerror("Error", f"Could not set power plan '{name}'.\n(May need administrator rights)")

    def _apply_ve(self):
        mode = self._ve_var.get()
        ok = mo.set_visual_effects(mode)
        label = mode.replace("_", " ").title()
        if ok:
            self._ve_cur.config(text=f"Current: {label}")
            self._status.set(f"Visual effects set to: {label}")
            messagebox.showinfo("Visual Effects", f"Applied: {label}\n\nSome changes take effect after restarting Explorer or logging off.")
        else:
            messagebox.showerror("Error", "Could not apply visual effects settings.")

    def _boost_selected(self):
        sel = self._proc_tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a process first.")
            return
        prio_name = self._prio_var.get()
        prio_map = {
            "High":        mo.HIGH_PRIORITY,
            "Above Normal": mo.ABOVE_NORMAL,
            "Normal":       mo.NORMAL_PRIORITY,
            "Below Normal": mo.BELOW_NORMAL,
            "Idle":         mo.IDLE_PRIORITY,
        }
        prio = prio_map.get(prio_name, mo.NORMAL_PRIORITY)
        ok_count = 0
        for iid in sel:
            vals = self._proc_tv.item(iid, "values")
            if vals:
                try:
                    pid = int(vals[0])
                    if mo.boost_process(pid, prio):
                        ok_count += 1
                except (ValueError, Exception):
                    pass
        self._status.set(f"Set {prio_name} priority on {ok_count} process(es).")
