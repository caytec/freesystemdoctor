"""Cron Builder page — visual cron expression editor with validation and suggestions."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton
from engine import cron_builder as cb


class CronBuilderPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Cron Builder", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Visual cron expression editor with validation",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_quick_select_card(body)
        self._build_custom_builder_card(body)
        self._build_expression_card(body)
        self._build_preview_card(body)

    def _build_quick_select_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Quick Patterns").pack(anchor="w", padx=10, pady=8)

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        patterns = cb.get_common_patterns()
        self._pattern_var = tk.StringVar()
        pattern_combo = ttk.Combobox(btn_row, textvariable=self._pattern_var, state="readonly", width=35)
        pattern_combo["values"] = list(patterns.keys())
        pattern_combo.pack(side="left", fill="x", expand=True)
        pattern_combo.bind("<<ComboboxSelected>>", lambda e: self._on_pattern_selected())

        ActionButton(btn_row, text="Apply Pattern",
                     command=self._on_apply_pattern).pack(side="left", padx=(10, 0))

    def _build_custom_builder_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Custom Builder").pack(anchor="w", padx=10, pady=8)

        # Simple builder mode
        mode_row = tk.Frame(card, bg=T.PANEL)
        mode_row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(mode_row, text="Build by:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left", padx=10)

        self._mode_var = tk.StringVar(value="frequency")
        ttk.Radiobutton(mode_row, text="Frequency", variable=self._mode_var, value="frequency",
                       command=self._on_mode_changed).pack(side="left", padx=5)
        ttk.Radiobutton(mode_row, text="Interval", variable=self._mode_var, value="interval",
                       command=self._on_mode_changed).pack(side="left", padx=5)
        ttk.Radiobutton(mode_row, text="Manual", variable=self._mode_var, value="manual",
                       command=self._on_mode_changed).pack(side="left", padx=5)

        # Frequency builder
        self._freq_frame = tk.Frame(card, bg=T.PANEL)
        self._freq_frame.pack(fill="x", padx=10, pady=8)

        row1 = tk.Frame(self._freq_frame, bg=T.PANEL)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Frequency:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=15).pack(side="left")
        self._freq_var = tk.StringVar(value="daily")
        freq_combo = ttk.Combobox(row1, textvariable=self._freq_var, state="readonly", width=20)
        freq_combo["values"] = ["hourly", "daily", "weekly", "monthly", "quarterly"]
        freq_combo.pack(side="left", fill="x", expand=True, padx=(10, 0))

        row2 = tk.Frame(self._freq_frame, bg=T.PANEL)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Time (HH:MM):", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=15).pack(side="left")
        self._time_entry = tk.Entry(row2, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY, width=10)
        self._time_entry.insert(0, "00:00")
        self._time_entry.pack(side="left", padx=(10, 0))

        # Interval builder
        self._interval_frame = tk.Frame(card, bg=T.PANEL)
        self._interval_frame.pack(fill="x", padx=10, pady=8)

        row3 = tk.Frame(self._interval_frame, bg=T.PANEL)
        row3.pack(fill="x", pady=4)
        tk.Label(row3, text="Every N:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=15).pack(side="left")
        self._interval_var = tk.StringVar(value="5")
        self._interval_spin = tk.Spinbox(row3, from_=1, to=59, textvariable=self._interval_var, width=10)
        self._interval_spin.pack(side="left", padx=(10, 0))

        tk.Label(row3, text="Unit:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left", padx=(20, 0))
        self._unit_var = tk.StringVar(value="minutes")
        unit_combo = ttk.Combobox(row3, textvariable=self._unit_var, state="readonly", width=15)
        unit_combo["values"] = ["minutes", "hours", "days"]
        unit_combo.pack(side="left", padx=(10, 0))

        # Build button
        tk.Button(card, text="Build Expression", command=self._on_build, bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_BODY, padx=10, pady=6).pack(anchor="w", padx=10, pady=(8, 0))

        self._interval_frame.pack_forget()

    def _build_expression_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Cron Expression").pack(anchor="w", padx=10, pady=8)

        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row1, text="Expression:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left", padx=10)
        self._expr_entry = tk.Entry(row1, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY)
        self._expr_entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
        self._expr_entry.bind("<KeyRelease>", lambda e: self._on_expr_changed())

        ActionButton(row1, text="Validate",
                     command=self._on_validate).pack(side="left", padx=(0, 10))

        # Validation status
        self._validation_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._validation_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_preview_card(self, parent):
        card = Card(parent)
        card.pack(fill="x")

        SectionLabel(card, "Preview").pack(anchor="w", padx=10, pady=8)

        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row1, text="Description:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left", padx=10)
        self._description = tk.Label(row1, text="(Enter expression to preview)", bg=T.PANEL, fg=T.FG,
                                     font=T.FONT_SMALL, wraplength=600, justify="left")
        self._description.pack(side="left", fill="x", expand=True, padx=(10, 0))

        row2 = tk.Frame(card, bg=T.PANEL)
        row2.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row2, text="Next Run:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left", padx=10)
        self._next_run = tk.Label(row2, text="–", bg=T.PANEL, fg=T.FG, font=T.FONT_SMALL)
        self._next_run.pack(side="left", fill="x", expand=True, padx=(10, 0))

    def _on_mode_changed(self):
        mode = self._mode_var.get()
        if mode == "frequency":
            self._freq_frame.pack(fill="x", padx=10, pady=8)
            self._interval_frame.pack_forget()
        elif mode == "interval":
            self._freq_frame.pack_forget()
            self._interval_frame.pack(fill="x", padx=10, pady=8)
        else:
            self._freq_frame.pack_forget()
            self._interval_frame.pack_forget()

    def _on_pattern_selected(self):
        patterns = cb.get_common_patterns()
        pattern = self._pattern_var.get()
        if pattern in patterns:
            self._expr_entry.delete(0, tk.END)
            self._expr_entry.insert(0, patterns[pattern])
            self._on_expr_changed()

    def _on_apply_pattern(self):
        self._on_pattern_selected()

    def _on_build(self):
        mode = self._mode_var.get()

        if mode == "frequency":
            freq = self._freq_var.get()
            time_str = self._time_entry.get()
            expr = cb.build_simple_schedule(freq, time_str)
        elif mode == "interval":
            unit = self._unit_var.get()
            interval = int(self._interval_var.get())
            expr = cb.schedule_with_interval(unit, interval)
        else:
            messagebox.showwarning("Mode", "Manual mode: edit expression directly")
            return

        if expr:
            self._expr_entry.delete(0, tk.END)
            self._expr_entry.insert(0, expr)
            self._on_expr_changed()
        else:
            messagebox.showerror("Error", "Could not build expression")

    def _on_expr_changed(self):
        expr = self._expr_entry.get().strip()

        if not expr:
            self._description.config(text="(Enter expression to preview)")
            self._next_run.config(text="–")
            self._validation_status.config(text="")
            return

        # Validate
        valid, msg = cb.validate_cron(expr)

        if valid:
            description = cb.explain_cron(expr)
            next_run = cb.suggest_next_runtime(expr)

            self._description.config(text=description, fg=T.SUCCESS)
            self._next_run.config(text=next_run)
            self._validation_status.config(text="✓ Valid expression", fg=T.SUCCESS)
        else:
            self._description.config(text="(Invalid expression)", fg=T.FG2)
            self._next_run.config(text="–")
            self._validation_status.config(text=f"✗ {msg}", fg=T.DANGER)

    def _on_validate(self):
        expr = self._expr_entry.get().strip()
        if not expr:
            messagebox.showwarning("Empty", "Enter a cron expression to validate")
            return

        valid, msg = cb.validate_cron(expr)

        if valid:
            description = cb.explain_cron(expr)
            next_run = cb.suggest_next_runtime(expr)
            messagebox.showinfo("Valid Expression",
                f"Expression: {expr}\n\n{description}\n\nNext run: {next_run}")
        else:
            messagebox.showerror("Invalid Expression", f"Error: {msg}")

    def on_activate(self):
        pass
