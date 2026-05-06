"""Scheduler tab — configure and manage the automated cleaning schedule."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import scheduled_cleaner


# Available modules with display labels
_MODULES = [
    ("disk_cleaner",        "Disk Cleaner"),
    ("registry_cleaner",    "Registry Cleaner"),
    ("empty_folder_finder", "Empty Folder Finder"),
]


class SchedulerTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._module_vars: dict[str, tk.BooleanVar] = {}
        self._build_ui()
        self.after(400, self._refresh)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top: current schedule status ──────────────────────────────────────
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(16, 4))

        # Status card
        st_card = Card(top)
        st_card.pack(side="left", fill="y", padx=(0, 8))
        SectionLabel(st_card, "Schedule Status").pack(anchor="w", padx=8, pady=(6, 2))

        self._enabled_lbl = tk.Label(st_card, text="Checking…",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_BOLD)
        self._enabled_lbl.pack(padx=12, pady=(4, 2), anchor="w")

        info_rows = [
            ("Frequency:", "_freq_lbl"),
            ("Time:",      "_time_lbl"),
            ("Last run:",  "_last_lbl"),
            ("Next run:",  "_next_lbl"),
        ]
        for label_text, attr in info_rows:
            row = tk.Frame(st_card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text=label_text, bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, width=11, anchor="w").pack(side="left")
            lbl = tk.Label(row, text="—", bg=T.PANEL, fg=T.FG,
                           font=T.FONT_SMALL, anchor="w")
            lbl.pack(side="left")
            setattr(self, attr, lbl)

        tk.Frame(st_card, bg=T.PANEL, height=4).pack()  # spacer

        # Configuration card
        cfg_card = Card(top)
        cfg_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(cfg_card, "Configure Schedule").pack(anchor="w", padx=8, pady=(6, 2))

        # Enable toggle
        en_row = tk.Frame(cfg_card, bg=T.PANEL)
        en_row.pack(fill="x", padx=10, pady=4)
        tk.Label(en_row, text="Enable schedule:", bg=T.PANEL,
                 fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._enable_var = tk.BooleanVar(value=False)
        tk.Checkbutton(en_row, variable=self._enable_var, bg=T.PANEL,
                       fg=T.FG, selectcolor=T.ACCENT,
                       activebackground=T.PANEL).pack(side="left", padx=6)

        # Frequency selector
        freq_row = tk.Frame(cfg_card, bg=T.PANEL)
        freq_row.pack(fill="x", padx=10, pady=4)
        tk.Label(freq_row, text="Frequency:", bg=T.PANEL,
                 fg=T.FG, font=T.FONT_BODY, width=11,
                 anchor="w").pack(side="left")
        self._freq_var = tk.StringVar(value="Daily")
        freq_cb = ttk.Combobox(freq_row, textvariable=self._freq_var,
                               state="readonly", width=12,
                               values=["Daily", "Weekly", "Monthly"])
        freq_cb.pack(side="left", padx=4)

        # Time picker
        time_row = tk.Frame(cfg_card, bg=T.PANEL)
        time_row.pack(fill="x", padx=10, pady=4)
        tk.Label(time_row, text="Time (HH:MM):", bg=T.PANEL,
                 fg=T.FG, font=T.FONT_BODY, width=14,
                 anchor="w").pack(side="left")
        self._hour_spin = tk.Spinbox(time_row, from_=0, to=23, width=3,
                                     format="%02.0f",
                                     bg=T.ACCENT, fg=T.FG,
                                     insertbackground=T.FG,
                                     buttonbackground=T.ACCENT,
                                     font=T.FONT_BODY)
        self._hour_spin.pack(side="left")
        tk.Label(time_row, text=":", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BOLD).pack(side="left")
        self._min_spin = tk.Spinbox(time_row, from_=0, to=59, width=3,
                                    format="%02.0f",
                                    bg=T.ACCENT, fg=T.FG,
                                    insertbackground=T.FG,
                                    buttonbackground=T.ACCENT,
                                    font=T.FONT_BODY)
        self._min_spin.pack(side="left")

        # Modules checklist
        mod_card = Card(top)
        mod_card.pack(side="left", fill="y")
        SectionLabel(mod_card, "Modules to Run").pack(anchor="w", padx=8, pady=(6, 2))
        for key, label in _MODULES:
            var = tk.BooleanVar(value=True)
            self._module_vars[key] = var
            tk.Checkbutton(mod_card, text=label, variable=var,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL,
                           font=T.FONT_BODY).pack(anchor="w", padx=12, pady=2)
        tk.Frame(mod_card, bg=T.PANEL, height=4).pack()  # spacer

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Save Schedule",
                     command=self._save_schedule).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Run Now",
                     command=self._run_now).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Delete Schedule",
                     command=self._delete_schedule,
                     danger=True).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Refresh",
                     command=self._refresh).pack(side="left")

        # ── Progress bar ──────────────────────────────────────────────────────
        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        # ── Last run results ──────────────────────────────────────────────────
        res_card = Card(self)
        res_card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        SectionLabel(res_card, "Last Run Results").pack(anchor="w", padx=8, pady=(6, 2))
        self._results_text = tk.Text(res_card, height=8, bg=T.ACCENT, fg=T.FG,
                                     font=T.FONT_SMALL, state="disabled",
                                     relief="flat", wrap="word")
        self._results_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_results_text(self, text: str):
        try:
            self._results_text.config(state="normal")
            self._results_text.delete("1.0", "end")
            self._results_text.insert("end", text)
            self._results_text.config(state="disabled")
        except tk.TclError:
            pass

    def _selected_modules(self) -> list[str]:
        return [key for key, var in self._module_vars.items() if var.get()]

    def _time_string(self) -> str:
        h = self._hour_spin.get().strip().zfill(2)
        m = self._min_spin.get().strip().zfill(2)
        return f"{h}:{m}"

    # ── refresh ───────────────────────────────────────────────────────────────

    def _refresh(self):
        self._progress.indeterminate(True)
        self._status.set("Loading schedule…")
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        try:
            sched = scheduled_cleaner.get_schedule()
            self.after(0, self._apply_refresh, sched)
        except Exception as exc:
            self.after(0, self._status.set, f"Refresh error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _apply_refresh(self, sched: dict):
        self._progress.indeterminate(False)

        enabled   = sched.get("enabled", False)
        frequency = sched.get("frequency", "daily").capitalize()
        time_str  = sched.get("time", "03:00")
        last_run  = sched.get("last_run", "")
        next_run  = sched.get("next_run", "")
        modules   = sched.get("modules", [])

        # Status labels
        if enabled:
            self._enabled_lbl.config(text="ENABLED", fg=T.SUCCESS)
        else:
            self._enabled_lbl.config(text="DISABLED", fg=T.DANGER)
        self._freq_lbl.config(text=frequency)
        self._time_lbl.config(text=time_str)
        self._last_lbl.config(text=last_run[:19] if last_run else "Never")
        self._next_lbl.config(text=next_run[:19] if next_run else "—")

        # Configuration widgets
        self._enable_var.set(enabled)
        freq_map = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly"}
        self._freq_var.set(freq_map.get(frequency.lower(), frequency))

        # Parse time
        parts = time_str.split(":")
        if len(parts) == 2:
            self._hour_spin.delete(0, "end")
            self._hour_spin.insert(0, parts[0].zfill(2))
            self._min_spin.delete(0, "end")
            self._min_spin.insert(0, parts[1].zfill(2))

        # Module checkboxes
        for key, var in self._module_vars.items():
            var.set(key in modules)

        self._status.set(
            f"Schedule {'enabled' if enabled else 'disabled'} — "
            f"{frequency} at {time_str}."
        )

    # ── save schedule ─────────────────────────────────────────────────────────

    def _save_schedule(self):
        enabled  = self._enable_var.get()
        freq     = self._freq_var.get().lower()
        time_str = self._time_string()
        modules  = self._selected_modules()

        if enabled and not modules:
            messagebox.showwarning("No modules",
                                   "Select at least one module to include in the schedule.")
            return

        self._progress.indeterminate(True)
        self._status.set("Saving schedule…")
        threading.Thread(target=self._do_save,
                         args=(enabled, freq, time_str, modules),
                         daemon=True).start()

    def _do_save(self, enabled: bool, freq: str, time_str: str, modules: list[str]):
        try:
            ok = scheduled_cleaner.set_schedule(enabled, freq, time_str, modules)
            self.after(0, self._save_done, ok, enabled)
        except Exception as exc:
            self.after(0, self._status.set, f"Save error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _save_done(self, ok: bool, enabled: bool):
        self._progress.indeterminate(False)
        if ok:
            state = "enabled" if enabled else "disabled"
            self._status.set(f"Schedule {state} and saved.")
            messagebox.showinfo("Schedule Saved",
                                f"Schedule has been {state} successfully.\n\n"
                                "(Requires administrator rights to register the task)")
            self._refresh()
        else:
            messagebox.showerror("Error",
                                 "Could not save schedule.\n"
                                 "(May require administrator rights)")

    # ── delete schedule ───────────────────────────────────────────────────────

    def _delete_schedule(self):
        if not messagebox.askyesno("Delete Schedule",
                                   "Remove the FreeSystemDoctor scheduled task?"):
            return
        self._progress.indeterminate(True)
        self._status.set("Deleting scheduled task…")
        threading.Thread(target=self._do_delete, daemon=True).start()

    def _do_delete(self):
        try:
            ok = scheduled_cleaner.delete_schedule()
            self.after(0, self._delete_done, ok)
        except Exception as exc:
            self.after(0, self._status.set, f"Delete error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _delete_done(self, ok: bool):
        self._progress.indeterminate(False)
        if ok:
            self._status.set("Scheduled task deleted.")
            self._refresh()
        else:
            messagebox.showerror("Error",
                                 "Could not delete the scheduled task.\n"
                                 "(May require administrator rights)")

    # ── run now ───────────────────────────────────────────────────────────────

    def _run_now(self):
        modules = self._selected_modules()
        if not modules:
            messagebox.showwarning("No modules",
                                   "Select at least one module to run.")
            return
        labels = [label for key, label in _MODULES if key in modules]
        if not messagebox.askyesno(
            "Run Now",
            f"Run the following cleaning modules now?\n\n"
            + "\n".join(f"  • {l}" for l in labels)
        ):
            return
        self._progress.indeterminate(True)
        self._status.set("Running auto-clean…")
        self._set_results_text("Running…")
        threading.Thread(target=self._do_run_now, args=(modules,), daemon=True).start()

    def _do_run_now(self, modules: list[str]):
        try:
            result = scheduled_cleaner.run_auto_clean(modules=modules)
            self.after(0, self._run_done, result)
        except Exception as exc:
            self.after(0, self._status.set, f"Run error: {exc}")
            self.after(0, self._progress.indeterminate, False)
            self.after(0, self._set_results_text, f"Error: {exc}")

    def _run_done(self, result: dict):
        self._progress.indeterminate(False)
        modules_run  = result.get("modules_run", [])
        issues_fixed = result.get("issues_fixed", 0)
        errors       = result.get("errors", [])
        ts           = result.get("timestamp", "")

        lines = [
            f"Auto-clean completed at {ts}",
            f"Modules run:    {', '.join(modules_run) if modules_run else 'none'}",
            f"Issues fixed:   {issues_fixed}",
        ]
        if errors:
            lines.append("")
            lines.append("Errors:")
            for e in errors:
                lines.append(f"  • {e}")
        self._set_results_text("\n".join(lines))
        self._status.set(
            f"Auto-clean done — {issues_fixed} issue(s) fixed, "
            f"{len(errors)} error(s)."
        )
        self._refresh()
