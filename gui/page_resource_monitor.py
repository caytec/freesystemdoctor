"""Resource Monitor page — real-time system metrics and alerts."""

import threading
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import Card, SectionLabel, apply_treeview_style, ProgressBar
from engine import resource_monitor as rm


class ResourceMonitorPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()
        rm.start_monitoring()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Resource Monitor", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Real-time CPU, RAM, Disk, and Network monitoring",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Current metrics
        self._build_metrics_card(body)

        # Top processes
        self._build_top_processes_card(body)

        # Alerts
        self._build_alerts_card(body)

        # Start refresh loop
        self._start_refresh()

    def _build_metrics_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Current System Metrics").pack(anchor="w", padx=10, pady=8)

        for label, key, unit in [
            ("CPU Usage", "cpu_percent", "%"),
            ("RAM Usage", "ram_percent", "%"),
            ("Disk Usage", "disk_percent", "%"),
        ]:
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=6)

            tk.Label(row, text=label, bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_BODY, width=15, anchor="w").pack(side="left")

            bar = ProgressBar(row)
            bar.pack(side="left", fill="x", expand=True, padx=10)

            value_label = tk.Label(row, text="–%", bg=T.PANEL, fg=T.FG,
                                  font=T.FONT_BODY, width=6)
            value_label.pack(side="left", padx=10)

            setattr(self, f"_{key}_bar", bar)
            setattr(self, f"_{key}_label", value_label)

    def _build_top_processes_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Top Processes (CPU)").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._proc_tree = ttk.Treeview(tree_frame, columns=("pid", "usage"),
                                        show="tree headings", height=8)
        apply_treeview_style(self._proc_tree)
        self._proc_tree.column("#0", width=280)
        self._proc_tree.column("pid", width=80)
        self._proc_tree.column("usage", width=100)
        self._proc_tree.heading("#0", text="Process")
        self._proc_tree.heading("pid", text="PID")
        self._proc_tree.heading("usage", text="CPU %")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._proc_tree.yview)
        self._proc_tree.configure(yscrollcommand=sb.set)
        self._proc_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

    def _build_alerts_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False)

        SectionLabel(card, "Recent Alerts").pack(anchor="w", padx=10, pady=8)

        self._alerts_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_SMALL,
                                   height=4, bd=0, padx=8, pady=6,
                                   state="disabled", wrap="word")
        self._alerts_text.pack(fill="x", padx=10, pady=(0, 8))

    def _start_refresh(self):
        """Start periodic refresh."""
        def refresh():
            while self.winfo_exists():
                metrics = rm.get_current_metrics()
                processes = rm.get_top_processes(metric="cpu", limit=8)
                alerts = rm.get_alerts(limit=10)

                self.after(0, self._update_ui, metrics, processes, alerts)
                threading.Event().wait(3)

        threading.Thread(target=refresh, daemon=True).start()

    def _update_ui(self, metrics, processes, alerts):
        """Update UI with latest data."""
        if not metrics:
            return

        # Update metrics
        for key, bar_attr, label_attr in [
            ("cpu_percent", "_cpu_percent_bar", "_cpu_percent_label"),
            ("ram_percent", "_ram_percent_bar", "_ram_percent_label"),
            ("disk_percent", "_disk_percent_bar", "_disk_percent_label"),
        ]:
            value = metrics.get(key, 0)
            if hasattr(self, bar_attr):
                getattr(self, bar_attr).set_value(value)
                getattr(self, label_attr).config(text=f"{value:.0f}%")

        # Update processes
        self._proc_tree.delete(*self._proc_tree.get_children())
        if processes:
            for proc in processes:
                self._proc_tree.insert(
                    "", "end",
                    text=proc.get("name", "?"),
                    values=(proc.get("pid", "—"),
                            f"{proc.get('usage', 0):.1f}%"),
                )
        else:
            self._proc_tree.insert(
                "", "end", text="(measuring CPU... refresh in a moment)",
                values=("", ""),
            )

        # Update alerts
        self._alerts_text.config(state="normal")
        self._alerts_text.delete("1.0", "end")
        if alerts:
            for alert in alerts:
                color = T.DANGER if alert["severity"] == "CRITICAL" else T.WARNING if alert["severity"] == "HIGH" else T.FG2
                self._alerts_text.insert("end", f"[{alert['severity']}] {alert['message']}\n")
        else:
            self._alerts_text.insert("end", "No active alerts")
        self._alerts_text.config(state="disabled")

    def on_activate(self):
        rm.start_monitoring()
