"""Network Optimizer tab."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import network_optimizer as no


class NetworkTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._adapters = []
        self._build_ui()
        self.after(300, self._refresh)

    def _build_ui(self):
        # Top row: quick actions
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(12, 4))

        quick = Card(top)
        quick.pack(side="left", fill="y", padx=(0, 8))
        SectionLabel(quick, "Quick Actions").pack(anchor="w", padx=8, pady=(6, 2))
        ActionButton(quick, "Flush DNS Cache", command=self._flush_dns).pack(anchor="w", padx=8, pady=3)
        ActionButton(quick, "Flush ARP Cache", command=self._flush_arp).pack(anchor="w", padx=8, pady=3)
        ActionButton(quick, "Apply TCP Tweaks", command=self._apply_tcp).pack(anchor="w", padx=8, pady=3)
        ActionButton(quick, "Reset TCP/IP Stack", command=self._reset_tcp, danger=True).pack(anchor="w", padx=8, pady=3)
        ActionButton(quick, "Ping Google (8.8.8.8)", command=self._ping_google).pack(anchor="w", padx=8, pady=(3, 8))

        # DNS server changer
        dns_card = Card(top)
        dns_card.pack(side="left", fill="both", expand=True)
        SectionLabel(dns_card, "DNS Server").pack(anchor="w", padx=8, pady=(6, 2))
        arow = tk.Frame(dns_card, bg=T.PANEL)
        arow.pack(fill="x", padx=8, pady=2)
        tk.Label(arow, text="Interface:", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._adapter_var = tk.StringVar()
        self._adapter_cb = ttk.Combobox(arow, textvariable=self._adapter_var,
                                        state="readonly", width=22)
        self._adapter_cb.pack(side="left", padx=6)

        self._dns_var = tk.StringVar(value=list(no.DNS_PRESETS.keys())[0])
        for label in no.DNS_PRESETS:
            tk.Radiobutton(dns_card, text=label, variable=self._dns_var, value=label,
                           bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                           activebackground=T.PANEL, font=T.FONT_SMALL).pack(anchor="w", padx=14)
        ActionButton(dns_card, "Apply DNS", command=self._apply_dns).pack(anchor="w", padx=8, pady=(4, 8))

        # Middle: TCP settings display
        mid = Card(self)
        mid.pack(fill="x", padx=16, pady=4)
        hdr = tk.Frame(mid, bg=T.PANEL)
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(hdr, "Current TCP Global Settings").pack(side="left")
        ActionButton(hdr, "Refresh", command=self._show_tcp_settings).pack(side="right")
        self._tcp_text = tk.Text(mid, height=6, bg=T.ACCENT, fg=T.FG, font=T.FONT_SMALL,
                                 state="disabled", relief="flat", wrap="none")
        self._tcp_text.pack(fill="x", padx=8, pady=(0, 8))

        # Bottom: adapters + ping results
        bot = tk.Frame(self, bg=T.BG)
        bot.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        adapt_card = Card(bot)
        adapt_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(adapt_card, "Network Adapters").pack(anchor="w", padx=8, pady=(6, 2))
        cols = ("Status", "Speed", "MAC")
        self._adapt_tv = ttk.Treeview(adapt_card, columns=cols, show="tree headings", height=8)
        apply_treeview_style(self._adapt_tv)
        self._adapt_tv.heading("#0",     text="Name",     anchor="w")
        self._adapt_tv.heading("Status", text="Status",   anchor="w")
        self._adapt_tv.heading("Speed",  text="Speed",    anchor="w")
        self._adapt_tv.heading("MAC",    text="MAC Addr", anchor="w")
        self._adapt_tv.column("#0",     width=150)
        self._adapt_tv.column("Status", width=70)
        self._adapt_tv.column("Speed",  width=90)
        self._adapt_tv.column("MAC",    width=120)
        self._adapt_tv.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        ping_card = Card(bot)
        ping_card.pack(side="left", fill="both", expand=True)
        SectionLabel(ping_card, "Ping / Latency").pack(anchor="w", padx=8, pady=(6, 2))
        row = tk.Frame(ping_card, bg=T.PANEL)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text="Host:", bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._ping_host = tk.Entry(row, width=18, bg=T.ACCENT, fg=T.FG,
                                   insertbackground=T.FG, font=T.FONT_BODY)
        self._ping_host.insert(0, "8.8.8.8")
        self._ping_host.pack(side="left", padx=4)
        ActionButton(row, "Ping", command=self._do_ping).pack(side="left", padx=4)
        self._ping_out = tk.Text(ping_card, height=8, bg=T.ACCENT, fg=T.FG,
                                  font=T.FONT_SMALL, state="disabled", relief="flat", wrap="none")
        self._ping_out.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    # ── actions ───────────────────────────────────────────────────────────────

    def _refresh(self):
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        adapters = no.get_adapters()
        self.after(0, self._apply_refresh, adapters)
        self.after(0, self._show_tcp_settings)

    def _apply_refresh(self, adapters):
        self._adapters = adapters
        names = [a.get("Name", "") for a in adapters if a.get("Status") == "Up"]
        self._adapter_cb["values"] = names
        if names:
            self._adapter_var.set(names[0])

        for item in self._adapt_tv.get_children():
            self._adapt_tv.delete(item)
        for a in adapters:
            status = a.get("Status", "")
            color_tag = "up" if status == "Up" else "down"
            self._adapt_tv.insert("", "end", text=a.get("Name", ""),
                                  values=(status, a.get("LinkSpeed", ""), a.get("MacAddress", "")),
                                  tags=(color_tag,))
        self._adapt_tv.tag_configure("up",   foreground=T.SUCCESS)
        self._adapt_tv.tag_configure("down", foreground=T.DANGER)

    def _show_tcp_settings(self):
        threading.Thread(target=lambda: self.after(
            0, self._set_tcp_text, no.get_tcp_global()), daemon=True).start()

    def _set_tcp_text(self, text):
        self._tcp_text.config(state="normal")
        self._tcp_text.delete("1.0", "end")
        self._tcp_text.insert("end", text)
        self._tcp_text.config(state="disabled")

    def _flush_dns(self):
        ok = no.flush_dns()
        if ok:
            self._status.set("DNS cache flushed successfully.")
            messagebox.showinfo("DNS Flushed", "DNS resolver cache has been cleared.")
        else:
            self._status.set("DNS flush failed.")

    def _flush_arp(self):
        ok = no.flush_arp()
        self._status.set("ARP cache flushed." if ok else "ARP flush failed.")

    def _apply_tcp(self):
        done = no.apply_tcp_tweaks()
        self._status.set(f"TCP tweaks applied: {len(done)} settings changed.")
        messagebox.showinfo("TCP Tweaks Applied",
                            "Changes applied:\n" + "\n".join(done[:10]) +
                            "\n\nA restart may be needed for all changes to take effect.")
        self._show_tcp_settings()

    def _reset_tcp(self):
        if not messagebox.askyesno("Reset TCP/IP",
                                   "Reset the TCP/IP stack to defaults?\n"
                                   "This requires a restart and may briefly interrupt connectivity."):
            return
        done = no.reset_tcp_tweaks()
        self._status.set("TCP/IP reset — restart recommended.")
        messagebox.showinfo("TCP Reset", "\n".join(done))

    def _apply_dns(self):
        iface = self._adapter_var.get()
        if not iface:
            messagebox.showwarning("No interface", "Select a network interface first.")
            return
        label = self._dns_var.get()
        primary, secondary = no.DNS_PRESETS.get(label, ("dhcp", ""))
        ok = no.set_dns(iface, primary, secondary)
        if ok:
            self._status.set(f"DNS set to {label} on {iface}.")
            messagebox.showinfo("DNS Changed", f"DNS on '{iface}' set to:\n{label}")
        else:
            messagebox.showerror("Error", "Could not change DNS.\n(May require administrator rights)")

    def _ping_google(self):
        self._ping_host.delete(0, "end")
        self._ping_host.insert(0, "8.8.8.8")
        self._do_ping()

    def _do_ping(self):
        host = self._ping_host.get().strip()
        self._status.set(f"Pinging {host}...")
        threading.Thread(target=self._run_ping, args=(host,), daemon=True).start()

    def _run_ping(self, host):
        result = no.ping(host, count=4)
        self.after(0, self._show_ping, result)

    def _show_ping(self, result):
        self._ping_out.config(state="normal")
        self._ping_out.delete("1.0", "end")
        self._ping_out.insert("end", result.get("output", ""))
        self._ping_out.config(state="disabled")
        avg = result.get("avg_ms")
        if avg is not None:
            self._status.set(f"Ping {result['host']}: avg {avg} ms, {result.get('loss_pct', 0)}% loss")
        else:
            self._status.set(f"Ping {result['host']}: unreachable")
