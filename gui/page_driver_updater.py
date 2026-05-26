"""Driver Updater page — Detect and update outdated drivers."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import driver_updater as du


class DriverUpdaterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._mode = "drivers"   # drivers | updates | problems
        self._update_rows: list[dict] = []
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔧  Driver Updater", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Detect, diagnose and update Windows drivers",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        card = Card(body)
        card.pack(fill="both", expand=True)

        # View toggle row
        toggle_row = tk.Frame(card, bg=T.PANEL)
        toggle_row.pack(fill="x", padx=12, pady=8)

        SectionLabel(toggle_row, "View:").pack(side="left", padx=(0, 8))
        for label, mode in [("Installed Drivers", "drivers"),
                             ("Available Updates", "updates"),
                             ("Problem Devices",   "problems")]:
            ActionButton(toggle_row, text=label, width=160,
                          command=lambda m=mode: self._switch_mode(m),
                          secondary=(mode != "drivers")).pack(side="left", padx=(0, 6))

        # Progress
        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=12, pady=(0, 4))

        self._status_lbl = tk.Label(card, text="",
                                      bg=T.PANEL, fg=T.FG2,
                                      font=T.FONT_SMALL, anchor="w")
        self._status_lbl.pack(fill="x", padx=12, pady=(0, 4))

        # Treeview
        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("a", "b", "c", "d"),
                                    show="headings", height=14, selectmode="extended")
        self._tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._tree.yview)
        sb.pack(side="right", fill="y")
        self._tree.configure(yscrollcommand=sb.set)

        # Buttons
        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))

        self._scan_btn = ActionButton(btn_frame, text="🔬 Scan",
                                        command=self._refresh, width=130)
        self._scan_btn.pack(side="left", padx=(0, 6))

        self._update_btn = ActionButton(btn_frame, text="⚡ Update Selected",
                                          command=self._on_update_selected, width=160)
        self._update_btn.pack(side="left", padx=(0, 6))

        ActionButton(btn_frame, text="⬇ Update All",
                      command=self._on_update_all, width=130,
                      secondary=True).pack(side="left", padx=(0, 6))

        ActionButton(btn_frame, text="🛠 Device Manager",
                      command=du.open_device_manager, width=150,
                      secondary=True).pack(side="left", padx=(0, 6))

        ActionButton(btn_frame, text="📄 Export Report",
                      command=self._on_export, width=140,
                      secondary=True).pack(side="left")

        self._switch_mode("drivers")

    # ── view modes ────────────────────────────────────────────────────────────

    def _switch_mode(self, mode: str):
        self._mode = mode
        cols = {
            "drivers":  [("Driver", 280, "w"),
                         ("Version", 110, "w"),
                         ("Manufacturer", 180, "w"),
                         ("Class", 110, "w")],
            "updates":  [("Package", 320, "w"),
                         ("Installed", 120, "w"),
                         ("Available", 120, "w"),
                         ("Winget ID", 200, "w")],
            "problems": [("Device", 320, "w"),
                         ("Error", 80, "center"),
                         ("Description", 260, "w"),
                         ("Status", 100, "w")],
        }
        for col, (label, w, anchor) in zip(("a", "b", "c", "d"), cols[mode]):
            self._tree.heading(col, text=label)
            self._tree.column(col, width=w, anchor=anchor)
        self._tree.delete(*self._tree.get_children())

        # Disable buttons that don't make sense in this mode
        if mode == "updates":
            self._update_btn.set_enabled(True)
        else:
            self._update_btn.set_enabled(mode == "problems")  # restart-driver fallback

        self._refresh()

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        self._progress.indeterminate(True)
        self._status_lbl.config(text="Scanning…", fg=T.FG2)

        def work():
            try:
                if self._mode == "drivers":
                    data = du.get_installed_drivers()
                    self.after(0, lambda: self._populate_drivers(data))
                elif self._mode == "updates":
                    data = du.check_driver_updates_winget()
                    self.after(0, lambda: self._populate_updates(data))
                elif self._mode == "problems":
                    data = du.find_problematic_drivers()
                    self.after(0, lambda: self._populate_problems(data))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._status_lbl.config(
                    text=f"Error: {err}", fg=T.DANGER))
                self.after(0, lambda: self._progress.indeterminate(False))

        threading.Thread(target=work, daemon=True).start()

    def _populate_drivers(self, drivers: list[dict]):
        self._progress.indeterminate(False)
        self._progress.set(100)
        for d in drivers:
            self._tree.insert("", "end", values=(
                d.get("name", "?"),
                d.get("version", ""),
                d.get("manufacturer", ""),
                d.get("device_class", ""),
            ))
        self._status_lbl.config(text=f"Found {len(drivers)} installed drivers",
                                  fg=T.SUCCESS)

    def _populate_updates(self, updates: list[dict]):
        self._progress.indeterminate(False)
        self._progress.set(100)
        self._update_rows = updates
        for u in updates:
            self._tree.insert("", "end", values=(
                u.get("name", "?"),
                u.get("installed", ""),
                u.get("available", ""),
                u.get("winget_id", ""),
            ), tags=("update",))
        self._tree.tag_configure("update", foreground=T.HIGHLIGHT)

        if updates:
            self._status_lbl.config(
                text=f"⬇ {len(updates)} driver/firmware update(s) available",
                fg=T.HIGHLIGHT)
        else:
            self._status_lbl.config(text="✓ All drivers up to date",
                                      fg=T.SUCCESS)

    def _populate_problems(self, problems: list[dict]):
        self._progress.indeterminate(False)
        self._progress.set(100)
        for p in problems:
            self._tree.insert("", "end", values=(
                p.get("name", "?"),
                p.get("error_code", ""),
                p.get("error_description", ""),
                p.get("status", ""),
            ), tags=("problem",))
        self._tree.tag_configure("problem", foreground=T.DANGER)
        if problems:
            self._status_lbl.config(
                text=f"⚠ {len(problems)} device(s) with errors",
                fg=T.DANGER)
        else:
            self._status_lbl.config(text="✓ No problem devices",
                                      fg=T.SUCCESS)

    # ── actions ───────────────────────────────────────────────────────────────

    def _on_update_selected(self):
        if self._mode != "updates":
            messagebox.showinfo("Switch view",
                                  "Switch to 'Available Updates' first.")
            return
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No selection",
                                    "Select one or more rows to update.")
            return
        ids = []
        for item in sel:
            vals = self._tree.item(item)["values"]
            if len(vals) >= 4 and vals[3]:
                ids.append(str(vals[3]))
        if not ids:
            return
        self._update_packages(ids)

    def _on_update_all(self):
        if self._mode != "updates":
            self._switch_mode("updates")
            return
        if not self._update_rows:
            return
        if not messagebox.askyesno("Update all",
                                    f"Install {len(self._update_rows)} update(s)?"):
            return
        ids = [u["winget_id"] for u in self._update_rows if u.get("winget_id")]
        self._update_packages(ids)

    def _update_packages(self, winget_ids: list[str]):
        self._progress.indeterminate(True)
        self._status_lbl.config(text=f"Updating {len(winget_ids)} package(s)…",
                                  fg=T.FG2)

        def work():
            ok = 0
            for wid in winget_ids:
                try:
                    if du.update_driver_winget(wid):
                        ok += 1
                except Exception:
                    pass
            self.after(0, lambda: self._after_update(ok, len(winget_ids)))

        threading.Thread(target=work, daemon=True).start()

    def _after_update(self, ok: int, total: int):
        self._progress.indeterminate(False)
        self._progress.set(100)
        self._status_lbl.config(
            text=f"✓ {ok}/{total} package(s) updated",
            fg=T.SUCCESS if ok == total else T.WARNING)
        self._refresh()

    def _on_export(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Report", "*.txt"), ("All Files", "*.*")],
            title="Save driver report",
        )
        if not path:
            return

        def work():
            try:
                ok = du.export_driver_report(path)
                self.after(0, lambda: self._status_lbl.config(
                    text=f"✓ Report saved to {path}" if ok
                          else "✕ Export failed",
                    fg=T.SUCCESS if ok else T.DANGER))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._status_lbl.config(
                    text=f"Export error: {err}", fg=T.DANGER))

        threading.Thread(target=work, daemon=True).start()

    def on_activate(self):
        if not self._tree.get_children():
            self._refresh()
