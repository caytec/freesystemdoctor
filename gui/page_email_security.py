"""Email Security page — check email client configuration and account security."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import email_security as es


class EmailSecurityPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Email Security", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Check email client configuration and account security",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_clients_card(body)
        self._build_accounts_card(body)
        self._build_issues_card(body)
        self._build_recommendations_card(body)

    def _build_clients_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Email Clients Detected").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))

        self._clients_label = tk.Label(row, text="Scanning...", bg=T.PANEL, fg=T.FG,
                                       font=T.FONT_BODY)
        self._clients_label.pack(side="left", padx=10, fill="x", expand=True)

        ActionButton(row, text="Check Security",
                     command=self._on_check).pack(side="left", padx=(10, 0))

    def _build_accounts_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Email Accounts").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._acct_tree = ttk.Treeview(tree_frame, columns=("client", "encryption"), height=6)
        self._acct_tree.column("#0", width=250)
        self._acct_tree.column("client", width=120)
        self._acct_tree.column("encryption", width=100)
        self._acct_tree.heading("#0", text="Email Address")
        self._acct_tree.heading("client", text="Client")
        self._acct_tree.heading("encryption", text="Encryption")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._acct_tree.yview)
        self._acct_tree.configure(yscrollcommand=sb.set)
        self._acct_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

    def _build_issues_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Security Issues").pack(anchor="w", padx=10, pady=8)

        self._issues_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                    height=6, bd=0, padx=8, pady=6,
                                    state="disabled", wrap="word")
        self._issues_text.pack(fill="both", expand=True, padx=10, pady=(0, 8))

    def _build_recommendations_card(self, parent):
        card = Card(parent)
        card.pack(fill="x")

        SectionLabel(card, "Recommendations").pack(anchor="w", padx=10, pady=8)

        self._rec_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                 height=4, bd=0, padx=8, pady=6,
                                 state="disabled", wrap="word")
        self._rec_text.pack(fill="x", padx=10, pady=(0, 8))

    def _on_check(self):
        def check():
            clients = es.get_email_clients()
            accounts, issues = es.check_email_security()
            recommendations = es.get_email_recommendations()
            self.after(0, self._display_data, clients, accounts, issues, recommendations)

        threading.Thread(target=check, daemon=True).start()

    def _display_data(self, clients, accounts, issues, recommendations):
        # Update clients
        if clients:
            self._clients_label.config(text=", ".join(clients))
        else:
            self._clients_label.config(text="No email clients found")

        # Update accounts
        self._acct_tree.delete(*self._acct_tree.get_children())
        for account in accounts:
            self._acct_tree.insert("", "end", text=account.email,
                                  values=(account.client, account.encryption or "Unknown"))

        # Update issues
        self._issues_text.config(state="normal")
        self._issues_text.delete("1.0", "end")
        if issues:
            for issue in issues:
                self._issues_text.insert("end", f"• {issue}\n")
        else:
            self._issues_text.insert("end", "No security issues detected!")
        self._issues_text.config(state="disabled")

        # Update recommendations
        self._rec_text.config(state="normal")
        self._rec_text.delete("1.0", "end")
        if recommendations:
            self._rec_text.insert("end", "\n".join(f"• {r}" for r in recommendations))
        else:
            self._rec_text.insert("end", "Email security configuration is optimal!")
        self._rec_text.config(state="disabled")

    def on_activate(self):
        self._on_check()
