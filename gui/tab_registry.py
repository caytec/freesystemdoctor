"""Registry Cleaner tab."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import registry_cleaner


class RegistryTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._issues: list[registry_cleaner.RegIssue] = []
        self._build_ui()

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Registry Cleaner").pack(side="left", padx=8, pady=8)

        warn = tk.Label(hdr,
            text="Always backup registry before cleaning (File > Export in regedit.exe)",
            bg=T.PANEL, fg=T.WARNING, font=T.FONT_SMALL)
        warn.pack(side="right", padx=10)

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Scan Registry", command=self._start_scan).pack(side="left", padx=(0, 8))
        self._fix_btn = ActionButton(btn_row, "Fix Selected (Safe only)",
                                     command=self._fix_selected, danger=True)
        self._fix_btn.pack(side="left")
        self._fix_btn.config(state="disabled")

        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        self._summary_lbl = tk.Label(self, text="", bg=T.BG, fg=T.HIGHLIGHT, font=T.FONT_BOLD)
        self._summary_lbl.pack(anchor="w", padx=16)

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Hive", "Category", "Reason", "Safe")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",        text="Key / Value", anchor="w")
        self._tv.heading("Hive",      text="Hive",        anchor="w")
        self._tv.heading("Category",  text="Category",    anchor="w")
        self._tv.heading("Reason",    text="Reason",      anchor="w")
        self._tv.heading("Safe",      text="Safe?",       anchor="w")
        self._tv.column("#0",       width=280)
        self._tv.column("Hive",     width=55)
        self._tv.column("Category", width=160)
        self._tv.column("Reason",   width=220)
        self._tv.column("Safe",     width=55)
        self._tv.tag_configure("safe",   foreground=T.SUCCESS)
        self._tv.tag_configure("unsafe", foreground=T.WARNING)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _start_scan(self):
        self._progress.indeterminate(True)
        self._fix_btn.config(state="disabled")
        self._summary_lbl.config(text="")
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._status.set("Scanning registry...")
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        def cb(msg):
            self.after(0, self._status.set, msg)

        issues = registry_cleaner.scan_registry(progress_cb=cb)
        self.after(0, self._show_results, issues)

    def _show_results(self, issues):
        self._progress.indeterminate(False)
        self._issues = issues
        for item in self._tv.get_children():
            self._tv.delete(item)

        safe_count = sum(1 for i in issues if i.safe_to_remove)
        self._summary_lbl.config(
            text=f"{len(issues)} issue(s) found  ({safe_count} safe to remove)"
        )

        for idx, issue in enumerate(issues):
            tag = "safe" if issue.safe_to_remove else "unsafe"
            label = f"{issue.key_path}  [{issue.value_name}]"
            self._tv.insert("", "end", iid=str(idx),
                            text=label,
                            values=(issue.hive, issue.category, issue.reason,
                                    "Yes" if issue.safe_to_remove else "No"),
                            tags=(tag,))

        self._status.set(f"Registry scan complete — {len(issues)} issue(s) found.")
        if any(i.safe_to_remove for i in issues):
            self._fix_btn.config(state="normal")

    def _fix_selected(self):
        sel = self._tv.selection()
        if not sel:
            messagebox.showinfo("Select items", "Select registry issues to fix.")
            return

        to_fix = [self._issues[int(iid)] for iid in sel if self._issues[int(iid)].safe_to_remove]
        unsafe = [self._issues[int(iid)] for iid in sel if not self._issues[int(iid)].safe_to_remove]

        if unsafe:
            messagebox.showwarning(
                "Unsafe items skipped",
                f"{len(unsafe)} item(s) are marked as unsafe and will be skipped."
            )

        if not to_fix:
            messagebox.showinfo("Nothing to fix", "No safe items selected.")
            return

        if not messagebox.askyesno(
            "Fix Registry",
            f"Remove {len(to_fix)} registry value(s)?\n\n"
            "Tip: export your registry in regedit.exe first as a backup."
        ):
            return

        fixed = 0
        for issue in to_fix:
            if registry_cleaner.remove_issue(issue):
                fixed += 1

        self._status.set(f"Fixed {fixed}/{len(to_fix)} registry issues.")
        messagebox.showinfo("Done", f"Fixed {fixed} registry issue(s).")
        self._start_scan()
