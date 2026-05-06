"""Network Security page — scan devices, check ports, identify threats."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import network_security as ns
from engine import network_diagnostics as nd


class NetworkSecurityPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._scanning = False
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Network Security", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Scan network devices and identify security risks",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Notebook: basic / diagnostics tabs
        nb = ttk.Notebook(body)
        nb.pack(fill="both", expand=True)

        # Tab 1: Basic Security
        tab1 = tk.Frame(nb, bg=T.BG)
        nb.add(tab1, text="  Security Status  ")

        self._build_status_card(tab1)
        self._build_ports_card(tab1)
        self._build_devices_card(tab1)

        # Tab 2: Advanced Diagnostics
        tab2 = tk.Frame(nb, bg=T.BG)
        nb.add(tab2, text="  Diagnostics  ")

        self._build_diagnostics_card(tab2)

    def _build_status_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Network Security Status").pack(anchor="w", padx=10, pady=8)

        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=4)

        tk.Label(row1, text="Local IP:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left")
        self._local_ip = tk.Label(row1, text="–", bg=T.PANEL, fg=T.FG,
                                 font=T.FONT_BODY)
        self._local_ip.pack(side="left", padx=10)

        row2 = tk.Frame(card, bg=T.PANEL)
        row2.pack(fill="x", padx=10, pady=4)

        tk.Label(row2, text="Risk Level:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left")
        self._risk_level = tk.Label(row2, text="–", bg=T.PANEL, fg=T.FG,
                                   font=T.FONT_BODY)
        self._risk_level.pack(side="left", padx=10)

        row3 = tk.Frame(card, bg=T.PANEL)
        row3.pack(fill="x", padx=10, pady=(4, 8))

        tk.Label(row3, text="Firewall:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY).pack(side="left")
        self._firewall = tk.Label(row3, text="–", bg=T.PANEL, fg=T.FG,
                                 font=T.FONT_BODY)
        self._firewall.pack(side="left", padx=10)

        ActionButton(card, text="Scan Network & Ports",
                     command=self._on_scan).pack(anchor="w", padx=10, pady=(0, 8))

    def _build_ports_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Open Ports").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._ports_tree = ttk.Treeview(tree_frame, columns=("service", "risk"), height=6)
        self._ports_tree.column("#0", width=80)
        self._ports_tree.column("service", width=150)
        self._ports_tree.column("risk", width=100)
        self._ports_tree.heading("#0", text="Port")
        self._ports_tree.heading("service", text="Service")
        self._ports_tree.heading("risk", text="Risk Level")

        self._ports_tree.tag_configure("critical", foreground=T.DANGER)
        self._ports_tree.tag_configure("high", foreground=T.WARNING)
        self._ports_tree.tag_configure("medium", foreground="#FF9800")
        self._ports_tree.tag_configure("low", foreground=T.FG2)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._ports_tree.yview)
        self._ports_tree.configure(yscrollcommand=sb.set)
        self._ports_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        self._ports_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._ports_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_devices_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Network Devices").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._devices_tree = ttk.Treeview(tree_frame, columns=("hostname", "status"), height=8)
        self._devices_tree.column("#0", width=100)
        self._devices_tree.column("hostname", width=200)
        self._devices_tree.column("status", width=80)
        self._devices_tree.heading("#0", text="IP Address")
        self._devices_tree.heading("hostname", text="Hostname")
        self._devices_tree.heading("status", text="Status")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._devices_tree.yview)
        self._devices_tree.configure(yscrollcommand=sb.set)
        self._devices_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        self._devices_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._devices_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_diagnostics_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, padx=16, pady=12)

        SectionLabel(card, "Advanced Network Diagnostics").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._diag_tree = ttk.Treeview(tree_frame, columns=("status", "value"), height=12)
        self._diag_tree.column("#0", width=250)
        self._diag_tree.column("status", width=100)
        self._diag_tree.column("value", width=150)
        self._diag_tree.heading("#0", text="Test")
        self._diag_tree.heading("status", text="Status")
        self._diag_tree.heading("value", text="Result")

        self._diag_tree.tag_configure("pass", foreground=T.SUCCESS)
        self._diag_tree.tag_configure("fail", foreground=T.DANGER)
        self._diag_tree.tag_configure("slow", foreground=T.WARNING)
        self._diag_tree.tag_configure("unknown", foreground=T.FG2)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._diag_tree.yview)
        self._diag_tree.configure(yscrollcommand=sb.set)
        self._diag_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_row, text="Run Diagnostics",
                     command=self._on_run_diagnostics).pack(side="left")

        self._diag_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._diag_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_run_diagnostics(self):
        def run():
            basic_tests, port_tests = nd.run_all_diagnostics()
            recommendations = nd.get_network_recommendations()
            self.after(0, self._display_diagnostics, basic_tests, port_tests, recommendations)

        threading.Thread(target=run, daemon=True).start()

    def _display_diagnostics(self, basic_tests, port_tests, recommendations):
        self._diag_tree.delete(*self._diag_tree.get_children())

        # Add basic tests
        for test in basic_tests:
            tag = test.status.lower()
            value_text = f"{test.value} {test.unit}".strip()
            self._diag_tree.insert("", "end", text=test.name,
                                  values=(test.status, value_text),
                                  tags=(tag,))

        # Add port tests
        if port_tests:
            port_iid = self._diag_tree.insert("", "end", text="Open Ports", values=("", ""), tags=("unknown",))
            for test in port_tests:
                self._diag_tree.insert(port_iid, "end", text=test.name,
                                      values=(test.status, test.value),
                                      tags=("fail",))

        # Update status
        passed = sum(1 for t in basic_tests if t.status == "PASS")
        failed = sum(1 for t in basic_tests if t.status == "FAIL")
        self._diag_status.config(
            text=f"Passed: {passed}/{len(basic_tests)} | {' | '.join(recommendations[:2])}"
        )

    def _on_scan(self):
        if self._scanning:
            return

        self._scanning = True

        def scan():
            self.after(0, lambda: self._local_ip.config(text=ns.get_local_ip()))

            status = ns.get_network_security_status()
            fw = ns.get_firewall_status()

            self.after(0, lambda: self._display_security(status, fw))

            devices = ns.scan_network_devices(timeout=3)
            self.after(0, lambda: self._display_devices(devices))

            self._scanning = False

        threading.Thread(target=scan, daemon=True).start()

    def _display_security(self, status, fw):
        risk = status["risk_level"].upper()
        risk_color = T.DANGER if risk == "CRITICAL" else T.WARNING if risk == "HIGH" else T.SUCCESS

        self._risk_level.config(text=risk, fg=risk_color)
        self._firewall.config(text="Enabled" if fw["firewall_enabled"] else "Disabled",
                             fg=T.SUCCESS if fw["firewall_enabled"] else T.WARNING)

        self._ports_tree.delete(*self._ports_tree.get_children())
        for port in status["open_ports"]:
            tag = "low"
            for vuln in status["vulnerable_ports"]:
                if vuln["port"] == port["port"]:
                    tag = vuln["risk"].lower() if vuln["risk"] else "low"
                    break

            self._ports_tree.insert("", "end", text=str(port["port"]),
                                   values=(port["service"], tag.upper()),
                                   tags=(tag,))

        self._ports_status.config(text=f"Open ports: {len(status['open_ports'])} | Vulnerable: {len(status['vulnerable_ports'])}")

    def _display_devices(self, devices):
        self._devices_tree.delete(*self._devices_tree.get_children())
        for device in devices:
            self._devices_tree.insert("", "end", text=device["ip"],
                                     values=(device["hostname"], device["status"]))

        self._devices_status.config(text=f"Found {len(devices)} active device(s)")

    def on_activate(self):
        pass
