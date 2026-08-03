"""Speed Test — real internet throughput, latency and Wi-Fi signal analysis."""

import threading
import tkinter as tk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, PageHeader
from engine import net_speed as ns


class SpeedTestPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Speed Test",
                   subtitle="Measure your real internet speed and Wi-Fi quality",
                   icon="📶", color=T.INFO).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # ── result panel ────────────────────────────────────────────────
        card = Card(body, glow=True)
        card.pack(fill="x", pady=(0, 12))

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=18, pady=(16, 4))
        self._mbps_lbl = tk.Label(row, text="—", bg=T.PANEL, fg=T.HIGHLIGHT,
                                  font=("Segoe UI", 34, "bold"))
        self._mbps_lbl.pack(side="left")
        tk.Label(row, text=" Mbps", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", pady=(18, 0))
        ActionButton(row, text="▶  Start test", width=150,
                     command=self._run).pack(side="right", pady=(8, 0))

        self._detail_lbl = tk.Label(card, text="Click “Start test” to measure "
                                    "your connection.",
                                    bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                    anchor="w")
        self._detail_lbl.pack(fill="x", padx=18)

        self._prog = ProgressBar(card)
        self._prog.pack(fill="x", padx=18, pady=(8, 16))

        # ── latency ─────────────────────────────────────────────────────
        lat = Card(body)
        lat.pack(fill="x", pady=(0, 12))
        SectionLabel(lat, "Latency").pack(anchor="w", padx=14, pady=(10, 4))
        self._lat_lbl = tk.Label(lat, text="Not measured yet.", bg=T.PANEL,
                                 fg=T.FG, font=T.FONT_BODY, anchor="w")
        self._lat_lbl.pack(fill="x", padx=14, pady=(0, 12))

        # ── Wi-Fi ───────────────────────────────────────────────────────
        wifi = Card(body)
        wifi.pack(fill="both", expand=True)
        hdr = tk.Frame(wifi, bg=T.PANEL)
        hdr.pack(fill="x", padx=14, pady=(10, 4))
        SectionLabel(hdr, "Wi-Fi signal").pack(side="left")
        ActionButton(hdr, text="Refresh", width=100, secondary=True,
                     command=self._refresh_wifi).pack(side="right")

        self._wifi_lbl = tk.Label(wifi, text="", bg=T.PANEL, fg=T.FG,
                                  font=T.FONT_BODY, anchor="w", justify="left")
        self._wifi_lbl.pack(fill="x", padx=14)

        self._wifi_bar = ProgressBar(wifi)
        self._wifi_bar.pack(fill="x", padx=14, pady=(6, 6))

        self._tips_lbl = tk.Label(wifi, text="", bg=T.PANEL, fg=T.FG2,
                                  font=T.FONT_SMALL, anchor="w", justify="left",
                                  wraplength=700)
        self._tips_lbl.pack(fill="x", padx=14, pady=(0, 12))

    # ── actions ──────────────────────────────────────────────────────────────
    def _run(self):
        if self._busy:
            return
        self._busy = True
        self._mbps_lbl.config(text="…")
        self._detail_lbl.config(text="Measuring…")
        self._prog.set(0)

        def progress(msg, pct):
            self.after(0, lambda: (self._detail_lbl.config(text=str(msg)),
                                   self._prog.set(pct)))

        def work():
            lat = ns.measure_latency()
            self.after(0, lambda: self._show_latency(lat))
            res = ns.measure_download(progress_cb=progress)
            self.after(0, lambda: self._show_speed(res))

        threading.Thread(target=work, daemon=True).start()

    def _show_speed(self, res: dict):
        self._busy = False
        if res.get("ok"):
            mbps = res["mbps"]
            self._mbps_lbl.config(
                text=f"{mbps:.0f}",
                fg=T.SUCCESS if mbps >= 50 else T.WARNING if mbps >= 15 else T.DANGER)
            self._detail_lbl.config(
                text=f"Downloaded {res['mb']} MB in {res['seconds']}s "
                     f"via {res['endpoint']}")
            self._prog.set(100)
        else:
            self._mbps_lbl.config(text="—", fg=T.DANGER)
            self._detail_lbl.config(text=f"Test failed: {res.get('error', '')}")
            self._prog.set(0)

    def _show_latency(self, lat: dict):
        if lat.get("ok"):
            self._lat_lbl.config(
                text=f"{lat['avg_ms']} ms average   ·   {lat['min_ms']}–"
                     f"{lat['max_ms']} ms   ·   jitter {lat['jitter_ms']} ms"
                     f"   ·   {lat['loss_pct']}% packet loss",
                fg=T.SUCCESS if lat["avg_ms"] < 50 else T.WARNING)
        else:
            self._lat_lbl.config(text="Could not reach the test host.", fg=T.DANGER)

    def _refresh_wifi(self):
        def work():
            info = ns.get_wifi_info()
            tips = ns.get_wifi_recommendations(info)
            self.after(0, lambda: self._show_wifi(info, tips))

        threading.Thread(target=work, daemon=True).start()

    def _show_wifi(self, info: dict, tips: list):
        if info.get("connected"):
            self._wifi_lbl.config(
                text=f"{info['ssid']}   ·   {info['quality']} "
                     f"({info['signal_pct']}%)   ·   {info['band']}, "
                     f"channel {info['channel']}   ·   {info['radio']}"
                     + (f"   ·   link {info['rx_mbps']:.0f} Mbps"
                        if info.get("rx_mbps") else ""))
            self._wifi_bar.set(info.get("signal_pct", 0))
        else:
            self._wifi_lbl.config(text="Not connected to Wi-Fi "
                                       "(wired connection or no adapter).")
            self._wifi_bar.set(0)
        self._tips_lbl.config(text="\n".join(f"• {t}" for t in tips))

    def on_activate(self):
        self._refresh_wifi()
