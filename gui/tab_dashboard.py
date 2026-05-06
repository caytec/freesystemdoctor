"""Dashboard tab — health score + live stats."""

import tkinter as tk
from tkinter import ttk
import threading

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import system_info


class DashboardTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._build_ui()
        self.after(300, self._refresh)
        self.after(2000, self._schedule_live)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top row: score card + gauges
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(16, 8))

        self._score_card = self._make_score_card(top)
        self._score_card.pack(side="left", padx=(0, 12))

        gauges = self._make_gauges(top)
        gauges.pack(side="left", fill="both", expand=True)

        # Middle: static info
        mid = Card(self)
        mid.pack(fill="x", padx=16, pady=4)
        SectionLabel(mid, "System Information").pack(anchor="w", padx=8, pady=(6, 2))
        self._info_tv = self._make_2col_tv(mid)
        self._info_tv.pack(fill="x", padx=8, pady=(0, 8))

        # Bottom: top processes
        bot = Card(self)
        bot.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        hdr = tk.Frame(bot, bg=T.PANEL)
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(hdr, "Top Processes (by RAM)").pack(side="left")
        ActionButton(hdr, "Refresh", command=self._refresh).pack(side="right")
        self._proc_tv = self._make_proc_tv(bot)
        self._proc_tv.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _make_score_card(self, parent):
        card = Card(parent, width=160, height=160)
        card.pack_propagate(False)
        tk.Label(card, text="Health Score", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(pady=(18, 0))
        self._score_lbl = tk.Label(card, text="--", bg=T.PANEL,
                                   fg=T.SUCCESS, font=T.FONT_SCORE)
        self._score_lbl.pack()
        self._score_status = tk.Label(card, text="Calculating...", bg=T.PANEL,
                                      fg=T.FG2, font=T.FONT_SMALL)
        self._score_status.pack()
        return card

    def _make_gauges(self, parent):
        f = Card(parent)
        rows = [
            ("CPU Usage",  "cpu"),
            ("RAM Usage",  "ram"),
            ("Swap Usage", "swap"),
        ]
        self._gauges = {}
        for label, key in rows:
            row = tk.Frame(f, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text=label, bg=T.PANEL, fg=T.FG, font=T.FONT_SMALL,
                     width=12, anchor="w").pack(side="left")
            bar = ttk.Progressbar(row, length=200, mode="determinate", maximum=100)
            bar.pack(side="left", padx=6)
            val_lbl = tk.Label(row, text="--", bg=T.PANEL, fg=T.FG2,
                               font=T.FONT_SMALL, width=8)
            val_lbl.pack(side="left")
            self._gauges[key] = (bar, val_lbl)

        # Battery row (hidden if no battery)
        self._bat_row = tk.Frame(f, bg=T.PANEL)
        self._bat_row.pack(fill="x", padx=10, pady=4)
        tk.Label(self._bat_row, text="Battery", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_SMALL, width=12, anchor="w").pack(side="left")
        self._bat_bar = ttk.Progressbar(self._bat_row, length=200,
                                        mode="determinate", maximum=100)
        self._bat_bar.pack(side="left", padx=6)
        self._bat_lbl = tk.Label(self._bat_row, text="--", bg=T.PANEL,
                                 fg=T.FG2, font=T.FONT_SMALL, width=8)
        self._bat_lbl.pack(side="left")
        self._bat_row.pack_forget()
        return f

    def _make_2col_tv(self, parent):
        tv = ttk.Treeview(parent, columns=("value",), show="tree headings", height=8)
        apply_treeview_style(tv)
        tv.heading("#0", text="Property", anchor="w")
        tv.heading("value", text="Value", anchor="w")
        tv.column("#0", width=220)
        tv.column("value", width=400)
        return tv

    def _make_proc_tv(self, parent):
        cols = ("PID", "CPU %", "RAM %", "Status")
        tv = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        apply_treeview_style(tv)
        widths = {"PID": 60, "CPU %": 70, "RAM %": 70, "Status": 90}
        for c in cols:
            tv.heading(c, text=c, anchor="w")
            tv.column(c, width=widths.get(c, 100), anchor="w")
        # name column via tree
        tv["show"] = "tree headings"
        tv.heading("#0", text="Name", anchor="w")
        tv.column("#0", width=180)
        return tv

    # ── data loading ──────────────────────────────────────────────────────────

    def _refresh(self):
        self._status.set("Refreshing dashboard...")
        threading.Thread(target=self._load_data, daemon=True).start()

    def _load_data(self):
        info = system_info.get_static_info()
        disks = system_info.get_disk_info()
        score, issues = system_info.get_health_score()
        procs = system_info.get_top_processes(15)
        self.after(0, self._apply_data, info, disks, score, issues, procs)

    def _apply_data(self, info, disks, score, issues, procs):
        # Score
        self._score_lbl.config(text=str(score), fg=T.score_color(score))
        if score >= 80:
            status_text = "Healthy"
        elif score >= 50:
            status_text = "Needs Attention"
        else:
            status_text = "Critical"
        self._score_status.config(text=status_text, fg=T.score_color(score))

        # Info tree
        for item in self._info_tv.get_children():
            self._info_tv.delete(item)
        for k, v in info.items():
            self._info_tv.insert("", "end", text=k, values=(v,))
        for disk in disks:
            bar = "█" * int(disk["used_pct"] / 10) + "░" * (10 - int(disk["used_pct"] / 10))
            self._info_tv.insert("", "end",
                text=f"Drive {disk['Drive']}",
                values=(f"{bar}  {disk['Used']} / {disk['Total']} ({disk['Used %']} used, {disk['Free']} free)",))

        # Processes
        for item in self._proc_tv.get_children():
            self._proc_tv.delete(item)
        for p in procs:
            self._proc_tv.insert("", "end", text=p["Name"],
                                 values=(p["PID"], p["CPU %"], p["RAM %"], p["Status"]))

        self._status.set("Dashboard refreshed.")

    # ── live gauge update ──────────────────────────────────────────────────────

    def _schedule_live(self):
        self._update_live()

    def _update_live(self):
        m = system_info.get_live_metrics()
        if m:
            for key, field in (("cpu", "cpu_pct"), ("ram", "ram_pct"), ("swap", "swap_pct")):
                val = m.get(field, 0)
                bar, lbl = self._gauges[key]
                bar["value"] = val
                lbl.config(text=f"{val:.0f}%")

            if "battery_pct" in m:
                self._bat_row.pack(fill="x", padx=10, pady=4)
                self._bat_bar["value"] = m["battery_pct"]
                plug = " ⚡" if m.get("battery_plugged") else ""
                self._bat_lbl.config(text=f"{m['battery_pct']:.0f}%{plug}")
        self.after(2000, self._update_live)
