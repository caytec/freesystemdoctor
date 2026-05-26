"""Game Booster page — Arena Breakout Infinite ANTI-CHEAT SAFE profile."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import game_booster as gb


class GameBoosterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()

    def on_activate(self):
        self._refresh_status()
        self._start_auto_refresh()

    def _start_auto_refresh(self):
        try:
            self._refresh_status()
        except Exception:
            pass
        try:
            self.after(3000, self._start_auto_refresh)
        except tk.TclError:
            pass

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🎮 Game Booster", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Arena Breakout Infinite — profil optymalizacji",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        # 🛡️ Anti-cheat safety banner (always visible at top)
        banner = tk.Frame(self, bg=T.SUCCESS, height=36)
        banner.pack(fill="x")
        banner.pack_propagate(False)
        tk.Label(
            banner,
            text="🛡️  ANTI-CHEAT SAFE MODE  —  zero modyfikacji plików gry / procesu gry / pamięci gry",
            bg=T.SUCCESS, fg="#0a1f0a",
            font=(T.FONT_FAMILY, 9, "bold"),
        ).pack(expand=True)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        left = tk.Frame(body, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = tk.Frame(body, bg=T.BG, width=340)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        self._build_status_card(left)
        self._build_log_card(left)
        self._build_action_panel(right)
        self._build_ingame_settings_card(right)

    # ── status card ───────────────────────────────────────────────────────────

    def _build_status_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Status").pack(anchor="w", padx=10, pady=(8, 4))

        grid = tk.Frame(card, bg=T.PANEL)
        grid.pack(fill="x", padx=10, pady=(0, 10))

        self._status_labels = {}
        for i, (key, label) in enumerate([
            ("installed",   "Gra wykryta:"),
            ("running",     "Gra uruchomiona:"),
            ("process",     "Proces gry:"),
            ("boost",       "Boost aktywny:"),
            ("config_dir",  "Folder konfiguracji:"),
        ]):
            tk.Label(grid, text=label, bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_BODY, anchor="w").grid(row=i, column=0, sticky="w", pady=2)
            v = tk.Label(grid, text="—", bg=T.PANEL, fg=T.FG,
                         font=T.FONT_BOLD, anchor="w")
            v.grid(row=i, column=1, sticky="w", padx=10, pady=2)
            self._status_labels[key] = v

        grid.grid_columnconfigure(1, weight=1)

        det_row = tk.Frame(card, bg=T.PANEL)
        det_row.pack(fill="x", padx=10, pady=(0, 10))
        ActionButton(det_row, text="🔍 Wykryj proces gry",
                     command=self._on_detect_game).pack(side="left")
        ActionButton(det_row, text="↻ Odśwież status",
                     command=self._refresh_status).pack(side="left", padx=6)

    # ── log card ──────────────────────────────────────────────────────────────

    def _build_log_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, "Wynik optymalizacji").pack(anchor="w", padx=10, pady=8)

        cols = ("Status", "Detail")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings", height=10)
        apply_treeview_style(self._tv)
        self._tv.heading("#0", text="Krok", anchor="w")
        self._tv.heading("Status", text="Status", anchor="w")
        self._tv.heading("Detail", text="Szczegóły", anchor="w")
        self._tv.column("#0", width=240)
        self._tv.column("Status", width=80)
        self._tv.column("Detail", width=300)
        self._tv.tag_configure("ok",   foreground=T.SUCCESS)
        self._tv.tag_configure("fail", foreground=T.DANGER)
        self._tv.tag_configure("info", foreground=T.HIGHLIGHT)

        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

    # ── action panel (right column) ───────────────────────────────────────────

    def _build_action_panel(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Pełen boost (safe)").pack(anchor="w", padx=10, pady=(8, 4))

        tk.Label(card,
                 text="Stosuje TYLKO system-level optymalizacje Windows.\n"
                      "Plik gry, proces gry i pamięć gry pozostają NIETKNIĘTE.\n\n"
                      "• Power plan: Ultimate Performance\n"
                      "• Wyłączenie Game Bar / DVR\n"
                      "• HAGS (Hardware GPU Scheduling)\n"
                      "• Timer 1 ms\n"
                      "• Niskolatencyjny TCP\n"
                      "• Visual effects: performance\n"
                      "• Kill 15+ procesów w tle\n"
                      "• Trim pamięci innych procesów\n"
                      "• Watchdog DETECTION-ONLY (czyta status, nie modyfikuje)",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 justify="left", anchor="w", wraplength=310).pack(
            anchor="w", padx=10, pady=(0, 8))

        self._boost_btn = ActionButton(
            card, text="🛡️ APPLY SAFE BOOST",
            command=self._on_boost,
        )
        self._boost_btn.config(font=T.FONT_BOLD, pady=10)
        self._boost_btn.pack(fill="x", padx=10, pady=(0, 8))

        self._progress_lbl = tk.Label(card, text="", bg=T.PANEL,
                                      fg=T.HIGHLIGHT, font=T.FONT_SMALL,
                                      anchor="w")
        self._progress_lbl.pack(fill="x", padx=10)
        self._progress = ProgressBar(card)
        self._progress.pack(fill="x", padx=10, pady=(2, 10))

        # Revert
        card2 = Card(parent)
        card2.pack(fill="x", pady=(0, 12))
        SectionLabel(card2, "Cofnij").pack(anchor="w", padx=10, pady=(8, 4))
        tk.Label(card2,
                 text="Przywraca power plan, visual effects i klucze rejestru.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 justify="left", anchor="w", wraplength=310).pack(
            anchor="w", padx=10, pady=(0, 8))
        ActionButton(card2, text="↩ Przywróć ustawienia",
                     command=self._on_revert).pack(fill="x", padx=10, pady=(0, 10))

        # Quick actions
        card3 = Card(parent)
        card3.pack(fill="x", pady=(0, 12))
        SectionLabel(card3, "Szybkie akcje").pack(anchor="w", padx=10, pady=(8, 4))
        ActionButton(card3, text="Zabij procesy w tle",
                     command=self._on_kill_bloat).pack(fill="x", padx=10, pady=2)
        ActionButton(card3, text="Trim pamięci (poza grą)",
                     command=self._on_trim_memory).pack(fill="x", padx=10, pady=(2, 10))

    # ── recommended in-game settings card ─────────────────────────────────────

    def _build_ingame_settings_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "📋 Ustawienia w grze").pack(anchor="w", padx=10, pady=(8, 4))

        tk.Label(card,
                 text="Zastosuj te ustawienia ręcznie w grze.\n"
                      "Gra sama zapisze swój config — nie tykamy plików.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 justify="left", anchor="w", wraplength=310).pack(
            anchor="w", padx=10, pady=(0, 8))

        for label, value in gb.RECOMMENDED_INGAME_SETTINGS:
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text="• " + label, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_SMALL, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=T.PANEL, fg=T.HIGHLIGHT,
                     font=(T.FONT_FAMILY, 9, "bold"),
                     anchor="e", wraplength=180, justify="right").pack(side="right")

        tk.Frame(card, bg=T.PANEL, height=10).pack()

    # ── actions ───────────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool):
        self._busy = busy
        try:
            self._boost_btn.config(state="disabled" if busy else "normal")
        except Exception:
            pass

    def _refresh_status(self):
        cfg = gb.find_game_config_dir()
        self._status_labels["installed"].config(
            text="Tak ✓" if cfg else "Nie wykryto",
            fg=T.SUCCESS if cfg else T.WARNING,
        )

        running = gb.find_running_game()
        if running:
            self._status_labels["running"].config(
                text=f"Tak — PID {running['pid']} ✓", fg=T.SUCCESS,
            )
            self._status_labels["process"].config(
                text=running["name"], fg=T.HIGHLIGHT,
            )
        else:
            self._status_labels["running"].config(text="Nie", fg=T.FG2)
            override = gb._DETECTED_PROCESS or "—"
            self._status_labels["process"].config(text=override, fg=T.FG2)

        self._status_labels["boost"].config(
            text="Aktywny ✓" if gb.is_boost_active() else "Nieaktywny",
            fg=T.SUCCESS if gb.is_boost_active() else T.FG2,
        )
        self._status_labels["config_dir"].config(
            text=str(cfg) if cfg else "—",
            fg=T.FG if cfg else T.FG2,
        )

    def _on_detect_game(self):
        candidates = gb.scan_for_game_candidates()
        if not candidates:
            messagebox.showinfo(
                "Wykrywanie",
                "Nie znaleziono kandydatów. Uruchom Arena Breakout Infinite\n"
                "i spróbuj ponownie.",
            )
            return

        dlg = tk.Toplevel(self)
        dlg.title("Wybierz proces gry")
        dlg.configure(bg=T.BG)
        dlg.geometry("640x420")
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg,
                 text="Wybierz proces gry. Watchdog będzie go tylko OBSERWOWAĆ "
                      "(nie modyfikuje):",
                 bg=T.BG, fg=T.FG, font=T.FONT_BODY,
                 anchor="w").pack(fill="x", padx=14, pady=(14, 6))

        cols = ("PID", "Score", "Path")
        tv = ttk.Treeview(dlg, columns=cols, show="tree headings", height=14)
        apply_treeview_style(tv)
        tv.heading("#0", text="Nazwa procesu", anchor="w")
        tv.heading("PID", text="PID", anchor="w")
        tv.heading("Score", text="Trafność", anchor="w")
        tv.heading("Path", text="Ścieżka", anchor="w")
        tv.column("#0", width=200)
        tv.column("PID", width=70)
        tv.column("Score", width=80)
        tv.column("Path", width=270)

        for c in candidates:
            tv.insert("", "end", text=c["name"],
                      values=(c["pid"], c["score"], c["exe"][:60]))

        children = tv.get_children()
        if children:
            tv.selection_set(children[0])
        tv.pack(fill="both", expand=True, padx=14, pady=4)

        btn_row = tk.Frame(dlg, bg=T.BG)
        btn_row.pack(fill="x", padx=14, pady=12)

        def confirm():
            sel = tv.selection()
            if not sel:
                return
            row = tv.item(sel[0])
            name = row["text"]
            gb.set_detected_process(name)
            dlg.destroy()
            messagebox.showinfo(
                "Wykryto",
                f"Watchdog będzie OBSERWOWAĆ proces:\n{name}\n\n"
                f"(detection-only — nie modyfikuje go w żaden sposób)",
            )
            self._refresh_status()

        ActionButton(btn_row, text="✓ Użyj wybranego procesu",
                     command=confirm).pack(side="left")
        ActionButton(btn_row, text="Anuluj",
                     command=dlg.destroy).pack(side="left", padx=8)

    def _clear_log(self):
        for child in self._tv.get_children():
            self._tv.delete(child)

    def _add_log(self, step: str, ok: bool, detail: str):
        tag = "ok" if ok else "fail"
        status = "✓" if ok else "✗"
        self._tv.insert("", "end", text=step, values=(status, detail), tags=(tag,))

    def _on_boost(self):
        if self._busy:
            return
        if not messagebox.askyesno(
            "Safe Boost",
            "Aplikuję ANTI-CHEAT SAFE optymalizacje:\n\n"
            "• Wszystko system-level (Windows, sieć, GPU scheduling)\n"
            "• ŻADNYCH modyfikacji plików gry\n"
            "• ŻADNYCH modyfikacji procesu gry\n"
            "• Watchdog tylko obserwuje status gry\n\n"
            "Wszystkie zmiany odwracalne. Kontynuować?"
        ):
            return

        self._set_busy(True)
        self._clear_log()
        self._progress.set(0)
        self._progress_lbl.config(text="Startuję…")

        def progress(pct: int, msg: str):
            self.after(0, lambda: (self._progress.set(pct),
                                    self._progress_lbl.config(text=msg)))

        def worker():
            results = gb.apply_all_safe(progress_cb=progress)
            self.after(0, lambda: self._boost_done(results))

        threading.Thread(target=worker, daemon=True).start()

    def _boost_done(self, results: dict):
        for step, (ok, detail) in results.items():
            self._add_log(step, ok, detail)
        self._progress.set(100)
        self._progress_lbl.config(text="✓ Safe boost aktywny")
        self._set_busy(False)
        self._refresh_status()

        ok_count = sum(1 for ok, _ in results.values() if ok)
        messagebox.showinfo(
            "Safe Boost zakończony",
            f"Zastosowano {ok_count}/{len(results)} optymalizacji.\n\n"
            f"🛡️ Anti-cheat safe — nie tykamy plików ani procesu gry.\n\n"
            f"Po uruchomieniu gry zastosuj rekomendowane ustawienia\n"
            f"w grze (panel po prawej) ręcznie przez menu gry.",
        )

    def _on_revert(self):
        if not messagebox.askyesno(
            "Cofnij",
            "Przywrócić oryginalne ustawienia Windows?"
        ):
            return
        self._clear_log()
        results = gb.revert_all()
        for step, (ok, detail) in results.items():
            self._add_log(step, ok, detail)
        self._refresh_status()
        messagebox.showinfo("Gotowe", "Ustawienia przywrócone.")

    def _on_kill_bloat(self):
        n, killed = gb.kill_background_bloat()
        self._clear_log()
        self._add_log("Kill background bloat", n > 0,
                      f"{n} procesów (gra/ACE/system pominięte): "
                      f"{', '.join(killed[:10])}")

    def _on_trim_memory(self):
        ok, msg = gb.trim_memory_before_launch()
        self._clear_log()
        self._add_log("Trim pamięci", ok, msg)
