"""Turbo Mode tab — performance / gaming turbo toggle."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import turbo_mode


# Descriptions shown to the user for each profile
_PROFILE_DESCRIPTIONS = {
    "performance": (
        "HIGH PERFORMANCE MODE\n\n"
        "  • Switches to High Performance power plan\n"
        "  • Sets visual effects to Best Performance\n"
        "  • Stops SysMain, WSearch, DiagTrack, Fax, Print Spooler\n"
        "  • Disables telemetry collection\n"
        "  • Frees unused RAM\n\n"
        "All changes are reversed when Turbo Mode is disabled."
    ),
    "gaming": (
        "GAMING MODE\n\n"
        "  • Everything in Performance mode, plus:\n"
        "  • Stops Xbox Live services (Auth, Game Save, Networking)\n"
        "  • Disables Windows Game Bar / GameDVR\n"
        "  • Disables desktop notifications\n"
        "  • Boosts foreground process CPU priority\n\n"
        "All changes are reversed when Turbo Mode is disabled."
    ),
}


class TurboModeTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._mode_var = tk.StringVar(value="performance")
        self._turbo_active = False
        self._build_ui()
        self.after(300, self._refresh_status)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top: status indicator ─────────────────────────────────────────────
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(16, 4))

        status_card = Card(top)
        status_card.pack(side="left", fill="y", padx=(0, 8))

        SectionLabel(status_card, "Turbo Mode").pack(anchor="w", padx=8, pady=(6, 2))

        # Big status indicator
        self._status_canvas = tk.Canvas(status_card, width=140, height=140,
                                        bg=T.PANEL, highlightthickness=0)
        self._status_canvas.pack(padx=16, pady=8)
        self._draw_status_indicator(active=False)

        self._status_text_lbl = tk.Label(status_card, text="INACTIVE",
                                         bg=T.PANEL, fg=T.DANGER,
                                         font=(T.FONT_FAMILY, 11, "bold"))
        self._status_text_lbl.pack(pady=(0, 4))

        self._active_mode_lbl = tk.Label(status_card, text="",
                                         bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._active_mode_lbl.pack(pady=(0, 8))

        # ── Mode selector + description ───────────────────────────────────────
        mode_card = Card(top)
        mode_card.pack(side="left", fill="both", expand=True)

        SectionLabel(mode_card, "Select Mode").pack(anchor="w", padx=8, pady=(6, 2))

        radio_row = tk.Frame(mode_card, bg=T.PANEL)
        radio_row.pack(fill="x", padx=8, pady=4)
        for label, val in [("Performance", "performance"), ("Gaming", "gaming")]:
            tk.Radiobutton(radio_row, text=label, variable=self._mode_var, value=val,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL, font=T.FONT_BOLD,
                           command=self._on_mode_changed).pack(side="left", padx=12)

        self._desc_lbl = tk.Label(mode_card, text=_PROFILE_DESCRIPTIONS["performance"],
                                  bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                  justify="left", anchor="nw", wraplength=340)
        self._desc_lbl.pack(padx=12, pady=(4, 8), anchor="w")

        # ── Action buttons row ────────────────────────────────────────────────
        btn_card = Card(self)
        btn_card.pack(fill="x", padx=16, pady=4)
        btn_row = tk.Frame(btn_card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=8, pady=8)

        self._enable_btn = ActionButton(btn_row, "Enable Turbo Mode",
                                        command=self._start_enable)
        self._enable_btn.pack(side="left", padx=(0, 8))

        self._disable_btn = ActionButton(btn_row, "Disable Turbo Mode",
                                         command=self._start_disable, danger=True)
        self._disable_btn.pack(side="left", padx=(0, 8))
        self._disable_btn.config(state="disabled")

        # Warning label
        tk.Label(btn_row,
                 text="Warning: temporarily stops non-essential Windows services.",
                 bg=T.PANEL, fg=T.WARNING, font=T.FONT_SMALL).pack(side="right", padx=8)

        # ── Progress ──────────────────────────────────────────────────────────
        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=2)

        # ── Changes applied list ──────────────────────────────────────────────
        changes_card = Card(self)
        changes_card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        SectionLabel(changes_card, "Applied Changes").pack(anchor="w", padx=8, pady=(6, 2))
        self._changes_text = tk.Text(changes_card, height=8, bg=T.ACCENT, fg=T.FG,
                                     font=T.FONT_SMALL, state="disabled",
                                     relief="flat", wrap="word")
        self._changes_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── drawing ───────────────────────────────────────────────────────────────

    def _draw_status_indicator(self, active: bool):
        c = self._status_canvas
        c.delete("all")
        cx, cy, r = 70, 70, 55
        color = T.SUCCESS if active else T.DANGER
        outer = T.lerp_color(color, T.PANEL, 0.6)
        c.create_oval(cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10,
                      fill=outer, outline="")
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      fill=color, outline="")
        symbol = "ON" if active else "OFF"
        c.create_text(cx, cy, text=symbol, fill="#ffffff",
                      font=(T.FONT_FAMILY, 18, "bold"))

    # ── mode selector ─────────────────────────────────────────────────────────

    def _on_mode_changed(self):
        mode = self._mode_var.get()
        self._desc_lbl.config(text=_PROFILE_DESCRIPTIONS.get(mode, ""))

    # ── refresh status ────────────────────────────────────────────────────────

    def _refresh_status(self):
        threading.Thread(target=self._do_refresh_status, daemon=True).start()

    def _do_refresh_status(self):
        try:
            st = turbo_mode.get_turbo_status()
            self.after(0, self._apply_status, st)
        except Exception as exc:
            self.after(0, self._status.set, f"Status error: {exc}")

    def _apply_status(self, st: dict):
        active  = st.get("active", False)
        mode    = st.get("mode", "")
        changes = st.get("changes_applied", [])

        self._turbo_active = active
        self._draw_status_indicator(active)

        if active:
            self._status_text_lbl.config(text="ACTIVE", fg=T.SUCCESS)
            self._active_mode_lbl.config(
                text=f"Mode: {mode.capitalize()}" if mode else "Mode: unknown")
            self._enable_btn.config(state="disabled")
            self._disable_btn.config(state="normal")
        else:
            self._status_text_lbl.config(text="INACTIVE", fg=T.DANGER)
            self._active_mode_lbl.config(text="")
            self._enable_btn.config(state="normal")
            self._disable_btn.config(state="disabled")

        self._set_changes_text(changes)

    def _set_changes_text(self, changes: list[str]):
        try:
            self._changes_text.config(state="normal")
            self._changes_text.delete("1.0", "end")
            if changes:
                for item in changes:
                    self._changes_text.insert("end", f"  {item}\n")
            else:
                self._changes_text.insert("end", "No changes applied yet.")
            self._changes_text.config(state="disabled")
        except tk.TclError:
            pass

    # ── enable turbo ──────────────────────────────────────────────────────────

    def _start_enable(self):
        mode = self._mode_var.get()
        if not messagebox.askyesno(
            "Enable Turbo Mode",
            f"Enable Turbo Mode in {mode.capitalize()} profile?\n\n"
            "Non-essential services will be temporarily stopped.\n"
            "You can revert all changes by clicking 'Disable Turbo Mode'."
        ):
            return
        self._enable_btn.config(state="disabled")
        self._disable_btn.config(state="disabled")
        self._progress.indeterminate(True)
        self._status.set(f"Enabling Turbo Mode ({mode})…")
        threading.Thread(target=self._do_enable, args=(mode,), daemon=True).start()

    def _do_enable(self, mode: str):
        def cb(msg: str):
            self.after(0, self._status.set, msg)

        try:
            changes = turbo_mode.enable_turbo(mode=mode, progress_cb=cb)
            self.after(0, self._enable_done, changes, mode)
        except Exception as exc:
            self.after(0, self._status.set, f"Enable error: {exc}")
            self.after(0, self._progress.indeterminate, False)
            self.after(0, self._enable_btn.config, {"state": "normal"})

    def _enable_done(self, changes: list[str], mode: str):
        self._progress.indeterminate(False)
        self._status.set(
            f"Turbo Mode ({mode.capitalize()}) enabled — {len(changes)} changes applied.")
        self._refresh_status()

    # ── disable turbo ─────────────────────────────────────────────────────────

    def _start_disable(self):
        if not messagebox.askyesno(
            "Disable Turbo Mode",
            "Disable Turbo Mode and restore all previous settings?"
        ):
            return
        self._enable_btn.config(state="disabled")
        self._disable_btn.config(state="disabled")
        self._progress.indeterminate(True)
        self._status.set("Restoring system settings…")
        threading.Thread(target=self._do_disable, daemon=True).start()

    def _do_disable(self):
        def cb(msg: str):
            self.after(0, self._status.set, msg)

        try:
            changes = turbo_mode.disable_turbo(progress_cb=cb)
            self.after(0, self._disable_done, changes)
        except Exception as exc:
            self.after(0, self._status.set, f"Disable error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _disable_done(self, changes: list[str]):
        self._progress.indeterminate(False)
        self._status.set(
            f"Turbo Mode disabled — {len(changes)} settings restored.")
        self._refresh_status()
