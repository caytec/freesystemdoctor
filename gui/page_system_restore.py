"""System Restore page — Manage restore points and shadow copies."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import system_restore as sr


class SystemRestorePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="System Restore", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Manage restore points and shadow copies",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Restore points section
        self._build_restore_points_section(body)

        # Shadow copies info
        self._build_shadow_section(body)

    def _build_restore_points_section(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Restore Points").pack(anchor="w", padx=10, pady=8)

        # Tree
        tree_frame = tk.Frame(card, bg=T.ACCENT)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("created", "type"), height=8)
        self._tree.column("#0", width=250)
        self._tree.column("created", width=150)
        self._tree.column("type", width=100)
        self._tree.heading("#0", text="Restore Point")
        self._tree.heading("created", text="Created")
        self._tree.heading("type", text="Type")
        self._tree.pack(fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Create Restore Point",
                     command=self._on_create).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Delete Selected",
                     command=self._on_delete).pack(side="left", padx=0)

    def _build_shadow_section(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=False)

        SectionLabel(card, "Shadow Copies (VSS)").pack(anchor="w", padx=10, pady=8)

        self._shadow_info = tk.Label(card, text="Loading...", bg=T.PANEL, fg=T.FG2,
                                    font=T.FONT_SMALL, justify="left")
        self._shadow_info.pack(anchor="w", padx=10, pady=(0, 8))

        # Load data
        self._load_data()

    def _load_data(self):
        def load():
            try:
                points = sr.get_restore_points()
                self._tree.delete(*self._tree.get_children())
                for point in points[:20]:
                    self._tree.insert("", "end", text=point.get("name", "Unknown"),
                                    values=(point.get("created", ""), point.get("type", "")))

                storage = sr.get_shadow_storage()
                info_text = f"Shadow Copy Storage:\n"
                info_text += f"  Used: {storage.get('used_mb', 0) / 1024:.1f} GB\n"
                info_text += f"  Available: {storage.get('available_mb', 0) / 1024:.1f} GB"
                self._shadow_info.config(text=info_text)
            except Exception as e:
                self._shadow_info.config(text=f"Error: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _on_create(self):
        def create():
            try:
                sr.create_restore_point()
                messagebox.showinfo("Success", "Restore point created successfully")
                self._load_data()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create restore point: {e}")

        threading.Thread(target=create, daemon=True).start()

    def _on_delete(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a restore point to delete")
            return

        if messagebox.askyesno("Confirm", "Delete selected restore point(s)?"):
            def delete():
                try:
                    for item in selected:
                        point_name = self._tree.item(item)["text"]
                        sr.delete_restore_point(point_name)
                    messagebox.showinfo("Success", "Restore point(s) deleted")
                    self._load_data()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete: {e}")

            threading.Thread(target=delete, daemon=True).start()

    def on_activate(self):
        self._load_data()
