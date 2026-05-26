"""Internet Booster page — DNS optimization, TCP tweaks, network monitoring."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import internet_booster as ib


class InternetBoosterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._benchmark_results: list[dict] = []
        self._adapters: list[dict] = []
        self._build_ui()
        self._refresh_status_async()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🌐  Internet Booster", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="DNS optimization and TCP tuning",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_dns_section(body)
        self._build_tcp_section(body)

    # ── DNS section ───────────────────────────────────────────────────────────

    def _build_dns_section(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))
        SectionLabel(card, "DNS Benchmark & Optimization").pack(
            anchor="w", padx=12, pady=8)

        # Adapter row
        adapter_row = tk.Frame(card, bg=T.PANEL)
        adapter_row.pack(fill="x", padx=12, pady=4)
        tk.Label(adapter_row, text="Adapter:",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY,
                 width=10, anchor="w").pack(side="left")

        self._adapter_var = tk.StringVar(value="(loading)")
        self._adapter_cb = ttk.Combobox(adapter_row, textvariable=self._adapter_var,
                                          state="readonly", width=32)
        self._adapter_cb.pack(side="left", padx=6, fill="x", expand=True)

        ActionButton(adapter_row, text="↻ Refresh",
                      command=self._refresh_status_async, width=100,
                      secondary=True).pack(side="left", padx=(8, 0))

        # Current DNS row
        self._dns_status = tk.Label(card, text="Current DNS: Loading…",
                                    bg=T.PANEL, fg=T.FG2,
                                    font=T.FONT_SMALL, anchor="w")
        self._dns_status.pack(fill="x", padx=12, pady=(8, 4))

        # Progress + status
        self._dns_progress = ProgressBar(card)
        self._dns_progress.pack(fill="x", padx=12, pady=(4, 4))

        self._dns_msg = tk.Label(card, text="",
                                  bg=T.PANEL, fg=T.FG2,
                                  font=T.FONT_SMALL, anchor="w")
        self._dns_msg.pack(fill="x", padx=12, pady=(0, 6))

        # Results table
        table_frame = tk.Frame(card, bg=T.PANEL)
        table_frame.pack(fill="both", expand=True, padx=12, pady=4)

        cols = ("rank", "name", "ip", "avg", "min", "max", "success")
        self._tv = ttk.Treeview(table_frame, columns=cols, show="headings",
                                  height=8, selectmode="browse")
        for col, label, w, anchor in [
            ("rank", "#", 36, "center"),
            ("name", "Provider", 200, "w"),
            ("ip",   "IP Address", 130, "w"),
            ("avg",  "Avg (ms)", 80, "e"),
            ("min",  "Min (ms)", 80, "e"),
            ("max",  "Max (ms)", 80, "e"),
            ("success", "Success %", 80, "e"),
        ]:
            self._tv.heading(col, text=label)
            self._tv.column(col, width=w, anchor=anchor)
        self._tv.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self._tv.yview)
        sb.pack(side="right", fill="y")
        self._tv.configure(yscrollcommand=sb.set)

        # Action buttons
        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=12, pady=(8, 12))

        ActionButton(btn_frame, text="🔬 Benchmark DNS",
                     command=self._on_benchmark_dns,
                     width=160).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="⚡ Optimize to Best",
                     command=self._on_optimize_dns,
                     width=160).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="🎯 Apply Selected",
                     command=self._on_apply_selected,
                     width=140, secondary=True).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="↺ Reset to DHCP",
                     command=self._on_reset_dns,
                     width=130, secondary=True).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="🔄 Flush Cache",
                     command=self._on_flush_dns,
                     width=120, secondary=True).pack(side="left")

    # ── TCP section ───────────────────────────────────────────────────────────

    def _build_tcp_section(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "TCP Optimization").pack(anchor="w", padx=12, pady=8)

        self._tcp_status = tk.Label(card, text="TCP settings: Loading…",
                                    bg=T.PANEL, fg=T.FG2,
                                    font=T.FONT_SMALL, anchor="w",
                                    justify="left")
        self._tcp_status.pack(fill="x", padx=12, pady=4)

        self._tcp_aggressive_var = tk.BooleanVar(value=False)
        agg_row = tk.Frame(card, bg=T.PANEL)
        agg_row.pack(fill="x", padx=12, pady=4)
        tk.Checkbutton(agg_row, text="Aggressive mode (larger TCP window)",
                        variable=self._tcp_aggressive_var,
                        bg=T.PANEL, fg=T.FG,
                        selectcolor=T.ACCENT,
                        activebackground=T.PANEL,
                        activeforeground=T.HIGHLIGHT,
                        font=T.FONT_SMALL).pack(side="left")

        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=12, pady=(4, 12))
        ActionButton(btn_frame, text="⚡ Apply TCP Tweaks",
                     command=self._on_optimize_tcp,
                     width=180).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="↺ Reset to Defaults",
                     command=self._on_reset_tcp,
                     width=160, secondary=True).pack(side="left")

    # ── status loading ────────────────────────────────────────────────────────

    def _refresh_status_async(self):
        self._dns_status.config(text="Current DNS: Loading…")
        self._tcp_status.config(text="TCP settings: Loading…")

        def work():
            adapters = ib.get_network_adapters()
            current = ib.get_current_dns()
            tcp = ib.get_tcp_settings()
            self.after(0, lambda: self._apply_status(adapters, current, tcp))

        threading.Thread(target=work, daemon=True).start()

    def _apply_status(self, adapters, current_dns, tcp):
        # Adapter dropdown
        self._adapters = adapters or []
        names = [a["name"] for a in self._adapters if a.get("status") == "Up"]
        if not names and self._adapters:
            names = [a["name"] for a in self._adapters]
        if not names:
            # Fallback to ipconfig adapters
            names = [a["adapter"] for a in current_dns.get("adapters", [])]

        self._adapter_cb["values"] = names
        if names:
            current_sel = self._adapter_var.get()
            if current_sel not in names:
                self._adapter_var.set(names[0])
        else:
            self._adapter_var.set("(no adapters)")
            self._dns_msg.config(
                text="No network adapters detected — DNS cannot be applied. "
                     "Try running as administrator.",
                fg=T.WARNING)

        # Current DNS string
        parts = []
        for a in current_dns.get("adapters", []):
            dns = a.get("dns_servers") or []
            if dns:
                parts.append(f"{a['adapter']}: {', '.join(dns)}")
        if parts:
            self._dns_status.config(text="Current DNS — " + "  •  ".join(parts),
                                     fg=T.FG)
        else:
            self._dns_status.config(text="Current DNS: (none detected)",
                                     fg=T.WARNING)

        # TCP status
        if tcp:
            ttl  = tcp.get("DefaultTTL")
            twd  = tcp.get("TcpTimedWaitDelay")
            mup  = tcp.get("MaxUserPort")
            t13  = tcp.get("Tcp1323Opts")
            optimised = ttl == 64 and t13 == 1 and (mup or 0) >= 65000
            tag = "✓ Optimized" if optimised else "○ Default values"
            color = T.SUCCESS if optimised else T.FG2
            self._tcp_status.config(
                text=(f"TCP settings: {tag}\n"
                      f"  TTL={ttl}   TimeWaitDelay={twd}s   "
                      f"MaxUserPort={mup}   WindowScaling={t13}"),
                fg=color)
        else:
            self._tcp_status.config(text="TCP settings: (unable to read)",
                                     fg=T.DANGER)

    # ── DNS actions ───────────────────────────────────────────────────────────

    def _on_benchmark_dns(self):
        self._dns_progress.indeterminate(True)
        self._dns_msg.config(text="Benchmarking — testing DNS servers…",
                              fg=T.FG2)
        for it in self._tv.get_children():
            self._tv.delete(it)

        def progress(msg):
            try:
                self.after(0, lambda: self._dns_msg.config(
                    text=msg, fg=T.FG2))
            except Exception:
                pass

        def work():
            try:
                results = ib.dns_benchmark(progress_cb=progress)
                self.after(0, lambda: self._on_benchmark_done(results, None))
            except Exception as e:
                self.after(0, lambda: self._on_benchmark_done([], str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _on_benchmark_done(self, results: list[dict], error):
        self._dns_progress.indeterminate(False)
        self._dns_progress.set(100 if not error else 0)

        if error:
            self._dns_msg.config(text=f"Error: {error}", fg=T.DANGER)
            return

        self._benchmark_results = results

        for it in self._tv.get_children():
            self._tv.delete(it)

        if not results:
            self._dns_msg.config(text="No results.", fg=T.WARNING)
            return

        for i, r in enumerate(results):
            tag = "best" if i == 0 else ("good" if i < 3 else "")
            self._tv.insert("", "end", values=(
                i + 1,
                r.get("name", "?"),
                r.get("server", "?"),
                f"{r.get('avg_ms', 0):.1f}",
                f"{r.get('min_ms', 0):.1f}",
                f"{r.get('max_ms', 0):.1f}",
                f"{r.get('success_rate', 0):.0f}",
            ), tags=(tag,))

        self._tv.tag_configure("best", foreground=T.SUCCESS)
        self._tv.tag_configure("good", foreground=T.HIGHLIGHT)

        best = results[0]
        self._dns_msg.config(
            text=f"✓  Best: {best['name']} ({best['server']}) — "
                 f"{best['avg_ms']:.1f} ms avg",
            fg=T.SUCCESS)

    def _selected_adapter(self) -> str:
        a = self._adapter_var.get()
        if a in ("(loading)", "(no adapters)", ""):
            return ""
        return a

    def _on_optimize_dns(self):
        adapter = self._selected_adapter()
        if not adapter:
            messagebox.showwarning("No adapter",
                                    "Select an adapter from the dropdown first.")
            return

        if not self._benchmark_results:
            # Run benchmark first, then optimize
            self._dns_msg.config(text="Running benchmark first…", fg=T.FG2)
            self._dns_progress.indeterminate(True)

            def work():
                try:
                    results = ib.dns_benchmark()
                    self.after(0, lambda: self._on_benchmark_done(results, None))
                    if results:
                        self.after(50, lambda: self._apply_best_dns(adapter))
                except Exception as e:
                    self.after(0, lambda: self._on_benchmark_done([], str(e)))

            threading.Thread(target=work, daemon=True).start()
        else:
            self._apply_best_dns(adapter)

    def _apply_best_dns(self, adapter: str):
        if not self._benchmark_results:
            return
        best = self._benchmark_results[0]
        secondary = ""
        # Try to pick a secondary from the same provider family or 2nd-best
        primary_name = best.get("name", "")
        for r in self._benchmark_results[1:]:
            n = r.get("name", "")
            if primary_name.split()[0] in n and r["server"] != best["server"]:
                secondary = r["server"]
                break
        if not secondary and len(self._benchmark_results) > 1:
            secondary = self._benchmark_results[1]["server"]

        primary = best["server"]

        def work():
            ok = ib.set_dns(adapter, primary, secondary)
            ib.flush_dns()
            self.after(0, lambda: self._after_set_dns(ok, best, primary, secondary))

        threading.Thread(target=work, daemon=True).start()

    def _on_apply_selected(self):
        adapter = self._selected_adapter()
        if not adapter:
            messagebox.showwarning("No adapter", "Select an adapter first.")
            return
        sel = self._tv.selection()
        if not sel:
            messagebox.showinfo("Select row",
                                  "Select a row in the benchmark table first.")
            return
        vals = self._tv.item(sel[0])["values"]
        if len(vals) < 3:
            return
        primary = str(vals[2])

        def work():
            ok = ib.set_dns(adapter, primary, "")
            ib.flush_dns()
            self.after(0, lambda: self._dns_msg.config(
                text=(f"✓  DNS set to {primary} on {adapter}"
                      if ok else f"✕  Failed to apply {primary}"),
                fg=T.SUCCESS if ok else T.DANGER))
            self.after(100, self._refresh_status_async)

        threading.Thread(target=work, daemon=True).start()

    def _after_set_dns(self, ok, best, primary, secondary):
        if ok:
            sec_part = f" / {secondary}" if secondary else ""
            self._dns_msg.config(
                text=f"✓  Applied {best['name']}: {primary}{sec_part}",
                fg=T.SUCCESS)
            self._refresh_status_async()
        else:
            self._dns_msg.config(
                text=f"✕  Failed to set DNS — admin rights required?",
                fg=T.DANGER)

    def _on_reset_dns(self):
        adapter = self._selected_adapter()
        if not adapter:
            messagebox.showwarning("No adapter", "Select an adapter first.")
            return

        def work():
            ok = ib.reset_dns_to_auto(adapter)
            ib.flush_dns()
            self.after(0, lambda: self._dns_msg.config(
                text=(f"✓  Reset {adapter} to DHCP"
                      if ok else f"✕  Failed to reset DNS"),
                fg=T.SUCCESS if ok else T.DANGER))
            self.after(100, self._refresh_status_async)

        threading.Thread(target=work, daemon=True).start()

    def _on_flush_dns(self):
        def work():
            ok = ib.flush_dns()
            self.after(0, lambda: self._dns_msg.config(
                text="✓  DNS cache flushed" if ok else "✕  Flush failed",
                fg=T.SUCCESS if ok else T.DANGER))

        threading.Thread(target=work, daemon=True).start()

    # ── TCP actions ───────────────────────────────────────────────────────────

    def _on_optimize_tcp(self):
        aggressive = self._tcp_aggressive_var.get()

        def work():
            try:
                changes = ib.optimize_tcp(aggressive=aggressive)
                self.after(0, lambda: self._after_tcp(changes, None))
            except Exception as e:
                self.after(0, lambda: self._after_tcp([], str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _on_reset_tcp(self):
        if not messagebox.askyesno("Reset TCP",
                                    "Reset all TCP tweaks to Windows defaults?"):
            return

        def work():
            try:
                changes = ib.reset_tcp()
                self.after(0, lambda: self._after_tcp(changes, None,
                                                        reset=True))
            except Exception as e:
                self.after(0, lambda: self._after_tcp([], str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _after_tcp(self, changes, error, reset: bool = False):
        if error:
            messagebox.showerror("TCP", f"Failed: {error}")
            self._tcp_status.config(text=f"TCP settings: error — {error}",
                                     fg=T.DANGER)
            return

        if not changes:
            messagebox.showinfo("TCP", "No changes were applied.")
            return

        verb = "Reset" if reset else "Applied"
        msg = f"{verb} {len(changes)} TCP tweak(s):\n\n" + "\n".join(
            f"  • {c}" for c in changes)
        msg += "\n\nA system restart is recommended."
        messagebox.showinfo("TCP Optimization", msg)
        self._refresh_status_async()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_activate(self):
        self._refresh_status_async()
