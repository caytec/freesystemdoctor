"""DNS Protector page — lock & monitor DNS settings."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import dns_protector as dp


class DnsProtectorPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._lock_var = tk.BooleanVar(value=dp.is_locked())
        self._build_ui()
        self._refresh_adapters()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔒  DNS Protector", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Lock DNS settings against malware hijacking",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Provider picker card
        card = Card(body)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Choose DNS Provider").pack(anchor="w", padx=12, pady=8)

        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=12, pady=4)
        tk.Label(row1, text="Provider:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY, width=12, anchor="w").pack(side="left")
        self._provider_var = tk.StringVar(value="Cloudflare")
        cb = ttk.Combobox(row1, textvariable=self._provider_var,
                           values=list(dp.PROVIDERS.keys()),
                           state="readonly", width=20)
        cb.pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_provider())

        row2 = tk.Frame(card, bg=T.PANEL)
        row2.pack(fill="x", padx=12, pady=4)
        tk.Label(row2, text="Primary:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY, width=12, anchor="w").pack(side="left")
        self._primary = tk.Entry(row2, bg=T.ACCENT, fg=T.FG,
                                  font=T.FONT_BODY, width=20,
                                  insertbackground=T.FG)
        self._primary.pack(side="left", padx=8)
        self._primary.insert(0, "1.1.1.1")

        tk.Label(row2, text="Secondary:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_BODY, width=12, anchor="w").pack(side="left", padx=(20, 0))
        self._secondary = tk.Entry(row2, bg=T.ACCENT, fg=T.FG,
                                    font=T.FONT_BODY, width=20,
                                    insertbackground=T.FG)
        self._secondary.pack(side="left", padx=8)
        self._secondary.insert(0, "1.0.0.1")

        # Action row
        actions = tk.Frame(card, bg=T.PANEL)
        actions.pack(fill="x", padx=12, pady=(8, 12))

        ActionButton(actions, text="Apply DNS",
                     command=self._on_apply, width=120).pack(side="left", padx=(0, 8))

        tk.Label(actions, text="Lock DNS:",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left", padx=(20, 6))
        ToggleSwitch(actions, variable=self._lock_var,
                      command=self._on_lock_toggle).pack(side="left")

        ActionButton(actions, text="Flush Cache",
                     command=self._on_flush, width=120,
                     secondary=True).pack(side="right")

        # Adapters card
        adapt_card = Card(body)
        adapt_card.pack(fill="both", expand=True)
        SectionLabel(adapt_card, "Active Network Adapters").pack(anchor="w", padx=12, pady=8)

        cols = ("alias", "primary", "secondary")
        self._tv = ttk.Treeview(adapt_card, columns=cols, show="headings", height=8)
        for c, t, w in [("alias", "Adapter", 220), ("primary", "Primary DNS", 180),
                        ("secondary", "Secondary DNS", 180)]:
            self._tv.heading(c, text=t)
            self._tv.column(c, width=w, anchor="w")
        self._tv.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        bot = tk.Frame(adapt_card, bg=T.PANEL)
        bot.pack(fill="x", padx=12, pady=(0, 12))
        ActionButton(bot, text="↻ Refresh", command=self._refresh_adapters,
                      secondary=True, width=100).pack(side="left")
        self._status_lbl = tk.Label(bot, text="", bg=T.PANEL, fg=T.FG2,
                                     font=T.FONT_SMALL)
        self._status_lbl.pack(side="left", padx=12)

    def _on_provider(self):
        name = self._provider_var.get()
        prim, sec = dp.PROVIDERS.get(name, ("", ""))
        self._primary.delete(0, tk.END)
        self._primary.insert(0, prim)
        self._secondary.delete(0, tk.END)
        self._secondary.insert(0, sec)

    def _on_apply(self):
        prim = self._primary.get().strip()
        sec = self._secondary.get().strip()
        self._status_lbl.config(text="Applying…", fg=T.FG2)

        def work():
            results = dp.apply_to_all(prim, sec)
            ok = sum(1 for _, o, _ in results if o)
            self.after(0, lambda: self._status_lbl.config(
                text=f"Applied to {ok}/{len(results)} adapters",
                fg=T.SUCCESS if ok else T.DANGER))
            self.after(0, self._refresh_adapters)

        threading.Thread(target=work, daemon=True).start()

    def _on_lock_toggle(self):
        if self._lock_var.get():
            prim = self._primary.get().strip()
            if not prim:
                messagebox.showwarning("DNS Protector",
                                       "Set a primary DNS first.")
                self._lock_var.set(False)
                return
            dp.lock(prim, self._secondary.get().strip(),
                     self._provider_var.get())
            self._status_lbl.config(text="Locked — watcher active",
                                     fg=T.SUCCESS)
        else:
            dp.unlock()
            self._status_lbl.config(text="Unlocked", fg=T.FG2)

    def _on_flush(self):
        if dp.flush_dns():
            self._status_lbl.config(text="DNS cache flushed", fg=T.SUCCESS)
        else:
            self._status_lbl.config(text="Flush failed", fg=T.DANGER)

    def _refresh_adapters(self):
        for item in self._tv.get_children():
            self._tv.delete(item)

        def fetch():
            adapters = dp.list_adapters()
            self.after(0, lambda: self._populate(adapters))

        threading.Thread(target=fetch, daemon=True).start()

    def _populate(self, adapters):
        for a in adapters:
            self._tv.insert("", "end", values=(
                a["alias"], a["primary"] or "—", a["secondary"] or "—"))

    def on_activate(self):
        self._refresh_adapters()
