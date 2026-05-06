"""Internet Booster page — DNS optimization, TCP tweaks, network monitoring."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import internet_booster as ib


class InternetBoosterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Internet Booster", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="DNS optimization and TCP tuning",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # DNS section
        self._build_dns_section(body)

        # TCP section
        self._build_tcp_section(body)

    def _build_dns_section(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=False, pady=(0, 12))
        SectionLabel(card, "DNS Benchmark & Optimization").pack(anchor="w", padx=10, pady=8)

        # DNS status
        self._dns_status = tk.Label(card, text="Current DNS: Loading...",
                                    bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._dns_status.pack(anchor="w", padx=10, pady=4)

        # Benchmark results
        self._dns_results = tk.Label(card, text="", bg=T.PANEL, fg=T.FG,
                                     font=T.FONT_SMALL, justify="left")
        self._dns_results.pack(anchor="w", padx=10, pady=4)

        # Progress
        self._dns_progress = ProgressBar(card)
        self._dns_progress.pack(fill="x", padx=10, pady=(4, 8))

        # Action buttons
        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Benchmark DNS",
                     command=self._on_benchmark_dns).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Optimize to Best",
                     command=self._on_optimize_dns).pack(side="left", padx=0)

    def _build_tcp_section(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=False, pady=(0, 12))
        SectionLabel(card, "TCP Optimization").pack(anchor="w", padx=10, pady=8)

        self._tcp_status = tk.Label(card, text="TCP settings: Loading...",
                                    bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._tcp_status.pack(anchor="w", padx=10, pady=4)

        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Apply TCP Tweaks",
                     command=self._on_optimize_tcp).pack(side="left", padx=0)

    def _on_benchmark_dns(self):
        self._dns_progress.set_value(0)
        self._dns_results.config(text="Benchmarking...")

        def benchmark():
            try:
                results = ib.dns_benchmark()
                text = "Benchmark Results (ms):\n"
                for name, latency in results.items():
                    text += f"  {name}: {latency:.1f}ms\n"
                self._dns_results.config(text=text)
                self._dns_progress.set_value(100)
            except Exception as e:
                self._dns_results.config(text=f"Error: {e}")
                self._dns_progress.set_value(0)

        threading.Thread(target=benchmark, daemon=True).start()

    def _on_optimize_dns(self):
        def optimize():
            try:
                results = ib.dns_benchmark()
                best = min(results.items(), key=lambda x: x[1])
                best_name = best[0]

                # Map DNS name to IP address
                dns_map = {
                    "Cloudflare": "1.1.1.1",
                    "Google": "8.8.8.8",
                    "Quad9": "9.9.9.9",
                }

                if best_name in dns_map:
                    ip = dns_map[best_name]
                    ib.set_dns(ip)
                    self._dns_status.config(text=f"Current DNS: {best_name} ({ip}) — ✓ Optimized")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to set DNS: {e}")

        threading.Thread(target=optimize, daemon=True).start()

    def _on_optimize_tcp(self):
        def optimize():
            try:
                ib.optimize_tcp()
                self._tcp_status.config(text="TCP settings: ✓ Optimized")
                messagebox.showinfo("Success", "TCP optimization applied successfully")
            except Exception as e:
                messagebox.showerror("Error", f"TCP optimization failed: {e}")

        threading.Thread(target=optimize, daemon=True).start()

    def on_activate(self):
        pass
