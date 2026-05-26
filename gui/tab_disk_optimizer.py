"""Disk Optimizer tab — drive analysis, defrag/TRIM, and health checks."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import disk_optimizer


class DiskOptimizerTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._drives: list[dict] = []
        self._build_ui()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header row
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Disk Optimizer").pack(side="left", padx=8, pady=8)
        self._drive_count_lbl = tk.Label(hdr, text="", bg=T.PANEL,
                                         fg=T.HIGHLIGHT, font=T.FONT_BOLD)
        self._drive_count_lbl.pack(side="right", padx=12)

        # Button row
        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Analyze All Drives",
                     command=self._start_analyze).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Optimize Selected",
                     command=self._optimize_selected).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Check Health",
                     command=self._check_health_selected).pack(side="left", padx=(0, 8))

        # Progress bar
        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        # Drive treeview
        tv_card = Card(self)
        tv_card.pack(fill="both", expand=True, padx=16, pady=(4, 4))
        SectionLabel(tv_card, "Drives").pack(anchor="w", padx=8, pady=(6, 2))

        cols = ("Label", "FS", "Total GB", "Free GB", "Free %", "Type", "Status")
        self._tv = ttk.Treeview(tv_card, columns=cols, show="tree headings", height=8)
        apply_treeview_style(self._tv)
        self._tv.heading("#0",       text="Letter",   anchor="w")
        self._tv.heading("Label",    text="Label",    anchor="w")
        self._tv.heading("FS",       text="FS",       anchor="w")
        self._tv.heading("Total GB", text="Total GB", anchor="w")
        self._tv.heading("Free GB",  text="Free GB",  anchor="w")
        self._tv.heading("Free %",   text="Free %",   anchor="w")
        self._tv.heading("Type",     text="Type",     anchor="w")
        self._tv.heading("Status",   text="Status",   anchor="w")

        self._tv.column("#0",       width=60,  minwidth=50)
        self._tv.column("Label",    width=100, minwidth=60)
        self._tv.column("FS",       width=60,  minwidth=40)
        self._tv.column("Total GB", width=75,  minwidth=55)
        self._tv.column("Free GB",  width=75,  minwidth=55)
        self._tv.column("Free %",   width=60,  minwidth=45)
        self._tv.column("Type",     width=60,  minwidth=45)
        self._tv.column("Status",   width=130, minwidth=80)

        sb = ttk.Scrollbar(tv_card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

        # Results / output area
        res_card = Card(self)
        res_card.pack(fill="x", padx=16, pady=(0, 16))
        hdr2 = tk.Frame(res_card, bg=T.PANEL)
        hdr2.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(hdr2, "Operation Output").pack(side="left")
        ActionButton(hdr2, "Clear", command=self._clear_output).pack(side="right")
        self._output = tk.Text(res_card, height=7, bg=T.ACCENT, fg=T.FG,
                               font=T.FONT_SMALL, state="disabled",
                               relief="flat", wrap="none")
        self._output.pack(fill="x", padx=8, pady=(0, 8))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _append_output(self, text: str):
        """Thread-safe append to the output text widget."""
        try:
            self._output.config(state="normal")
            self._output.insert("end", text + "\n")
            self._output.see("end")
            self._output.config(state="disabled")
        except tk.TclError:
            pass

    def _clear_output(self):
        try:
            self._output.config(state="normal")
            self._output.delete("1.0", "end")
            self._output.config(state="disabled")
        except tk.TclError:
            pass

    def _selected_drive(self) -> dict | None:
        sel = self._tv.selection()
        if not sel:
            return None
        iid = sel[0]
        letter = self._tv.item(iid, "text").strip(":")
        for d in self._drives:
            if d["letter"] == letter:
                return d
        return None

    # ── analyze ───────────────────────────────────────────────────────────────

    def _start_analyze(self):
        self._progress.indeterminate(True)
        self._status.set("Scanning drives…")
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._drives = []
        threading.Thread(target=self._do_analyze, daemon=True).start()

    def _do_analyze(self):
        try:
            drives = disk_optimizer.get_drives()
            self.after(0, self._show_drives, drives)
        except Exception as exc:
            self.after(0, self._status.set, f"Error scanning drives: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _show_drives(self, drives: list[dict]):
        self._progress.indeterminate(False)
        self._drives = drives

        for item in self._tv.get_children():
            self._tv.delete(item)

        for d in drives:
            letter   = d.get("letter", "?")
            label    = d.get("label", "")
            fs       = d.get("fs", "")
            total_gb = d.get("total_gb", 0.0)
            free_gb  = d.get("free_gb", 0.0)
            free_pct = d.get("free_pct", 0.0)
            is_ssd   = d.get("is_ssd", False)
            rec      = d.get("recommendation", "ok")

            drive_type = "SSD" if is_ssd else "HDD"
            if rec == "defrag":
                status = "Fragmented — defrag recommended"
                tag = "warn"
            elif rec == "trim":
                status = "SSD — TRIM available"
                tag = "info"
            else:
                status = "OK"
                tag = "ok"

            self._tv.insert("", "end", text=f"{letter}:",
                            values=(label, fs, f"{total_gb:.1f}", f"{free_gb:.1f}",
                                    f"{free_pct:.1f}%", drive_type, status),
                            tags=(tag,))

        self._tv.tag_configure("warn", foreground=T.WARNING)
        self._tv.tag_configure("info", foreground=T.HIGHLIGHT)
        self._tv.tag_configure("ok",   foreground=T.SUCCESS)

        count = len(drives)
        self._drive_count_lbl.config(text=f"{count} drive{'s' if count != 1 else ''} found")
        self._status.set(f"Found {count} drive(s). Select one and use the buttons above.")

    # ── optimize (defrag / TRIM) ───────────────────────────────────────────────

    def _optimize_selected(self):
        drive = self._selected_drive()
        if not drive:
            messagebox.showinfo("No selection", "Select a drive from the list first.")
            return
        letter = drive["letter"]
        is_ssd = drive.get("is_ssd", False)
        op = "TRIM" if is_ssd else "Defrag"
        if not messagebox.askyesno(
            f"Confirm {op}",
            f"Run {op} on drive {letter}:?\n\n"
            f"{'TRIM on SSD — fast, non-destructive.' if is_ssd else 'Defragmentation may take several minutes on large drives.'}",
        ):
            return
        self._progress.indeterminate(True)
        self._status.set(f"Running {op} on {letter}:…")
        self._append_output(f"--- Starting {op} on {letter}: ---")
        threading.Thread(target=self._do_optimize, args=(drive,), daemon=True).start()

    def _do_optimize(self, drive: dict):
        letter = drive["letter"]
        is_ssd = drive.get("is_ssd", False)

        def cb(line: str):
            self.after(0, self._append_output, line)
            self.after(0, self._status.set, line[:80])

        try:
            if is_ssd:
                result = disk_optimizer.trim_drive(letter)
                self.after(0, self._optimize_done, letter, "TRIM", result)
            else:
                result = disk_optimizer.defrag_drive(letter, progress_cb=cb)
                self.after(0, self._optimize_done, letter, "Defrag", result)
        except Exception as exc:
            self.after(0, self._append_output, f"Error: {exc}")
            self.after(0, self._progress.indeterminate, False)
            self.after(0, self._status.set, f"Operation failed: {exc}")

    def _optimize_done(self, letter: str, op: str, result: dict):
        self._progress.indeterminate(False)
        success = result.get("success", False)
        output  = result.get("output", "")
        if output:
            self._append_output(output[-1000:])  # cap long outputs
        if success:
            self._status.set(f"{op} on {letter}: completed successfully.")
            self._append_output(f"--- {op} on {letter}: DONE ---")
        else:
            self._status.set(f"{op} on {letter}: failed or requires admin rights.")
            self._append_output(f"--- {op} on {letter}: FAILED (may need admin rights) ---")

    # ── health check ──────────────────────────────────────────────────────────

    def _check_health_selected(self):
        drive = self._selected_drive()
        if not drive:
            messagebox.showinfo("No selection", "Select a drive from the list first.")
            return
        letter = drive["letter"]
        self._progress.indeterminate(True)
        self._status.set(f"Checking health of drive {letter}:… (this may take a few minutes)")
        self._append_output(f"--- Health check on {letter}: ---")
        threading.Thread(target=self._do_health, args=(letter,), daemon=True).start()

    def _do_health(self, letter: str):
        try:
            result = disk_optimizer.get_drive_health(letter)
            self.after(0, self._health_done, letter, result)
        except Exception as exc:
            self.after(0, self._append_output, f"Error: {exc}")
            self.after(0, self._progress.indeterminate, False)
            self.after(0, self._status.set, f"Health check failed: {exc}")

    def _health_done(self, letter: str, result: dict):
        self._progress.indeterminate(False)
        status    = result.get("status", "unknown")
        has_error = result.get("errors_found", False)
        output    = result.get("output", "")

        if output:
            self._append_output(output[-800:])

        if status == "healthy":
            msg = f"Drive {letter}: is healthy — no errors found."
            self._status.set(msg)
            self._append_output(f"--- Health: OK ---")
            messagebox.showinfo("Drive Health", msg)
        elif has_error or status == "errors_detected":
            msg = f"Drive {letter}: errors detected! Consider running chkdsk /f."
            self._status.set(msg)
            self._append_output(f"--- Health: ERRORS DETECTED ---")
            messagebox.showwarning("Drive Health", msg)
        else:
            self._status.set(f"Drive {letter}: scan complete (status: {status}).")
            self._append_output(f"--- Health: {status} ---")
