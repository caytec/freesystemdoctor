"""Benchmark tab — CPU, RAM, and Disk performance scoring."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import benchmark


def _score_color(score: int) -> str:
    """Return a colour string based on the 0-100 score."""
    if score >= 75:
        return T.SUCCESS
    if score >= 50:
        return T.WARNING
    return T.DANGER


class _BenchCard(tk.Frame):
    """A self-contained card for one benchmark category."""

    def __init__(self, parent, title: str, unit_label: str, run_cmd, **kw):
        kw.setdefault("bg", T.PANEL)
        super().__init__(parent, **kw)
        self._run_cmd = run_cmd

        # Title
        tk.Label(self, text=title, bg=T.PANEL, fg=T.FG,
                 font=T.FONT_H2).pack(pady=(10, 0))

        # Score canvas
        self._canvas = tk.Canvas(self, width=110, height=110,
                                 bg=T.PANEL, highlightthickness=0)
        self._canvas.pack(pady=6)
        self._draw_score(0)

        # Raw measurement label
        self._raw_lbl = tk.Label(self, text=unit_label, bg=T.PANEL,
                                 fg=T.FG2, font=T.FONT_SMALL)
        self._raw_lbl.pack()

        # Last result label
        self._last_lbl = tk.Label(self, text="No result yet", bg=T.PANEL,
                                  fg=T.FG2, font=T.FONT_SMALL)
        self._last_lbl.pack(pady=(2, 6))

        # Progress bar
        self._progress = ProgressBar(self, bg=T.PANEL)
        self._progress.pack(fill="x", padx=10, pady=(0, 4))

        # Run button
        self._run_btn = ActionButton(self, "Run", command=self._run_cmd)
        self._run_btn.pack(pady=(0, 10))

    def _draw_score(self, score: int):
        c = self._canvas
        c.delete("all")
        cx, cy, r = 55, 55, 46
        color = _score_color(score)
        bg_ring = T.lerp_color(T.PANEL, T.BORDER, 0.6)

        # Background ring
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      outline=bg_ring, width=10, fill=T.PANEL)
        # Score arc (0 = full ring at score 100)
        if score > 0:
            extent = int(score / 100 * 360)
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=90, extent=-extent,
                         outline=color, width=10, style="arc")
        # Score text
        c.create_text(cx, cy - 6, text=str(score),
                      fill=color, font=(T.FONT_FAMILY, 26, "bold"))
        c.create_text(cx, cy + 16, text="/100",
                      fill=T.FG2, font=T.FONT_SMALL)

    def set_running(self, running: bool):
        """Toggle indeterminate progress and disable run button while running."""
        self._progress.indeterminate(running)
        self._run_btn.config(state="disabled" if running else "normal")

    def update_result(self, score: int, raw_text: str, last_text: str):
        self._draw_score(score)
        self._raw_lbl.config(text=raw_text)
        self._last_lbl.config(text=last_text)
        self.set_running(False)


class BenchmarkTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._running = False
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header row
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "System Benchmark").pack(side="left", padx=8, pady=8)
        self._run_all_btn = ActionButton(hdr, "Run All Benchmarks",
                                         command=self._run_all)
        self._run_all_btn.pack(side="right", padx=12, pady=6)
        tk.Label(hdr, text="Scores: green >= 75  |  orange >= 50  |  red < 50",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=8)

        # Global progress bar
        self._global_progress = ProgressBar(self, bg=T.BG)
        self._global_progress.pack(fill="x", padx=16, pady=2)

        # Three benchmark cards in a row
        cards_row = tk.Frame(self, bg=T.BG)
        cards_row.pack(fill="both", expand=True, padx=16, pady=8)

        self._cpu_card = _BenchCard(cards_row, "CPU", "ops/sec: —",
                                    run_cmd=self._run_cpu_only)
        self._cpu_card.pack(side="left", fill="both", expand=True,
                            padx=(0, 6))

        self._ram_card = _BenchCard(cards_row, "RAM", "read/write: — MB/s",
                                    run_cmd=self._run_ram_only)
        self._ram_card.pack(side="left", fill="both", expand=True,
                            padx=(6, 6))

        self._disk_card = _BenchCard(cards_row, "Disk", "read/write: — MB/s",
                                     run_cmd=self._run_disk_only)
        self._disk_card.pack(side="left", fill="both", expand=True,
                             padx=(6, 0))

        # Overall score card
        overall_card = Card(self)
        overall_card.pack(fill="x", padx=16, pady=(0, 16))
        overall_row = tk.Frame(overall_card, bg=T.PANEL)
        overall_row.pack(fill="x", padx=12, pady=10)
        tk.Label(overall_row, text="Overall Score:", bg=T.PANEL,
                 fg=T.FG, font=T.FONT_H2).pack(side="left")
        self._overall_lbl = tk.Label(overall_row, text="—",
                                     bg=T.PANEL, fg=T.FG2,
                                     font=(T.FONT_FAMILY, 26, "bold"))
        self._overall_lbl.pack(side="left", padx=12)
        self._overall_sub = tk.Label(overall_row, text="Run benchmarks to see results.",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._overall_sub.pack(side="left", padx=6)

    # ── run all ───────────────────────────────────────────────────────────────

    def _run_all(self):
        if self._running:
            return
        self._running = True
        self._run_all_btn.config(state="disabled")
        self._global_progress.indeterminate(True)
        for card in (self._cpu_card, self._ram_card, self._disk_card):
            card.set_running(True)
        self._status.set("Running all benchmarks… this will take about 15–20 seconds.")
        threading.Thread(target=self._do_run_all, daemon=True).start()

    def _do_run_all(self):
        def cb(msg: str):
            self.after(0, self._status.set, msg)

        try:
            result = benchmark.run_all(progress_cb=cb)
            self.after(0, self._show_all, result)
        except Exception as exc:
            self.after(0, self._status.set, f"Benchmark error: {exc}")
            self.after(0, self._all_done_cleanup)

    def _show_all(self, result: dict):
        self._global_progress.indeterminate(False)
        self._running = False
        self._run_all_btn.config(state="normal")

        cpu  = result.get("cpu", {})
        ram  = result.get("ram", {})
        disk = result.get("disk", {})
        overall = result.get("overall_score", 0)
        ts   = result.get("timestamp", "")

        self._apply_cpu_result(cpu)
        self._apply_ram_result(ram)
        self._apply_disk_result(disk)

        color = _score_color(overall)
        self._overall_lbl.config(text=f"{overall}/100", fg=color)
        self._overall_sub.config(text=f"Last run: {ts}")
        self._status.set(f"Benchmark complete. Overall score: {overall}/100.")

    def _all_done_cleanup(self):
        self._global_progress.indeterminate(False)
        self._running = False
        self._run_all_btn.config(state="normal")
        for card in (self._cpu_card, self._ram_card, self._disk_card):
            card.set_running(False)

    # ── individual benchmarks ─────────────────────────────────────────────────

    def _run_cpu_only(self):
        if self._running:
            return
        self._cpu_card.set_running(True)
        self._status.set("Running CPU benchmark… (~5 seconds)")
        threading.Thread(target=self._do_cpu, daemon=True).start()

    def _do_cpu(self):
        def cb(msg: str):
            self.after(0, self._status.set, msg)
        try:
            result = benchmark.cpu_benchmark(duration_sec=5, progress_cb=cb)
            self.after(0, self._apply_cpu_result, result)
        except Exception as exc:
            self.after(0, self._status.set, f"CPU benchmark error: {exc}")
            self.after(0, self._cpu_card.set_running, False)

    def _apply_cpu_result(self, result: dict):
        score   = result.get("score", 0)
        ops     = result.get("ops_per_sec", 0)
        cores   = result.get("cores_tested", 0)
        dur     = result.get("duration", 0)
        err     = result.get("error", "")
        if err:
            self._cpu_card.update_result(0, f"Error: {err}", "Failed")
            return
        raw  = f"{ops:,} ops/sec  |  {cores} cores"
        last = f"Tested {cores} cores in {dur:.1f}s"
        self._cpu_card.update_result(score, raw, last)

    def _run_ram_only(self):
        if self._running:
            return
        self._ram_card.set_running(True)
        self._status.set("Running RAM benchmark…")
        threading.Thread(target=self._do_ram, daemon=True).start()

    def _do_ram(self):
        def cb(msg: str):
            self.after(0, self._status.set, msg)
        try:
            result = benchmark.ram_benchmark(size_mb=256, progress_cb=cb)
            self.after(0, self._apply_ram_result, result)
        except Exception as exc:
            self.after(0, self._status.set, f"RAM benchmark error: {exc}")
            self.after(0, self._ram_card.set_running, False)

    def _apply_ram_result(self, result: dict):
        score = result.get("score", 0)
        read  = result.get("read_mbps", 0.0)
        write = result.get("write_mbps", 0.0)
        err   = result.get("error", "")
        if err:
            self._ram_card.update_result(0, f"Error: {err}", "Failed")
            return
        raw  = f"R: {read:,.0f} MB/s  |  W: {write:,.0f} MB/s"
        last = f"256 MB buffer  |  avg {(read + write) / 2:,.0f} MB/s"
        self._ram_card.update_result(score, raw, last)

    def _run_disk_only(self):
        if self._running:
            return
        self._disk_card.set_running(True)
        self._status.set("Running Disk benchmark…")
        threading.Thread(target=self._do_disk, daemon=True).start()

    def _do_disk(self):
        def cb(msg: str):
            self.after(0, self._status.set, msg)
        try:
            result = benchmark.disk_benchmark(drive="C:", size_mb=100, progress_cb=cb)
            self.after(0, self._apply_disk_result, result)
        except Exception as exc:
            self.after(0, self._status.set, f"Disk benchmark error: {exc}")
            self.after(0, self._disk_card.set_running, False)

    def _apply_disk_result(self, result: dict):
        score = result.get("score", 0)
        read  = result.get("read_mbps", 0.0)
        write = result.get("write_mbps", 0.0)
        drive = result.get("drive", "C:")
        err   = result.get("error", "")
        if err:
            self._disk_card.update_result(0, f"Error: {err}", "Failed")
            return
        raw  = f"R: {read:,.0f} MB/s  |  W: {write:,.0f} MB/s"
        last = f"Drive {drive}  |  100 MB test file"
        self._disk_card.update_result(score, raw, last)
