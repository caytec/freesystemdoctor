"""Desktop Icon Saver page."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton
from engine import icon_saver as ic


class IconSaverPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🖥  Desktop Icon Saver", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Snapshot and restore desktop icon positions",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Action card
        act_card = Card(body)
        act_card.pack(fill="x", pady=(0, 12))
        SectionLabel(act_card, "Save Current Layout").pack(anchor="w", padx=12, pady=8)

        row = tk.Frame(act_card, bg=T.PANEL)
        row.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(row, text="Layout name:",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left")
        self._name_entry = tk.Entry(row, bg=T.ACCENT, fg=T.FG,
                                      font=T.FONT_BODY, width=24,
                                      insertbackground=T.FG)
        self._name_entry.pack(side="left", padx=8)

        ActionButton(row, text="📸 Snapshot Now",
                      command=self._on_save, width=160).pack(side="left", padx=(8, 0))

        self._status_lbl = tk.Label(act_card, text="",
                                      bg=T.PANEL, fg=T.FG2,
                                      font=T.FONT_SMALL)
        self._status_lbl.pack(anchor="w", padx=12, pady=(0, 12))

        # Saved layouts card
        list_card = Card(body)
        list_card.pack(fill="both", expand=True)
        SectionLabel(list_card, "Saved Layouts").pack(anchor="w", padx=12, pady=8)

        cols = ("name", "saved", "count")
        self._tv = ttk.Treeview(list_card, columns=cols, show="headings", height=8)
        self._tv.heading("name", text="Name")
        self._tv.heading("saved", text="Saved")
        self._tv.heading("count", text="Icons")
        self._tv.column("name", width=240, anchor="w")
        self._tv.column("saved", width=180, anchor="w")
        self._tv.column("count", width=80, anchor="center")
        self._tv.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        bot = tk.Frame(list_card, bg=T.PANEL)
        bot.pack(fill="x", padx=12, pady=(0, 12))
        ActionButton(bot, text="↺ Restore",
                      command=self._on_restore, width=120).pack(side="left", padx=(0, 8))
        ActionButton(bot, text="🗑 Delete",
                      command=self._on_delete, width=120,
                      danger=True).pack(side="left", padx=(0, 8))
        ActionButton(bot, text="↻ Refresh",
                      command=self._refresh, width=100,
                      secondary=True).pack(side="left")

    def _on_save(self):
        name = self._name_entry.get().strip() or None
        self._status_lbl.config(text="Saving…", fg=T.FG2)

        def work():
            try:
                path = ic.save_layout(name)
                count = len(ic.list_icons())
                self.after(0, lambda: self._status_lbl.config(
                    text=f"  ✓ Saved {count} icons to {path}", fg=T.SUCCESS))
                self.after(0, self._refresh)
                self.after(0, lambda: self._name_entry.delete(0, tk.END))
            except Exception as e:
                self.after(0, lambda: self._status_lbl.config(
                    text=f"  ✕ {e}", fg=T.DANGER))

        threading.Thread(target=work, daemon=True).start()

    def _selected_path(self):
        sel = self._tv.selection()
        if not sel:
            return None
        return self._tv.item(sel[0])["tags"][0] if self._tv.item(sel[0])["tags"] else None

    def _on_restore(self):
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Restore", "Select a layout first.")
            return

        def work():
            ok, msg = ic.restore_layout(path)
            self.after(0, lambda: self._status_lbl.config(
                text=f"  {msg}", fg=T.SUCCESS if ok else T.DANGER))

        threading.Thread(target=work, daemon=True).start()

    def _on_delete(self):
        path = self._selected_path()
        if not path:
            return
        if not messagebox.askyesno("Delete layout", "Delete this saved layout?"):
            return
        ic.delete_layout(path)
        self._refresh()

    def _refresh(self):
        for item in self._tv.get_children():
            self._tv.delete(item)
        for layout in ic.list_saved_layouts():
            saved = layout["saved"][:19].replace("T", " ")
            self._tv.insert("", "end",
                             values=(layout["name"], saved, layout["count"]),
                             tags=(layout["file"],))

    def on_activate(self):
        self._refresh()
