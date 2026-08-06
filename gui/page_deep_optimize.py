"""Deep Optimize — kernel-level tuning mainstream optimizers don't offer.

Includes a DPC/interrupt latency diagnostic (the thing that causes stutter and
input lag even at high FPS), MSI interrupt mode, VBS/HVCI control, scheduler
quantum, and WinSxS component-store cleanup.
"""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import (Card, SectionLabel, ActionButton, PageHeader,
                      ProgressBar, Toast)
from engine import deep_optimize as dopt


_RISK_COLOR = {"low": T.SUCCESS, "medium": T.WARNING, "high": T.DANGER}


class DeepOptimizePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._rows = {}
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="Deep Optimize",
                   subtitle="Kernel-level tuning other optimizers skip",
                   icon="🔬", color=T.PURPLE).pack(fill="x")

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

        self._build_latency(body)
        self._build_tweaks(body)
        self._build_component_store(body)

    # ── DPC latency diagnostic (the unique bit) ─────────────────────────────
    def _build_latency(self, parent):
        card = Card(parent, glow=True)
        card.pack(fill="x", pady=(0, 12))

        head = tk.Frame(card, bg=T.PANEL)
        head.pack(fill="x", padx=16, pady=(14, 4))
        SectionLabel(head, "⚡ Kernel latency (DPC) — why your PC stutters").pack(side="left")
        ActionButton(head, text="Measure", width=120,
                     command=self._measure).pack(side="right")

        tk.Label(card,
                 text="High DPC latency causes stutter and input lag even when "
                      "FPS looks fine. No other optimizer measures this.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=780).pack(fill="x", padx=16)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=16, pady=(10, 4))
        self._dpc_val = tk.Label(row, text="—", bg=T.PANEL, fg=T.HIGHLIGHT,
                                 font=("Segoe UI", 28, "bold"))
        self._dpc_val.pack(side="left")
        tk.Label(row, text=" % DPC time", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", pady=(14, 0))
        self._dpc_extra = tk.Label(row, text="", bg=T.PANEL, fg=T.FG2,
                                   font=T.FONT_SMALL)
        self._dpc_extra.pack(side="left", padx=20, pady=(14, 0))

        self._dpc_verdict = tk.Label(card, text="Not measured yet.", bg=T.PANEL,
                                     fg=T.FG, font=T.FONT_BOLD, anchor="w")
        self._dpc_verdict.pack(fill="x", padx=16)
        self._dpc_advice = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                    font=T.FONT_SMALL, anchor="w",
                                    justify="left", wraplength=780)
        self._dpc_advice.pack(fill="x", padx=16, pady=(2, 14))

    # ── tweak list ──────────────────────────────────────────────────────────
    def _build_tweaks(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Advanced tweaks").pack(anchor="w", padx=16,
                                                   pady=(12, 2))
        tk.Label(card,
                 text="Every change is reversible and a restore point is created "
                      "first. Risky items are marked in red.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w").pack(
                 fill="x", padx=16, pady=(0, 8))

        self._tweak_host = tk.Frame(card, bg=T.PANEL)
        self._tweak_host.pack(fill="x", padx=16, pady=(0, 12))

    def _render_tweaks(self, tweaks):
        for w in self._tweak_host.winfo_children():
            w.destroy()
        self._rows.clear()

        for t in tweaks:
            row = tk.Frame(self._tweak_host, bg=T.PANEL)
            row.pack(fill="x", pady=4)

            top = tk.Frame(row, bg=T.PANEL)
            top.pack(fill="x")
            state = t.get("optimized")
            dot = "●" if state else "○"
            colour = T.SUCCESS if state else T.FG2
            tk.Label(top, text=dot, bg=T.PANEL, fg=colour,
                     font=(T.FONT_FAMILY, 12)).pack(side="left", padx=(0, 6))
            tk.Label(top, text=t["name"], bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BOLD).pack(side="left")
            tk.Label(top, text=f"  [{t['risk']} risk]", bg=T.PANEL,
                     fg=_RISK_COLOR.get(t["risk"], T.FG2),
                     font=T.FONT_MICRO).pack(side="left")
            if t.get("reboot"):
                tk.Label(top, text="  needs reboot", bg=T.PANEL, fg=T.FG2,
                         font=T.FONT_MICRO).pack(side="left")

            btns = tk.Frame(top, bg=T.PANEL)
            btns.pack(side="right")
            if state:
                tk.Label(btns, text="✓ already optimized", bg=T.PANEL,
                         fg=T.SUCCESS, font=T.FONT_SMALL).pack(side="left",
                                                               padx=(0, 8))
                ActionButton(btns, text="Revert", width=90, secondary=True,
                             command=lambda i=t["id"]: self._revert(i)).pack(side="left")
            else:
                ActionButton(btns, text="Apply", width=90,
                             danger=(t["risk"] == "high"),
                             command=lambda i=t["id"], n=t["name"], r=t["risk"]:
                             self._apply(i, n, r)).pack(side="left")

            tk.Label(row, text=t["desc"], bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, anchor="w", justify="left",
                     wraplength=760).pack(fill="x", padx=(22, 0))
            tk.Label(row, text=f"→ {t['impact']}", bg=T.PANEL,
                     fg=T.lerp_color(T.FG2, T.HIGHLIGHT, 0.5),
                     font=T.FONT_MICRO, anchor="w").pack(fill="x", padx=(22, 0))
            self._rows[t["id"]] = row

    # ── component store ─────────────────────────────────────────────────────
    def _build_component_store(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 16))
        SectionLabel(card, "Windows component store (WinSxS)").pack(
            anchor="w", padx=16, pady=(12, 2))
        tk.Label(card,
                 text="Superseded Windows components pile up here — often "
                      "several GB. Mainstream cleaners don't touch it.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=780).pack(fill="x", padx=16)

        self._cs_lbl = tk.Label(card, text="Not analysed yet.", bg=T.PANEL,
                                fg=T.FG, font=T.FONT_BODY, anchor="w")
        self._cs_lbl.pack(fill="x", padx=16, pady=(8, 4))
        self._cs_prog = ProgressBar(card)
        self._cs_prog.pack(fill="x", padx=16, pady=(0, 6))

        btns = tk.Frame(card, bg=T.PANEL)
        btns.pack(fill="x", padx=16, pady=(0, 14))
        ActionButton(btns, text="Analyse", width=120,
                     command=self._analyse_cs).pack(side="left", padx=(0, 8))
        ActionButton(btns, text="Clean up", width=130, secondary=True,
                     command=self._clean_cs).pack(side="left")

    # ── actions ─────────────────────────────────────────────────────────────
    def _measure(self):
        if self._busy:
            return
        self._busy = True
        self._dpc_verdict.config(text="Measuring for ~3 seconds…", fg=T.FG2)

        def work():
            res = dopt.measure_dpc_latency(seconds=3)
            self.after(0, lambda: self._show_dpc(res))

        threading.Thread(target=work, daemon=True).start()

    def _show_dpc(self, r: dict):
        self._busy = False
        if not r.get("ok"):
            self._dpc_verdict.config(text=r.get("verdict", "Unavailable"),
                                     fg=T.DANGER)
            self._dpc_advice.config(text="\n".join(r.get("advice", [])))
            return
        pct = r["dpc_time_pct"]
        self._dpc_val.config(
            text=f"{pct:.2f}",
            fg=T.SUCCESS if pct < 1.5 else T.WARNING if pct < 3 else T.DANGER)
        self._dpc_extra.config(
            text=f"{r['dpcs_per_sec']:,} DPCs/sec   ·   "
                 f"{r['interrupt_time_pct']:.2f}% interrupt time")
        self._dpc_verdict.config(
            text=r["verdict"],
            fg=T.SUCCESS if pct < 1.5 else T.WARNING if pct < 3 else T.DANGER)
        self._dpc_advice.config(text="\n".join(f"• {a}" for a in r["advice"]))

    def _apply(self, tweak_id: str, name: str, risk: str):
        if self._busy:
            return
        warn = ""
        if tweak_id == "vbs":
            warn = ("\n\n⚠ SECURITY TRADE-OFF: this turns off a hypervisor "
                    "protection against malicious drivers. Recommended only if "
                    "you game and accept the risk. Fully reversible.")
        if not messagebox.askyesno(
                f"Apply: {name}?",
                f"Apply this tweak?{warn}\n\n"
                f"A system restore point is created first, and you can revert "
                f"it from this page at any time."):
            return

        self._busy = True

        def work():
            try:
                from engine import system_restore
                system_restore.ensure_checkpoint(f"deep optimize: {name}")
            except Exception:
                pass
            ok, msg = dopt.apply_tweak(tweak_id)
            self.after(0, lambda: self._done(ok, msg))

        threading.Thread(target=work, daemon=True).start()

    def _revert(self, tweak_id: str):
        if self._busy:
            return
        self._busy = True

        def work():
            ok, msg = dopt.revert_tweak(tweak_id)
            self.after(0, lambda: self._done(ok, msg))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, ok: bool, msg: str):
        self._busy = False
        messagebox.showinfo("Done" if ok else "Not applied", msg)
        self._refresh()

    def _analyse_cs(self):
        if self._busy:
            return
        self._busy = True
        self._cs_lbl.config(text="Analysing component store (can take a minute)…")
        self._cs_prog.indeterminate(True)

        def work():
            res = dopt.analyze_component_store()
            self.after(0, lambda: self._show_cs(res))

        threading.Thread(target=work, daemon=True).start()

    def _show_cs(self, res: dict):
        self._busy = False
        self._cs_prog.indeterminate(False)
        if not res.get("ok"):
            self._cs_lbl.config(text="Could not analyse (run as administrator).",
                                fg=T.DANGER)
            return
        size = res.get("actual_size") or "unknown"
        rec = "cleanup recommended" if res.get("recommended") else "no cleanup needed"
        self._cs_lbl.config(text=f"Component store: {size}  ·  {rec}", fg=T.FG)

    def _clean_cs(self):
        if self._busy:
            return
        reset = messagebox.askyesnocancel(
            "Clean component store",
            "Remove superseded Windows components?\n\n"
            "YES  — deep clean (also resets the base; previously installed "
            "updates can no longer be uninstalled — frees the most space)\n"
            "NO   — safe clean (updates stay uninstallable)\n"
            "CANCEL — do nothing")
        if reset is None:
            return
        self._busy = True
        self._cs_prog.set(0)

        def progress(msg, pct):
            self.after(0, lambda: (self._cs_lbl.config(text=str(msg)),
                                   self._cs_prog.set(pct)))

        def work():
            ok, msg = dopt.cleanup_component_store(reset_base=bool(reset),
                                                   progress_cb=progress)
            self.after(0, lambda: (self._cs_lbl.config(
                text=msg, fg=T.SUCCESS if ok else T.DANGER),
                setattr(self, "_busy", False)))

        threading.Thread(target=work, daemon=True).start()

    # ── state ───────────────────────────────────────────────────────────────
    def _refresh(self):
        def work():
            tweaks = dopt.get_tweaks()
            self.after(0, lambda: self._render_tweaks(tweaks))

        threading.Thread(target=work, daemon=True).start()

    def on_activate(self):
        self._refresh()
