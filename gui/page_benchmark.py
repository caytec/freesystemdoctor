"""Benchmark page — CPU, RAM, and disk performance testing."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import benchmark as bm


class BenchmarkPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="System Benchmark", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Test CPU, RAM, and disk performance",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Overall progress
        card = Card(body)
        card.pack(fill="both", expand=False, pady=(0, 12))
        SectionLabel(card, "Overall Benchmark").pack(anchor="w", padx=10, pady=8)

        self._overall_progress = ProgressBar(card)
        self._overall_progress.pack(fill="x", padx=10, pady=(0, 12))

        self._overall_status = tk.Label(card, text="Ready to benchmark",
                                       bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY)
        self._overall_status.pack(anchor="w", padx=10, pady=(0, 8))

        # CPU benchmark card
        self._build_bench_card(body, "CPU Benchmark", "cpu")

        # RAM benchmark card
        self._build_bench_card(body, "RAM Benchmark", "ram")

        # Disk benchmark card
        self._build_bench_card(body, "Disk Benchmark", "disk")

    def _build_bench_card(self, parent, title, bench_type):
        card = Card(parent)
        card.pack(fill="both", expand=False, pady=(0, 12))
        SectionLabel(card, title).pack(anchor="w", padx=10, pady=8)

        progress = ProgressBar(card)
        progress.pack(fill="x", padx=10, pady=(0, 8))

        status = tk.Label(card, text="Not run", bg=T.PANEL, fg=T.FG2,
                         font=T.FONT_BODY)
        status.pack(anchor="w", padx=10, pady=(0, 8))

        btn = ActionButton(card, text=f"Run {title}",
                          command=lambda: self._run_benchmark(bench_type, progress, status))
        btn.pack(anchor="w", padx=10, pady=(0, 8))

        setattr(self, f"_{bench_type}_progress", progress)
        setattr(self, f"_{bench_type}_status", status)

    def _run_benchmark(self, bench_type, progress, status):
        progress.set_value(0)
        status.config(text="Running...", fg=T.FG2)

        def run():
            try:
                if bench_type == "cpu":
                    score = bm.cpu_benchmark()
                elif bench_type == "ram":
                    score = bm.ram_benchmark()
                elif bench_type == "disk":
                    score = bm.disk_benchmark()
                else:
                    return

                progress.set_value(score)
                status.config(text=f"Score: {score:.0f}/100", fg=T.SUCCESS)
            except Exception as e:
                status.config(text=f"Error: {e}", fg=T.DANGER)
                progress.set_value(0)

        threading.Thread(target=run, daemon=True).start()

    def on_activate(self):
        pass
