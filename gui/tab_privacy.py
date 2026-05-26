"""Privacy & Telemetry tab."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import privacy_cleaner as pc


def _fmt(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


class PrivacyTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._browser_items = []
        self._browser_vars: dict[str, tk.BooleanVar] = {}
        self._build_ui()
        self.after(300, self._refresh_status)
        self.after(500, self._scan_browser)

    def _build_ui(self):
        # ── Telemetry panel ───────────────────────────────────────────────────
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(12, 4))

        tel = Card(top)
        tel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SectionLabel(tel, "Windows Telemetry & Tracking").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(tel,
                 text="Controls what Windows reports back to Microsoft.\n"
                      "Disabling is safe and improves privacy.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, justify="left").pack(padx=10, anchor="w")

        self._tel_status = tk.Label(tel, text="Checking...", bg=T.PANEL,
                                    fg=T.WARNING, font=T.FONT_BOLD)
        self._tel_status.pack(anchor="w", padx=10, pady=2)

        btn_row = tk.Frame(tel, bg=T.PANEL)
        btn_row.pack(fill="x", padx=8, pady=(4, 8))
        ActionButton(btn_row, "Disable Telemetry", command=self._disable_telemetry).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Re-enable Telemetry", command=self._enable_telemetry).pack(side="left")

        # ── Privacy toggles ───────────────────────────────────────────────────
        priv = Card(top)
        priv.pack(side="left", fill="both", expand=True)
        SectionLabel(priv, "Privacy Settings").pack(anchor="w", padx=8, pady=(6, 2))

        self._loc_var = tk.BooleanVar()
        self._adid_var = tk.BooleanVar()

        tk.Checkbutton(priv, text="Block Location Tracking",
                       variable=self._loc_var, bg=T.PANEL, fg=T.FG,
                       selectcolor=T.ACCENT, activebackground=T.PANEL,
                       font=T.FONT_BODY, command=self._toggle_location).pack(anchor="w", padx=12, pady=2)
        tk.Checkbutton(priv, text="Disable Advertising ID",
                       variable=self._adid_var, bg=T.PANEL, fg=T.FG,
                       selectcolor=T.ACCENT, activebackground=T.PANEL,
                       font=T.FONT_BODY, command=self._toggle_adid).pack(anchor="w", padx=12, pady=2)

        ActionButton(priv, "Clear Activity History", command=self._clear_activity).pack(anchor="w", padx=8, pady=(8, 4))
        self._activity_result = tk.Label(priv, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._activity_result.pack(anchor="w", padx=12, pady=(0, 8))

        # ── Browser privacy ───────────────────────────────────────────────────
        bot = Card(self)
        bot.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        hdr = tk.Frame(bot, bg=T.PANEL)
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        SectionLabel(hdr, "Browser Privacy Cleaner").pack(side="left")
        ActionButton(hdr, "Scan", command=self._scan_browser).pack(side="right")
        ActionButton(hdr, "Clean Selected", command=self._clean_browser).pack(side="right", padx=4)

        self._progress = ProgressBar(bot, bg=T.PANEL)
        self._progress.pack(fill="x", padx=8, pady=2)

        scroll_frame = tk.Frame(bot, bg=T.PANEL)
        scroll_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._canvas = tk.Canvas(scroll_frame, bg=T.PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(scroll_frame, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._items_frame = tk.Frame(self._canvas, bg=T.PANEL)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._items_frame, anchor="nw")
        self._items_frame.bind("<Configure>",
                               lambda e: self._canvas.configure(
                                   scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._canvas_win, width=e.width))

    # ── actions ───────────────────────────────────────────────────────────────

    def _refresh_status(self):
        threading.Thread(target=self._do_refresh_status, daemon=True).start()

    def _do_refresh_status(self):
        status = pc.get_telemetry_status()
        loc = pc.get_location_status()
        adid = pc.get_advertising_id_status()
        self.after(0, self._apply_status, status, loc, adid)

    def _apply_status(self, status, loc, adid):
        level = status.get("telemetry_level", "Not set")
        if level == 0 or level == "0":
            self._tel_status.config(text="Telemetry: DISABLED", fg=T.SUCCESS)
        else:
            self._tel_status.config(text=f"Telemetry: ENABLED (level {level})", fg=T.WARNING)
        self._loc_var.set(loc.lower() == "deny")
        self._adid_var.set(adid == 0)

    def _disable_telemetry(self):
        self._progress.indeterminate(True)
        self._status.set("Disabling telemetry...")
        def cb(msg):
            self.after(0, self._status.set, msg)
        def run():
            done = pc.disable_telemetry(progress_cb=cb)
            self.after(0, self._tel_done, done, "Telemetry disabled")
        threading.Thread(target=run, daemon=True).start()

    def _enable_telemetry(self):
        if not messagebox.askyesno("Enable Telemetry",
                                   "Re-enable Windows telemetry and diagnostics?"):
            return
        self._progress.indeterminate(True)
        threading.Thread(target=lambda: self.after(
            0, self._tel_done, pc.enable_telemetry(), "Telemetry enabled"), daemon=True).start()

    def _tel_done(self, done, msg):
        self._progress.indeterminate(False)
        self._status.set(f"{msg} ({len(done)} changes)")
        self._refresh_status()

    def _toggle_location(self):
        if self._loc_var.get():
            pc.disable_location()
            self._status.set("Location tracking blocked.")
        else:
            pc.enable_location()
            self._status.set("Location tracking enabled.")

    def _toggle_adid(self):
        if self._adid_var.get():
            pc.disable_advertising_id()
            self._status.set("Advertising ID disabled.")
        else:
            pc.enable_advertising_id()
            self._status.set("Advertising ID enabled.")

    def _clear_activity(self):
        done = pc.clear_activity_history()
        self._activity_result.config(text=f"{len(done)} items cleared")
        self._status.set(f"Activity history cleared ({len(done)} items).")

    def _scan_browser(self):
        self._progress.indeterminate(True)
        self._status.set("Scanning browser data...")
        threading.Thread(target=self._do_scan_browser, daemon=True).start()

    def _do_scan_browser(self):
        items = pc.scan_browser_privacy()
        self.after(0, self._show_browser_items, items)

    def _show_browser_items(self, items):
        self._progress.indeterminate(False)
        self._browser_items = items
        self._browser_vars = {}
        for widget in self._items_frame.winfo_children():
            widget.destroy()

        total = sum(i["size"] for i in items)
        tk.Label(self._items_frame,
                 text=f"{len(items)} items found  —  {_fmt(total)} total",
                 bg=T.PANEL, fg=T.HIGHLIGHT, font=T.FONT_BOLD).pack(anchor="w", pady=(0, 4))

        for item in items:
            var = tk.BooleanVar(value=item["selected"])
            self._browser_vars[item["path"]] = var
            row = tk.Frame(self._items_frame, bg=T.PANEL)
            row.pack(fill="x", pady=1)
            tk.Checkbutton(row, text=f"{item['label']}",
                           variable=var, bg=T.PANEL, fg=T.FG,
                           selectcolor=T.ACCENT, activebackground=T.PANEL,
                           font=T.FONT_BODY, anchor="w").pack(side="left")
            tk.Label(row, text=item["size_str"], bg=T.PANEL,
                     fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=8)

        self._status.set(f"Browser scan complete — {len(items)} items, {_fmt(total)} total.")

    def _clean_browser(self):
        to_clean = [i for i in self._browser_items
                    if self._browser_vars.get(i["path"], tk.BooleanVar()).get()]
        if not to_clean:
            messagebox.showinfo("Nothing selected", "Check at least one item to clean.")
            return
        total = sum(i["size"] for i in to_clean)
        if not messagebox.askyesno("Clean Browser Data",
                                   f"Delete {len(to_clean)} selected items ({_fmt(total)})?\n\n"
                                   "Close your browsers first for best results."):
            return
        self._progress.indeterminate(True)
        def cb(label):
            self.after(0, self._status.set, f"Cleaning: {label}")
        def run():
            freed, count = pc.clean_browser_privacy(to_clean, progress_cb=cb)
            self.after(0, self._browser_clean_done, freed, count)
        threading.Thread(target=run, daemon=True).start()

    def _browser_clean_done(self, freed, count):
        self._progress.indeterminate(False)
        self._status.set(f"Browser data cleaned — {count} items, {_fmt(freed)} freed.")
        messagebox.showinfo("Done", f"Cleaned {count} browser items\nFreed: {_fmt(freed)}")
        self._scan_browser()
