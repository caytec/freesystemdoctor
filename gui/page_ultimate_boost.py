"""Ultimate Boost — one click, every layer, measured proof.

System + CPU + GPU + RAM + network in a single staged sequence, with a
before/after scorecard (RAM freed, kernel timer, DPC latency) and a
one-click full revert. The measurement is the feature no competitor has.
"""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, PageHeader, ProgressBar
from engine import ultimate_boost as ub


class UltimateBoostPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Ultimate Boost",
                   subtitle="One click — system, CPU, GPU, RAM and network, "
                            "with measured proof",
                   icon="🚀", color="#ff5c5c").pack(fill="x")

        outer = tk.Frame(self, bg=T.BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=T.BG, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=T.BG)
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw", width=880)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True, padx=16, pady=12)
        sb.pack(side="right", fill="y")

        self._build_hero(body)
        self._build_scorecard(body)
        self._build_log(body)

    def _build_hero(self, parent):
        card = Card(parent, glow=True)
        card.pack(fill="x", pady=(0, 12))

        tk.Label(card, text="🚀", bg=T.PANEL, font=("Segoe UI Emoji", 40)
                 ).pack(pady=(16, 0))
        self._status_lbl = tk.Label(card, text="Ready to boost every layer.",
                                    bg=T.PANEL, fg=T.FG, font=T.FONT_BOLD)
        self._status_lbl.pack(pady=(2, 2))
        tk.Label(card,
                 text="SYSTEM → CPU → GPU → RAM → NETWORK in one sequence. "
                      "Baseline is measured first, the result after — you see "
                      "exactly what you gained. Restore point created; one "
                      "click reverts everything.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 justify="center", wraplength=680).pack(padx=16)

        self._extreme_var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(
            card, text="EXTREME mode — also disable C-states and force NVIDIA "
                       "max clocks (more heat/power; desktops only)",
            variable=self._extreme_var, bg=T.PANEL, fg=T.WARNING,
            activebackground=T.PANEL, activeforeground=T.WARNING,
            selectcolor=T.BG, font=T.FONT_SMALL)
        chk.pack(pady=(8, 2))

        btns = tk.Frame(card, bg=T.PANEL)
        btns.pack(pady=(6, 4))
        self._boost_btn = ActionButton(btns, text="🚀 ULTIMATE BOOST",
                                       width=220, command=self._on_boost)
        self._boost_btn.pack(side="left", padx=(0, 10))
        ActionButton(btns, text="↺ Revert everything", width=170,
                     secondary=True, command=self._on_revert).pack(side="left")

        # ── A/B verification — the thing no competitor does ──────────────
        vrow = tk.Frame(card, bg=T.PANEL)
        vrow.pack(pady=(6, 4))
        ActionButton(vrow, text="🔬 Verify tweaks (measure & auto-undo)",
                     width=300, secondary=True,
                     command=self._on_verify).pack()
        tk.Label(card,
                 text="Verification applies tweaks one at a time, measures the "
                      "machine before and after, and automatically undoes any "
                      "that made it worse. Takes a few minutes — it samples "
                      "your PC's own noise level first so the verdict is real.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_MICRO,
                 justify="center", wraplength=640).pack(padx=16, pady=(0, 4))

        self._prog = ProgressBar(card)
        self._prog.pack(fill="x", padx=24, pady=(4, 6))
        self._active_lbl = tk.Label(card, text="", bg=T.PANEL, fg=T.SUCCESS,
                                    font=T.FONT_SMALL)
        self._active_lbl.pack(pady=(0, 14))

    def _build_scorecard(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "📊 Measured gains — proof, not promises").pack(
            anchor="w", padx=16, pady=(12, 4))

        grid = tk.Frame(card, bg=T.PANEL)
        grid.pack(fill="x", padx=16, pady=(0, 14))
        self._score_ram = self._score_cell(grid, 0, "RAM freed")
        self._score_timer = self._score_cell(grid, 1, "Kernel timer")
        self._score_dpc = self._score_cell(grid, 2, "DPC latency")

    def _score_cell(self, parent, col, title):
        cell = tk.Frame(parent, bg=T.BG, padx=14, pady=10)
        cell.grid(row=0, column=col, padx=6, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(cell, text=title, bg=T.BG, fg=T.FG2,
                 font=T.FONT_SMALL).pack()
        val = tk.Label(cell, text="—", bg=T.BG, fg=T.HIGHLIGHT,
                       font=(T.FONT_FAMILY, 18, "bold"))
        val.pack()
        sub = tk.Label(cell, text="", bg=T.BG, fg=T.FG2, font=T.FONT_MICRO)
        sub.pack()
        return val, sub

    def _build_log(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 16))
        SectionLabel(card, "Boost sequence").pack(anchor="w", padx=16,
                                                  pady=(12, 4))
        self._log = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_SMALL,
                            height=14, wrap="word", state="disabled",
                            bd=0, relief="flat", padx=10, pady=8)
        self._log.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self._log.tag_configure("ok", foreground=T.SUCCESS)
        self._log.tag_configure("fail", foreground=T.DANGER)
        self._log.tag_configure("head", foreground=T.HIGHLIGHT)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _log_line(self, msg: str, tag: str | None = None):
        self._log.config(state="normal")
        self._log.insert("end", msg + "\n", tag or ())
        self._log.see("end")
        self._log.config(state="disabled")

    def _set_progress(self, msg: str, pct: int):
        self._status_lbl.config(text=msg)
        self._prog.set(pct)

    # ── actions ──────────────────────────────────────────────────────────────
    def _on_boost(self):
        if self._busy:
            return
        extreme = bool(self._extreme_var.get())
        warn = ("\n\n⚠ EXTREME adds: C-states off (CPU never idles) and "
                "NVIDIA forced max clocks — significantly more heat and "
                "power. Desktops with good cooling only." if extreme else "")
        if not messagebox.askyesno(
                "Ultimate Boost",
                "Boost every layer — system, CPU, GPU, RAM, network?\n\n"
                "A restore point is created first and one click reverts "
                f"everything.{warn}"):
            return
        self._busy = True
        self._log_line("═══ ULTIMATE BOOST "
                       + ("(EXTREME) " if extreme else "") + "═══", "head")

        def progress(msg, pct):
            self.after(0, self._set_progress, str(msg), int(pct))

        def work():
            try:
                report = ub.run_ultimate_boost(extreme=extreme,
                                               progress_cb=progress)
                self.after(0, self._show_report, report)
            except Exception as e:
                self.after(0, self._log_line, f"✗ Fatal: {e}", "fail")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _show_report(self, r: dict):
        for s in r["steps"]:
            mark, tag = ("✓", "ok") if s["ok"] else ("✗", "fail")
            self._log_line(f"  {mark} {s['name']} — {s['msg']}", tag)
        self._log_line(f"═══ {r['ok_count']}/{r['total']} steps applied ═══",
                       "head")

        g = r.get("gains", {})
        if "ram_freed_mb" in g:
            freed = g["ram_freed_mb"]
            val, sub = self._score_ram
            val.config(fg=T.SUCCESS if freed > 0 else T.FG2)
            T.count_up(val, freed,
                       fmt=("+{:,.0f} MB" if freed > 0 else "{:,.0f} MB"),
                       duration_ms=800)
            sub.config(text="more available RAM")
        if "timer_after_ms" in g:
            val, sub = self._score_timer
            val.config(fg=T.SUCCESS if g["timer_after_ms"] <= 1.01
                       else T.HIGHLIGHT)
            T.count_up(val, g["timer_after_ms"], fmt="{:.2f} ms",
                       duration_ms=650, start_value=g["timer_before_ms"])
            sub.config(text=f"was {g['timer_before_ms']:.2f} ms")
        if "dpc_after_pct" in g:
            val, sub = self._score_dpc
            val.config(fg=T.SUCCESS if g["dpc_after_pct"] < 1.5 else T.WARNING)
            T.count_up(val, g["dpc_after_pct"], fmt="{:.2f}%",
                       duration_ms=650, start_value=g["dpc_before_pct"])
            sub.config(text=f"was {g['dpc_before_pct']:.2f}%")

        self._refresh_state()
        messagebox.showinfo(
            "Ultimate Boost",
            f"{r['ok_count']}/{r['total']} steps applied.\n\n"
            "Some changes (HAGS, timer flag) reach full effect after a "
            "reboot. Revert any time from this page.")

    def _on_verify(self):
        if self._busy:
            return
        if not messagebox.askyesno(
                "Verify tweaks",
                "Apply performance tweaks one at a time, measuring your PC "
                "before and after each one?\n\n"
                "Anything that measurably makes things WORSE is undone "
                "automatically. This takes a few minutes and your PC should be "
                "otherwise idle for the measurements to mean anything."):
            return
        self._busy = True
        self._log_line("═══ VERIFY (measure → keep or undo) ═══", "head")

        def progress(msg, pct):
            self.after(0, self._set_progress, str(msg), int(pct))

        def work():
            try:
                rep = ub.verify_tweaks(progress_cb=progress)
                self.after(0, self._show_verify, rep)
            except Exception as e:
                self.after(0, self._log_line, f"✗ Fatal: {e}", "fail")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _show_verify(self, rep: dict):
        for r in rep["results"]:
            verdict = r.get("verdict", "")
            tag = {"improved": "ok", "no_change": None,
                   "worse_reverted": "fail", "worse_kept": "fail",
                   "apply_failed": "fail"}.get(verdict)
            mark = {"improved": "✓", "no_change": "=", "worse_reverted": "↩",
                    "worse_kept": "!", "apply_failed": "✗"}.get(verdict, "·")
            self._log_line(f"  {mark} {r['name']} — {r.get('summary', '')}", tag)
            for d in (r.get("comparison", {}).get("metrics", {}) or {}).values():
                if d["verdict"] == "unchanged":
                    continue
                self._log_line(
                    f"      {d['label']}: {d['before']} → {d['after']} "
                    f"{d['unit']}  ({d['verdict']}, noise ±{d['noise_floor']})")
        self._log_line(
            f"═══ {rep['kept']}/{rep['total']} kept, "
            f"{rep['reverted']} automatically undone ═══", "head")
        self._set_progress("Verification complete.", 100)
        messagebox.showinfo(
            "Verification complete",
            f"{rep['kept']} of {rep['total']} tweaks kept.\n"
            f"{rep['reverted']} were undone automatically because they "
            f"measurably made things worse.")

    def _on_revert(self):
        if self._busy:
            return
        if not messagebox.askyesno(
                "Revert everything",
                "Undo every layer of Ultimate Boost and restore your "
                "previous settings?"):
            return
        self._busy = True
        self._log_line("═══ FULL REVERT ═══", "head")

        def progress(msg, pct):
            self.after(0, self._set_progress, str(msg), int(pct))

        def work():
            try:
                report = ub.revert_ultimate_boost(progress_cb=progress)
                def show():
                    for s in report["steps"]:
                        mark, tag = ("✓", "ok") if s["ok"] else ("✗", "fail")
                        self._log_line(f"  {mark} {s['name']} — {s['msg']}",
                                       tag)
                    self._log_line(
                        f"═══ {report['ok_count']}/{report['total']} layers "
                        f"restored ═══", "head")
                    self._refresh_state()
                    messagebox.showinfo("Revert",
                                        "Previous settings restored. Some "
                                        "changes need a reboot to fully "
                                        "revert.")
                self.after(0, show)
            except Exception as e:
                self.after(0, self._log_line, f"✗ Fatal: {e}", "fail")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _refresh_state(self):
        st = ub.get_boost_state()
        if st.get("active"):
            self._active_lbl.config(
                text=f"● BOOST ACTIVE since {st.get('applied_at', '?')}"
                     + ("  ·  EXTREME" if st.get("extreme") else ""),
                fg=T.SUCCESS)
        else:
            self._active_lbl.config(text="")

    def on_activate(self):
        self._refresh_state()
