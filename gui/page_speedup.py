"""Speed Up page — Smart RAM App, power plans, visual effects, startup optimizer."""

import threading
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch, RAMGauge, apply_treeview_style
from engine import memory_optimizer as mo
from engine import ram_daemon as rd
from engine import startup_manager


def _fmt_mb(mb):
    if mb >= 1024:
        return f"{mb/1024:.1f} GB"
    return f"{mb} MB"


class SpeedUpPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._daemon = rd.daemon
        self._build_ui()
        self._loop_started = False

    def on_activate(self):
        if not self._loop_started:
            self._loop_started = True
            self._update_ram_loop()
            self._load_startup()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Speed Up", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Optimize RAM, startup and performance settings",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Top row: RAM card + Power card + Visual effects card
        top = tk.Frame(body, bg=T.BG)
        top.pack(fill="x", pady=(0, 10))
        self._build_ram_card(top)
        self._build_power_card(top)
        self._build_visual_card(top)

        # Bottom: startup list
        self._build_startup_card(body)

    def _build_ram_card(self, parent):
        card = Card(parent)
        card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(card, "Smart RAM App").pack(anchor="w", padx=10, pady=(8, 2))

        self._gauge = RAMGauge(card)
        self._gauge.pack(pady=4)

        # Auto-clean toggle
        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=4)
        tk.Label(row, text="Auto-Clean RAM", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._auto_var = tk.BooleanVar(value=self._daemon.enabled)
        self._auto_toggle = ToggleSwitch(row, variable=self._auto_var,
                                         command=self._toggle_auto)
        self._auto_toggle.pack(side="right")

        # Threshold
        thr_row = tk.Frame(card, bg=T.PANEL)
        thr_row.pack(fill="x", padx=10, pady=2)
        tk.Label(thr_row, text="Trigger at RAM %:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")
        self._threshold_var = tk.IntVar(value=int(self._daemon.threshold_pct))
        threshold_spin = tk.Spinbox(thr_row, from_=50, to=95, increment=5,
                                    textvariable=self._threshold_var, width=5,
                                    bg=T.ACCENT, fg=T.FG, buttonbackground=T.ACCENT,
                                    font=T.FONT_SMALL, command=self._apply_threshold)
        threshold_spin.pack(side="right")

        # Interval
        int_row = tk.Frame(card, bg=T.PANEL)
        int_row.pack(fill="x", padx=10, pady=2)
        tk.Label(int_row, text="Check interval (sec):", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")
        self._interval_var = tk.IntVar(value=self._daemon.interval_sec)
        tk.Spinbox(int_row, from_=10, to=600, increment=10,
                   textvariable=self._interval_var, width=5,
                   bg=T.ACCENT, fg=T.FG, buttonbackground=T.ACCENT,
                   font=T.FONT_SMALL, command=self._apply_interval).pack(side="right")

        # Stats
        self._ram_stats = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                   font=T.FONT_SMALL, justify="left")
        self._ram_stats.pack(anchor="w", padx=10, pady=4)

        ActionButton(card, "Optimize RAM Now", command=self._optimize_now
                     ).pack(fill="x", padx=10, pady=(4, 10))

    def _build_power_card(self, parent):
        card = Card(parent)
        card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(card, "Power Plan").pack(anchor="w", padx=10, pady=(8, 4))

        self._pp_var = tk.StringVar(value=mo.get_active_power_plan())
        for name in mo.POWER_PLANS:
            icon = {"High Performance": "⚡", "Balanced": "⚖", "Power Saver": "🔋"}.get(name, "")
            tk.Radiobutton(card, text=f" {icon} {name}", variable=self._pp_var, value=name,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL, font=T.FONT_BODY
                           ).pack(anchor="w", padx=14, pady=4)

        self._pp_label = tk.Label(card, text=f"Current: {self._pp_var.get()}",
                                   bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._pp_label.pack(anchor="w", padx=14)
        ActionButton(card, "Apply Power Plan", command=self._apply_power
                     ).pack(fill="x", padx=10, pady=(8, 10))

    def _build_visual_card(self, parent):
        card = Card(parent)
        card.pack(side="left", fill="both", expand=True)
        SectionLabel(card, "Visual Effects").pack(anchor="w", padx=10, pady=(8, 4))

        current = mo.get_visual_effects_mode()
        self._ve_var = tk.StringVar(value=current)
        for label, val in [("Best appearance",   "best_appearance"),
                            ("Custom (default)",  "custom"),
                            ("Best performance",  "best_performance")]:
            tk.Radiobutton(card, text=label, variable=self._ve_var, value=val,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL, font=T.FONT_BODY
                           ).pack(anchor="w", padx=14, pady=4)

        self._ve_label = tk.Label(card, text=f"Current: {current.replace('_',' ').title()}",
                                   bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._ve_label.pack(anchor="w", padx=14)
        ActionButton(card, "Apply Visual Effects", command=self._apply_ve
                     ).pack(fill="x", padx=10, pady=(8, 10))

    def _build_startup_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        hdr = tk.Frame(card, bg=T.PANEL)
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(hdr, "Startup Programs").pack(side="left")
        ActionButton(hdr, "Refresh", command=self._load_startup).pack(side="right")
        ActionButton(hdr, "Toggle Selected", command=self._toggle_startup).pack(side="right", padx=4)

        cols = ("Source", "Command", "Status")
        self._st_tv = ttk.Treeview(card, columns=cols, show="tree headings", height=6)
        apply_treeview_style(self._st_tv)
        self._st_tv.heading("#0",     text="Name",    anchor="w")
        self._st_tv.heading("Source", text="Source",  anchor="w")
        self._st_tv.heading("Command",text="Command", anchor="w")
        self._st_tv.heading("Status", text="Status",  anchor="w")
        self._st_tv.column("#0",     width=180)
        self._st_tv.column("Source", width=110)
        self._st_tv.column("Command",width=320)
        self._st_tv.column("Status", width=75)
        self._st_tv.tag_configure("enabled",  foreground=T.SUCCESS)
        self._st_tv.tag_configure("disabled", foreground=T.DANGER)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._st_tv.yview)
        self._st_tv.configure(yscrollcommand=sb.set)
        self._st_tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))
        self._entries: list[startup_manager.StartupEntry] = []

    # ── actions ───────────────────────────────────────────────────────────────

    def _update_ram_loop(self):
        try:
            s = self._daemon.get_status()
            if s:
                from engine.memory_optimizer import _fmt
                self._gauge.update_gauge(
                    s["ram_pct"],
                    _fmt(s["ram_used"]),
                    _fmt(s["ram_total"])
                )
                last = s["last_clean"]
                freed = s["last_freed_mb"]
                total_freed = s["total_freed_mb"]
                count = s["clean_count"]
                self._ram_stats.config(text=(
                    f"Auto-clean: {'ON' if s['enabled'] else 'OFF'}  |  "
                    f"Threshold: {s['threshold']:.0f}%\n"
                    f"Last clean: {last}  |  Freed: {freed} MB\n"
                    f"Total cleans: {count}  |  Total freed: {_fmt(total_freed*1024*1024)}"
                ))
        except Exception:
            pass
        self.after(2000, self._update_ram_loop)

    def _toggle_auto(self):
        self._daemon.enabled = self._auto_var.get()
        status = "ON" if self._daemon.enabled else "OFF"
        if self._daemon.enabled:
            self._daemon.start()

    def _apply_threshold(self):
        self._daemon.threshold_pct = float(self._threshold_var.get())

    def _apply_interval(self):
        self._daemon.interval_sec = int(self._interval_var.get())

    def _optimize_now(self):
        def run():
            freed_mb = self._daemon.trigger_now()
            self.after(0, lambda: self._ram_stats.config(
                text=f"Optimization complete — freed ~{freed_mb} MB"))
        threading.Thread(target=run, daemon=True).start()

    def _apply_power(self):
        name = self._pp_var.get()
        ok = mo.set_power_plan(name)
        if ok:
            self._pp_label.config(text=f"Current: {name}")
        else:
            from tkinter import messagebox
            messagebox.showerror("Error", "Could not set power plan. (May need admin rights)")

    def _apply_ve(self):
        mo.set_visual_effects(self._ve_var.get())
        self._ve_label.config(text=f"Current: {self._ve_var.get().replace('_',' ').title()}")

    def _load_startup(self):
        threading.Thread(target=self._do_load_startup, daemon=True).start()

    def _do_load_startup(self):
        entries = startup_manager.get_startup_entries()
        self.after(0, self._show_startup, entries)

    def _show_startup(self, entries):
        self._entries = entries
        for item in self._st_tv.get_children():
            self._st_tv.delete(item)
        for i, e in enumerate(entries):
            tag = "enabled" if e.enabled else "disabled"
            self._st_tv.insert("", "end", iid=str(i), text=e.name,
                                values=(e.source, e.command[:60],
                                        "Enabled" if e.enabled else "Disabled"),
                                tags=(tag,))

    def _toggle_startup(self):
        sel = self._st_tv.selection()
        for iid in sel:
            idx = int(iid)
            e = self._entries[idx]
            ok = startup_manager.toggle_entry(e)
            if ok:
                tag = "enabled" if e.enabled else "disabled"
                self._st_tv.item(iid, values=(e.source, e.command[:60],
                                               "Enabled" if e.enabled else "Disabled"),
                                  tags=(tag,))
