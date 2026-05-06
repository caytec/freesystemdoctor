"""Theme Manager page — customize application colors and appearance."""

import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton
from engine import theme_manager as tm


class ThemeManagerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()
        self._load_themes()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Theme Manager", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Customize application colors and appearance",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_presets_card(body)
        self._build_color_picker_card(body)

    def _build_presets_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Preset Themes").pack(anchor="w", padx=10, pady=8)

        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(row1, text="Select Theme:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left", padx=10)

        self._theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(row1, textvariable=self._theme_var, state="readonly", width=30)
        theme_combo.pack(side="left", fill="x", expand=True, padx=(10, 0))
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self._on_theme_selected())

        ActionButton(row1, text="Apply",
                     command=self._on_apply_preset).pack(side="left", padx=(10, 0))

        # Preview row
        preview_row = tk.Frame(card, bg=T.PANEL)
        preview_row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(preview_row, text="Preview:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left", padx=10)

        self._preview_bg = tk.Frame(preview_row, bg="#ffffff", width=20, height=20)
        self._preview_bg.pack(side="left", padx=10, fill="both", expand=False)

        self._preview_fg = tk.Frame(preview_row, bg="#000000", width=20, height=20)
        self._preview_fg.pack(side="left", padx=2, fill="both", expand=False)

        self._preview_accent = tk.Frame(preview_row, bg="#cccccc", width=20, height=20)
        self._preview_accent.pack(side="left", padx=2, fill="both", expand=False)

        self._preview_highlight = tk.Frame(preview_row, bg="#0000ff", width=20, height=20)
        self._preview_highlight.pack(side="left", padx=2, fill="both", expand=False)

    def _build_color_picker_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Custom Theme Editor").pack(anchor="w", padx=10, pady=8)

        # Custom theme name
        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=4)
        tk.Label(row1, text="Theme Name:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY, width=15).pack(side="left")
        self._custom_name = tk.Entry(row1, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY)
        self._custom_name.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Color pickers grid
        colors_frame = tk.Frame(card, bg=T.PANEL)
        colors_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self._color_buttons = {}
        color_names = ["Background", "Foreground", "Accent", "Panel", "Highlight", "Success", "Warning", "Danger"]
        color_keys = ["bg", "fg", "accent", "panel", "highlight", "success", "warning", "danger"]

        for i, (name, key) in enumerate(zip(color_names, color_keys)):
            row = tk.Frame(colors_frame, bg=T.PANEL)
            row.pack(fill="x", pady=4)

            tk.Label(row, text=f"{name}:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=15).pack(side="left")

            color_display = tk.Frame(row, bg="#cccccc", width=30, height=25)
            color_display.pack(side="left", padx=10)
            self._color_buttons[key] = color_display

            color_label = tk.Label(row, text="#ffffff", bg=T.PANEL, fg=T.FG, font=T.FONT_SMALL, width=10)
            color_label.pack(side="left", padx=5)
            self._color_buttons[f"{key}_label"] = color_label

            def on_color_click(k=key):
                self._on_pick_color(k)

            tk.Button(row, text="Pick", command=on_color_click, bg=T.ACCENT, fg=T.FG,
                     font=T.FONT_SMALL, width=8).pack(side="left", padx=5)

        # Action buttons
        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(8, 0))

        ActionButton(btn_row, text="Save Custom Theme",
                     command=self._on_save_custom).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Reset to Preset",
                     command=self._on_reset_preset).pack(side="left")

        self._status_label = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._status_label.pack(anchor="w", padx=10, pady=(8, 0))

    def _load_themes(self):
        all_themes = tm.get_all_themes()
        theme_names = sorted(all_themes.keys())

        if hasattr(self, '_theme_var'):
            self._theme_var.set(theme_names[0] if theme_names else "Dark (Default)")

            # Find and set combo values
            for widget in self.winfo_children():
                for child in self._find_widget(widget, ttk.Combobox):
                    child["values"] = theme_names

    def _find_widget(self, parent, widget_type):
        """Recursively find widgets of a specific type."""
        results = []
        if isinstance(parent, widget_type):
            results.append(parent)
        for child in parent.winfo_children():
            results.extend(self._find_widget(child, widget_type))
        return results

    def _on_theme_selected(self):
        theme_name = self._theme_var.get()
        all_themes = tm.get_all_themes()
        if theme_name in all_themes:
            theme = all_themes[theme_name]
            self._update_preview(theme)

    def _update_preview(self, theme):
        """Update preview colors."""
        self._preview_bg.config(bg=theme.bg)
        self._preview_fg.config(bg=theme.fg)
        self._preview_accent.config(bg=theme.accent)
        self._preview_highlight.config(bg=theme.highlight)

    def _on_pick_color(self, color_key):
        current_color = self._color_buttons[color_key].cget("bg")
        color = colorchooser.askcolor(color=current_color, title=f"Pick {color_key} color")

        if color[1]:  # color[1] is the hex value
            self._color_buttons[color_key].config(bg=color[1])
            self._color_buttons[f"{color_key}_label"].config(text=color[1])

    def _on_apply_preset(self):
        theme_name = self._theme_var.get()
        tm.save_theme(theme_name)
        messagebox.showinfo("Success", f"Applied theme: {theme_name}\n\nRestart the application to see changes.")

    def _on_save_custom(self):
        name = self._custom_name.get().strip()
        if not name:
            messagebox.showwarning("Missing Name", "Enter a custom theme name")
            return

        colors = {}
        color_keys = ["bg", "fg", "accent", "panel", "highlight", "success", "warning", "danger"]
        for key in color_keys:
            color_hex = self._color_buttons[f"{key}_label"].cget("text")
            if tm.validate_color(color_hex):
                colors[key] = color_hex
            else:
                messagebox.showerror("Invalid Color", f"Invalid color for {key}: {color_hex}")
                return

        if tm.save_custom_theme(name, colors):
            messagebox.showinfo("Success", f"Saved custom theme: {name}\n\nRestart the application to see changes.")
            self._custom_name.delete(0, tk.END)
            self._load_themes()
        else:
            messagebox.showerror("Error", "Failed to save custom theme")

    def _on_reset_preset(self):
        theme_name = self._theme_var.get()
        all_themes = tm.get_all_themes()
        if theme_name in all_themes:
            theme = all_themes[theme_name]
            # Update color picker with theme colors
            for key in ["bg", "fg", "accent", "panel", "highlight", "success", "warning", "danger"]:
                color = getattr(theme, key, "#ffffff")
                self._color_buttons[key].config(bg=color)
                self._color_buttons[f"{key}_label"].config(text=color)

    def on_activate(self):
        pass
