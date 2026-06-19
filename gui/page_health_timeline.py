"""
Health Timeline — trend chart of system-health scores over time, with regression
alerts. Reads engine/health_timeline.py (snapshots persisted on launch + Auto-Pilot).
"""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime

from . import theme as T
from .widgets import Card, PageHeader, SectionLabel, ActionButton, Toast

_METRICS = [
    ("overall",  "Overall",  T.HIGHLIGHT),
    ("privacy",  "Privacy",  T.PURPLE),
    ("space",    "Space",    T.WARNING),
    ("speed",    "Speed",    T.SUCCESS),
    ("security", "Security", T.DANGER),
    ("cpu_pct",  "CPU %",    T.INFO),
    ("ram_pct",  "RAM %",    "#ff80ab"),
]


class HealthTimelinePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._active_metric = "overall"
        self._series: list[tuple[datetime, float]] = []
        self._metric_btns: dict[str, tk.Label] = {}
        self._build_ui()

    def _build_ui(self):
        PageHeader(self, title="Health Timeline",
                   subtitle="Your system health over time",
                   icon="📉", color=T.HIGHLIGHT).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)

        from ._pro_gate import limit_banner
        banner = limit_banner(body, "health_timeline")
        if banner:
            banner.pack(fill="x", pady=(0, 10))

        # Metric selector
        sel = tk.Frame(body, bg=T.BG)
        sel.pack(fill="x", pady=(0, 8))
        for key, label, color in _METRICS:
            b = tk.Label(sel, text=label, bg=T.PANEL, fg=T.FG2,
                         font=T.FONT_SMALL, padx=12, pady=5, cursor="hand2")
            b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, k=key: self._select_metric(k))
            self._metric_btns[key] = b

        # Chart card
        chart_card = Card(body)
        chart_card.pack(fill="both", expand=True)
        from engine import license_manager as lm
        self._window_days = 7 if lm.feature_mode("health_timeline") == "limited" else 30
        SectionLabel(chart_card, f"Trend (last {self._window_days} days)").pack(
            anchor="w", padx=14, pady=(12, 4))
        self._canvas = tk.Canvas(chart_card, bg=T.PANEL, highlightthickness=0, bd=0, height=260)
        self._canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._canvas.bind("<Configure>", lambda e: self._draw_chart())

        # Toolbar
        bar = tk.Frame(body, bg=T.BG)
        bar.pack(fill="x", pady=(10, 0))
        ActionButton(bar, text="Snapshot now", width=130,
                     command=self._snapshot_now).pack(side="left")
        ActionButton(bar, text="Run Auto-Pilot", width=140, secondary=True,
                     command=lambda: self._app.activate_key("autopilot")).pack(side="left", padx=(8, 0))

        # Alerts card
        self._alerts = tk.Frame(body, bg=T.BG)
        self._alerts.pack(fill="x", pady=(12, 0))

        self._select_metric("overall", redraw=False)

    def on_activate(self):
        self._reload()

    # ── data ───────────────────────────────────────────────────────────────
    def _reload(self):
        def work():
            try:
                from engine import health_timeline, license_manager as lm
                days = getattr(self, "_window_days", 30)
                series = health_timeline.get_series(self._active_metric, days=days)
                # Regression alerts are a Pro feature.
                alert = (health_timeline.detect_regression("overall", drop_threshold=10)
                         if lm.is_pro() else None)
            except Exception:
                series, alert = [], None
            parsed = []
            for ts, val in series:
                try:
                    parsed.append((datetime.fromisoformat(ts), float(val)))
                except ValueError:
                    pass
            self.after(0, self._render, parsed, alert)
        threading.Thread(target=work, daemon=True).start()

    def _render(self, series, alert):
        self._series = series
        self._draw_chart()
        for w in self._alerts.winfo_children():
            w.destroy()
        if alert:
            tint = T.lerp_color(T.PANEL, T.DANGER if alert["severity"] == "DANGER" else T.WARNING, 0.16)
            card = tk.Frame(self._alerts, bg=tint)
            card.pack(fill="x")
            tk.Label(card, text="⚠", bg=tint, fg=T.WARNING,
                     font=(T.FONT_FAMILY, 16)).pack(side="left", padx=12, pady=10)
            tk.Label(card,
                     text=f"Health dropped {alert['drop']:.0f} pts "
                          f"(now {alert['latest']:.0f}, was ~{alert['baseline']:.0f}). "
                          f"Run Auto-Pilot to recover.",
                     bg=tint, fg=T.FG, font=T.FONT_SMALL, anchor="w",
                     justify="left", wraplength=620).pack(side="left", pady=10)
            try:
                Toast.show(self._app, f"Health dropped {alert['drop']:.0f} pts since last week", "warning")
            except Exception:
                pass

    def _select_metric(self, key: str, redraw: bool = True):
        self._active_metric = key
        for k, b in self._metric_btns.items():
            color = next((c for kk, _, c in _METRICS if kk == k), T.HIGHLIGHT)
            if k == key:
                b.config(bg=T.lerp_color(T.PANEL, color, 0.30), fg=T.FG)
            else:
                b.config(bg=T.PANEL, fg=T.FG2)
        if redraw:
            self._reload()

    def _snapshot_now(self):
        def work():
            try:
                from engine import health_check, system_info, health_timeline
                health_timeline.record_snapshot(
                    health_check.get_health_scores(),
                    system_info.get_live_metrics(),
                    source="manual")
            except Exception:
                pass
            self.after(0, self._reload)
        threading.Thread(target=work, daemon=True).start()
        try:
            Toast.show(self._app, "Snapshot recorded", "info")
        except Exception:
            pass

    # ── chart ──────────────────────────────────────────────────────────────
    def _metric_color(self) -> str:
        return next((c for k, _, c in _METRICS if k == self._active_metric), T.HIGHLIGHT)

    def _draw_chart(self):
        c = self._canvas
        try:
            c.delete("all")
        except tk.TclError:
            return
        w = c.winfo_width() or 600
        h = c.winfo_height() or 260
        pad_l, pad_r, pad_t, pad_b = 42, 16, 16, 28
        plot_w = max(1, w - pad_l - pad_r)
        plot_h = max(1, h - pad_t - pad_b)
        color = self._metric_color()

        # Gridlines + Y labels (0–100)
        for gv in (0, 25, 50, 75, 100):
            y = pad_t + (1 - gv / 100) * plot_h
            c.create_line(pad_l, y, w - pad_r, y, fill=T.BORDER)
            c.create_text(pad_l - 8, y, text=str(gv), fill=T.FG2,
                          font=T.FONT_MICRO, anchor="e")

        if len(self._series) < 2:
            c.create_text(w // 2, h // 2,
                          text="Not enough data yet — run Auto-Pilot or relaunch tomorrow.",
                          fill=T.FG2, font=T.FONT_BODY)
            return

        n = len(self._series)
        xs, ys = [], []
        for i, (_dt, val) in enumerate(self._series):
            x = pad_l + (i * plot_w / (n - 1))
            y = pad_t + (1 - max(0, min(100, val)) / 100) * plot_h
            xs.append(x)
            ys.append(y)

        # Area fill under line
        poly = [pad_l, pad_t + plot_h]
        for x, y in zip(xs, ys):
            poly += [x, y]
        poly += [xs[-1], pad_t + plot_h]
        c.create_polygon(poly, fill=T.lerp_color(color, T.BG, 0.82), outline="")

        # Line
        line_pts = []
        for x, y in zip(xs, ys):
            line_pts += [x, y]
        c.create_line(line_pts, fill=color, width=2, smooth=True)

        # Vertex dots
        for x, y in zip(xs, ys):
            c.create_oval(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill=color, outline="")

        # X labels (first & last date)
        first_dt = self._series[0][0].strftime("%d %b")
        last_dt = self._series[-1][0].strftime("%d %b")
        c.create_text(pad_l, h - pad_b + 12, text=first_dt, fill=T.FG2,
                      font=T.FONT_MICRO, anchor="w")
        c.create_text(w - pad_r, h - pad_b + 12, text=last_dt, fill=T.FG2,
                      font=T.FONT_MICRO, anchor="e")

        # Latest value badge
        c.create_text(xs[-1], ys[-1] - 12, text=f"{self._series[-1][1]:.0f}",
                      fill=color, font=T.FONT_BOLD)
