"""Health Check page — comprehensive system audit with 4 health scores."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import health_check as hc


class HealthCheckPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._scanning = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Health Check", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Comprehensive system audit and recommendations",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Overall score card
        self._build_overall_card(body)

        # 4 gauge cards
        self._build_gauge_row(body)

        # Top issues card
        self._build_issues_card(body)

    def _build_overall_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False, pady=(0, 12))

        SectionLabel(card, "Overall System Health").pack(anchor="w", padx=10, pady=8)

        frame = tk.Frame(card, bg=T.PANEL)
        frame.pack(fill="x", padx=10, pady=(0, 8))

        self._overall_score = tk.Label(frame, text="–", bg=T.PANEL, fg=T.HIGHLIGHT,
                                       font=(T.FONT_FAMILY, 32, "bold"))
        self._overall_score.pack(side="left", padx=10)

        info = tk.Frame(frame, bg=T.PANEL)
        info.pack(side="left", padx=10, fill="both", expand=True)

        self._overall_status = tk.Label(info, text="Ready to scan", bg=T.PANEL,
                                        fg=T.FG2, font=T.FONT_BODY)
        self._overall_status.pack(anchor="w")

        self._overall_desc = tk.Label(info, text="", bg=T.PANEL, fg=T.FG2,
                                      font=T.FONT_SMALL, wraplength=400)
        self._overall_desc.pack(anchor="w", pady=(2, 0))

        ActionButton(card, text="Run Full Scan",
                     command=self._on_scan_full).pack(anchor="w", padx=10, pady=(0, 8))

    def _build_gauge_row(self, parent):
        row = tk.Frame(parent, bg=T.BG)
        row.pack(fill="both", expand=False, pady=(0, 12))

        self._gauges = {}
        for label, key, icon in [
            ("Privacy", "privacy_score", "🔒"),
            ("Space", "space_score", "💾"),
            ("Speed", "speed_score", "⚡"),
            ("Security", "security_score", "🛡"),
        ]:
            self._gauges[key] = self._build_gauge(row, icon, label, key)

    def _build_gauge(self, parent, icon, label, key) -> dict:
        card = Card(parent)
        card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        hdr = tk.Frame(card, bg=T.PANEL)
        hdr.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(hdr, text=f"{icon} {label}", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BOLD).pack(side="left")

        score_lbl = tk.Label(hdr, text="–", bg=T.PANEL, fg=T.FG2, font=T.FONT_BOLD)
        score_lbl.pack(side="right")

        progress = ProgressBar(card)
        progress.pack(fill="x", padx=8, pady=(0, 8))

        status_lbl = tk.Label(card, text="Not scanned", bg=T.PANEL, fg=T.FG2,
                              font=T.FONT_SMALL)
        status_lbl.pack(anchor="w", padx=8, pady=(0, 8))

        return {
            "score": score_lbl,
            "progress": progress,
            "status": status_lbl,
            "card": card,
        }

    def _build_issues_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Top Issues").pack(anchor="w", padx=10, pady=8)

        self._issues_frame = tk.Frame(card, bg=T.PANEL)
        self._issues_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._issues_text = tk.Label(self._issues_frame, text="Ready to scan",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                     justify="left", wraplength=700)
        self._issues_text.pack(anchor="nw", fill="both", expand=True)

    def _on_scan_full(self):
        if self._scanning:
            messagebox.showinfo("Scanning", "Scan already in progress")
            return

        self._scanning = True

        def scan():
            # Run engine work on the worker thread; marshal UI updates via after()
            try:
                scores  = hc.get_health_scores()
                overall = hc.calculate_overall_score(scores)
                issues  = hc.get_top_issues(5)
                self.after(0, lambda: self._render(scores, overall, issues, None))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._render({}, 0, [], err))

        threading.Thread(target=scan, daemon=True).start()

    def _render(self, scores, overall, issues, error):
        self._scanning = False

        if error:
            messagebox.showerror("Error", f"Scan failed: {error}")
            return

        for key, gauge in self._gauges.items():
            score = scores.get(key, 0)
            gauge["score"].config(text=f"{score}")
            gauge["progress"].set_value(score)
            if score >= 80:
                color, status_text = T.SUCCESS, "Good"
            elif score >= 60:
                color, status_text = T.WARNING, "Fair"
            else:
                color, status_text = T.DANGER, "Poor"
            gauge["status"].config(text=status_text, fg=color)

        self._overall_score.config(text=f"{overall}")
        if overall >= 80:
            status, desc, color = "✓ Excellent", "Your system is in great condition", T.SUCCESS
        elif overall >= 60:
            status, desc, color = "⚠ Good", "Some issues found, cleanup recommended", T.WARNING
        else:
            status, desc, color = "✗ Poor", "Significant issues found, cleanup needed", T.DANGER
        self._overall_status.config(text=status, fg=color)
        self._overall_desc.config(text=desc, fg=color)

        issues_text = "\n".join(f"• {i}" for i in issues) if issues else "No issues found!"
        self._issues_text.config(text=issues_text, fg=T.FG)

    def on_activate(self):
        pass
