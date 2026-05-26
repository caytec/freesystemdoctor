"""Action Center page — system health overview, quick fixes, issue summary."""

import threading
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import system_info


class ActionCenterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._scan_results: dict[str, int] = {}
        self._build_ui()

    def on_activate(self):
        self._refresh_health()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Action Center", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="System health overview and quick actions",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)
        ActionButton(hdr, "Refresh", command=self._refresh_health
                     ).pack(side="right", padx=12)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left: health score + issues
        left = tk.Frame(body, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._build_health_card(left)
        self._build_issues_card(left)

        # Right: quick actions + disk info
        right = tk.Frame(body, bg=T.BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_quick_actions(right)
        self._build_disk_card(right)

    def _build_health_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 8))

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=10)

        # Score circle (canvas)
        self._score_canvas = tk.Canvas(row, width=120, height=120,
                                       bg=T.PANEL, highlightthickness=0)
        self._score_canvas.pack(side="left", padx=(0, 16))
        self._draw_score(75)

        right_info = tk.Frame(row, bg=T.PANEL)
        right_info.pack(side="left", fill="both", expand=True)
        tk.Label(right_info, text="System Health Score", bg=T.PANEL,
                 fg=T.FG, font=T.FONT_H2).pack(anchor="w")
        self._health_label = tk.Label(right_info, text="Good", bg=T.PANEL,
                                       fg=T.SUCCESS, font=T.FONT_TITLE)
        self._health_label.pack(anchor="w")
        self._health_detail = tk.Label(right_info, text="", bg=T.PANEL,
                                        fg=T.FG2, font=T.FONT_SMALL,
                                        wraplength=300, justify="left")
        self._health_detail.pack(anchor="w")

    def _draw_score(self, score: int):
        self._score_canvas.delete("all")
        cx, cy, r = 60, 60, 50
        color = T.score_color(score)
        # Background ring
        self._score_canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                        outline="#2a2a4a", width=10, fill=T.PANEL)
        # Score arc
        angle = int(score / 100 * 360)
        self._score_canvas.create_arc(cx-r, cy-r, cx+r, cy+r,
                                       start=90, extent=-angle, style="arc",
                                       outline=color, width=10)
        # Score text
        self._score_canvas.create_text(cx, cy - 6, text=str(score),
                                        fill=color, font=T.FONT_TITLE)
        self._score_canvas.create_text(cx, cy + 16, text="/100",
                                        fill=T.FG2, font=T.FONT_SMALL)

    def _build_issues_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, "Issues from Last Scan").pack(anchor="w", padx=10, pady=(8, 4))
        self._issues_text = tk.Text(card, height=8, bg=T.ACCENT, fg=T.FG,
                                     font=T.FONT_SMALL, state="disabled",
                                     relief="flat", wrap="word")
        self._issues_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._update_issues_panel()

    def _build_quick_actions(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 8))
        SectionLabel(card, "Quick Actions").pack(anchor="w", padx=10, pady=(8, 4))

        actions = [
            ("🔍 Run Full Scan",     self._go_scan),
            ("🧹 Clean Junk Files",  self._quick_clean),
            ("💾 Optimize RAM",      self._quick_ram),
            ("🌐 Flush DNS Cache",   self._quick_dns),
            ("🛡 Check Protection",  self._go_protect),
            ("📦 Check Updates",     self._go_software),
        ]
        grid = tk.Frame(card, bg=T.PANEL)
        grid.pack(fill="x", padx=10, pady=(0, 10))
        for idx, (label, cmd) in enumerate(actions):
            col, row = idx % 2, idx // 2
            btn = ActionButton(grid, label, command=cmd)
            btn.config(font=T.FONT_SMALL, pady=8)
            btn.grid(row=row, column=col, sticky="ew", padx=4, pady=3)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def _build_disk_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, "Disk Usage").pack(anchor="w", padx=10, pady=(8, 4))
        cols = ("Used", "Free", "Total", "%")
        self._disk_tv = ttk.Treeview(card, columns=cols, show="tree headings", height=6)
        apply_treeview_style(self._disk_tv)
        self._disk_tv.heading("#0",   text="Drive",   anchor="w")
        self._disk_tv.heading("Used", text="Used",    anchor="w")
        self._disk_tv.heading("Free", text="Free",    anchor="w")
        self._disk_tv.heading("Total",text="Total",   anchor="w")
        self._disk_tv.heading("%",    text="Usage",   anchor="w")
        self._disk_tv.column("#0",   width=70)
        self._disk_tv.column("Used", width=80)
        self._disk_tv.column("Free", width=80)
        self._disk_tv.column("Total",width=80)
        self._disk_tv.column("%",    width=70)
        self._disk_tv.tag_configure("warn", foreground=T.WARNING)
        self._disk_tv.tag_configure("ok",   foreground=T.SUCCESS)
        self._disk_tv.tag_configure("crit", foreground=T.DANGER)
        self._disk_tv.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ── data loading ──────────────────────────────────────────────────────────

    def _refresh_health(self):
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        score, issues = system_info.get_health_score()
        disks = system_info.get_disk_info()
        self.after(0, self._apply_health, score, issues, disks)

    def _apply_health(self, score: int, issues: list[str], disks: list[dict]):
        self._draw_score(score)
        label = "Excellent" if score >= 90 else \
                "Good"      if score >= 75 else \
                "Fair"      if score >= 50 else "Poor"
        self._health_label.config(text=label, fg=T.score_color(score))
        detail = "\n".join(f"• {i}" for i in issues) if issues else "No critical issues detected."
        self._health_detail.config(text=detail)

        for item in self._disk_tv.get_children():
            self._disk_tv.delete(item)
        for d in disks:
            pct = d.get("used_pct", 0)
            tag = "crit" if pct > 90 else "warn" if pct > 75 else "ok"
            self._disk_tv.insert("", "end", text=d.get("Drive", ""),
                                  values=(d["Used"], d["Free"], d["Total"], d["Used %"]),
                                  tags=(tag,))

    def update_from_scan(self, results: dict):
        self._scan_results = results
        self._update_issues_panel()

    def _update_issues_panel(self):
        self._issues_text.config(state="normal")
        self._issues_text.delete("1.0", "end")
        if not self._scan_results:
            self._issues_text.insert("end", "Run a scan from the Care page to see issues here.")
        else:
            for key, count in self._scan_results.items():
                icon = "⚠" if count > 0 else "✓"
                label = key.replace("_", " ").title()
                self._issues_text.insert("end", f"  {icon}  {label}: {count} issue(s)\n")
        self._issues_text.config(state="disabled")

    # ── navigation ────────────────────────────────────────────────────────────

    def _go_scan(self):
        if hasattr(self._app, "_switch_page"):
            self._app._switch_page("care")
            if "care" in self._app._pages:
                self._app._pages["care"]._start_scan()

    def _go_protect(self):
        if hasattr(self._app, "_switch_page"):
            self._app._switch_page("protect")

    def _go_software(self):
        if hasattr(self._app, "_switch_page"):
            self._app._switch_page("software")

    def _quick_clean(self):
        from engine import disk_cleaner
        threading.Thread(target=lambda: [
            disk_cleaner.clean_folder(r.path)
            for r in disk_cleaner.scan_junk()
        ], daemon=True).start()

    def _quick_ram(self):
        from engine import ram_daemon
        threading.Thread(target=ram_daemon.daemon.trigger_now, daemon=True).start()

    def _quick_dns(self):
        from engine import network_optimizer
        network_optimizer.flush_dns()
