"""Internet Booster tab — DNS benchmark, TCP optimisation, adapter info."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import internet_booster


class InternetBoosterTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._benchmark_results: list[dict] = []
        self._adapters: list[dict] = []
        self._build_ui()
        self.after(400, self._refresh_all)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top row: current DNS + adapters ───────────────────────────────────
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(12, 4))

        # Current DNS card
        dns_card = Card(top)
        dns_card.pack(side="left", fill="y", padx=(0, 8))
        SectionLabel(dns_card, "Current DNS").pack(anchor="w", padx=8, pady=(6, 2))
        self._dns_info = tk.Label(dns_card, text="Loading…", bg=T.PANEL,
                                  fg=T.FG2, font=T.FONT_SMALL,
                                  justify="left", anchor="nw", wraplength=220)
        self._dns_info.pack(padx=10, pady=(0, 4), anchor="w")
        ActionButton(dns_card, "Flush DNS Cache",
                     command=self._flush_dns).pack(padx=8, pady=(0, 8), anchor="w")

        # Adapters card
        adapt_card = Card(top)
        adapt_card.pack(side="left", fill="both", expand=True)
        SectionLabel(adapt_card, "Network Adapters").pack(anchor="w", padx=8, pady=(6, 2))
        cols_a = ("IP", "Speed (Mbps)", "Status")
        self._adapt_tv = ttk.Treeview(adapt_card, columns=cols_a,
                                      show="tree headings", height=5)
        apply_treeview_style(self._adapt_tv)
        self._adapt_tv.heading("#0",          text="Name",        anchor="w")
        self._adapt_tv.heading("IP",          text="IP",          anchor="w")
        self._adapt_tv.heading("Speed (Mbps)",text="Speed (Mbps)",anchor="w")
        self._adapt_tv.heading("Status",      text="Status",      anchor="w")
        self._adapt_tv.column("#0",          width=150)
        self._adapt_tv.column("IP",          width=110)
        self._adapt_tv.column("Speed (Mbps)",width=95)
        self._adapt_tv.column("Status",      width=70)
        self._adapt_tv.pack(fill="both", expand=True, padx=(8, 8), pady=(0, 8))

        # ── DNS Benchmark section ──────────────────────────────────────────────
        bench_card = Card(self)
        bench_card.pack(fill="both", expand=True, padx=16, pady=4)

        bench_hdr = tk.Frame(bench_card, bg=T.PANEL)
        bench_hdr.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(bench_hdr, "DNS Benchmark").pack(side="left")
        self._bench_btn = ActionButton(bench_hdr, "Run DNS Benchmark",
                                       command=self._start_benchmark)
        self._bench_btn.pack(side="right")

        self._bench_progress = ProgressBar(bench_card, bg=T.PANEL)
        self._bench_progress.pack(fill="x", padx=8, pady=(2, 4))

        cols_b = ("Name", "Avg ms", "Min ms", "Max ms", "Success %")
        self._bench_tv = ttk.Treeview(bench_card, columns=cols_b,
                                      show="tree headings", height=7)
        apply_treeview_style(self._bench_tv)
        self._bench_tv.heading("#0",        text="Server IP", anchor="w")
        self._bench_tv.heading("Name",      text="Name",      anchor="w")
        self._bench_tv.heading("Avg ms",    text="Avg ms",    anchor="w")
        self._bench_tv.heading("Min ms",    text="Min ms",    anchor="w")
        self._bench_tv.heading("Max ms",    text="Max ms",    anchor="w")
        self._bench_tv.heading("Success %", text="Success %", anchor="w")
        self._bench_tv.column("#0",        width=120)
        self._bench_tv.column("Name",      width=180)
        self._bench_tv.column("Avg ms",    width=70)
        self._bench_tv.column("Min ms",    width=70)
        self._bench_tv.column("Max ms",    width=70)
        self._bench_tv.column("Success %", width=75)

        bench_sb = ttk.Scrollbar(bench_card, orient="vertical",
                                  command=self._bench_tv.yview)
        self._bench_tv.configure(yscrollcommand=bench_sb.set)
        self._bench_tv.pack(side="left", fill="both", expand=True,
                            padx=(8, 0), pady=(0, 8))
        bench_sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

        # ── Bottom row: DNS actions + TCP ────────────────────────────────────
        bot = tk.Frame(self, bg=T.BG)
        bot.pack(fill="x", padx=16, pady=(0, 16))

        # DNS apply card
        dns_act = Card(bot)
        dns_act.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(dns_act, "Apply DNS").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(dns_act, text="Adapter:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(anchor="w", padx=10)
        self._adapter_var = tk.StringVar()
        self._adapter_cb = ttk.Combobox(dns_act, textvariable=self._adapter_var,
                                        state="readonly", width=24)
        self._adapter_cb.pack(anchor="w", padx=10, pady=2)
        btn_row = tk.Frame(dns_act, bg=T.PANEL)
        btn_row.pack(fill="x", padx=8, pady=(4, 8))
        ActionButton(btn_row, "Apply Fastest DNS",
                     command=self._apply_fastest_dns).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Reset DNS to Auto",
                     command=self._reset_dns).pack(side="left")

        # TCP card
        tcp_card = Card(bot)
        tcp_card.pack(side="left", fill="both", expand=True)
        SectionLabel(tcp_card, "TCP Optimisation").pack(anchor="w", padx=8, pady=(6, 2))
        self._tcp_lbl = tk.Label(tcp_card, text="Click Refresh to read TCP settings.",
                                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                 justify="left", anchor="nw", wraplength=230)
        self._tcp_lbl.pack(padx=10, pady=(0, 4), anchor="w")
        tcp_btn_row = tk.Frame(tcp_card, bg=T.PANEL)
        tcp_btn_row.pack(fill="x", padx=8, pady=(2, 8))
        ActionButton(tcp_btn_row, "Optimize TCP",
                     command=self._optimize_tcp).pack(side="left", padx=(0, 6))
        ActionButton(tcp_btn_row, "Reset TCP",
                     command=self._reset_tcp, danger=True).pack(side="left", padx=(0, 6))
        ActionButton(tcp_btn_row, "Refresh",
                     command=self._refresh_tcp).pack(side="left")

    # ── actions ───────────────────────────────────────────────────────────────

    def _refresh_all(self):
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        try:
            dns_info = internet_booster.get_current_dns()
            adapters = internet_booster.get_network_adapters()
            self.after(0, self._apply_refresh, dns_info, adapters)
        except Exception as exc:
            self.after(0, self._status.set, f"Refresh error: {exc}")

    def _apply_refresh(self, dns_info: dict, adapters: list[dict]):
        # DNS label
        lines = []
        for a in dns_info.get("adapters", []):
            servers = a.get("dns_servers", [])
            if servers:
                lines.append(f"{a['adapter']}:")
                for s in servers:
                    lines.append(f"  {s}")
        self._dns_info.config(text="\n".join(lines) if lines else "No DNS info available.")

        # Adapter combobox + treeview
        self._adapters = adapters
        names = [a["name"] for a in adapters if a.get("status", "").lower() == "up"]
        if not names:
            names = [a["name"] for a in adapters]
        self._adapter_cb["values"] = names
        if names and not self._adapter_var.get():
            self._adapter_var.set(names[0])

        for item in self._adapt_tv.get_children():
            self._adapt_tv.delete(item)
        for a in adapters:
            status = a.get("status", "")
            tag = "up" if status.lower() == "up" else "down"
            speed = a.get("speed_mbps", 0)
            speed_str = f"{speed:.0f}" if speed else "—"
            self._adapt_tv.insert("", "end", text=a.get("name", ""),
                                  values=(a.get("ip", ""), speed_str, status),
                                  tags=(tag,))
        self._adapt_tv.tag_configure("up",   foreground=T.SUCCESS)
        self._adapt_tv.tag_configure("down", foreground=T.DANGER)

    # DNS benchmark
    def _start_benchmark(self):
        self._bench_btn.config(state="disabled")
        self._bench_progress.indeterminate(True)
        self._status.set("Running DNS benchmark… this may take 30–60 seconds.")
        for item in self._bench_tv.get_children():
            self._bench_tv.delete(item)
        threading.Thread(target=self._do_benchmark, daemon=True).start()

    def _do_benchmark(self):
        def cb(msg: str):
            self.after(0, self._status.set, msg)

        try:
            results = internet_booster.dns_benchmark(progress_cb=cb)
            self.after(0, self._show_benchmark, results)
        except Exception as exc:
            self.after(0, self._status.set, f"Benchmark error: {exc}")
            self.after(0, self._bench_progress.indeterminate, False)
            self.after(0, self._bench_btn.config, {"state": "normal"})

    def _show_benchmark(self, results: list[dict]):
        self._bench_progress.indeterminate(False)
        self._bench_btn.config(state="normal")
        self._benchmark_results = results
        for item in self._bench_tv.get_children():
            self._bench_tv.delete(item)

        for i, r in enumerate(results):
            tag = "fastest" if i == 0 else ""
            self._bench_tv.insert("", "end",
                                  text=r.get("server", ""),
                                  values=(r.get("name", ""),
                                          f"{r.get('avg_ms', 0):.1f}",
                                          f"{r.get('min_ms', 0):.1f}",
                                          f"{r.get('max_ms', 0):.1f}",
                                          f"{r.get('success_rate', 0):.1f}%"),
                                  tags=(tag,))
        self._bench_tv.tag_configure("fastest", foreground=T.SUCCESS)

        if results:
            best = results[0]
            self._status.set(
                f"Benchmark complete. Fastest: {best['name']} ({best['server']}) "
                f"— {best['avg_ms']:.1f} ms avg"
            )
        else:
            self._status.set("DNS benchmark complete — no results.")

    # Apply fastest DNS
    def _apply_fastest_dns(self):
        if not self._benchmark_results:
            messagebox.showinfo("No results",
                                "Run the DNS Benchmark first to find the fastest server.")
            return
        adapter = self._adapter_var.get().strip()
        if not adapter:
            messagebox.showwarning("No adapter", "Select a network adapter first.")
            return
        best = self._benchmark_results[0]
        primary = best["server"]
        # Use second result as secondary if available
        secondary = self._benchmark_results[1]["server"] if len(self._benchmark_results) > 1 else ""
        if not messagebox.askyesno(
            "Apply DNS",
            f"Set DNS for '{adapter}' to:\n  Primary:   {primary} ({best['name']})"
            f"\n  Secondary: {secondary if secondary else 'none'}\n\nProceed?"
        ):
            return
        self._status.set(f"Setting DNS on {adapter}…")
        threading.Thread(target=self._do_set_dns,
                         args=(adapter, primary, secondary), daemon=True).start()

    def _do_set_dns(self, adapter: str, primary: str, secondary: str):
        try:
            ok = internet_booster.set_dns(adapter, primary, secondary)
            self.after(0, self._dns_set_done, adapter, primary, ok)
        except Exception as exc:
            self.after(0, self._status.set, f"DNS set error: {exc}")

    def _dns_set_done(self, adapter: str, primary: str, ok: bool):
        if ok:
            self._status.set(f"DNS on '{adapter}' set to {primary}.")
            messagebox.showinfo("DNS Applied",
                                f"DNS on '{adapter}' updated.\n"
                                f"Primary: {primary}\n\n"
                                "Flushing DNS cache…")
            internet_booster.flush_dns()
            self._refresh_all()
        else:
            messagebox.showerror("Error",
                                 "Could not set DNS.\n(May require administrator rights)")

    # Reset DNS
    def _reset_dns(self):
        adapter = self._adapter_var.get().strip()
        if not adapter:
            messagebox.showwarning("No adapter", "Select a network adapter first.")
            return
        if not messagebox.askyesno("Reset DNS",
                                   f"Reset DNS for '{adapter}' to automatic (DHCP)?"):
            return
        self._status.set(f"Resetting DNS on {adapter}…")
        threading.Thread(target=self._do_reset_dns, args=(adapter,), daemon=True).start()

    def _do_reset_dns(self, adapter: str):
        try:
            ok = internet_booster.reset_dns_to_auto(adapter)
            self.after(0, self._reset_dns_done, adapter, ok)
        except Exception as exc:
            self.after(0, self._status.set, f"DNS reset error: {exc}")

    def _reset_dns_done(self, adapter: str, ok: bool):
        if ok:
            self._status.set(f"DNS on '{adapter}' reset to automatic.")
            internet_booster.flush_dns()
            self._refresh_all()
        else:
            messagebox.showerror("Error",
                                 f"Could not reset DNS on '{adapter}'.\n"
                                 "(May require administrator rights)")

    # Flush DNS cache
    def _flush_dns(self):
        ok = internet_booster.flush_dns()
        if ok:
            self._status.set("DNS cache flushed.")
            messagebox.showinfo("DNS Flushed", "DNS resolver cache has been cleared.")
        else:
            self._status.set("DNS flush failed.")

    # TCP optimisation
    def _refresh_tcp(self):
        threading.Thread(target=self._do_refresh_tcp, daemon=True).start()

    def _do_refresh_tcp(self):
        try:
            settings = internet_booster.get_tcp_settings()
            lines = []
            for k, v in settings.items():
                if k == "interfaces":
                    continue
                lines.append(f"{k}: {v}")
            text = "\n".join(lines) if lines else "No TCP settings read."
            self.after(0, self._tcp_lbl.config, {"text": text})
        except Exception as exc:
            self.after(0, self._tcp_lbl.config, {"text": f"Error: {exc}"})

    def _optimize_tcp(self):
        if not messagebox.askyesno(
            "Optimize TCP",
            "Apply TCP registry tweaks for lower latency and higher throughput?\n\n"
            "Changes take effect after restarting network services or rebooting."
        ):
            return
        self._status.set("Applying TCP optimisations…")
        threading.Thread(target=self._do_optimize_tcp, daemon=True).start()

    def _do_optimize_tcp(self):
        try:
            changes = internet_booster.optimize_tcp()
            self.after(0, self._tcp_optimized, changes)
        except Exception as exc:
            self.after(0, self._status.set, f"TCP optimisation error: {exc}")

    def _tcp_optimized(self, changes: list[str]):
        self._status.set(f"TCP optimised — {len(changes)} settings changed.")
        messagebox.showinfo("TCP Optimised",
                            "Changes applied:\n" + "\n".join(changes) +
                            "\n\nA restart may be needed for all changes to take effect.")
        self._refresh_tcp()

    def _reset_tcp(self):
        if not messagebox.askyesno("Reset TCP",
                                   "Reset TCP settings to Windows defaults?\n"
                                   "A restart may be required."):
            return
        self._status.set("Resetting TCP settings…")
        threading.Thread(target=self._do_reset_tcp, daemon=True).start()

    def _do_reset_tcp(self):
        try:
            changes = internet_booster.reset_tcp()
            self.after(0, self._tcp_reset_done, changes)
        except Exception as exc:
            self.after(0, self._status.set, f"TCP reset error: {exc}")

    def _tcp_reset_done(self, changes: list[str]):
        self._status.set(f"TCP reset — {len(changes)} settings restored.")
        messagebox.showinfo("TCP Reset",
                            "TCP settings restored to defaults:\n" + "\n".join(changes))
        self._refresh_tcp()
