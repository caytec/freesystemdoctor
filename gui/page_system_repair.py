"""System Repair page — detect and automatically fix common Windows issues."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import system_repair as sr


class SystemRepairPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="System Repair", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Detect and fix common Windows issues",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_recommendations_card(body)
        self._build_issues_card(body)
        self._build_actions_card(body)

    def _build_recommendations_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Repair Recommendations").pack(anchor="w", padx=10, pady=8)

        self._rec_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                 height=3, bd=0, padx=8, pady=6,
                                 state="disabled", wrap="word")
        self._rec_text.pack(fill="x", padx=10, pady=(0, 8))

    def _build_issues_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Detected Issues").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("category", "severity"), height=10)
        self._tree.column("#0", width=300)
        self._tree.column("category", width=120)
        self._tree.column("severity", width=100)
        self._tree.heading("#0", text="Issue")
        self._tree.heading("category", text="Category")
        self._tree.heading("severity", text="Severity")

        self._tree.tag_configure("critical", foreground=T.DANGER)
        self._tree.tag_configure("high", foreground=T.WARNING)
        self._tree.tag_configure("medium", foreground=T.WARNING)
        self._tree.tag_configure("low", foreground=T.SUCCESS)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

    def _build_actions_card(self, parent):
        card = Card(parent)
        card.pack(fill="x")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=8)

        ActionButton(btn_row, text="Scan for Issues",
                     command=self._on_scan).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Fix Selected Issues",
                     command=self._on_fix_selected).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Fix All Issues",
                     command=self._on_fix_all).pack(side="left")

        self._status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._status.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_scan(self):
        def scan():
            issues = sr.scan_for_issues()
            recommendations = sr.get_repair_recommendations()
            self.after(0, self._display_data, issues, recommendations)

        threading.Thread(target=scan, daemon=True).start()

    def _on_fix_selected(self):
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select issues to fix")
            return

        if not messagebox.askyesno("Fix Issues",
                f"Attempt to fix {len(selection)} issue(s)?\n\nA system restore point will be created first."):
            return

        def fix():
            issues = sr.scan_for_issues()
            selected_issues = []

            for iid in selection:
                for issue in issues:
                    if issue.name == iid:
                        selected_issues.append(issue)
                        break

            fixed, failed = sr.fix_multiple_issues(selected_issues)
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Fixed {fixed} issue(s). {failed} could not be fixed automatically."))
            self._on_scan()

        threading.Thread(target=fix, daemon=True).start()

    def _on_fix_all(self):
        if not messagebox.askyesno("Fix All Issues",
                "Attempt to fix all detected issues?\n\nA system restore point will be created first."):
            return

        def fix():
            issues = sr.scan_for_issues()
            fixed, failed = sr.fix_multiple_issues(issues)
            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Fixed {fixed} issue(s). {failed} could not be fixed automatically."))
            self._on_scan()

        threading.Thread(target=fix, daemon=True).start()

    def _display_data(self, issues, recommendations):
        # Update recommendations
        self._rec_text.config(state="normal")
        self._rec_text.delete("1.0", "end")
        if recommendations:
            self._rec_text.insert("end", "\n".join(f"• {r}" for r in recommendations))
        else:
            self._rec_text.insert("end", "No issues detected — your system is healthy!")
        self._rec_text.config(state="disabled")

        # Update issues tree
        self._tree.delete(*self._tree.get_children())
        for issue in issues:
            tag = issue.severity.lower()
            fixable_marker = " [FIXABLE]" if issue.fixable else ""
            self._tree.insert("", "end", iid=issue.name,
                             text=f"{issue.name}{fixable_marker}",
                             values=(issue.category, issue.severity),
                             tags=(tag,))

        # Update status
        critical = sum(1 for i in issues if i.severity == "CRITICAL")
        high = sum(1 for i in issues if i.severity == "HIGH")
        fixable = sum(1 for i in issues if i.fixable)

        self._status.config(
            text=f"Found {len(issues)} issue(s) — {critical} critical, {high} high, {fixable} fixable"
        )

    def on_activate(self):
        self._on_scan()
