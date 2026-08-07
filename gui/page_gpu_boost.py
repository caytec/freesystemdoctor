"""GPU Boost page — squeeze the full potential out of the GPU.

Live telemetry (clocks, utilisation, temperature, power) plus persistent
GPU tweaks: HAGS, PCIe link power, windowed-game flip model, Game Mode/DVR,
MPO, NVIDIA maximum performance state.
"""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, PageHeader
from engine import gpu_boost as gb


class GpuBoostPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="GPU Boost",
                   subtitle="Unlock the full potential of your graphics card",
                   icon="🎯", color="#ff5c5c").pack(fill="x")

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

        self._build_snapshot(body)
        self._build_tweaks(body)

    def _build_snapshot(self, parent):
        card = Card(parent, glow=True)
        card.pack(fill="x", pady=(0, 12))

        head = tk.Frame(card, bg=T.PANEL)
        head.pack(fill="x", padx=16, pady=(12, 2))
        SectionLabel(head, "🎯 Live GPU — proof, not promises").pack(side="left")
        ActionButton(head, text="Measure", width=110,
                     command=self._measure).pack(side="right")

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=16, pady=(4, 2))
        self._clock = tk.Label(row, text="—", bg=T.PANEL, fg=T.HIGHLIGHT,
                               font=("Segoe UI", 28, "bold"))
        self._clock.pack(side="left")
        tk.Label(row, text=" MHz now", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", pady=(14, 0))
        self._extra = tk.Label(row, text="", bg=T.PANEL, fg=T.FG2,
                               font=T.FONT_SMALL)
        self._extra.pack(side="left", padx=20, pady=(14, 0))

        self._gpu_name = tk.Label(card, text="Click Measure to read your GPU.",
                                  bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                  anchor="w")
        self._gpu_name.pack(fill="x", padx=16, pady=(0, 12))

    def _build_tweaks(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 16))
        SectionLabel(card, "GPU tweaks").pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(card,
                 text="Persistent GPU-side tuning — every change is backed up "
                      "first and individually revertible. Items marked medium "
                      "risk are situational; read the description.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=780).pack(fill="x", padx=16)
        self._host = tk.Frame(card, bg=T.PANEL)
        self._host.pack(fill="x", padx=16, pady=(6, 14))
        tk.Label(self._host, text="Reading current settings…",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

    def _render_tweaks(self, tweaks):
        risk_color = {"low": T.SUCCESS, "medium": T.WARNING, "high": T.DANGER}
        for w in self._host.winfo_children():
            w.destroy()
        rows = []
        for t in tweaks:
            row = tk.Frame(self._host, bg=T.PANEL)
            row.pack(fill="x", pady=4)
            rows.append(row)

            top = tk.Frame(row, bg=T.PANEL)
            top.pack(fill="x")
            state = t.get("optimized")
            tk.Label(top, text="●" if state else "○", bg=T.PANEL,
                     fg=T.SUCCESS if state else T.FG2,
                     font=(T.FONT_FAMILY, 12)).pack(side="left", padx=(0, 6))
            tk.Label(top, text=t["name"], bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BOLD).pack(side="left")
            tk.Label(top, text=f"  [{t['risk']} risk]", bg=T.PANEL,
                     fg=risk_color.get(t["risk"], T.FG2),
                     font=T.FONT_MICRO).pack(side="left")
            if t.get("reboot"):
                tk.Label(top, text="  needs reboot", bg=T.PANEL, fg=T.FG2,
                         font=T.FONT_MICRO).pack(side="left")

            btns = tk.Frame(top, bg=T.PANEL)
            btns.pack(side="right")
            if state:
                tk.Label(btns, text="✓ active", bg=T.PANEL, fg=T.SUCCESS,
                         font=T.FONT_SMALL).pack(side="left", padx=(0, 8))
                ActionButton(btns, text="Revert", width=90, secondary=True,
                             command=lambda i=t["id"]: self._revert(i)
                             ).pack(side="left")
            else:
                ActionButton(btns, text="Apply", width=90,
                             danger=(t["risk"] == "high"),
                             command=lambda i=t["id"], n=t["name"],
                             r=t["risk"]: self._apply(i, n, r)
                             ).pack(side="left")

            tk.Label(row, text=t["desc"], bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, anchor="w", justify="left",
                     wraplength=760).pack(fill="x", padx=(22, 0))
            tk.Label(row, text=f"→ {t['impact']}", bg=T.PANEL,
                     fg=T.lerp_color(T.FG2, T.HIGHLIGHT, 0.5),
                     font=T.FONT_MICRO, anchor="w").pack(fill="x", padx=(22, 0))
        T.stagger_in(rows, step_ms=45)

    # ── actions ──────────────────────────────────────────────────────────────
    def _measure(self):
        self._gpu_name.config(text="Reading GPU telemetry…")

        def work():
            try:
                s = gb.get_gpu_snapshot()
                self.after(0, self._show_snapshot, s)
            except Exception as e:
                self.after(0, lambda: self._gpu_name.config(
                    text=f"Error: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _show_snapshot(self, s: dict):
        if not s.get("ok"):
            self._gpu_name.config(text="Could not detect a GPU.")
            return
        if s.get("clock_mhz") is not None:
            T.count_up(self._clock, s["clock_mhz"], fmt="{:,.0f}",
                       duration_ms=750)
            bits = []
            if s.get("clock_max_mhz"):
                bits.append(f"max {s['clock_max_mhz']:,} MHz")
            if s.get("util_pct") is not None:
                bits.append(f"{s['util_pct']}% load")
            if s.get("temp_c") is not None:
                bits.append(f"{s['temp_c']}°C")
            if s.get("power_w") is not None and s.get("power_limit_w"):
                bits.append(f"{s['power_w']:.0f}/{s['power_limit_w']:.0f} W")
            self._extra.config(text="   ·   ".join(bits))
        else:
            self._clock.config(text="—")
            self._extra.config(text="live clocks need an NVIDIA driver "
                                    "(nvidia-smi)")
        vram = f"  ·  {s['vram_mb'] / 1024:.0f} GB VRAM" if s.get("vram_mb") else ""
        self._gpu_name.config(text=f"{s['name']}{vram}")

    def _refresh(self):
        def work():
            try:
                tweaks = gb.get_tweaks()
                self.after(0, self._render_tweaks, tweaks)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _apply(self, tweak_id: str, name: str, risk: str):
        if self._busy:
            return
        warn = ""
        if tweak_id == "mpo":
            warn = ("\n\n⚠ Apply only if you actually see flicker, black "
                    "flashes or VRR stutter — MPO is beneficial otherwise.")
        if tweak_id == "nv_max_perf":
            warn = ("\n\n⚠ The GPU will keep higher clocks at idle — more "
                    "power draw and heat when doing nothing.")
        if not messagebox.askyesno(
                f"Apply: {name}?",
                f"Apply this tweak?{warn}\n\nBacked up first — revertible "
                f"from this page at any time."):
            return
        self._busy = True

        def work():
            try:
                if risk != "low":
                    try:
                        from engine import system_restore
                        system_restore.ensure_checkpoint(f"GPU boost: {name}")
                    except Exception:
                        pass
                ok, msg = gb.apply_tweak(tweak_id)
                self.after(0, self._done, ok, msg)
            except Exception as e:
                self.after(0, self._done, False, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _revert(self, tweak_id: str):
        if self._busy:
            return
        self._busy = True

        def work():
            try:
                ok, msg = gb.revert_tweak(tweak_id)
                self.after(0, self._done, ok, msg)
            except Exception as e:
                self.after(0, self._done, False, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, ok: bool, msg: str):
        self._busy = False
        messagebox.showinfo("Done" if ok else "Not applied", msg)
        self._refresh()

    def on_activate(self):
        self._refresh()
        self._measure()
