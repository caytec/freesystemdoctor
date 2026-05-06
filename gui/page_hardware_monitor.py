"""Hardware Monitor page — CPU/GPU/disk temperature and thermal health."""

import threading
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import hardware_monitor as hm


class HardwareMonitorPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._monitoring = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Hardware Monitor", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Real-time CPU, GPU, and disk temperature monitoring",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Thermal health card
        self._build_thermal_card(body)

        # Temperature display
        self._build_temps_card(body)

        # Fan info card
        self._build_fan_card(body)

        # Action button
        ActionButton(body, text="Refresh Temperatures",
                     command=self._on_refresh).pack(anchor="w", pady=(0, 12))

    def _build_thermal_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Thermal Health Status").pack(anchor="w", padx=10, pady=8)

        frame = tk.Frame(card, bg=T.PANEL)
        frame.pack(fill="x", padx=10, pady=(0, 8))

        self._thermal_score = tk.Label(frame, text="–", bg=T.PANEL, fg=T.SUCCESS,
                                       font=(T.FONT_FAMILY, 24, "bold"))
        self._thermal_score.pack(side="left", padx=10)

        info = tk.Frame(frame, bg=T.PANEL)
        info.pack(side="left", padx=10, fill="both", expand=True)

        self._thermal_status = tk.Label(info, text="Loading...", bg=T.PANEL,
                                        fg=T.FG2, font=T.FONT_BODY)
        self._thermal_status.pack(anchor="w")

        self._thermal_recommendation = tk.Label(info, text="", bg=T.PANEL, fg=T.FG2,
                                               font=T.FONT_SMALL, wraplength=400)
        self._thermal_recommendation.pack(anchor="w", pady=(2, 0))

    def _build_temps_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Temperature Readings").pack(anchor="w", padx=10, pady=8)

        for label, key, unit in [
            ("CPU Temperature", "cpu_temp", "°C"),
            ("Disk Temperature", "disk_temp", "°C"),
        ]:
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=4)

            tk.Label(row, text=label, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BODY, width=20, anchor="w").pack(side="left")

            temp_label = tk.Label(row, text="–", bg=T.PANEL, fg=T.FG,
                                 font=(T.FONT_FAMILY, 14, "bold"))
            temp_label.pack(side="left", padx=10)

            setattr(self, f"_{key}_label", temp_label)

    def _build_fan_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Fan Information").pack(anchor="w", padx=10, pady=8)

        self._fan_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                height=6, bd=0, padx=8, pady=6,
                                state="disabled", wrap="word")
        self._fan_text.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    def _load_temps(self):
        """Load thermal data in background."""
        def load():
            health = hm.check_thermal_health()
            temps = hm.get_system_temps()
            fans = hm.get_fan_speeds()
            self.after(0, self._display_temps, health, temps, fans)

        threading.Thread(target=load, daemon=True).start()

    def _display_temps(self, health, temps, fans):
        """Display temperature data."""
        score = health["score"]
        status = health["status"]

        self._thermal_score.config(text=str(int(score)))
        color = T.SUCCESS if score >= 80 else T.WARNING if score >= 50 else T.DANGER
        self._thermal_score.config(fg=color)

        status_text = "Normal" if status == "normal" else "Warning" if status == "warning" else "Critical" if status == "critical" else "Unavailable"
        self._thermal_status.config(text=f"Status: {status_text}", fg=color)
        self._thermal_recommendation.config(text=health["recommendation"])

        self._cpu_temp_label.config(text=f"{temps['cpu_temp']:.1f}°C")
        self._disk_temp_label.config(text=f"{temps['disk_temp']:.1f}°C")

        self._fan_text.config(state="normal")
        self._fan_text.delete("1.0", "end")

        if fans:
            for fan in fans:
                self._fan_text.insert("end", f"{fan['name']}: {fan['speed_rpm']} RPM ({fan['status']})\n")
        else:
            self._fan_text.insert("end", "No fan information available (admin privileges may be required)")

        self._fan_text.config(state="disabled")

    def _on_refresh(self):
        self._load_temps()

    def on_activate(self):
        self._load_temps()
