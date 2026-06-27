"""Real-time Dashboard page — continuous system metrics with time-series visualization."""

import threading
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import Card, SectionLabel, ProgressBar, apply_treeview_style
from engine import realtime_monitor as rm


class RealtimeDashboardPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._monitoring = False
        self._build_ui()
        self._start_monitoring()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Real-time Dashboard", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Continuous system metrics monitoring",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_metrics_card(body)
        self._build_trends_card(body)
        self._build_alerts_card(body)

    def _build_metrics_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Current System Metrics").pack(anchor="w", padx=10, pady=8)

        # CPU
        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=6)

        tk.Label(row1, text="CPU", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._cpu_bar = ProgressBar(row1)
        self._cpu_bar.pack(side="left", fill="x", expand=True, padx=10)
        self._cpu_label = tk.Label(row1, text="–%", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY, width=6)
        self._cpu_label.pack(side="left", padx=10)
        self._cpu_trend = tk.Label(row1, text="→", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=2)
        self._cpu_trend.pack(side="left")

        # RAM
        row2 = tk.Frame(card, bg=T.PANEL)
        row2.pack(fill="x", padx=10, pady=6)

        tk.Label(row2, text="RAM", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._ram_bar = ProgressBar(row2)
        self._ram_bar.pack(side="left", fill="x", expand=True, padx=10)
        self._ram_label = tk.Label(row2, text="–%", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY, width=6)
        self._ram_label.pack(side="left", padx=10)
        self._ram_trend = tk.Label(row2, text="→", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=2)
        self._ram_trend.pack(side="left")

        # Disk
        row3 = tk.Frame(card, bg=T.PANEL)
        row3.pack(fill="x", padx=10, pady=(6, 8))

        tk.Label(row3, text="Disk", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._disk_bar = ProgressBar(row3)
        self._disk_bar.pack(side="left", fill="x", expand=True, padx=10)
        self._disk_label = tk.Label(row3, text="–%", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY, width=6)
        self._disk_label.pack(side="left", padx=10)
        self._disk_trend = tk.Label(row3, text="→", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=2)
        self._disk_trend.pack(side="left")

        # Peak stats
        self._stats_label = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._stats_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_trends_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "60-Minute Peak Analysis").pack(anchor="w", padx=10, pady=8)

        # Peak metrics grid (2 columns x 3 rows)
        grid = tk.Frame(card, bg=T.PANEL)
        grid.pack(fill="x", padx=10, pady=8)

        metrics = [
            ("CPU Peak", "cpu_peak"),
            ("CPU Avg", "cpu_avg"),
            ("RAM Peak", "ram_peak"),
            ("RAM Avg", "ram_avg"),
            ("Disk Peak", "disk_peak"),
            ("Disk Avg", "disk_avg"),
        ]

        self._peak_labels = {}
        for i, (label, key) in enumerate(metrics):
            row = tk.Frame(grid, bg=T.PANEL)
            row.pack(fill="x", pady=4)

            tk.Label(row, text=f"{label}:", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, width=12).pack(side="left")
            val_label = tk.Label(row, text="–%", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY)
            val_label.pack(side="left", padx=10)
            self._peak_labels[key] = val_label

    def _build_alerts_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Recent Alerts").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._alert_tree = ttk.Treeview(tree_frame, columns=("metric", "value", "severity"), height=8)
        self._alert_tree.column("#0", width=150)
        self._alert_tree.column("metric", width=80)
        self._alert_tree.column("value", width=80)
        self._alert_tree.column("severity", width=100)
        self._alert_tree.heading("#0", text="Time")
        self._alert_tree.heading("metric", text="Metric")
        self._alert_tree.heading("value", text="Value")
        self._alert_tree.heading("severity", text="Severity")

        self._alert_tree.tag_configure("critical", foreground=T.DANGER)
        self._alert_tree.tag_configure("warning", foreground=T.WARNING)
        self._alert_tree.tag_configure("info", foreground=T.FG2)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._alert_tree.yview)
        self._alert_tree.configure(yscrollcommand=sb.set)
        self._alert_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        self._alert_status = tk.Label(card, text="No alerts", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._alert_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _start_monitoring(self):
        """Start background monitoring."""
        if not self._monitoring:
            self._monitoring = True
            rm.start_monitoring()
            self._update_loop()

    def _update_loop(self):
        """Periodic refresh — gathers metrics OFF the UI thread.

        rm.get_current_metrics() calls psutil.cpu_percent(interval=0.5), which
        blocks for half a second. Running it on the Tk thread froze the whole
        window every 5s; we now sample in a worker and marshal the result back
        via after(0, ...) so the UI stays responsive.
        """
        if not self._monitoring or not self.winfo_exists():
            return

        def gather():
            try:
                data = (rm.get_current_metrics(), rm.get_peak_metrics(minutes=60),
                        rm.get_recent_alerts(limit=15), rm.get_alerts_summary(),
                        rm.get_trend("cpu", minutes=60), rm.get_trend("ram", minutes=60),
                        rm.get_trend("disk", minutes=60))
            except Exception:
                data = None
            try:
                self.after(0, lambda: self._apply_metrics(data))
            except tk.TclError:
                pass

        threading.Thread(target=gather, daemon=True).start()

    def _apply_metrics(self, data):
        if not self._monitoring or not self.winfo_exists():
            return
        if not data:
            self.after(5000, self._update_loop)
            return
        metrics, peaks, alerts, alert_summary, cpu_trend, ram_trend, disk_trend = data

        # Update current metrics
        if metrics:
            cpu_val = metrics.get("cpu", 0)
            ram_val = metrics.get("ram", 0)
            disk_val = metrics.get("disk", 0)

            self._cpu_bar.set(cpu_val)
            self._cpu_label.config(text=f"{cpu_val:.0f}%")

            self._ram_bar.set(ram_val)
            self._ram_label.config(text=f"{ram_val:.0f}%")

            self._disk_bar.set(disk_val)
            self._disk_label.config(text=f"{disk_val:.0f}%")

            # Trends were computed off-thread (cpu_trend/ram_trend/disk_trend)
            trend_char = {"increasing": "↑", "decreasing": "↓", "stable": "→", "unknown": "?"}
            self._cpu_trend.config(text=trend_char.get(cpu_trend, "?"))
            self._ram_trend.config(text=trend_char.get(ram_trend, "?"))
            self._disk_trend.config(text=trend_char.get(disk_trend, "?"))

            # Update peak stats
            self._stats_label.config(
                text=f"Peak CPU: {peaks.get('cpu_peak', 0):.0f}% | Peak RAM: {peaks.get('ram_peak', 0):.0f}% | Peak Disk: {peaks.get('disk_peak', 0):.0f}%"
            )

        # Update peak metrics grid
        for key, label in self._peak_labels.items():
            val = peaks.get(key, 0)
            label.config(text=f"{val:.1f}%")

        # Update alerts tree
        self._alert_tree.delete(*self._alert_tree.get_children())
        for alert in reversed(alerts):
            time_str = alert.timestamp.strftime("%H:%M:%S")
            severity_tag = alert.severity.lower()
            self._alert_tree.insert("", "end", text=time_str,
                                   values=(alert.metric, f"{alert.value:.1f}%", alert.severity),
                                   tags=(severity_tag,))

        # Update alert status
        summary = alert_summary
        status_text = f"Total: {summary['total_alerts']} | Critical: {summary['critical_count']} | Warning: {summary['warning_count']}"
        self._alert_status.config(text=status_text)

        # Schedule next update (every 5 seconds for responsive UI)
        self.after(5000, self._update_loop)

    def on_activate(self):
        self._start_monitoring()
