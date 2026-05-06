"""Software Updater page — detect installed software and check for updates."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import software_updater as su


class SoftwarePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._entries: list[su.SoftwareEntry] = []
        self._all_entries: list[su.SoftwareEntry] = []
        self._checking = False
        self._build_ui()

    def on_activate(self):
        pass

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Software Updater", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Detect and update outdated software",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        # Controls bar
        ctrl = tk.Frame(self, bg=T.BG)
        ctrl.pack(fill="x", padx=16, pady=8)
        ActionButton(ctrl, "Check for Updates", command=self._start_check
                     ).pack(side="left", padx=(0, 8))
        self._update_all_btn = ActionButton(ctrl, "Update All Outdated",
                                            command=self._update_all)
        self._update_all_btn.pack(side="left", padx=(0, 12))
        self._update_all_btn.config(state="disabled")

        tk.Label(ctrl, text="Filter:", bg=T.BG, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(ctrl, textvariable=self._filter_var, width=22,
                 bg=T.PANEL, fg=T.FG, insertbackground=T.FG,
                 font=T.FONT_BODY).pack(side="left", padx=6)

        self._show_outdated_only = tk.BooleanVar(value=False)
        tk.Checkbutton(ctrl, text="Outdated only", variable=self._show_outdated_only,
                       bg=T.BG, fg=T.FG, selectcolor=T.ACCENT, activebackground=T.BG,
                       command=self._apply_filter).pack(side="left", padx=4)

        # Summary labels
        self._summary_lbl = tk.Label(self, text="", bg=T.BG, fg=T.HIGHLIGHT, font=T.FONT_BOLD)
        self._summary_lbl.pack(anchor="w", padx=16)

        self._winget_lbl = tk.Label(self, text="", bg=T.BG, fg=T.FG2, font=T.FONT_SMALL)
        self._winget_lbl.pack(anchor="w", padx=16)

        # Progress
        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)
        self._progress_lbl = tk.Label(self, text="", bg=T.BG, fg=T.FG2, font=T.FONT_SMALL)
        self._progress_lbl.pack(anchor="w", padx=16)

        # Software list
        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Installed", "Latest", "Status")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",       text="Software Name",     anchor="w")
        self._tv.heading("Installed",text="Installed Version", anchor="w")
        self._tv.heading("Latest",   text="Latest Version",    anchor="w")
        self._tv.heading("Status",   text="Status",            anchor="w")
        self._tv.column("#0",        width=260)
        self._tv.column("Installed", width=130)
        self._tv.column("Latest",    width=130)
        self._tv.column("Status",    width=120)
        self._tv.tag_configure("outdated",   foreground=T.WARNING)
        self._tv.tag_configure("up_to_date", foreground=T.SUCCESS)
        self._tv.tag_configure("unknown",    foreground=T.FG2)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Update button for selected
        btn_bar = tk.Frame(self, bg=T.BG)
        btn_bar.pack(fill="x", padx=16, pady=(4, 8))
        ActionButton(btn_bar, "Update Selected",
                     command=self._update_selected).pack(side="left", padx=(0, 8))
        ActionButton(btn_bar, "Open Download Page",
                     command=self._open_download).pack(side="left")
        tk.Label(btn_bar,
                 text="Tip: 'Update' uses winget if available, otherwise opens the download page",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL).pack(side="right", padx=8)

    # ── check ─────────────────────────────────────────────────────────────────

    def _start_check(self):
        if self._checking:
            return
        self._checking = True
        self._entries = []
        self._all_entries = []
        self._summary_lbl.config(text="Scanning installed software...")
        self._update_all_btn.config(state="disabled")
        self._progress.indeterminate(True)
        for item in self._tv.get_children():
            self._tv.delete(item)

        # Show winget status
        winget_ok = su.check_winget()
        if winget_ok:
            self._winget_lbl.config(text="winget detected — live update data available",
                                     fg=T.SUCCESS)
        else:
            self._winget_lbl.config(text="winget not found — using known versions database",
                                     fg=T.WARNING)

        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        try:
            def cb(msg, pct):
                try:
                    self.after(0, self._progress_lbl.config, {"text": msg})
                    if pct > 0:
                        self.after(0, self._progress.set, pct)
                except tk.TclError:
                    pass  # Widget was destroyed

            entries = su.get_installed_with_updates(progress_cb=cb)
            self.after(0, self._show_results, entries)
        except Exception as e:
            self.after(0, lambda: self._on_check_error(str(e)))

    def _show_results(self, entries: list[su.SoftwareEntry]):
        try:
            self._checking = False
            self._progress.indeterminate(False)
            self._progress_lbl.config(text="")
            self._all_entries = entries
            self._entries = entries

            outdated = sum(1 for e in entries if e.status == "outdated")
            up_to_date = sum(1 for e in entries if e.status == "up_to_date")
            self._summary_lbl.config(
                text=f"{len(entries)} programs found  —  "
                     f"{outdated} outdated  |  {up_to_date} up to date"
            )
            if outdated > 0:
                self._update_all_btn.config(state="normal")

            self._apply_filter()
            self._app._status.set("Software check complete")
        except tk.TclError:
            pass  # Widget was destroyed

    def _on_check_error(self, error: str):
        """Handle errors during software check."""
        try:
            self._checking = False
            self._progress.indeterminate(False)
            self._summary_lbl.config(text=f"❌ Error: {error}", fg=T.WARNING)
            self._app._status.set(f"Software check failed: {error[:50]}")
        except tk.TclError:
            pass

    def _apply_filter(self):
        q = self._filter_var.get().lower()
        outdated_only = self._show_outdated_only.get()
        for item in self._tv.get_children():
            self._tv.delete(item)

        for e in self._all_entries:
            if q and q not in e.name.lower() and q not in e.publisher.lower():
                continue
            if outdated_only and e.status != "outdated":
                continue
            status_str = {
                "outdated":   "⬆ Outdated",
                "up_to_date": "✓ Up to date",
                "unknown":    "? Unknown",
            }.get(e.status, e.status)
            latest = e.latest_version or "–"
            installed = e.installed_version or "–"
            self._tv.insert("", "end", iid=e.name, text=e.name,
                            values=(installed, latest, status_str),
                            tags=(e.status,))

    # ── update ────────────────────────────────────────────────────────────────

    def _get_selected_entry(self) -> su.SoftwareEntry | None:
        sel = self._tv.selection()
        if not sel:
            return None
        name = sel[0]
        return next((e for e in self._all_entries if e.name == name), None)

    def _update_selected(self):
        sel = self._tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a software entry first.")
            return
        for iid in sel:
            entry = next((e for e in self._all_entries if e.name == iid), None)
            if entry:
                self._launch_update(entry)

    def _launch_update(self, entry: su.SoftwareEntry):
        try:
            ok = su.launch_update(entry)
            if ok:
                try:
                    self._tv.item(entry.name, values=(
                        entry.installed_version or "–",
                        entry.latest_version or "–",
                        "🔄 Updating..."
                    ), tags=("unknown",))
                    self._app._status.set(f"Update started for {entry.name}")
                except tk.TclError:
                    pass
            else:
                messagebox.showinfo("Update", f"Could not auto-update {entry.name}.\n"
                                              "No winget ID or download URL found.")
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to update {entry.name}:\n{str(e)[:100]}")

    def _open_download(self):
        entry = self._get_selected_entry()
        if not entry:
            messagebox.showinfo("No selection", "Select an entry first.")
            return
        import webbrowser
        if entry.download_url:
            webbrowser.open(entry.download_url)
        else:
            messagebox.showinfo("No URL", f"No download URL for {entry.name}")

    def _update_all(self):
        outdated = [e for e in self._all_entries if e.status == "outdated"]
        if not outdated:
            messagebox.showinfo("Nothing to update", "All software is up to date.")
            return
        if not messagebox.askyesno("Update All",
                                   f"Start update for {len(outdated)} outdated programs?\n\n"
                                   "Updates will run silently in background.\n"
                                   "Programs without winget support will open in browser."):
            return
        for entry in outdated:
            self._launch_update(entry)
        messagebox.showinfo("Updates Launched",
                            f"Launched updates for {len(outdated)} programs.\n"
                            "Check your taskbar for update progress.")
