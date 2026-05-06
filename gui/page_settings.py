"""Settings page — theme, language, report export, tray icon."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import webbrowser

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import i18n
from engine import report_exporter


class SettingsPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._tray_var = tk.BooleanVar(value=False)
        self._lang_var = tk.StringVar(value=i18n.get_language())
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Settings", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Application preferences and configuration",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_appearance_card(body)
        self._build_tray_card(body)
        self._build_language_card(body)
        self._build_report_card(body)
        self._build_about_card(body)

    def _build_appearance_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Appearance").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(row, text="Theme:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")

        theme_frame = tk.Frame(row, bg=T.PANEL)
        theme_frame.pack(side="left")
        ActionButton(theme_frame, text="Dark (current)",
                     command=lambda: self._set_theme("dark")).pack(side="left", padx=(0, 6))
        ActionButton(theme_frame, text="Light",
                     command=lambda: self._set_theme("light")).pack(side="left")

        self._theme_note = tk.Label(card,
            text="Theme change requires application restart to fully apply.",
            bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._theme_note.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_tray_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "System Tray").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(row, text="Show tray icon with live CPU/RAM",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        ToggleSwitch(row, variable=self._tray_var,
                     command=self._on_tray_toggle).pack(side="left", padx=12)

        self._tray_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._tray_status.pack(anchor="w", padx=10, pady=(0, 8))

        note = tk.Label(card,
            text="Requires: pip install pystray pillow",
            bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        note.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_language_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Language").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(row, text="Interface language:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")

        langs = i18n.available_languages()
        lang_display = [name for _, name in langs]
        lang_codes = [code for code, _ in langs]

        current_name = next((n for c, n in langs if c == self._lang_var.get()), "English")
        self._lang_display_var = tk.StringVar(value=current_name)

        cb = ttk.Combobox(row, textvariable=self._lang_display_var,
                          values=lang_display, state="readonly", width=15)
        cb.pack(side="left", padx=8)

        def on_lang_change(event=None):
            name = self._lang_display_var.get()
            code = next((c for c, n in langs if n == name), "en")
            i18n.set_language(code)
            messagebox.showinfo("Language", "Language saved. Restart the application to apply.")

        cb.bind("<<ComboboxSelected>>", on_lang_change)
        ActionButton(row, text="Apply", command=on_lang_change).pack(side="left")

    def _build_report_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Reports").pack(anchor="w", padx=10, pady=8)

        tk.Label(card, text="Generate a detailed HTML report of your system status and scan results.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, wraplength=550, justify="left"
                 ).pack(anchor="w", padx=10, pady=(0, 8))

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row, text="Generate Report (Desktop)",
                     command=self._on_generate_report).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Choose Save Location",
                     command=self._on_generate_report_custom).pack(side="left")

        self._report_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._report_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_about_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "About FreeSystemDoctor").pack(anchor="w", padx=10, pady=8)

        info = [
            ("Version", "2.1"),
            ("Python", "3.11+"),
            ("Platform", "Windows 10/11"),
            ("License", "Free & Open Source"),
        ]
        for label, value in info:
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=label + ":", bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, width=12, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BODY).pack(side="left")

        tk.Frame(card, bg=T.PANEL, height=8).pack()

    def _set_theme(self, theme: str):
        import json, os
        from pathlib import Path
        cfg_dir = Path(os.environ.get("TEMP", "C:\\Temp")) / "FreeSystemDoctor"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        with open(cfg_dir / "theme.json", "w") as f:
            json.dump({"theme": theme}, f)
        messagebox.showinfo("Theme", f"{theme.capitalize()} theme saved. Restart to apply.")

    def _on_tray_toggle(self):
        enabled = self._tray_var.get()
        if enabled:
            try:
                from engine import system_tray
                ok = system_tray.start_tray(self._app)
                if ok:
                    self._tray_status.config(text="Tray icon active", fg=T.SUCCESS)
                else:
                    self._tray_var.set(False)
                    self._tray_status.config(
                        text="Failed — install pystray and pillow: pip install pystray pillow",
                        fg=T.DANGER)
            except Exception as e:
                self._tray_var.set(False)
                self._tray_status.config(text=f"Error: {e}", fg=T.DANGER)
        else:
            try:
                from engine import system_tray
                system_tray.stop_tray()
                self._tray_status.config(text="Tray icon stopped", fg=T.FG2)
            except Exception:
                pass

    def _on_generate_report(self):
        self._report_status.config(text="Generating report...", fg=T.FG2)

        def gen():
            try:
                path = report_exporter.generate_quick_report()
                self.after(0, lambda: self._report_status.config(
                    text=f"Saved to: {path}", fg=T.SUCCESS))
                webbrowser.open(path)
            except Exception as e:
                self.after(0, lambda: self._report_status.config(
                    text=f"Error: {e}", fg=T.DANGER))

        threading.Thread(target=gen, daemon=True).start()

    def _on_generate_report_custom(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Report", "*.html"), ("All Files", "*.*")],
            title="Save Report"
        )
        if not path:
            return
        self._report_status.config(text="Generating report...", fg=T.FG2)

        def gen():
            try:
                out = report_exporter.generate_quick_report(path)
                self.after(0, lambda: self._report_status.config(
                    text=f"Saved: {out}", fg=T.SUCCESS))
                webbrowser.open(out)
            except Exception as e:
                self.after(0, lambda: self._report_status.config(
                    text=f"Error: {e}", fg=T.DANGER))

        threading.Thread(target=gen, daemon=True).start()

    def on_activate(self):
        try:
            from engine import system_tray
            self._tray_var.set(system_tray.is_running())
        except Exception:
            pass
