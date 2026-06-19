"""Home Dashboard — animated landing page with live system stats and quick actions."""

import math
import threading
import tkinter as tk
from tkinter import ttk
import time

from . import theme as T
from .widgets import Card, ActionButton, ProgressBar, MetricCard

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class _AnimatedGauge(tk.Canvas):
    """Circular gauge with animated fill and glow."""
    SIZE = 110

    def __init__(self, parent, label: str, color: str, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self.SIZE, height=self.SIZE + 20, **kw)
        self._label = label
        self._color = color
        self._current = 0
        self._target = 0
        self._glow_phase = 0
        self._draw(0)
        self._animate()

    def set_value(self, pct: float):
        self._target = max(0, min(100, pct))

    def _draw(self, pct: float):
        self.delete("all")
        cx, cy = self.SIZE // 2, self.SIZE // 2 + 2
        r = self.SIZE // 2 - 8
        pct = max(0, min(100, pct))

        # Glow ring
        glow_t = (math.sin(self._glow_phase * 0.08) + 1) / 2
        glow_c = T.lerp_color(self._color, T.BG, 0.5 + glow_t * 0.2)
        self.create_oval(cx-r-3, cy-r-3, cx+r+3, cy+r+3,
                         fill="", outline=glow_c, width=6)

        # Track
        self.create_arc(cx-r, cy-r, cx+r, cy+r,
                        start=220, extent=-280, style="arc",
                        outline=T.BORDER, width=10)

        # Fill arc
        if pct > 0:
            extent = int(-280 * pct / 100)
            # Glow behind fill
            glow_fill = T.lerp_color(self._color, T.BG, 0.5)
            self.create_arc(cx-r, cy-r, cx+r, cy+r,
                            start=220, extent=extent, style="arc",
                            outline=glow_fill, width=14)
            self.create_arc(cx-r, cy-r, cx+r, cy+r,
                            start=220, extent=extent, style="arc",
                            outline=self._color, width=10)

        # Center
        self.create_text(cx, cy - 6, text=f"{pct:.0f}%",
                         fill=self._color, font=(T.FONT_FAMILY, 14, "bold"))
        self.create_text(cx, cy + 10, text=self._label,
                         fill=T.FG2, font=T.FONT_MICRO)

    def _animate(self):
        self._glow_phase = (self._glow_phase + 1) % 100
        diff = self._target - self._current
        if abs(diff) > 0.3:
            self._current += diff * 0.12
        else:
            self._current = self._target
        self._draw(self._current)
        self.after(30, self._animate)


class _SparkLine(tk.Canvas):
    """Mini sparkline chart for live metric history."""
    def __init__(self, parent, color: str, points: int = 60, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._color = color
        self._max_pts = points
        self._data = []
        self._draw()

    def push(self, value: float):
        self._data.append(max(0, min(100, value)))
        if len(self._data) > self._max_pts:
            self._data.pop(0)
        self._draw()

    def _draw(self):
        self.delete("all")
        if len(self._data) < 2:
            return
        w = self.winfo_width() or 200
        h = self.winfo_height() or 40

        # Fill area
        pts = self._data
        step = w / (len(pts) - 1)
        coords = []
        for i, v in enumerate(pts):
            x = i * step
            y = h - (v / 100) * (h - 4) - 2
            coords.append((x, y))

        # Fill polygon
        poly = [0, h]
        for x, y in coords:
            poly += [x, y]
        poly += [w, h]
        fill_c = T.lerp_color(self._color, T.PANEL, 0.75)
        self.create_polygon(poly, fill=fill_c, outline="")

        # Line
        flat = []
        for x, y in coords:
            flat += [x, y]
        if len(flat) >= 4:
            self.create_line(flat, fill=self._color, width=2, smooth=True)

        # End dot
        if coords:
            lx, ly = coords[-1]
            self.create_oval(lx-3, ly-3, lx+3, ly+3,
                             fill=self._color, outline="")


class _QuickActionBtn(tk.Frame):
    """Large icon + label quick-action tile."""
    def __init__(self, parent, icon: str, title: str, subtitle: str,
                 color: str, command=None, **kw):
        kw.setdefault("bg", T.PANEL)
        super().__init__(parent, **kw)
        self._color = color
        self._command = command
        self._bg = T.PANEL
        self.config(cursor="hand2")

        # Top color bar
        bar = tk.Frame(self, bg=color, height=3)
        bar.pack(fill="x")

        inner = tk.Frame(self, bg=T.PANEL, padx=14, pady=12)
        inner.pack(fill="both", expand=True)

        row = tk.Frame(inner, bg=T.PANEL)
        row.pack(fill="x")

        icon_lbl = tk.Label(row, text=icon, bg=T.PANEL, fg=color,
                            font=(T.FONT_FAMILY, 22))
        icon_lbl.pack(side="left", padx=(0, 10))

        txt_frame = tk.Frame(row, bg=T.PANEL)
        txt_frame.pack(side="left")

        title_lbl = tk.Label(txt_frame, text=title, bg=T.PANEL, fg=T.FG,
                             font=T.FONT_BOLD, anchor="w")
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(txt_frame, text=subtitle, bg=T.PANEL, fg=T.FG2,
                           font=T.FONT_MICRO, anchor="w")
        sub_lbl.pack(anchor="w")

        self._all_widgets = [self, bar, inner, row, icon_lbl, txt_frame, title_lbl, sub_lbl]

        for w in self._all_widgets:
            try:
                w.bind("<Enter>", self._on_enter)
                w.bind("<Leave>", self._on_leave)
                w.bind("<Button-1>", self._on_click)
            except Exception:
                pass

    def _on_enter(self, e=None):
        hbg = T.lerp_color(T.PANEL, self._color, 0.1)
        for w in self._all_widgets:
            try:
                w.config(bg=hbg)
            except Exception:
                pass

    def _on_leave(self, e=None):
        for w in self._all_widgets:
            try:
                w.config(bg=T.PANEL)
            except Exception:
                pass

    def _on_click(self, e=None):
        if self._command:
            self._command()


class _HeroCanvas(tk.Canvas):
    """Animated hero background with floating particles and gradient mesh."""
    N_PARTICLES = 30

    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.BG)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        import random
        self._particles = [
            {
                "x": random.uniform(0, 1),
                "y": random.uniform(0, 1),
                "vx": random.uniform(-0.0003, 0.0003),
                "vy": random.uniform(-0.0002, 0.0002),
                "r": random.uniform(1.5, 4),
                "color": random.choice([T.HIGHLIGHT, T.PURPLE, T.SUCCESS]),
                "alpha": random.uniform(0.15, 0.5),
            }
            for _ in range(self.N_PARTICLES)
        ]
        self._phase = 0
        self._animate()

    def _animate(self):
        self.delete("all")
        w = self.winfo_width() or 800
        h = self.winfo_height() or 120
        self._phase += 1

        # Gradient overlay (simulate with strips)
        strips = 8
        for i in range(strips):
            t = i / strips
            c = T.lerp_color(T.lerp_color(T.BG, T.HIGHLIGHT, 0.04),
                              T.BG, t)
            self.create_rectangle(0, int(h * t / strips * strips),
                                  w, int(h * (t + 1/strips)),
                                  fill=c, outline="")

        # Particles
        for p in self._particles:
            p["x"] = (p["x"] + p["vx"]) % 1.0
            p["y"] = (p["y"] + p["vy"]) % 1.0
            if p["y"] < 0: p["y"] = 1.0
            px, py = p["x"] * w, p["y"] * h
            alpha = p["alpha"] * ((math.sin(self._phase * 0.02 + px) + 1) / 2 * 0.6 + 0.4)
            c = T.lerp_color(p["color"], T.BG, 1 - alpha)
            r = p["r"]
            self.create_oval(px-r, py-r, px+r, py+r, fill=c, outline="")

        # Connection lines between close particles (web effect)
        for i, a in enumerate(self._particles[:15]):
            for b in self._particles[i+1:15]:
                dx = (a["x"] - b["x"]) * w
                dy = (a["y"] - b["y"]) * h
                dist = (dx*dx + dy*dy) ** 0.5
                if dist < 80:
                    alpha = (1 - dist/80) * 0.15
                    c = T.lerp_color(T.HIGHLIGHT, T.BG, 1 - alpha)
                    self.create_line(a["x"]*w, a["y"]*h, b["x"]*w, b["y"]*h,
                                     fill=c, width=1)

        self.after(33, self._animate)


class HomePage(tk.Frame):
    """Main landing page with live stats, gauges, and quick actions."""

    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._running = True
        self._build_ui()
        self._start_live_updates()

    def _build_ui(self):
        # ── Hero section ───────────────────────────────────────────────────────
        hero = tk.Frame(self, bg=T.BG, height=110)
        hero.pack(fill="x")
        hero.pack_propagate(False)

        # Animated background
        bg_canvas = _HeroCanvas(hero)
        bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        hero_inner = tk.Frame(hero, bg=T.BG)
        hero_inner.place(relx=0.04, rely=0.15, relwidth=0.6, relheight=0.7)

        tk.Label(hero_inner, text="Welcome to FreeSystemDoctor",
                 bg=T.BG, fg=T.FG,
                 font=(T.FONT_FAMILY, 18, "bold")).pack(anchor="w")
        tk.Label(hero_inner, text="Your PC is being monitored. All systems in check.",
                 bg=T.BG, fg=T.FG2,
                 font=T.FONT_BODY).pack(anchor="w", pady=(2, 0))

        # Quick scan button in hero
        scan_frame = tk.Frame(hero, bg=T.BG)
        scan_frame.place(relx=0.72, rely=0.2, relwidth=0.25, relheight=0.6)
        self._hero_btn = ActionButton(scan_frame, "⚡  Quick Scan",
                                      command=self._quick_scan, width=170)
        self._hero_btn.pack(expand=True)

        # ── Live metric bar ────────────────────────────────────────────────────
        metric_bar = tk.Frame(self, bg=T.ACCENT, height=1)
        metric_bar.pack(fill="x")

        metrics_row = tk.Frame(self, bg=T.PANEL)
        metrics_row.pack(fill="x")

        self._gauges = {}
        for metric, label, color in [
            ("cpu",  "CPU",  T.HIGHLIGHT),
            ("ram",  "RAM",  T.SUCCESS),
            ("disk", "DISK", T.WARNING),
            ("net",  "NET",  T.PURPLE),
        ]:
            frame = tk.Frame(metrics_row, bg=T.PANEL, padx=4, pady=4)
            frame.pack(side="left", expand=True, fill="x")

            g = _AnimatedGauge(frame, label, color)
            g.pack(anchor="center")

            # Separator
            if metric != "net":
                tk.Frame(metrics_row, bg=T.BORDER, width=1).pack(
                    side="left", fill="y", pady=8)

            self._gauges[metric] = g

        # Sparklines row
        sparks_frame = tk.Frame(self, bg=T.PANEL, height=50)
        sparks_frame.pack(fill="x")
        sparks_frame.pack_propagate(False)

        self._sparks = {}
        labels_colors = [("cpu", T.HIGHLIGHT), ("ram", T.SUCCESS),
                         ("disk", T.WARNING),  ("net", T.PURPLE)]
        for metric, color in labels_colors:
            sk = _SparkLine(sparks_frame, color=color, height=46)
            sk.pack(side="left", fill="both", expand=True, padx=2, pady=2)
            self._sparks[metric] = sk

        # ── Main content ───────────────────────────────────────────────────────
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        # Left column
        left = tk.Frame(body, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Quick actions grid
        self._build_quick_actions(left)

        # Right column
        right = tk.Frame(body, bg=T.BG, width=280)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        self._build_system_info(right)
        self._build_recent_activity(right)

        # ── Monetization surfaces (auto-hide when nothing to show) ─────────
        try:
            from .native_ad_widgets import TipCard, NewsletterCard
            tip = TipCard(left)
            tip.pack(fill="x", pady=(8, 0))
            news = NewsletterCard(left)
            news.pack(fill="x", pady=(8, 0))
        except Exception:
            pass

    def _build_quick_actions(self, parent):
        tk.Label(parent, text="Quick Actions", bg=T.BG, fg=T.FG,
                 font=T.FONT_H2, anchor="w").pack(fill="x", pady=(0, 6))

        grid = tk.Frame(parent, bg=T.BG)
        grid.pack(fill="both", expand=True)

        actions = [
            ("❤", "Health Check",   "Full system audit",         T.DANGER,    "health"),
            ("🧹", "Deep Clean",     "Remove junk files",         T.WARNING,   "deep_clean"),
            ("🎮", "Game Booster",   "Optimize for gaming",       T.SUCCESS,   "game"),
            ("🤖", "AI Analysis",    "Smart recommendations",     T.PURPLE,    "ai"),
            ("⚡", "Speed Up",       "Boost performance",         T.HIGHLIGHT, "speedup"),
            ("🛡", "Protect",        "Security & privacy",        T.DANGER,    "protect"),
            ("📊", "Live Monitor",   "Real-time system stats",    T.HIGHLIGHT, "dashboard"),
            ("💿", "Disk Analyzer",  "Find what's eating space",  T.WARNING,   "disk_analyzer"),
        ]

        for i, (icon, title, sub, color, key) in enumerate(actions):
            row = i // 4
            col = i % 4

            btn = _QuickActionBtn(grid, icon, title, sub, color,
                                   command=lambda k=key: self._nav(k))
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        for c in range(4):
            grid.columnconfigure(c, weight=1)
        grid.rowconfigure(0, weight=1)
        grid.rowconfigure(1, weight=1)

    def _build_system_info(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 8))

        tk.Label(card, text="System Info", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_H3, padx=12, pady=8, anchor="w").pack(fill="x")

        tk.Frame(card, bg=T.BORDER, height=1).pack(fill="x", padx=8)

        self._info_frame = tk.Frame(card, bg=T.PANEL, padx=12, pady=8)
        self._info_frame.pack(fill="x")

        rows = [
            ("OS",    "–"),
            ("CPU",   "–"),
            ("RAM",   "–"),
            ("Disk",  "–"),
            ("Uptime","–"),
        ]
        self._info_labels = {}
        for key, val in rows:
            row = tk.Frame(self._info_frame, bg=T.PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=key, bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_MICRO, width=7, anchor="w").pack(side="left")
            lbl = tk.Label(row, text=val, bg=T.PANEL, fg=T.FG,
                           font=T.FONT_SMALL, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            self._info_labels[key] = lbl

        self._load_system_info()

    def _build_recent_activity(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Recent Activity", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_H3, padx=12, pady=8, anchor="w").pack(fill="x")
        tk.Frame(card, bg=T.BORDER, height=1).pack(fill="x", padx=8)

        self._activity_frame = tk.Frame(card, bg=T.PANEL)
        self._activity_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self._refresh_activity()

    def _refresh_activity(self):
        """Populate Recent Activity from real Performance Guardian events."""
        try:
            from engine import performance_guardian
            events = performance_guardian.get_events(6)
        except Exception:
            events = []

        for child in self._activity_frame.winfo_children():
            child.destroy()

        kinds = {
            "action": ("✓", T.SUCCESS),
            "alert":  ("⚠", T.WARNING),
            "info":   ("ℹ", T.HIGHLIGHT),
        }
        if not events:
            row = tk.Frame(self._activity_frame, bg=T.PANEL, pady=3)
            row.pack(fill="x")
            tk.Label(row, text="●", bg=T.PANEL, fg=T.FG2,
                     font=(T.FONT_FAMILY, 10), width=3).pack(side="left")
            tk.Label(row, text="Monitoring active — no events yet",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_MICRO,
                     anchor="w").pack(side="left")
            return

        for ev in events:
            icon, color = kinds.get(ev.get("kind", "info"), ("ℹ", T.HIGHLIGHT))
            row = tk.Frame(self._activity_frame, bg=T.PANEL, pady=3)
            row.pack(fill="x")
            tk.Label(row, text=icon, bg=T.PANEL, fg=color,
                     font=(T.FONT_FAMILY, 10), width=3).pack(side="left")
            tk.Label(row, text=str(ev.get("message", ""))[:48], bg=T.PANEL,
                     fg=T.FG2, font=T.FONT_MICRO, anchor="w").pack(side="left")

    def _load_system_info(self):
        def fetch():
            import platform, subprocess
            info = {}
            try:
                info["OS"] = f"Windows {platform.version()[:10]}"
            except Exception:
                info["OS"] = platform.system()
            try:
                import psutil
                mem = psutil.virtual_memory()
                info["RAM"] = f"{mem.total/1024**3:.1f} GB"
                cpu_count = psutil.cpu_count()
                info["CPU"] = f"{cpu_count} cores"
                disk = psutil.disk_usage("C:\\")
                info["Disk"] = f"C: {disk.free/1024**3:.0f} GB free"
                bt = psutil.boot_time()
                uptime_s = time.time() - bt
                h = int(uptime_s // 3600)
                m = int((uptime_s % 3600) // 60)
                info["Uptime"] = f"{h}h {m}m"
            except Exception:
                pass
            self.after(0, lambda: self._apply_info(info))

        threading.Thread(target=fetch, daemon=True).start()

    def _apply_info(self, info: dict):
        for key, val in info.items():
            if key in self._info_labels:
                self._info_labels[key].config(text=val)

    def _start_live_updates(self):
        self._prev_net = None    # (total_bytes, timestamp) for throughput delta
        self._activity_tick = 0

        def update_loop():
            import time as _t
            while self._running:
                try:
                    if not _PSUTIL:
                        _t.sleep(2)
                        continue
                    cpu = psutil.cpu_percent(interval=1)
                    ram = psutil.virtual_memory().percent
                    disk = psutil.disk_usage("C:\\").percent
                    # Real network utilization: bytes/sec since the last sample,
                    # scaled against a 100 Mbps (12.5 MB/s) reference link.
                    net_pct = 0
                    try:
                        nio = psutil.net_io_counters()
                        total = nio.bytes_sent + nio.bytes_recv
                        now = _t.time()
                        if self._prev_net is not None:
                            prev_total, prev_t = self._prev_net
                            dt = max(0.001, now - prev_t)
                            bytes_per_s = max(0, total - prev_total) / dt
                            net_pct = min(100, bytes_per_s / 12_500_000 * 100)
                        self._prev_net = (total, now)
                    except Exception:
                        net_pct = 0
                    self.after(0, lambda c=cpu, r=ram, d=disk, n=net_pct:
                               self._apply_metrics(c, r, d, n))
                    # Refresh the activity feed roughly every ~5 samples.
                    self._activity_tick = (self._activity_tick + 1) % 5
                    if self._activity_tick == 0:
                        self.after(0, self._refresh_activity)
                except Exception:
                    _t.sleep(2)

        threading.Thread(target=update_loop, daemon=True).start()

    def _apply_metrics(self, cpu: float, ram: float, disk: float, net: float):
        try:
            self._gauges["cpu"].set_value(cpu)
            self._gauges["ram"].set_value(ram)
            self._gauges["disk"].set_value(disk)
            self._gauges["net"].set_value(net)
            self._sparks["cpu"].push(cpu)
            self._sparks["ram"].push(ram)
            self._sparks["disk"].push(disk)
            self._sparks["net"].push(net)
        except Exception:
            pass

    def _quick_scan(self):
        self._nav("health")

    def _nav(self, key: str):
        if hasattr(self._app, "_switch_page"):
            self._app._switch_page(key)

    def on_activate(self):
        pass

    def destroy(self):
        self._running = False
        super().destroy()
