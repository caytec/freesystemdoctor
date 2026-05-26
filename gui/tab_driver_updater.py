"""Driver Updater tab — installed drivers, problem detection, winget updates."""

import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import driver_updater


class DriverUpdaterTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._all_drivers: list[dict] = []
        self._winget_updates: list[dict] = []
        self._problem_ids: set[str] = set()
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header + buttons
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Driver Updater").pack(side="left", padx=8, pady=8)
        self._driver_count_lbl = tk.Label(hdr, text="", bg=T.PANEL,
                                          fg=T.HIGHLIGHT, font=T.FONT_BOLD)
        self._driver_count_lbl.pack(side="right", padx=12)

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Scan Drivers",
                     command=self._start_scan).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Check Updates (winget)",
                     command=self._start_winget_check).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Update Selected",
                     command=self._update_selected).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Open Device Manager",
                     command=self._open_devmgr).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Export CSV",
                     command=self._export_csv).pack(side="left", padx=(0, 8))

        # Filter row
        filt_row = tk.Frame(self, bg=T.BG)
        filt_row.pack(fill="x", padx=16, pady=2)
        tk.Label(filt_row, text="Filter by class:", bg=T.BG,
                 fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
        self._class_var = tk.StringVar(value="All")
        self._class_cb = ttk.Combobox(filt_row, textvariable=self._class_var,
                                      state="readonly", width=22)
        self._class_cb["values"] = ["All"]
        self._class_cb.pack(side="left", padx=6)
        self._class_cb.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        self._show_problems_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filt_row, text="Show problematic only",
                       variable=self._show_problems_var,
                       bg=T.BG, fg=T.FG, selectcolor=T.ACCENT,
                       activebackground=T.BG, font=T.FONT_SMALL,
                       command=self._apply_filter).pack(side="left", padx=8)

        # Progress bar
        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        # Driver treeview
        tv_card = Card(self)
        tv_card.pack(fill="both", expand=True, padx=16, pady=(4, 4))

        cols = ("Version", "Manufacturer", "Date", "Class")
        self._tv = ttk.Treeview(tv_card, columns=cols, show="tree headings", height=12)
        apply_treeview_style(self._tv)
        self._tv.heading("#0",          text="Device Name",   anchor="w")
        self._tv.heading("Version",     text="Version",       anchor="w")
        self._tv.heading("Manufacturer",text="Manufacturer",  anchor="w")
        self._tv.heading("Date",        text="Date",          anchor="w")
        self._tv.heading("Class",       text="Class",         anchor="w")
        self._tv.column("#0",          width=240, minwidth=140)
        self._tv.column("Version",     width=110, minwidth=80)
        self._tv.column("Manufacturer",width=160, minwidth=100)
        self._tv.column("Date",        width=130, minwidth=80)
        self._tv.column("Class",       width=120, minwidth=70)

        sb = ttk.Scrollbar(tv_card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

        # Winget updates card
        upd_card = Card(self)
        upd_card.pack(fill="x", padx=16, pady=(0, 16))
        upd_hdr = tk.Frame(upd_card, bg=T.PANEL)
        upd_hdr.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(upd_hdr, "Winget Driver Updates").pack(side="left")
        self._upd_count_lbl = tk.Label(upd_hdr, text="", bg=T.PANEL,
                                       fg=T.WARNING, font=T.FONT_BOLD)
        self._upd_count_lbl.pack(side="right")

        cols_u = ("Installed", "Available", "Winget ID")
        self._upd_tv = ttk.Treeview(upd_card, columns=cols_u,
                                    show="tree headings", height=5)
        apply_treeview_style(self._upd_tv)
        self._upd_tv.heading("#0",        text="Package Name", anchor="w")
        self._upd_tv.heading("Installed", text="Installed",    anchor="w")
        self._upd_tv.heading("Available", text="Available",    anchor="w")
        self._upd_tv.heading("Winget ID", text="Winget ID",    anchor="w")
        self._upd_tv.column("#0",        width=200)
        self._upd_tv.column("Installed", width=100)
        self._upd_tv.column("Available", width=100)
        self._upd_tv.column("Winget ID", width=200)
        self._upd_tv.pack(fill="x", padx=8, pady=(0, 8))

    # ── scan ──────────────────────────────────────────────────────────────────

    def _start_scan(self):
        self._progress.indeterminate(True)
        self._status.set("Scanning installed drivers… this may take a moment.")
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._all_drivers = []
        self._problem_ids = set()
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        try:
            drivers = driver_updater.get_installed_drivers()
            problems = driver_updater.find_problematic_drivers()
            self.after(0, self._show_drivers, drivers, problems)
        except Exception as exc:
            self.after(0, self._status.set, f"Scan error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _show_drivers(self, drivers: list[dict], problems: list[dict]):
        self._progress.indeterminate(False)
        self._all_drivers = drivers

        # Collect problematic device IDs for tag highlighting
        self._problem_ids = {p.get("device_id", "").upper() for p in problems}

        # Build class list for filter
        classes = sorted({d.get("device_class", "") for d in drivers if d.get("device_class")})
        self._class_cb["values"] = ["All"] + classes

        self._apply_filter()

        count = len(drivers)
        prob_count = len(problems)
        self._driver_count_lbl.config(
            text=f"{count} drivers | {prob_count} problematic"
        )
        self._status.set(
            f"Found {count} drivers — {prob_count} problematic (highlighted in yellow)."
        )

    def _apply_filter(self):
        for item in self._tv.get_children():
            self._tv.delete(item)

        sel_class  = self._class_var.get()
        prob_only  = self._show_problems_var.get()

        for d in self._all_drivers:
            device_id  = d.get("device_id", "").upper()
            drv_class  = d.get("device_class", "")
            is_problem = device_id in self._problem_ids

            if prob_only and not is_problem:
                continue
            if sel_class != "All" and drv_class != sel_class:
                continue

            tag = "problem" if is_problem else "normal"
            # Format WMI date e.g. "20240115000000.000000+000" -> "2024-01-15"
            raw_date = d.get("date", "")
            date_str = raw_date[:8] if len(raw_date) >= 8 else raw_date
            if len(date_str) == 8 and date_str.isdigit():
                date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            self._tv.insert("", "end",
                            text=d.get("name", "(no name)"),
                            values=(d.get("version", ""), d.get("manufacturer", ""),
                                    date_str, drv_class),
                            tags=(tag,))

        self._tv.tag_configure("problem", foreground=T.WARNING)
        self._tv.tag_configure("normal",  foreground=T.FG)

    # ── winget check ──────────────────────────────────────────────────────────

    def _start_winget_check(self):
        self._progress.indeterminate(True)
        self._status.set("Checking winget for driver updates… (requires internet connection)")
        for item in self._upd_tv.get_children():
            self._upd_tv.delete(item)
        self._winget_updates = []
        threading.Thread(target=self._do_winget_check, daemon=True).start()

    def _do_winget_check(self):
        try:
            updates = driver_updater.check_driver_updates_winget()
            self.after(0, self._show_winget, updates)
        except Exception as exc:
            self.after(0, self._status.set, f"Winget check error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _show_winget(self, updates: list[dict]):
        self._progress.indeterminate(False)
        self._winget_updates = updates
        for item in self._upd_tv.get_children():
            self._upd_tv.delete(item)
        for u in updates:
            self._upd_tv.insert("", "end",
                                 text=u.get("name", ""),
                                 values=(u.get("installed", ""),
                                         u.get("available", ""),
                                         u.get("winget_id", "")))
        count = len(updates)
        self._upd_count_lbl.config(text=f"{count} update{'s' if count != 1 else ''} found")
        self._status.set(
            f"Winget check complete — {count} driver-related update(s) available."
        )

    # ── update selected ───────────────────────────────────────────────────────

    def _update_selected(self):
        sel = self._upd_tv.selection()
        if not sel:
            messagebox.showinfo("No selection",
                                "Select one or more entries from the Winget Updates list.")
            return
        ids_to_update = []
        for iid in sel:
            vals = self._upd_tv.item(iid, "values")
            if vals and len(vals) >= 3:
                wid = vals[2]
                if wid:
                    ids_to_update.append(wid)
        if not ids_to_update:
            messagebox.showwarning("No winget IDs", "Selected entries have no winget IDs.")
            return
        if not messagebox.askyesno(
            "Update Drivers",
            f"Update {len(ids_to_update)} package(s) via winget?\n"
            f"\n{chr(10).join(ids_to_update[:10])}\n\n"
            "This may take several minutes and requires internet access."
        ):
            return
        self._progress.indeterminate(True)
        self._status.set(f"Updating {len(ids_to_update)} package(s)…")
        threading.Thread(target=self._do_update,
                         args=(ids_to_update,), daemon=True).start()

    def _do_update(self, winget_ids: list[str]):
        ok_count = 0
        fail_count = 0
        for wid in winget_ids:
            self.after(0, self._status.set, f"Updating {wid}…")
            try:
                ok = driver_updater.update_driver_winget(wid)
                if ok:
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1
        self.after(0, self._update_done, ok_count, fail_count)

    def _update_done(self, ok: int, fail: int):
        self._progress.indeterminate(False)
        self._status.set(f"Updates complete — {ok} succeeded, {fail} failed.")
        messagebox.showinfo("Update Complete",
                            f"Successfully updated: {ok}\nFailed: {fail}")

    # ── other actions ─────────────────────────────────────────────────────────

    def _open_devmgr(self):
        try:
            driver_updater.open_device_manager()
            self._status.set("Device Manager opened.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open Device Manager: {exc}")

    def _export_csv(self):
        if not self._all_drivers:
            messagebox.showinfo("No data", "Run Scan Drivers first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="drivers_export.csv",
            title="Export Driver List",
        )
        if not path:
            return
        self._status.set(f"Exporting to {path}…")
        threading.Thread(target=self._do_export, args=(path,), daemon=True).start()

    def _do_export(self, path: str):
        try:
            ok = driver_updater.export_driver_report(path)
            self.after(0, self._export_done, path, ok)
        except Exception as exc:
            self.after(0, self._status.set, f"Export error: {exc}")

    def _export_done(self, path: str, ok: bool):
        if ok:
            self._status.set(f"Exported to {os.path.basename(path)}.")
            messagebox.showinfo("Export Complete", f"Driver list saved to:\n{path}")
        else:
            messagebox.showerror("Export Failed", "Could not export driver list.")
