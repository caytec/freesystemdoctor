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

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_status_card(body)
        self._build_actions_card(body)
        self._build_log_card(body)

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

    def on_activate(self):
        self._refresh_status()
