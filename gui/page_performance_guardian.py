"""
Performance Guardian page — live view + config for the always-on system monitor
(engine/performance_guardian.py). Shows current CPU/RAM/disk, a rolling
sparkline, the guardian's recent actions/alerts, and threshold settings.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime

from . import theme as T
from .widgets import (Card, PageHeader, SectionLabel, ActionButton,
                      ToggleSwitch, MetricCard)
from engine import performance_guardian as pg


class PerformanceGuardianPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._refresh_job = None
        self._cfg = pg.get_config()
        self._build_ui()
        pg.subscribe(self._on_event)
        self.bind("<Destroy>", self._on_destroy, add="+")

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Performance Guardian",
                   subtitle="Continuous monitoring that keeps your PC fast",
                   icon="🛡", color=T.SUCCESS).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)

        # ── Live status ──
        status_card = Card(body)
        status_card.pack(fill="x", pady=(0, 12))
        head = tk.Frame(status_card, bg=T.PANEL)
        head.pack(fill="x", padx=14, pady=(12, 4))
        SectionLabel(head, "Live status").pack(side="left")
        self._state_lbl = tk.Label(head, text="●  starting…", bg=T.PANEL,
                                    fg=T.FG2, font=T.FONT_SMALL)
        self._state_lbl.pack(side="right")

        cards = tk.Frame(status_card, bg=T.PANEL)
        cards.pack(fill="x", padx=10, pady=(0, 6))
        self._cpu_card = MetricCard(cards, "⚙", "CPU", "–%", color=T.HIGHLIGHT)
        self._cpu_card.pack(side="left", padx=4)
        self._ram_card = MetricCard(cards, "🧠", "RAM", "–%", color=T.SUCCESS)
        self._ram_card.pack(side="left", padx=4)
        self._disk_card = MetricCard(cards, "💾", "Disk free", "– GB", color=T.WARNING)
        self._disk_card.pack(side="left", padx=4)
        self._temp_card = MetricCard(cards, "🌡", "Temp", "–", color=T.DANGER)
        self._temp_card.pack(side="left", padx=4)

        self._spark = tk.Canvas(status_card, bg=T.PANEL, highlightthickness=0,
                                bd=0, height=90)
        self._spark.pack(fill="x", padx=14, pady=(4, 12))

        # ── Settings ──
        cfg_card = Card(body)
        cfg_card.pack(fill="x", pady=(0, 12))
        SectionLabel(cfg_card, "Guardian settings").pack(anchor="w", padx=14, pady=(12, 6))

        self._enabled_var = tk.BooleanVar(value=self._cfg["enabled"])
        self._auto_var    = tk.BooleanVar(value=self._cfg["auto_actions"])
        self._notify_var  = tk.BooleanVar(value=self._cfg["notify"])

        self._toggle_row(cfg_card, "Monitoring enabled",
                         "Continuously sample CPU/RAM/disk (read-only).",
                         self._enabled_var)
        self._toggle_row(cfg_card, "Auto-fix (opt-in)",
                         "Automatically trim RAM when memory stays under pressure.",
                         self._auto_var)
        self._toggle_row(cfg_card, "Alerts",
                         "Show a toast when a threshold is crossed.",
                         self._notify_var)

        # Threshold entries
        thr = tk.Frame(cfg_card, bg=T.PANEL)
        thr.pack(fill="x", padx=14, pady=(4, 8))
        self._ram_thr  = self._thr_entry(thr, "RAM alert %", self._cfg["ram_threshold"])
        self._cpu_thr  = self._thr_entry(thr, "CPU alert %", self._cfg["cpu_threshold"])
        self._disk_thr = self._thr_entry(thr, "Min disk free GB", self._cfg["disk_min_free_gb"])

        ActionButton(cfg_card, text="Save settings", width=140,
                     command=self._save_cfg).pack(anchor="w", padx=14, pady=(0, 12))

        # ── Event log ──
        log_card = Card(body)
        log_card.pack(fill="both", expand=True)
        SectionLabel(log_card, "Recent activity").pack(anchor="w", padx=14, pady=(12, 4))
        self._log = tk.Text(log_card, bg=T.ACCENT, fg=T.FG, font=T.FONT_SMALL,
                            height=8, bd=0, padx=10, pady=8, wrap="word",
                            state="disabled")
        self._log.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._populate_log()

    def _toggle_row(self, parent, title, desc, var):
        row = tk.Frame(parent, bg=T.PANEL)
        row.pack(fill="x", padx=14, pady=2)
        ToggleSwitch(row, variable=var, command=self._save_cfg).pack(side="left")
        col = tk.Frame(row, bg=T.PANEL)
        col.pack(side="left", padx=10)
        tk.Label(col, text=title, bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, anchor="w").pack(anchor="w")
        tk.Label(col, text=desc, bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL, anchor="w").pack(anchor="w")

    def _thr_entry(self, parent, label, value):
        col = tk.Frame(parent, bg=T.PANEL)
        col.pack(side="left", padx=(0, 18))
        tk.Label(col, text=label, bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(anchor="w")
        e = tk.Entry(col, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                     width=8, insertbackground=T.FG, relief="flat")
        e.insert(0, str(value))
        e.pack(anchor="w", pady=2)
        return e

    # ── config save ──
    def _save_cfg(self):
        def _num(entry, default, cast=int):
            try:
                return cast(entry.get().strip())
            except Exception:
                return default
        cfg = pg.set_config({
            "enabled":          self._enabled_var.get(),
            "auto_actions":     self._auto_var.get(),
            "notify":           self._notify_var.get(),
            "ram_threshold":    _num(self._ram_thr, self._cfg["ram_threshold"]),
            "cpu_threshold":    _num(self._cpu_thr, self._cfg["cpu_threshold"]),
            "disk_min_free_gb": _num(self._disk_thr, self._cfg["disk_min_free_gb"], float),
        })
        self._cfg = cfg
        # Apply enable/disable immediately
        if cfg["enabled"] and not pg.is_running():
            pg.start()
        elif not cfg["enabled"] and pg.is_running():
            pg.stop()

    # ── live refresh ──
    def on_activate(self):
        if self._refresh_job is None:
            self._refresh()

    def _refresh(self):
        try:
            st = pg.get_status()
            latest = st.get("latest")
            if pg.is_running():
                self._state_lbl.config(text="●  active", fg=T.SUCCESS)
            elif self._cfg.get("enabled"):
                self._state_lbl.config(text="●  starting…", fg=T.WARNING)
            else:
                self._state_lbl.config(text="●  off", fg=T.FG2)
            if latest:
                cpu, ram = latest["cpu"], latest["ram"]
                self._cpu_card.update_value(f"{cpu:.0f}%",
                    color=_lvl_color(cpu, 90, 70))
                self._ram_card.update_value(f"{ram:.0f}%",
                    color=_lvl_color(ram, 88, 70))
                self._disk_card.update_value(f"{latest['disk_free_gb']:.0f} GB")
                self._temp_card.update_value(
                    f"{latest['temp']:.0f}°C" if latest.get("temp") else "n/a")
            self._draw_spark()
        except tk.TclError:
            return
        self._refresh_job = self.after(2000, self._refresh)

    def _draw_spark(self):
        c = self._spark
        try:
            c.delete("all")
        except tk.TclError:
            return
        w = c.winfo_width() or 600
        h = c.winfo_height() or 90
        for series, color in ((pg.get_series("cpu", 120), T.HIGHLIGHT),
                              (pg.get_series("ram", 120), T.SUCCESS)):
            if len(series) < 2:
                continue
            n = len(series)
            pts = []
            for i, v in enumerate(series):
                x = i * w / (n - 1)
                y = h - (max(0, min(100, v)) / 100) * (h - 6) - 3
                pts += [x, y]
            c.create_line(pts, fill=color, width=2, smooth=True)
        # baseline labels
        c.create_text(4, 8, text="100", fill=T.FG2, font=T.FONT_MICRO, anchor="w")
        c.create_text(4, h - 8, text="0", fill=T.FG2, font=T.FONT_MICRO, anchor="w")
        c.create_text(w - 4, 8, text="CPU", fill=T.HIGHLIGHT,
                      font=T.FONT_MICRO, anchor="e")
        c.create_text(w - 4, 20, text="RAM", fill=T.SUCCESS,
                      font=T.FONT_MICRO, anchor="e")

    # ── events ──
    def _populate_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        for evt in pg.get_events(40):
            self._log.insert("end", _fmt_event(evt) + "\n")
        self._log.config(state="disabled")

    def _on_event(self, evt: dict):
        # Called from the guardian thread — marshal to the UI thread.
        try:
            self.after(0, lambda: self._append_event(evt))
        except Exception:
            pass

    def _append_event(self, evt: dict):
        try:
            self._log.config(state="normal")
            self._log.insert("1.0", _fmt_event(evt) + "\n")
            self._log.config(state="disabled")
            if evt["kind"] in ("alert", "action") and self._cfg.get("notify"):
                from .widgets import Toast
                Toast.show(self._app, evt["message"],
                           "warning" if evt["kind"] == "alert" else "success")
        except tk.TclError:
            pass

    def _on_destroy(self, _e=None):
        if self._refresh_job:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None
        pg.unsubscribe(self._on_event)


def _lvl_color(v, hi, mid):
    if v >= hi:
        return T.DANGER
    if v >= mid:
        return T.WARNING
    return T.SUCCESS


def _fmt_event(evt: dict) -> str:
    t = datetime.fromtimestamp(evt["ts"]).strftime("%H:%M:%S")
    icon = {"alert": "⚠", "action": "✓", "info": "•"}.get(evt["kind"], "•")
    return f"[{t}] {icon} {evt['message']}"
