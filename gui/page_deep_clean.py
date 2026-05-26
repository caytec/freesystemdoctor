"""Deep Disk Cleaner — aggressive C: drive cleanup UI."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from .affiliate_banner import SponsoredBanner, ProUpgradePrompt
from engine import deep_disk_cleaner as ddc


class DeepCleanPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._results: list[ddc.CleanCategory] = []
        self._check_vars: dict[str, tk.BooleanVar] = {}
        self._build_ui()

    def on_activate(self):
        pass

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💾 Deep Disk Cleaner", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="22+ kategorii ukrytych plików — maksymalne odzyskanie miejsca",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        # Warning banner
        banner = tk.Frame(self, bg="#4f7ef8", height=30)
        banner.pack(fill="x")
        banner.pack_propagate(False)
        tk.Label(
            banner,
            text="⚡ Wszystkie operacje SAFE — nie tykamy gier, dokumentów, zdjęć. Backup nie wymagany.",
            bg="#4f7ef8", fg="white",
            font=(T.FONT_FAMILY, 9, "bold"),
        ).pack(expand=True)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Top toolbar
        toolbar = tk.Frame(body, bg=T.BG)
        toolbar.pack(fill="x", pady=(0, 12))

        self._scan_btn = ActionButton(
            toolbar, text="🔍 SKANUJ wszystkie kategorie",
            command=self._on_scan,
        )
        self._scan_btn.config(font=T.FONT_BOLD, pady=8)
        self._scan_btn.pack(side="left")

        self._clean_btn = ActionButton(
            toolbar, text="🧹 WYCZYŚĆ zaznaczone",
            command=self._on_clean,
        )
        self._clean_btn.config(state="disabled", font=T.FONT_BOLD, pady=8)
        self._clean_btn.pack(side="left", padx=8)

        self._summary_lbl = tk.Label(
            toolbar, text="Kliknij SKANUJ aby rozpocząć",
            bg=T.BG, fg=T.FG2, font=T.FONT_BODY,
        )
        self._summary_lbl.pack(side="left", padx=16)

        # Progress
        self._progress_frame = tk.Frame(body, bg=T.BG)
        self._progress_lbl = tk.Label(self._progress_frame, text="",
                                       bg=T.BG, fg=T.HIGHLIGHT,
                                       font=T.FONT_SMALL, anchor="w")
        self._progress_lbl.pack(fill="x")
        self._progress = ProgressBar(self._progress_frame)
        self._progress.pack(fill="x", pady=(2, 8))

        # Results area
        self._build_results(body)

        # Sponsored placement (only shows if user hasn't disabled in Settings)
        SponsoredBanner(self, page_key="deep_clean").pack(fill="x", side="bottom")

        # Bottom action row
        bottom = tk.Frame(body, bg=T.BG)
        bottom.pack(fill="x", pady=(12, 0))
        ActionButton(bottom, text="✓ Zaznacz wszystkie SAFE",
                     command=self._select_safe).pack(side="left")
        ActionButton(bottom, text="✓ Zaznacz wszystkie",
                     command=self._select_all).pack(side="left", padx=6)
        ActionButton(bottom, text="✗ Odznacz wszystkie",
                     command=self._deselect_all).pack(side="left", padx=6)

        self._total_lbl = tk.Label(
            bottom, text="", bg=T.BG, fg=T.SUCCESS,
            font=(T.FONT_FAMILY, 12, "bold"),
        )
        self._total_lbl.pack(side="right")

    def _build_results(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        # Treeview with checkboxes (simulated via tags)
        cols = ("size", "files", "risk")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings", height=20)
        apply_treeview_style(self._tv)
        self._tv.heading("#0", text="Kategoria (kliknij ✓ aby zaznaczyć)", anchor="w")
        self._tv.heading("size", text="Do odzyskania", anchor="w")
        self._tv.heading("files", text="Pliki", anchor="w")
        self._tv.heading("risk", text="Ryzyko", anchor="w")
        self._tv.column("#0", width=380)
        self._tv.column("size", width=140)
        self._tv.column("files", width=80)
        self._tv.column("risk", width=110)

        self._tv.tag_configure("safe", foreground=T.SUCCESS)
        self._tv.tag_configure("medium", foreground=T.WARNING)
        self._tv.tag_configure("reversible", foreground=T.HIGHLIGHT)
        self._tv.tag_configure("checked", background=T.lerp_color(T.PANEL, T.HIGHLIGHT, 0.15))

        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", pady=8, padx=(0, 8))

        # Click handler for toggle
        self._tv.bind("<Button-1>", self._on_row_click)

    # ── actions ───────────────────────────────────────────────────────────────

    def _on_scan(self):
        if self._busy:
            return
        self._busy = True
        self._scan_btn.config(state="disabled")
        self._clean_btn.config(state="disabled")
        self._clear_results()
        self._progress_frame.pack(fill="x", pady=(0, 12))
        self._progress.set(0)
        self._progress_lbl.config(text="Skanowanie 22 kategorii (DISM może zająć ~30s)...")

        def progress(pct: int, msg: str):
            self.after(0, lambda: (self._progress.set(pct),
                                    self._progress_lbl.config(text=msg)))

        def worker():
            results = ddc.scan_all(progress_cb=progress)
            self.after(0, lambda: self._scan_done(results))

        threading.Thread(target=worker, daemon=True).start()

    def _scan_done(self, results: list[ddc.CleanCategory]):
        self._results = results
        self._progress_frame.pack_forget()
        self._busy = False
        self._scan_btn.config(state="normal")

        # Render results
        self._render_results()

        total_potential = sum(r.size_bytes for r in results)
        n_with_data = sum(1 for r in results if r.size_bytes > 0)
        self._summary_lbl.config(
            text=f"Znaleziono {n_with_data} kategorii do wyczyszczenia",
            fg=T.SUCCESS if n_with_data > 0 else T.FG2,
        )
        self._total_lbl.config(
            text=f"Potencjalny zysk: {ddc._fmt(total_potential)}",
            fg=T.SUCCESS,
        )

        # Auto-select all SAFE by default
        self._select_safe()

    def _render_results(self):
        for r in self._results:
            # Sort by size descending
            pass
        # Sort
        sorted_results = sorted(self._results, key=lambda r: r.size_bytes, reverse=True)

        for r in sorted_results:
            checked = "☐"  # default unchecked
            risk_text = {
                "safe": "✓ Safe",
                "medium": "⚠ Medium",
                "reversible": "↺ Reversible",
            }.get(r.risk, r.risk)

            self._tv.insert(
                "", "end",
                iid=r.key,
                text=f"{checked}  {r.label}",
                values=(
                    ddc._fmt(r.size_bytes) if r.size_bytes > 0 else "—",
                    f"{r.file_count:,}" if r.file_count > 0 else "—",
                    risk_text,
                ),
                tags=(r.risk,),
            )

    def _on_row_click(self, event):
        item = self._tv.identify_row(event.y)
        if not item:
            return
        # Only toggle if click on first column area
        col = self._tv.identify_column(event.x)
        if col != "#0":
            return
        self._toggle_row(item)

    def _toggle_row(self, key: str):
        cat = next((r for r in self._results if r.key == key), None)
        if not cat:
            return
        cat.enabled = not cat.enabled
        checkbox = "☑" if cat.enabled else "☐"
        current_text = self._tv.item(key, "text")
        # Replace first 2 chars (checkbox)
        new_text = checkbox + current_text[1:]
        tags = list(self._tv.item(key, "tags"))
        if cat.enabled and "checked" not in tags:
            tags.append("checked")
        elif not cat.enabled and "checked" in tags:
            tags.remove("checked")
        self._tv.item(key, text=new_text, tags=tags)
        self._update_clean_button()

    def _select_safe(self):
        for r in self._results:
            r.enabled = (r.risk == "safe" and r.size_bytes > 0)
        self._refresh_checkboxes()
        self._update_clean_button()

    def _select_all(self):
        for r in self._results:
            r.enabled = r.size_bytes > 0
        self._refresh_checkboxes()
        self._update_clean_button()

    def _deselect_all(self):
        for r in self._results:
            r.enabled = False
        self._refresh_checkboxes()
        self._update_clean_button()

    def _refresh_checkboxes(self):
        for r in self._results:
            try:
                checkbox = "☑" if r.enabled else "☐"
                text = self._tv.item(r.key, "text")
                new_text = checkbox + text[1:]
                tags = list(self._tv.item(r.key, "tags"))
                if r.enabled and "checked" not in tags:
                    tags.append("checked")
                elif not r.enabled and "checked" in tags:
                    tags.remove("checked")
                self._tv.item(r.key, text=new_text, tags=tags)
            except tk.TclError:
                pass

    def _update_clean_button(self):
        selected = [r for r in self._results if r.enabled and r.size_bytes > 0]
        total = sum(r.size_bytes for r in selected)
        if total > 0:
            self._clean_btn.config(state="normal")
            self._total_lbl.config(
                text=f"Zaznaczono: {ddc._fmt(total)} ({len(selected)} kategorii)",
                fg=T.SUCCESS,
            )
        else:
            self._clean_btn.config(state="disabled")
            self._total_lbl.config(text="")

    def _clear_results(self):
        for item in self._tv.get_children():
            self._tv.delete(item)
        self._results = []
        self._total_lbl.config(text="")

    def _on_clean(self):
        if self._busy:
            return
        selected = [r for r in self._results if r.enabled]
        if not selected:
            return

        total = sum(r.size_bytes for r in selected)
        has_risky = any(r.risk != "safe" for r in selected)
        warning = ""
        if has_risky:
            warning = "\n\n⚠ Wybrane kategorie zawierają operacje 'reversible' lub 'medium ryzyko'.\n" \
                      "Hibernacja zostanie wyłączona / WinSxS zostanie skompaktowany / restore points usunięte."

        if not messagebox.askyesno(
            "Potwierdź czyszczenie",
            f"Wyczyścić {len(selected)} kategorii?\n\n"
            f"Łącznie do odzyskania: {ddc._fmt(total)}{warning}",
        ):
            return

        self._busy = True
        self._scan_btn.config(state="disabled")
        self._clean_btn.config(state="disabled")
        self._progress_frame.pack(fill="x", pady=(0, 12))
        self._progress.set(0)
        self._progress_lbl.config(text="Startuje czyszczenie...")

        def progress(pct: int, msg: str):
            self.after(0, lambda: (self._progress.set(pct),
                                    self._progress_lbl.config(text=msg)))

        def worker():
            stats = ddc.clean_selected(selected, progress_cb=progress)
            self.after(0, lambda: self._clean_done(stats))

        threading.Thread(target=worker, daemon=True).start()

    def _clean_done(self, stats: dict):
        self._progress_frame.pack_forget()
        self._busy = False
        self._scan_btn.config(state="normal")

        # Update tree with results
        for result in stats["results"]:
            key = result["key"]
            if not result["ok"]:
                continue
            try:
                self._tv.item(
                    key,
                    text="✓  " + self._tv.item(key, "text")[2:],
                    values=(
                        f"✓ {result['freed_human']}",
                        f"{result['items']:,}",
                        "Done",
                    ),
                    tags=("safe",),
                )
            except tk.TclError:
                pass

        self._summary_lbl.config(
            text=f"✓ Wyczyszczono {stats['total_freed_human']} ({stats['items_deleted']:,} plików)",
            fg=T.SUCCESS,
        )
        self._total_lbl.config(text="")

        # Big success dialog
        messagebox.showinfo(
            "Deep Clean zakończony",
            f"💾 Odzyskano: {stats['total_freed_human']}\n"
            f"📁 Usunięto: {stats['items_deleted']:,} plików\n\n"
            f"Możesz teraz uruchomić nowy skan żeby zobaczyć aktualny stan.",
        )

        # Pro upsell — gated by smart trigger (only after big wins, with
        # cooldown). Falls back gracefully if module is missing.
        try:
            from . import pro_upsell_smart
            gb_freed = stats.get("total_freed_bytes", 0) / (1024 ** 3)
            if pro_upsell_smart.should_show_post_clean(gb_freed):
                ProUpgradePrompt(self._app, context="post-clean").pack(
                    fill="x", side="bottom", padx=16, pady=(0, 12))
        except Exception:
            pass
