"""Bandwidth Monitor page — real-time network usage chart and per-adapter stats."""

import threading
import time
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import bandwidth_monitor as bm


_CHART_W = 400
_CHART_H = 120
_CHART_SAMPLES = 60


class BandwidthMonitorPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._poll_id = None
        self._history_sent = [0.0] * _CHART_SAMPLES
        self._history_recv = [0.0] * _CHART_SAMPLES
        self._adapter_var = tk.StringVar(value="All")
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Bandwidth Monitor", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Real-time network usage per adapter",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Top: adapter selector + current rates
        top = tk.Frame(body, bg=T.BG)
        top.pack(fill="x", pady=(0, 12))

        ctrl_card = Card(top)
        ctrl_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(ctrl_card, "Adapter").pack(anchor="w", padx=10, pady=8)
        row = tk.Frame(ctrl_card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(row, text="Show:", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._adapter_cb = ttk.Combobox(row, textvariable=self._adapter_var,
                                        values=["All"], state="readonly", width=20)
        self._adapter_cb.pack(side="left", padx=8)
        ActionButton(row, text="Refresh Adapters",
                     command=self._refresh_adapters).pack(side="left")

        rates_card = Card(top)
        rates_card.pack(side="left", fill="both", expand=True)
        SectionLabel(rates_card, "Current Rates").pack(anchor="w", padx=10, pady=8)
        rate_row = tk.Frame(rates_card, bg=T.PANEL)
        rate_row.pack(fill="x", padx=10, pady=(0, 8))
        self._down_label = tk.Label(rate_row, text="Down: -- KB/s",
                                    bg=T.PANEL, fg=T.SUCCESS, font=T.FONT_H2)
        self._down_label.pack(side="left", padx=(0, 20))
        self._up_label = tk.Label(rate_row, text="Up: -- KB/s",
                                  bg=T.PANEL, fg=T.HIGHLIGHT, font=T.FONT_H2)
        self._up_label.pack(side="left")

        # Chart
        chart_card = Card(body)
        chart_card.pack(fill="x", pady=(0, 12))
        SectionLabel(chart_card, "Network Activity (last 60s)").pack(anchor="w", padx=10, pady=8)

        self._canvas = tk.Canvas(chart_card, bg=T.ACCENT, height=_CHART_H,
                                 highlightthickness=0)
        self._canvas.pack(fill="x", padx=10, pady=(0, 4))

        legend = tk.Frame(chart_card, bg=T.PANEL)
        legend.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(legend, text="-- Download", bg=T.PANEL, fg=T.SUCCESS, font=T.FONT_SMALL).pack(side="left", padx=(0, 16))
        tk.Label(legend, text="-- Upload", bg=T.PANEL, fg=T.HIGHLIGHT, font=T.FONT_SMALL).pack(side="left")
        self._chart_scale = tk.Label(legend, text="Scale: auto", bg=T.PANEL,
                                     fg=T.FG2, font=T.FONT_SMALL)
        self._chart_scale.pack(side="right")

        # Process list
        proc_card = Card(body)
        proc_card.pack(fill="both", expand=True)
        SectionLabel(proc_card, "Active Connections by Process").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(proc_card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("pid", "connections"), height=8)
        self._tree.column("#0", width=250)
        self._tree.column("pid", width=70)
        self._tree.column("connections", width=100)
        self._tree.heading("#0", text="Process")
        self._tree.heading("pid", text="PID")
        self._tree.heading("connections", text="Connections")
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _refresh_adapters(self):
        adapters = ["All"] + bm.get_adapters()
        self._adapter_cb["values"] = adapters

    def _draw_chart(self):
        self._canvas.update_idletasks()
        w = self._canvas.winfo_width()
        h = _CHART_H
        if w < 10:
            return

        self._canvas.delete("all")

        # Grid lines
        for i in range(0, h, h // 4):
            self._canvas.create_line(0, i, w, i, fill=T.BORDER, dash=(2, 4))

        all_vals = self._history_sent + self._history_recv
        max_val = max(max(all_vals), 1024)  # min 1KB/s scale
        self._chart_scale.config(text=f"Scale: {bm._fmt_bytes(max_val)}/s")

        def draw_line(history, color):
            pts = []
            n = len(history)
            for i, val in enumerate(history):
                x = int(i * w / (n - 1)) if n > 1 else 0
                y = h - int(val / max_val * (h - 4)) - 2
                pts.extend([x, y])
            if len(pts) >= 4:
                self._canvas.create_line(pts, fill=color, width=2, smooth=True)

        draw_line(self._history_recv, T.SUCCESS)
        draw_line(self._history_sent, T.HIGHLIGHT)

    def _update_process_list(self):
        procs = bm.get_top_processes(8)
        self._tree.delete(*self._tree.get_children())
        for p in procs:
            self._tree.insert("", "end", text=p["name"],
                              values=(p["pid"], p["connections"]))

    def _poll(self):
        if not self.winfo_ismapped():
            self._poll_id = None
            return

        adapter = self._adapter_var.get()
        rates = bm.get_current_rates()

        if adapter == "All":
            sent = sum(v.get("sent_rate", 0) for v in rates.values())
            recv = sum(v.get("recv_rate", 0) for v in rates.values())
        else:
            data = rates.get(adapter, {})
            sent = data.get("sent_rate", 0)
            recv = data.get("recv_rate", 0)

        self._history_sent.append(sent)
        self._history_recv.append(recv)
        if len(self._history_sent) > _CHART_SAMPLES:
            self._history_sent.pop(0)
            self._history_recv.pop(0)

        self._down_label.config(text=f"Down: {bm._fmt_bytes(recv)}/s")
        self._up_label.config(text=f"Up: {bm._fmt_bytes(sent)}/s")

        self._draw_chart()

        # Update process list every 5 seconds
        if not hasattr(self, "_proc_tick"):
            self._proc_tick = 0
        self._proc_tick += 1
        if self._proc_tick >= 5:
            self._proc_tick = 0
            self._update_process_list()

        self._poll_id = self.after(1000, self._poll)

    def on_activate(self):
        bm.start_monitor()
        self._refresh_adapters()
        if self._poll_id is None:
            self._poll()
