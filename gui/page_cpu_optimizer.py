"""CPU Optimizer page — remove throttling, force max CPU performance."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton
from engine import cpu_optimizer as cpu


class CpuOptimizerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()
        self._refresh_status()

    # ── Layout ────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔥  CPU Optimizer", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Remove throttle, max out CPU performance",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

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

        self._build_snapshot_card(body)
        self._build_status_card(body)
        self._build_actions_card(body)
        self._build_deep_card(body)
        self._build_log_card(body)

    def _build_snapshot_card(self, parent):
        card = Card(parent, glow=True)
        card.pack(fill="x", pady=(0, 10))

        head = tk.Frame(card, bg=T.PANEL)
        head.pack(fill="x", padx=12, pady=(10, 2))
        SectionLabel(head, "⚡ Live CPU speed — proof, not promises").pack(side="left")
        ActionButton(head, text="Measure", width=110,
                     command=self._measure_snapshot).pack(side="right")

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=12, pady=(4, 4))
        self._snap_mhz = tk.Label(row, text="—", bg=T.PANEL, fg=T.HIGHLIGHT,
                                  font=("Segoe UI", 28, "bold"))
        self._snap_mhz.pack(side="left")
        tk.Label(row, text=" MHz now", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", pady=(14, 0))
        self._snap_turbo = tk.Label(row, text="", bg=T.PANEL, fg=T.FG2,
                                    font=T.FONT_SMALL)
        self._snap_turbo.pack(side="left", padx=20, pady=(14, 0))

        self._snap_name = tk.Label(card, text="Click Measure to read your CPU.",
                                   bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                   anchor="w")
        self._snap_name.pack(fill="x", padx=12, pady=(0, 10))

    def _build_status_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 10))
        SectionLabel(card, "Current CPU Power State").pack(
            anchor="w", padx=12, pady=8)

        self._status_grid = tk.Frame(card, bg=T.PANEL)
        self._status_grid.pack(fill="x", padx=12, pady=(0, 12))

        self._lbl_scheme = self._make_status_row("Active Power Scheme:")
        self._lbl_throttle = self._make_status_row("Power Throttling:")
        self._lbl_priority = self._make_status_row("Foreground Priority Boost:")
        self._lbl_optimized = self._make_status_row("Optimizer Status:")

    def _make_status_row(self, label: str) -> tk.Label:
        row = tk.Frame(self._status_grid, bg=T.PANEL)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY, width=28, anchor="w").pack(side="left")
        val = tk.Label(row, text="—", bg=T.PANEL, fg=T.FG,
                       font=T.FONT_BODY, anchor="w")
        val.pack(side="left", padx=6)
        return val

    def _build_actions_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 10))
        SectionLabel(card, "Actions").pack(anchor="w", padx=12, pady=8)

        info = (
            "MAX PERFORMANCE applies the following tweaks:\n"
            "  • Activates Ultimate Performance power scheme (creates if missing)\n"
            "  • Forces min/max processor state to 100% (no throttle, no cap)\n"
            "  • Disables CPU core parking (all cores stay active)\n"
            "  • Sets performance boost mode to AGGRESSIVE\n"
            "  • Sets performance increase policy to ROCKET (instant ramp-up)\n"
            "  • Energy-Performance Preference → 0 (CPU always prefers speed)\n"
            "  • Unlocks the full turbo boost range (boost policy 100%)\n"
            "  • Disables Windows Power Throttling for all processes\n"
            "  • Boosts foreground process scheduler priority"
        )
        tk.Label(card, text=info, bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL, justify="left",
                 wraplength=720).pack(anchor="w", padx=12, pady=(0, 10))

        warn = ("⚠  Disables battery-friendly throttling — laptops will run hotter "
                "and drain battery faster while active. Use 'Restore Defaults' to revert.")
        tk.Label(card, text=warn, bg=T.PANEL, fg=T.WARNING,
                 font=T.FONT_SMALL, justify="left",
                 wraplength=720).pack(anchor="w", padx=12, pady=(0, 10))

        btns = tk.Frame(card, bg=T.PANEL)
        btns.pack(anchor="w", padx=12, pady=(0, 12))
        ActionButton(btns, text="🔥 MAX PERFORMANCE",
                     command=self._on_optimize).pack(side="left", padx=(0, 8))
        ActionButton(btns, text="↺ Restore Defaults", danger=True,
                     command=self._on_restore).pack(side="left", padx=(0, 8))
        ActionButton(btns, text="Refresh",
                     command=self._refresh_status).pack(side="left")

    def _build_deep_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 10))
        SectionLabel(card, "🔥 Deep CPU tweaks — the last few percent").pack(
            anchor="w", padx=12, pady=(10, 2))
        tk.Label(card,
                 text="Hidden power settings Windows doesn't show. Each one is "
                      "backed up first and individually revertible. Risky items "
                      "are marked in red.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=780).pack(fill="x", padx=12)
        self._deep_host = tk.Frame(card, bg=T.PANEL)
        self._deep_host.pack(fill="x", padx=12, pady=(6, 12))
        tk.Label(self._deep_host, text="Reading current settings…",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

    def _render_deep(self, tweaks):
        risk_color = {"low": T.SUCCESS, "medium": T.WARNING, "high": T.DANGER}
        for w in self._deep_host.winfo_children():
            w.destroy()
        if not tweaks:
            tk.Label(self._deep_host, text="No deep tweaks available on this system.",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")
            return
        for t in tweaks:
            row = tk.Frame(self._deep_host, bg=T.PANEL)
            row.pack(fill="x", pady=4)

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
                tk.Label(top, text="  reboot for full effect", bg=T.PANEL,
                         fg=T.FG2, font=T.FONT_MICRO).pack(side="left")

            btns = tk.Frame(top, bg=T.PANEL)
            btns.pack(side="right")
            if state:
                tk.Label(btns, text="✓ active", bg=T.PANEL, fg=T.SUCCESS,
                         font=T.FONT_SMALL).pack(side="left", padx=(0, 8))
                ActionButton(btns, text="Revert", width=90, secondary=True,
                             command=lambda i=t["id"]: self._deep_revert(i)
                             ).pack(side="left")
            else:
                ActionButton(btns, text="Apply", width=90,
                             danger=(t["risk"] == "high"),
                             command=lambda i=t["id"], n=t["name"],
                             r=t["risk"]: self._deep_apply(i, n, r)
                             ).pack(side="left")

            tk.Label(row, text=t["desc"], bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, anchor="w", justify="left",
                     wraplength=760).pack(fill="x", padx=(22, 0))
            tk.Label(row, text=f"→ {t['impact']}", bg=T.PANEL,
                     fg=T.lerp_color(T.FG2, T.HIGHLIGHT, 0.5),
                     font=T.FONT_MICRO, anchor="w").pack(fill="x", padx=(22, 0))

    def _build_log_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, "Activity Log").pack(anchor="w", padx=12, pady=8)
        self._log = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_SMALL,
                             height=10, wrap="word", state="disabled",
                             bd=0, relief="flat")
        self._log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── Behavior ──────────────────────────────────────────────────────────
    def _log_line(self, msg: str):
        self._log.config(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.config(state="disabled")

    def _refresh_status(self):
        def work():
            try:
                s = cpu.get_status()
                self.after(0, self._apply_status, s)
            except Exception as e:
                self.after(0, self._log_line, f"Status error: {e}")
        threading.Thread(target=work, daemon=True).start()

    def _apply_status(self, s: dict):
        self._lbl_scheme.config(text=s.get("scheme_name", "—"))

        if s.get("power_throttling_disabled"):
            self._lbl_throttle.config(text="DISABLED ✓", fg=T.SUCCESS)
        else:
            self._lbl_throttle.config(text="enabled (default)", fg=T.FG)

        prio = s.get("win32_priority_separation")
        if prio == 38:
            self._lbl_priority.config(text="BOOSTED ✓ (38)", fg=T.SUCCESS)
        else:
            self._lbl_priority.config(text=f"default ({prio})", fg=T.FG)

        if s.get("optimized"):
            self._lbl_optimized.config(
                text=f"ACTIVE ✓  (applied {s.get('applied_at', '?')})",
                fg=T.SUCCESS)
        else:
            self._lbl_optimized.config(text="not applied", fg=T.FG2)

    def _on_optimize(self):
        if self._busy:
            return
        if not messagebox.askyesno(
                "Maximum Performance",
                "Apply aggressive CPU tweaks?\n\n"
                "This removes all throttling and forces the CPU to its highest "
                "sustained performance. Reversible via 'Restore Defaults'."):
            return
        self._busy = True
        self._log_line("─── MAX PERFORMANCE ───")

        def work():
            try:
                changes = cpu.optimize_cpu(
                    progress_cb=lambda m: self.after(0, self._log_line, "  " + m))
                self.after(0, self._refresh_status)
                self.after(0, self._log_line,
                           f"✓ Applied {len(changes)} CPU tweaks.")
            except Exception as e:
                self.after(0, self._log_line, f"✗ Error: {e}")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _on_restore(self):
        if self._busy:
            return
        if not messagebox.askyesno(
                "Restore Defaults",
                "Revert CPU optimizer changes and restore previous power state?"):
            return
        self._busy = True
        self._log_line("─── RESTORE DEFAULTS ───")

        def work():
            try:
                changes = cpu.restore_defaults(
                    progress_cb=lambda m: self.after(0, self._log_line, "  " + m))
                self.after(0, self._refresh_status)
                self.after(0, self._log_line,
                           f"✓ Restore complete ({len(changes)} steps).")
            except Exception as e:
                self.after(0, self._log_line, f"✗ Error: {e}")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    # ── Live snapshot ─────────────────────────────────────────────────────
    def _measure_snapshot(self):
        self._snap_name.config(text="Measuring (about 2 seconds)…")

        def work():
            try:
                s = cpu.get_cpu_snapshot()
                self.after(0, self._show_snapshot, s)
            except Exception as e:
                self.after(0, self._log_line, f"Snapshot error: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _show_snapshot(self, s: dict):
        if not s.get("ok") or not s.get("base_mhz"):
            self._snap_name.config(text="Could not read CPU counters.")
            return
        mhz = s.get("current_mhz") or s["base_mhz"]
        pct = s.get("perf_pct", 0)
        self._snap_mhz.config(
            text=f"{mhz:,}",
            fg=T.SUCCESS if pct >= 100 else T.HIGHLIGHT)
        turbo = (f"turbo +{pct - 100:.0f}% over base" if pct > 100
                 else f"{pct:.0f}% of base clock")
        self._snap_turbo.config(
            text=f"base {s['base_mhz']:,} MHz   ·   {turbo}")
        hybrid = "  ·  hybrid P/E cores" if s.get("hybrid") else ""
        self._snap_name.config(
            text=f"{s['name']}  ·  {s['cores']} cores / "
                 f"{s['threads']} threads{hybrid}")

    # ── Deep tweaks ───────────────────────────────────────────────────────
    def _refresh_deep(self):
        def work():
            try:
                tweaks = cpu.get_deep_tweaks()
                self.after(0, self._render_deep, tweaks)
            except Exception as e:
                self.after(0, self._log_line, f"Deep tweaks error: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _deep_apply(self, tweak_id: str, name: str, risk: str):
        if self._busy:
            return
        warn = ""
        if tweak_id == "idle_disable":
            warn = ("\n\n⚠ EXTREME: the CPU never idles — expect significantly "
                    "higher temperatures and power draw. Desktops with good "
                    "cooling only. Applied on AC power only, never battery.")
        if not messagebox.askyesno(
                f"Apply: {name}?",
                f"Apply this tweak?{warn}\n\nBacked up first — you can revert "
                f"it from this page at any time."):
            return
        self._busy = True
        self._log_line(f"─── APPLY: {name} ───")

        def work():
            try:
                if risk == "high":
                    try:
                        from engine import system_restore
                        system_restore.ensure_checkpoint(f"CPU tweak: {name}")
                    except Exception:
                        pass
                ok, msg = cpu.apply_deep_tweak(tweak_id)
                self.after(0, self._log_line, ("  ✓ " if ok else "  ✗ ") + msg)
                self.after(0, self._refresh_deep)
            except Exception as e:
                self.after(0, self._log_line, f"  ✗ Error: {e}")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _deep_revert(self, tweak_id: str):
        if self._busy:
            return
        self._busy = True

        def work():
            try:
                ok, msg = cpu.revert_deep_tweak(tweak_id)
                self.after(0, self._log_line, ("  ✓ " if ok else "  ✗ ") + msg)
                self.after(0, self._refresh_deep)
            except Exception as e:
                self.after(0, self._log_line, f"  ✗ Error: {e}")
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def on_activate(self):
        self._refresh_status()
        self._refresh_deep()
        self._measure_snapshot()
