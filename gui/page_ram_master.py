"""RAM Master — the memory page other optimizers don't have.

Live memory composition (in use / modified / standby / free), a staged deep
clean that reports the MB each technique actually freed, an opt-in standby
auto-policy, and the memory tweaks nobody exposes (compression, pagefile).
"""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, PageHeader, ProgressBar
from engine import ram_master as rm


_RISK_COLOR = {"low": T.SUCCESS, "medium": T.WARNING, "high": T.DANGER}

# composition segment → (label, colour)
_SEGMENTS = (
    ("in_use_mb",   "In use",   T.HIGHLIGHT),
    ("modified_mb", "Modified", T.WARNING),
    ("standby_mb",  "Standby",  T.PURPLE),
    ("free_mb",     "Free",     T.SUCCESS),
)


class RamMasterPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._build_ui()

    # ── layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        PageHeader(self, title="RAM Master",
                   subtitle="Deep memory cleaning with measured proof",
                   icon="🧠", color=T.PURPLE).pack(fill="x")

        outer = tk.Frame(self, bg=T.BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=T.BG, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=T.BG)
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw", width=880)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True, padx=16, pady=12)
        sb.pack(side="right", fill="y")

        self._build_composition(body)
        self._build_clean(body)
        self._build_policy(body)
        self._build_tweaks(body)

    # ── composition bar ─────────────────────────────────────────────────────
    def _build_composition(self, parent):
        card = Card(parent, glow=True)
        card.pack(fill="x", pady=(0, 12))

        head = tk.Frame(card, bg=T.PANEL)
        head.pack(fill="x", padx=16, pady=(12, 2))
        SectionLabel(head, "🧠 Live memory composition").pack(side="left")
        ActionButton(head, text="Refresh", width=110,
                     command=self._refresh_composition).pack(side="right")

        tk.Label(card,
                 text="Standby is cached data Windows kept in case you need it "
                      "again — it counts as \"used\" in Task Manager but can be "
                      "reclaimed instantly. No other optimizer shows you this.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=780).pack(fill="x", padx=16)

        self._bar = tk.Canvas(card, height=34, bg=T.BG, highlightthickness=0)
        self._bar.pack(fill="x", padx=16, pady=(10, 6))
        self._bar.bind("<Configure>", lambda e: self._draw_bar())

        self._legend = tk.Frame(card, bg=T.PANEL)
        self._legend.pack(fill="x", padx=16, pady=(0, 12))

        self._comp = {}

    def _draw_bar(self):
        c = self._bar
        c.delete("all")
        comp = self._comp
        total = comp.get("total_mb") or 0
        w = c.winfo_width() or 800
        h = 34
        if not total:
            c.create_text(w // 2, h // 2, text="Not measured yet",
                          fill=T.FG2, font=T.FONT_SMALL)
            return
        x = 0
        for key, label, colour in _SEGMENTS:
            val = comp.get(key)
            if not val:
                continue
            seg_w = max(1, int(w * (val / total)))
            c.create_rectangle(x, 0, x + seg_w, h, fill=colour, outline="")
            if seg_w > 54:
                c.create_text(x + seg_w // 2, h // 2,
                              text=f"{val:,} MB", fill="#0a1020",
                              font=(T.FONT_FAMILY, 8, "bold"))
            x += seg_w

    def _render_legend(self):
        for w in self._legend.winfo_children():
            w.destroy()
        comp = self._comp
        for key, label, colour in _SEGMENTS:
            val = comp.get(key)
            cell = tk.Frame(self._legend, bg=T.PANEL)
            cell.pack(side="left", padx=(0, 18))
            tk.Label(cell, text="■", bg=T.PANEL, fg=colour,
                     font=(T.FONT_FAMILY, 10)).pack(side="left")
            txt = f" {label}: " + (f"{val:,} MB" if val is not None else "n/a")
            tk.Label(cell, text=txt, bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL).pack(side="left")
        if comp.get("standby_mb") is None:
            tk.Label(self._legend,
                     text="  (standby/modified need performance counters)",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_MICRO).pack(side="left")

    # ── deep clean ──────────────────────────────────────────────────────────
    def _build_clean(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Deep RAM clean").pack(anchor="w", padx=16,
                                                  pady=(12, 2))
        tk.Label(card,
                 text="Runs each technique in turn and measures what it freed "
                      "separately — so you can see which one did the work. "
                      "The native memory-list calls need administrator rights.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=780).pack(fill="x", padx=16)

        btns = tk.Frame(card, bg=T.PANEL)
        btns.pack(fill="x", padx=16, pady=(10, 4))
        ActionButton(btns, text="🧹 Deep clean", width=150,
                     command=lambda: self._clean("deep")).pack(side="left",
                                                               padx=(0, 8))
        ActionButton(btns, text="Normal", width=110, secondary=True,
                     command=lambda: self._clean("normal")).pack(side="left",
                                                                 padx=(0, 8))
        ActionButton(btns, text="Quick", width=110, secondary=True,
                     command=lambda: self._clean("quick")).pack(side="left")

        self._prog = ProgressBar(card)
        self._prog.pack(fill="x", padx=16, pady=(6, 4))
        self._clean_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                      font=T.FONT_SMALL, anchor="w")
        self._clean_status.pack(fill="x", padx=16)
        self._results = tk.Frame(card, bg=T.PANEL)
        self._results.pack(fill="x", padx=16, pady=(4, 14))

    def _render_results(self, rep: dict):
        for w in self._results.winfo_children():
            w.destroy()
        total = rep.get("total_freed_mb", 0)
        head = tk.Frame(self._results, bg=T.PANEL)
        head.pack(fill="x", pady=(4, 6))
        tk.Label(head, text=f"+{total:,} MB", bg=T.PANEL,
                 fg=T.SUCCESS if total > 0 else T.FG2,
                 font=(T.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(head, text=f"  freed  ·  {rep.get('before_mb', 0):,} → "
                            f"{rep.get('after_mb', 0):,} MB available",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left",
                                                               pady=(8, 0))
        for s in rep.get("stages", []):
            row = tk.Frame(self._results, bg=T.PANEL)
            row.pack(fill="x", pady=1)
            ok = s["ok"]
            tk.Label(row, text="✓" if ok else "✗", bg=T.PANEL,
                     fg=T.SUCCESS if ok else T.FG2,
                     font=T.FONT_SMALL, width=2).pack(side="left")
            tk.Label(row, text=s["label"], bg=T.PANEL, fg=T.FG,
                     font=T.FONT_SMALL, width=34, anchor="w").pack(side="left")
            if ok:
                tk.Label(row, text=f"+{s['freed_mb']:,} MB", bg=T.PANEL,
                         fg=T.SUCCESS if s["freed_mb"] else T.FG2,
                         font=T.FONT_SMALL, width=12,
                         anchor="w").pack(side="left")
            else:
                tk.Label(row, text=s["msg"][:60], bg=T.PANEL, fg=T.WARNING,
                         font=T.FONT_MICRO, anchor="w").pack(side="left")

    # ── auto policy ─────────────────────────────────────────────────────────
    def _build_policy(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Automatic standby cleaning").pack(
            anchor="w", padx=16, pady=(12, 2))
        tk.Label(card,
                 text="Standby memory is a disk cache, so purging it constantly "
                      "makes things slower, not faster. Off by default; when on, "
                      "it only fires under real pressure — little free RAM AND a "
                      "large standby list worth reclaiming.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, anchor="w",
                 justify="left", wraplength=780).pack(fill="x", padx=16)

        self._policy_var = tk.BooleanVar(value=False)
        tk.Checkbutton(card, text="Enable automatic standby cleaning",
                       variable=self._policy_var, bg=T.PANEL, fg=T.FG,
                       activebackground=T.PANEL, activeforeground=T.FG,
                       selectcolor=T.BG, font=T.FONT_SMALL,
                       command=self._save_policy).pack(anchor="w", padx=16,
                                                       pady=(8, 2))

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=16, pady=(0, 4))
        tk.Label(row, text="Purge when free RAM is below", bg=T.PANEL,
                 fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
        self._free_below = tk.Spinbox(row, from_=128, to=8192, increment=128,
                                      width=6, bg=T.ACCENT, fg=T.FG,
                                      buttonbackground=T.PANEL,
                                      relief="flat", font=T.FONT_SMALL,
                                      command=self._save_policy)
        self._free_below.pack(side="left", padx=6)
        tk.Label(row, text="MB  and standby is above", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")
        self._standby_above = tk.Spinbox(row, from_=128, to=16384,
                                         increment=128, width=6, bg=T.ACCENT,
                                         fg=T.FG, buttonbackground=T.PANEL,
                                         relief="flat", font=T.FONT_SMALL,
                                         command=self._save_policy)
        self._standby_above.pack(side="left", padx=6)
        tk.Label(row, text="MB", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")

        self._policy_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                       font=T.FONT_MICRO, anchor="w")
        self._policy_status.pack(fill="x", padx=16, pady=(0, 14))

    def _save_policy(self):
        try:
            from engine import ram_daemon
            ram_daemon.daemon.save_policy(
                self._policy_var.get(),
                int(self._free_below.get()),
                int(self._standby_above.get()))
            self._policy_status.config(
                text="Saved." if self._policy_var.get()
                else "Automatic cleaning is off.")
        except Exception as e:
            self._policy_status.config(text=f"Could not save: {e}")

    def _load_policy(self):
        try:
            from engine import ram_daemon
            d = ram_daemon.daemon
            self._policy_var.set(d.standby_policy_enabled)
            self._free_below.delete(0, "end")
            self._free_below.insert(0, str(d.standby_free_below_mb))
            self._standby_above.delete(0, "end")
            self._standby_above.insert(0, str(d.standby_above_mb))
            if d.standby_purge_count:
                self._policy_status.config(
                    text=f"{d.standby_purge_count} automatic purge(s) so far; "
                         f"last freed {d.last_standby_freed_mb} MB.")
        except Exception:
            pass

    # ── tweaks ──────────────────────────────────────────────────────────────
    def _build_tweaks(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 16))
        SectionLabel(card, "Memory tweaks").pack(anchor="w", padx=16,
                                                 pady=(12, 2))
        tk.Label(card,
                 text="Backed up before the first change and individually "
                      "revertible.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 anchor="w").pack(fill="x", padx=16)
        self._tweak_host = tk.Frame(card, bg=T.PANEL)
        self._tweak_host.pack(fill="x", padx=16, pady=(6, 14))
        tk.Label(self._tweak_host, text="Reading current settings…",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

    def _render_tweaks(self, tweaks):
        for w in self._tweak_host.winfo_children():
            w.destroy()
        if not tweaks:
            tk.Label(self._tweak_host,
                     text="No memory tweaks available on this system.",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")
            return
        for t in tweaks:
            row = tk.Frame(self._tweak_host, bg=T.PANEL)
            row.pack(fill="x", pady=4)
            top = tk.Frame(row, bg=T.PANEL)
            top.pack(fill="x")
            state = t.get("optimized")
            tk.Label(top, text="●" if state else "○", bg=T.PANEL,
                     fg=T.SUCCESS if state else T.FG2,
                     font=(T.FONT_FAMILY, 12)).pack(side="left", padx=(0, 6))
            tk.Label(top, text=t["name"], bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BOLD).pack(side="left")
            tk.Label(top, text=f"  [{t['risk']} risk]", bg=T.PANEL,
                     fg=_RISK_COLOR.get(t["risk"], T.FG2),
                     font=T.FONT_MICRO).pack(side="left")
            if t.get("reboot"):
                tk.Label(top, text="  needs reboot", bg=T.PANEL, fg=T.FG2,
                         font=T.FONT_MICRO).pack(side="left")

            btns = tk.Frame(top, bg=T.PANEL)
            btns.pack(side="right")
            if t.get("_locked"):
                tk.Label(btns, text="needs administrator", bg=T.PANEL,
                         fg=T.WARNING, font=T.FONT_SMALL).pack(side="left")
            elif state:
                tk.Label(btns, text="✓ active", bg=T.PANEL, fg=T.SUCCESS,
                         font=T.FONT_SMALL).pack(side="left", padx=(0, 8))
                ActionButton(btns, text="Revert", width=90, secondary=True,
                             command=lambda i=t["id"]: self._revert(i)
                             ).pack(side="left")
            else:
                ActionButton(btns, text="Apply", width=90,
                             command=lambda i=t["id"], n=t["name"],
                             r=t["risk"]: self._apply(i, n, r)
                             ).pack(side="left")

            tk.Label(row, text=t["desc"], bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, anchor="w", justify="left",
                     wraplength=760).pack(fill="x", padx=(22, 0))
            tk.Label(row, text=f"→ {t['impact']}", bg=T.PANEL,
                     fg=T.lerp_color(T.FG2, T.HIGHLIGHT, 0.5),
                     font=T.FONT_MICRO, anchor="w").pack(fill="x", padx=(22, 0))

    # ── actions ─────────────────────────────────────────────────────────────
    def _clean(self, level: str):
        if self._busy:
            return
        self._busy = True
        self._prog.set(0)
        self._clean_status.config(text="Starting…")

        def progress(msg, pct):
            self.after(0, lambda: (self._clean_status.config(text=str(msg)),
                                   self._prog.set(int(pct))))

        def work():
            try:
                rep = rm.deep_clean(level, progress_cb=progress)
                self.after(0, self._clean_done, rep)
            except Exception as e:
                self.after(0, lambda: self._clean_status.config(
                    text=f"Error: {e}", fg=T.DANGER))
            finally:
                self._busy = False

        threading.Thread(target=work, daemon=True).start()

    def _clean_done(self, rep: dict):
        self._render_results(rep)
        self._clean_status.config(
            text=f"Finished — {rep['total_freed_mb']:,} MB freed.", fg=T.FG2)
        self._refresh_composition()

    def _apply(self, tweak_id: str, name: str, risk: str):
        if self._busy:
            return
        warn = ""
        if tweak_id == "pagefile":
            warn = ("\n\nThis writes a fixed pagefile size and takes effect "
                    "after a reboot.")
        if not messagebox.askyesno(
                f"Apply: {name}?",
                f"Apply this tweak?{warn}\n\nBacked up first — revertible from "
                f"this page at any time."):
            return
        self._busy = True

        def work():
            try:
                if risk != "low":
                    try:
                        from engine import system_restore
                        system_restore.ensure_checkpoint(f"RAM Master: {name}")
                    except Exception:
                        pass
                ok, msg = rm.apply_tweak(tweak_id)
                self.after(0, self._done, ok, msg)
            except Exception as e:
                self.after(0, self._done, False, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _revert(self, tweak_id: str):
        if self._busy:
            return
        self._busy = True

        def work():
            try:
                ok, msg = rm.revert_tweak(tweak_id)
                self.after(0, self._done, ok, msg)
            except Exception as e:
                self.after(0, self._done, False, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, ok: bool, msg: str):
        self._busy = False
        messagebox.showinfo("Done" if ok else "Not applied", msg)
        self._refresh_tweaks()

    # ── refresh ─────────────────────────────────────────────────────────────
    def _refresh_composition(self):
        def work():
            try:
                comp = rm.get_memory_composition()
                self.after(0, self._apply_composition, comp)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _apply_composition(self, comp: dict):
        self._comp = comp
        self._draw_bar()
        self._render_legend()

    def _refresh_tweaks(self):
        def work():
            try:
                tweaks = rm.get_tweaks()
                self.after(0, self._render_tweaks, tweaks)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def on_activate(self):
        self._load_policy()
        self._refresh_composition()
        self._refresh_tweaks()
