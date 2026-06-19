"""Disk Analyzer page — visual folder size breakdown."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import disk_analyzer as da


from ._pro_gate import gate_or_build


class DiskAnalyzerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._current_analysis = None
        self._drives: list[dict] = []
        self._busy = False
        self._build_ui()
        # Populate dropdown immediately (fast — just psutil listing, no walking)
        self._load_drives()

    def on_activate(self):
        # Refresh drive list each time user navigates here
        # (covers case where USB stick / external drive was plugged in)
        self._load_drives()

    def _build_ui(self):
        # Pro-feature gate — shows upsell for Free users
        if gate_or_build(self, "disk_analyzer", "Disk Analyzer"):
            return
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊 Disk Analyzer", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Visualize disk usage by folder",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Drive selector card ────────────────────────────────────────────
        sel_card = Card(body)
        sel_card.pack(fill="x", pady=(0, 12))
        SectionLabel(sel_card, "Select drive").pack(anchor="w", padx=10, pady=(8, 4))

        ctrl = tk.Frame(sel_card, bg=T.PANEL)
        ctrl.pack(fill="x", padx=10, pady=(0, 10))

        tk.Label(ctrl, text="Drive:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")

        self._drive_var = tk.StringVar()
        self._drive_combo = ttk.Combobox(
            ctrl, textvariable=self._drive_var,
            state="readonly", width=45, font=T.FONT_BODY,
        )
        self._drive_combo.pack(side="left", padx=8)
        self._drive_combo.bind("<<ComboboxSelected>>", lambda e: self._on_drive_changed())

        ActionButton(ctrl, text="↻ Refresh",
                     command=self._load_drives).pack(side="left", padx=(0, 6))
        ActionButton(ctrl, text="🔍 Analyze",
                     command=self._on_analyze).pack(side="left", padx=(0, 6))

        # Drive info row (filled after dropdown selection)
        self._drive_info = tk.Label(
            sel_card, text="", bg=T.PANEL, fg=T.FG2,
            font=T.FONT_SMALL, anchor="w",
        )
        self._drive_info.pack(fill="x", padx=10, pady=(0, 8))

        # ── Progress ──────────────────────────────────────────────────────
        self._progress_frame = tk.Frame(body, bg=T.BG)
        self._progress_lbl = tk.Label(
            self._progress_frame, text="",
            bg=T.BG, fg=T.HIGHLIGHT, font=T.FONT_SMALL, anchor="w",
        )
        self._progress_lbl.pack(fill="x")
        self._progress = ProgressBar(self._progress_frame)
        self._progress.pack(fill="x", pady=(2, 8))

        # ── Results tree ──────────────────────────────────────────────────
        card = Card(body)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Folder Breakdown").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        cols = ("size", "percent")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols,
            show="tree headings", height=18,
        )
        apply_treeview_style(self._tree)
        self._tree.heading("#0",      text="Folder",       anchor="w")
        self._tree.heading("size",    text="Size",         anchor="w")
        self._tree.heading("percent", text="% of Total",   anchor="w")
        self._tree.column("#0",      width=480)
        self._tree.column("size",    width=140)
        self._tree.column("percent", width=120)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Summary
        self._summary = tk.Label(
            card, text="", bg=T.PANEL, fg=T.FG2,
            font=T.FONT_BODY, anchor="w",
        )
        self._summary.pack(anchor="w", padx=10, pady=(0, 10))

    # ── actions ───────────────────────────────────────────────────────────

    def _load_drives(self):
        """FAST: just enumerate drives via psutil — no filesystem walking."""
        if getattr(self, "_pro_gated", False):
            return  # widgets not built (Pro upsell shown instead)
        try:
            drives = da.list_drives()
        except Exception as e:
            messagebox.showerror("Error", f"Could not list drives: {e}")
            return

        self._drives = drives
        labels = [d["label"] for d in drives]
        self._drive_combo.config(values=labels)

        if labels:
            # Keep current selection if still present, else pick first
            current = self._drive_var.get()
            if current not in labels:
                self._drive_var.set(labels[0])
            self._on_drive_changed()
        else:
            self._drive_var.set("")
            self._drive_info.config(text="No drives detected.")

    def _selected_drive(self) -> dict | None:
        label = self._drive_var.get()
        for d in self._drives:
            if d["label"] == label:
                return d
        return None

    def _on_drive_changed(self):
        """Just update the info label — DON'T auto-analyze (slow)."""
        d = self._selected_drive()
        if not d:
            return
        self._drive_info.config(
            text=(f"💾 {d['drive']}  ·  {d['fstype']}  ·  "
                  f"Used: {d['used_str']} of {d['total_str']}  "
                  f"({d['percent']:.1f}%)  ·  Free: {d['free_str']}"),
            fg=T.WARNING if d['percent'] > 85 else T.FG,
        )

    def _on_analyze(self):
        if self._busy:
            return
        d = self._selected_drive()
        if not d:
            messagebox.showwarning("No drive", "Select a drive to analyze.")
            return

        self._busy = True
        self._tree.delete(*self._tree.get_children())
        self._progress_frame.pack(fill="x", pady=(0, 8))
        self._progress.set(0)
        self._progress_lbl.config(
            text=f"Scanning {d['mountpoint']} — this may take 30-120 s for large drives...")

        def progress(file_count, total_str):
            # Pulse progress bar (we don't know how many files total)
            self.after(0, lambda: self._progress_lbl.config(
                text=f"Scanned {file_count:,} files · {total_str}..."))

        def worker():
            try:
                analysis = da.analyze_folder(d["mountpoint"], progress_cb=progress)
                self.after(0, lambda: self._render(analysis))
            except Exception as e:
                self.after(0, lambda: self._show_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _render(self, analysis: dict):
        self._current_analysis = analysis
        self._tree.delete(*self._tree.get_children())

        subfolders = analysis.get("subfolders", [])
        for sub in subfolders[:100]:   # show top 100
            pct = sub.get("percent", 0)
            # Visual bar in name column
            bar = "█" * int(pct / 5) if pct > 0 else ""
            self._tree.insert(
                "", "end",
                text=f"📁 {sub['name']}",
                values=(
                    sub.get("size_str", "—"),
                    f"{pct:>5.1f}%  {bar}",
                ),
            )

        total = analysis.get("total_size_str", "—")
        n = len(subfolders)
        self._summary.config(
            text=f"✓ Total scanned: {total}   |   Top-level folders: {n}",
            fg=T.SUCCESS,
        )
        self._progress_frame.pack_forget()
        self._busy = False

    def _show_error(self, msg: str):
        messagebox.showerror("Analysis failed", msg)
        self._progress_frame.pack_forget()
        self._busy = False
