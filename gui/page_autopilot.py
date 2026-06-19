"""
1-Click Auto-Pilot — the signature "fix everything" flow.

Runs a curated chain on a background thread:
    before-scan → turbo_clean (RAM/temp/recycle/DNS) → re-scan
…with live animated progress, then an animated before/after report (health-score
delta, space & RAM freed, per-score deltas). All Tk updates are marshalled via
self.after(0, …).
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import (Card, PageHeader, SectionLabel, ActionButton,
                      ProgressBar, MetricCard, CircleScanButton, ToggleSwitch, Toast)

_STEPS = [
    ("scan",   "Analyze system"),
    ("clean",  "Clean & optimize"),
    ("rescan", "Re-scan health"),
    ("done",   "Finished"),
]


class AutoPilotPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._running = False
        self._bench_var = tk.BooleanVar(value=False)
        self._step_rows: dict[str, dict] = {}
        self._anim_job = None
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Auto-Pilot",
                   subtitle="One click — clean, optimize & re-score your PC",
                   icon="🚀", color=T.HIGHLIGHT).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)

        from ._pro_gate import limit_banner
        banner = limit_banner(body, "autopilot")
        if banner:
            banner.pack(fill="x", pady=(0, 10))

        # Hero row: scan button + steps
        hero = tk.Frame(body, bg=T.BG)
        hero.pack(fill="x")

        left = tk.Frame(hero, bg=T.BG)
        left.pack(side="left", padx=(0, 24))
        self._scan_btn = CircleScanButton(left, command=self._start)
        self._scan_btn.pack()

        right = Card(hero)
        right.pack(side="left", fill="both", expand=True)
        SectionLabel(right, "What Auto-Pilot does").pack(anchor="w", padx=14, pady=(12, 6))
        for _key, label in _STEPS[:-1]:
            self._step_rows[_key] = self._make_step_row(right, label)
        # benchmark toggle
        bench_row = tk.Frame(right, bg=T.PANEL)
        bench_row.pack(fill="x", padx=14, pady=(8, 12))
        ToggleSwitch(bench_row, variable=self._bench_var).pack(side="left")
        tk.Label(bench_row, text="Include quick CPU benchmark (before/after)",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=10)

        # Progress
        prog_card = Card(body)
        prog_card.pack(fill="x", pady=(14, 0))
        self._status_lbl = tk.Label(prog_card, text="Ready when you are.",
                                    bg=T.PANEL, fg=T.FG, font=T.FONT_BODY, anchor="w")
        self._status_lbl.pack(fill="x", padx=14, pady=(12, 6))
        self._bar = ProgressBar(prog_card)
        self._bar.pack(fill="x", padx=14, pady=(0, 14))

        # Results container (filled on completion)
        self._results = tk.Frame(body, bg=T.BG)
        self._results.pack(fill="both", expand=True, pady=(14, 0))

    def _make_step_row(self, parent, label: str) -> dict:
        row = tk.Frame(parent, bg=T.PANEL)
        row.pack(fill="x", padx=14, pady=2)
        dot = tk.Label(row, text="○", bg=T.PANEL, fg=T.FG2,
                       font=(T.FONT_FAMILY, 12), width=2)
        dot.pack(side="left")
        lbl = tk.Label(row, text=label, bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY)
        lbl.pack(side="left")
        return {"dot": dot, "lbl": lbl}

    def _set_step(self, key: str, state: str):
        """state: 'pending' | 'active' | 'done'"""
        row = self._step_rows.get(key)
        if not row:
            return
        if state == "active":
            row["dot"].config(text="⟳", fg=T.HIGHLIGHT)
            row["lbl"].config(fg=T.FG)
        elif state == "done":
            row["dot"].config(text="✓", fg=T.SUCCESS)
            row["lbl"].config(fg=T.FG)
        else:
            row["dot"].config(text="○", fg=T.FG2)
            row["lbl"].config(fg=T.FG2)

    # ── run ───────────────────────────────────────────────────────────────────
    def _check_daily_limit(self) -> bool:
        """Free tier: max 1 Auto-Pilot run per calendar day."""
        from engine import license_manager as lm, app_settings
        limit = lm.effective_limit("autopilot")
        if limit is None:                    # Pro — unlimited
            return True
        import datetime
        today = datetime.date.today().isoformat()
        data = app_settings.get("autopilot_runs", {})
        count = data.get(today, 0) if isinstance(data, dict) else 0
        if count >= limit:
            from ._pro_gate import at_limit_dialog
            at_limit_dialog("autopilot")
            return False
        return True

    def _record_run(self):
        from engine import app_settings
        import datetime
        today = datetime.date.today().isoformat()
        data = app_settings.get("autopilot_runs", {})
        cur = data.get(today, 0) if isinstance(data, dict) else 0
        app_settings.set_and_save("autopilot_runs", {today: cur + 1})

    def _start(self):
        if self._running:
            return
        if not self._check_daily_limit():
            return
        if not messagebox.askyesno(
            "Run Auto-Pilot?",
            "Auto-Pilot will:\n"
            "  • free RAM\n"
            "  • delete temporary files\n"
            "  • empty the Recycle Bin\n"
            "  • flush the DNS cache\n\n"
            "Continue?",
            icon="question", parent=self):
            return

        self._record_run()
        self._running = True
        for w in self._results.winfo_children():
            w.destroy()
        for k, _ in _STEPS[:-1]:
            self._set_step(k, "pending")
        self._scan_btn.set_scanning(True)
        self._bar.set(0)
        self._status_lbl.config(text="Starting…")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        from engine import health_check, turbo_clean, system_info
        result = {"errors": []}
        try:
            # 1. BEFORE
            self._emit("scan", "Analyzing system…", 4)
            before_scores = _safe(health_check.get_health_scores, {})
            before_metrics = _safe(system_info.get_live_metrics, {})
            bench_before = None
            if self._bench_var.get():
                bench_before = _safe(lambda: _bench(), None)

            # 2. CLEAN (turbo_clean emits 0–100 → remap into 8–68)
            self._emit("clean", "Cleaning & optimizing…", 10)

            def _cb(step, pct):
                self._emit("clean", step, 8 + int(pct * 0.60))

            stats = turbo_clean.run(progress_cb=_cb)

            # 3. AFTER
            self._emit("rescan", "Re-scanning health…", 75)
            after_scores = _safe(health_check.get_health_scores, {})
            after_metrics = _safe(system_info.get_live_metrics, {})
            bench_after = None
            if self._bench_var.get():
                bench_after = _safe(lambda: _bench(), None)

            self._emit("done", "Done", 100)
            result.update({
                "before": before_scores, "after": after_scores,
                "before_metrics": before_metrics, "after_metrics": after_metrics,
                "bench_before": bench_before, "bench_after": bench_after,
                "stats": stats,
            })

            # persist snapshot
            try:
                from engine import health_timeline
                health_timeline.record_snapshot(after_scores, after_metrics, source="autopilot")
            except Exception:
                pass
        except Exception as e:  # pragma: no cover
            result["errors"].append(str(e))
        self.after(0, self._on_done, result)

    # ── progress marshalling ──────────────────────────────────────────────────
    def _emit(self, step_key: str, text: str, pct: int):
        self.after(0, self._update_progress, step_key, text, pct)

    def _update_progress(self, step_key: str, text: str, pct: int):
        try:
            # mark previous steps done, current active
            order = [k for k, _ in _STEPS[:-1]]
            if step_key in order:
                idx = order.index(step_key)
                for i, k in enumerate(order):
                    self._set_step(k, "done" if i < idx else ("active" if i == idx else "pending"))
            self._status_lbl.config(text=text)
            self._bar.set(pct)
        except tk.TclError:
            pass

    # ── completion ──────────────────────────────────────────────────────────
    def _on_done(self, result: dict):
        self._running = False
        try:
            self._scan_btn.set_scanning(False)
        except tk.TclError:
            pass
        for k, _ in _STEPS[:-1]:
            self._set_step(k, "done")

        if result.get("errors") and not result.get("after"):
            self._status_lbl.config(text="Auto-Pilot hit an error — see details below.", fg=T.DANGER)
            Card(self._results)  # noop placeholder
            tk.Label(self._results, text="; ".join(result["errors"]),
                     bg=T.BG, fg=T.DANGER, font=T.FONT_SMALL,
                     wraplength=560, justify="left").pack(anchor="w")
            return

        before = result.get("before", {})
        after = result.get("after", {})
        stats = result.get("stats", {})

        b_overall = int(before.get("overall_score", before.get("overall", 0)) or 0)
        a_overall = int(after.get("overall_score", after.get("overall", 0)) or 0)
        delta = a_overall - b_overall

        self._status_lbl.config(
            text=f"Auto-Pilot complete — health {b_overall} → {a_overall}", fg=T.FG)

        self._render_results(before, after, stats, b_overall, a_overall, delta, result)

        Toast.show(self._app,
                   f"Auto-Pilot complete — health {a_overall}/100"
                   + (f"  (+{delta})" if delta > 0 else ""),
                   "success")

    def _render_results(self, before, after, stats, b_overall, a_overall, delta, result):
        card = Card(self._results)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Results").pack(anchor="w", padx=14, pady=(12, 4))

        # Big animated overall score
        score_row = tk.Frame(card, bg=T.PANEL)
        score_row.pack(fill="x", padx=14, pady=(0, 8))
        self._score_lbl = tk.Label(score_row, text=str(b_overall),
                                    bg=T.PANEL, fg=T.score_color(a_overall),
                                    font=(T.FONT_FAMILY, 40, "bold"))
        self._score_lbl.pack(side="left")
        tk.Label(score_row, text="/100  health", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", padx=(6, 0), pady=(18, 0))
        if delta != 0:
            chip_col = T.SUCCESS if delta > 0 else T.DANGER
            sign = "+" if delta > 0 else ""
            tk.Label(score_row, text=f"  {sign}{delta}", bg=T.PANEL, fg=chip_col,
                     font=T.FONT_H2).pack(side="left", padx=(8, 0), pady=(20, 0))
        self._animate_score(b_overall, a_overall)

        # Metric cards
        cards_row = tk.Frame(card, bg=T.PANEL)
        cards_row.pack(fill="x", padx=10, pady=(4, 8))
        disk_freed = stats.get("disk_freed_mb", 0) or 0
        ram_freed = stats.get("ram_freed_mb", 0) or 0
        MetricCard(cards_row, "💾", "Space Freed", f"{disk_freed:.0f} MB",
                   color=T.SUCCESS).pack(side="left", padx=4)
        MetricCard(cards_row, "🧠", "RAM Freed", f"{ram_freed:.0f} MB",
                   color=T.HIGHLIGHT).pack(side="left", padx=4)
        MetricCard(cards_row, "♻", "Recycle Bin",
                   "Emptied" if stats.get("recycle_emptied") else "—",
                   color=T.WARNING).pack(side="left", padx=4)
        MetricCard(cards_row, "🌐", "DNS Cache",
                   "Flushed" if stats.get("dns_flushed") else "—",
                   color=T.INFO).pack(side="left", padx=4)

        # Per-score deltas
        grid = tk.Frame(card, bg=T.PANEL)
        grid.pack(fill="x", padx=14, pady=(4, 8))
        for key, label in (("privacy", "Privacy"), ("space", "Space"),
                           ("speed", "Speed"), ("security", "Security")):
            bv = int(before.get(key, before.get(f"{key}_score", 0)) or 0)
            av = int(after.get(key, after.get(f"{key}_score", 0)) or 0)
            self._score_bar(grid, label, bv, av)

        # Optional benchmark delta
        bb, ba = result.get("bench_before"), result.get("bench_after")
        if bb and ba:
            d = ba.get("ops_per_sec", 0) - bb.get("ops_per_sec", 0)
            tk.Label(card,
                     text=f"CPU benchmark: {bb.get('ops_per_sec',0):,} → "
                          f"{ba.get('ops_per_sec',0):,} ops/s"
                          + (f"  (+{d:,})" if d > 0 else ""),
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", padx=14, pady=(0, 4))

        # CTA to timeline
        cta = tk.Frame(card, bg=T.PANEL)
        cta.pack(fill="x", padx=14, pady=(4, 14))
        ActionButton(cta, text="View Health Timeline", width=170,
                     command=lambda: self._app.activate_key("timeline")).pack(side="left")

    def _score_bar(self, parent, label, before_v, after_v):
        row = tk.Frame(parent, bg=T.PANEL)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 width=10, anchor="w").pack(side="left")
        bar = ProgressBar(row)
        bar.pack(side="left", fill="x", expand=True, padx=(6, 8))
        bar.set(after_v)
        d = after_v - before_v
        txt = f"{after_v}" + (f"  ↑ +{d}" if d > 0 else (f"  ↓ {d}" if d < 0 else ""))
        col = T.SUCCESS if d > 0 else (T.DANGER if d < 0 else T.FG2)
        tk.Label(row, text=txt, bg=T.PANEL, fg=col, font=T.FONT_SMALL,
                 width=10, anchor="e").pack(side="left")

    def _animate_score(self, start: int, target: int, cur: float = None):
        if cur is None:
            cur = float(start)
        try:
            nxt = cur + (target - cur) * 0.18
            if abs(target - nxt) < 0.5:
                nxt = target
            self._score_lbl.config(text=str(int(round(nxt))))
            if nxt != target:
                self._anim_job = self.after(24, lambda: self._animate_score(start, target, nxt))
        except tk.TclError:
            pass


# ── helpers ───────────────────────────────────────────────────────────────────
def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _bench():
    from engine import benchmark
    return benchmark.cpu_benchmark(duration_sec=2)
