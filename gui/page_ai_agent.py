"""AI Agent page — multi-provider LLM analysis with Anthropic support."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
import os

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar
from engine import ai_agent


# API metadata: (display_name, env_key, env_model, default_model, signup_url)
_APIS = [
    ("Anthropic",  "ANTHROPIC_API_KEY",  "ANTHROPIC_MODEL",
     "claude-haiku-4-5-20251001",         "https://console.anthropic.com/"),
    ("Cerebras",   "CEREBRAS_API_KEY",   "CEREBRAS_MODEL",
     "qwen-3-235b-a22b-instruct-2507",    "https://console.cerebras.ai/keys"),
    ("Groq",       "GROQ_API_KEY",       "GROQ_MODEL",
     "llama-3.3-70b-versatile",           "https://console.groq.com/keys"),
    ("OpenRouter", "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
     "meta-llama/llama-3.2-3b-instruct:free", "https://openrouter.ai"),
]


class AIAgentPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app       = app_ref
        self._analyzing = False
        self._build_ui()

    def on_activate(self):
        self._refresh_api_status()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🤖  AI Agent", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="AI-powered system health analysis",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
        ActionButton(hdr, "Configure APIs", command=self._open_config
                     ).pack(side="right", padx=6)
        ActionButton(hdr, "Analyze Now", command=self._start_analysis
                     ).pack(side="right", padx=12)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=10)

        # ── top row: config status + score ───────────────────────────────────
        top = tk.Frame(body, bg=T.BG)
        top.pack(fill="x", pady=(0, 10))

        # API config card
        cfg_card = Card(top)
        cfg_card.pack(side="left", fill="y", padx=(0, 10))
        SectionLabel(cfg_card, "🔑 API Keys").pack(anchor="w", padx=10, pady=(8, 4))
        self._config_status_lbl = tk.Label(cfg_card, text="", bg=T.PANEL,
                                            fg=T.FG2, font=T.FONT_SMALL, justify="left")
        self._config_status_lbl.pack(anchor="w", padx=10, pady=(0, 4))

        # Preferred API selector
        sel_row = tk.Frame(cfg_card, bg=T.PANEL)
        sel_row.pack(fill="x", padx=10, pady=(4, 10))
        tk.Label(sel_row, text="Preferred API:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")
        self._pref_var = tk.StringVar(value="auto")
        api_options = ["auto"] + [name for name, *_ in _APIS]
        self._pref_combo = ttk.Combobox(sel_row, textvariable=self._pref_var,
                                         values=api_options, state="readonly", width=14,
                                         font=T.FONT_SMALL)
        self._pref_combo.pack(side="left", padx=(6, 0))
        self._pref_combo.bind("<<ComboboxSelected>>", self._on_pref_changed)

        # Health score card
        score_card = Card(top)
        score_card.pack(side="left", fill="both", expand=True)
        SectionLabel(score_card, "Health Score").pack(anchor="w", padx=10, pady=(8, 0))
        self._score_lbl = tk.Label(score_card, text="--", bg=T.PANEL,
                                    fg=T.SUCCESS, font=(T.FONT_FAMILY, 36, "bold"))
        self._score_lbl.pack(anchor="w", padx=14, pady=2)
        self._score_desc = tk.Label(score_card, text="Not yet analyzed", bg=T.PANEL,
                                     fg=T.FG2, font=T.FONT_SMALL)
        self._score_desc.pack(anchor="w", padx=14, pady=(0, 8))

        # ── status / progress card ────────────────────────────────────────────
        stat_card = Card(body)
        stat_card.pack(fill="x", pady=(0, 10))
        st_row = tk.Frame(stat_card, bg=T.PANEL)
        st_row.pack(fill="x", padx=10, pady=(8, 2))
        SectionLabel(st_row, "Status").pack(side="left")
        self._api_lbl = tk.Label(st_row, text="", bg=T.PANEL,
                                  fg=T.HIGHLIGHT, font=T.FONT_SMALL)
        self._api_lbl.pack(side="right")
        self._status_lbl = tk.Label(stat_card, text="Ready to analyze",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._status_lbl.pack(anchor="w", padx=10, pady=(0, 4))
        self._progress = ProgressBar(stat_card, bg=T.PANEL)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        # ── critical issues card ──────────────────────────────────────────────
        crit_card = Card(body)
        crit_card.pack(fill="x", pady=(0, 10))
        SectionLabel(crit_card, "🔴  Critical Issues").pack(anchor="w", padx=10, pady=(8, 4))
        self._crit_frame = tk.Frame(crit_card, bg=T.PANEL)
        self._crit_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(self._crit_frame, text="Run analysis to see issues.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

        # ── full analysis card (scrollable) ───────────────────────────────────
        rec_card = Card(body)
        rec_card.pack(fill="both", expand=True)
        SectionLabel(rec_card, "✅  Recommendations & Full Analysis"
                     ).pack(anchor="w", padx=10, pady=(8, 4))

        sf = tk.Frame(rec_card, bg=T.PANEL)
        sf.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._canvas = tk.Canvas(sf, bg=T.PANEL, highlightthickness=0)
        vsb = tk.Scrollbar(sf, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._analysis_frame = tk.Frame(self._canvas, bg=T.PANEL)
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self._analysis_frame, anchor="nw")
        self._analysis_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfig(self._canvas_win, width=e.width))

        tk.Label(self._analysis_frame, text="Run analysis to see recommendations.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

        # Init
        self._refresh_api_status()

    # ── API status helpers ────────────────────────────────────────────────────

    def _refresh_api_status(self):
        lines = []
        for name, env_key, *_ in _APIS:
            key = os.getenv(env_key, "")
            if key:
                lines.append(f"✅ {name}: {key[:18]}…")
            else:
                lines.append(f"❌ {name}: Not configured")
        self._config_status_lbl.config(text="\n".join(lines))

    def _on_pref_changed(self, e=None):
        pref = self._pref_var.get()
        ai_agent.set_preferred_api(pref)

    # ── config dialog ─────────────────────────────────────────────────────────

    def _open_config(self):
        win = tk.Toplevel(self)
        win.title("Configure AI APIs")
        win.geometry("640x560")
        win.resizable(False, False)
        win.configure(bg=T.BG)
        win.grab_set()

        tk.Label(win, text="🔑  AI API Configuration", bg=T.BG, fg=T.FG,
                 font=(T.FONT_FAMILY, 12, "bold")).pack(pady=(14, 2))
        tk.Label(win, text="Configure one or more APIs — the agent tries them in order.",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL).pack(pady=(0, 10))

        # Scrollable area
        outer = tk.Frame(win, bg=T.BG)
        outer.pack(fill="both", expand=True, padx=16)
        canvas = tk.Canvas(outer, bg=T.BG, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        inner = tk.Frame(canvas, bg=T.BG)
        cwin = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cwin, width=e.width))

        entries: dict[str, tk.Entry] = {}  # env_key → Entry widget

        for name, env_key, env_model, default_model, url in _APIS:
            grp = tk.Frame(inner, bg=T.PANEL)
            grp.pack(fill="x", pady=6)

            # Header row with provider name
            hdr = tk.Frame(grp, bg=T.HIGHLIGHT if name == "Anthropic" else T.ACCENT)
            hdr.pack(fill="x")
            tk.Label(hdr, text=f"  {name}",
                     bg=hdr.cget("bg"), fg="#ffffff",
                     font=(T.FONT_FAMILY, 10, "bold")).pack(side="left", pady=6)
            tk.Label(hdr, text=url, bg=hdr.cget("bg"), fg=T.lerp_color("#ffffff", hdr.cget("bg"), 0.35),
                     font=T.FONT_SMALL).pack(side="right", padx=10)

            tk.Label(grp, text="API Key:", bg=T.PANEL,
                     fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", padx=10, pady=(6, 0))
            e = tk.Entry(grp, width=72, bg=T.BG, fg=T.FG,
                         insertbackground=T.FG, font=T.FONT_SMALL, show="•", relief="flat")
            e.insert(0, os.getenv(env_key, ""))
            e.pack(anchor="w", padx=10, pady=(2, 6))
            entries[env_key] = (e, env_model, default_model)

            # Show / hide key toggle
            def _toggle_show(entry=e):
                entry.config(show="" if entry.cget("show") == "•" else "•")
            tk.Button(grp, text="Show/Hide", command=_toggle_show,
                      bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL,
                      relief="flat", cursor="hand2", padx=6).pack(anchor="w", padx=10, pady=(0, 8))

        # Bottom buttons
        btn_row = tk.Frame(win, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=12)

        def save():
            for env_key, (entry, env_model, default_model) in entries.items():
                val = entry.get().strip()
                if val:
                    os.environ[env_key]   = val
                    os.environ[env_model] = default_model
                else:
                    # Clear key if field was emptied
                    os.environ.pop(env_key, None)
            self._refresh_api_status()
            win.destroy()
            messagebox.showinfo("Saved", "✅ API keys saved.\nClick 'Analyze Now' to start.")

        def test_all():
            configured = [name for name, env_key, *_ in _APIS if os.getenv(env_key)]
            if configured:
                messagebox.showinfo("API Status",
                                    f"✅ Configured: {', '.join(configured)}\n\n"
                                    "Click 'Analyze Now' to test a real call.")
            else:
                messagebox.showwarning("Not Ready", "❌ No API keys entered yet.")

        ActionButton(btn_row, "Save & Close", command=save).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Test Status",  command=test_all).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", command=win.destroy,
                  bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                  relief="flat", cursor="hand2", padx=10).pack(side="left")

    # ── analysis ──────────────────────────────────────────────────────────────

    def _start_analysis(self):
        if self._analyzing:
            messagebox.showinfo("Busy", "Analysis already in progress.")
            return

        # Ensure preferred API is synced
        ai_agent.set_preferred_api(self._pref_var.get())

        # Check at least one key is set
        if not any(os.getenv(env_key) for _, env_key, *_ in _APIS):
            messagebox.showwarning(
                "No API Keys",
                "❌ No API keys configured.\n\nClick 'Configure APIs' to add them.")
            return

        self._analyzing = True
        self._progress.indeterminate(True)
        pref = self._pref_var.get()
        chain_desc = pref if pref != "auto" else "Anthropic → Cerebras → Groq → OpenRouter"
        self._status_lbl.config(text=f"🔄 Analyzing… ({chain_desc})", fg=T.FG2)
        self._api_lbl.config(text="")
        self._app._status.set("Running AI analysis…")

        threading.Thread(target=self._do_analysis, daemon=True).start()

    def _do_analysis(self):
        def stream_cb(text):
            try:
                self.after(0, self._status_lbl.config,
                           {"text": f"📡 Received {len(text)} chars…"})
            except tk.TclError:
                pass

        report = ai_agent.analyze_system(stream_cb=stream_cb)
        self.after(0, self._apply_report, report)

    def _apply_report(self, report: ai_agent.HealthReport):
        try:
            self._analyzing = False
            self._progress.indeterminate(False)

            if report.error:
                self._status_lbl.config(text=f"⚠️  {report.error}", fg=T.WARNING)
                self._api_lbl.config(text="failed")
                self._app._status.set("AI analysis failed")
                return

            # Score
            color = T.score_color(report.overall_score)
            self._score_lbl.config(text=str(report.overall_score), fg=color)
            desc = ("Excellent" if report.overall_score >= 90 else
                    "Good"      if report.overall_score >= 75 else
                    "Fair"      if report.overall_score >= 50 else "Poor")
            self._score_desc.config(text=desc, fg=color)

            self._status_lbl.config(text="✅ Analysis complete", fg=T.SUCCESS)
            self._api_lbl.config(text=f"via {report.api_used}", fg=T.HIGHLIGHT)
            self._app._status.set(f"AI analysis complete — via {report.api_used}")

            # Critical issues
            for w in self._crit_frame.winfo_children():
                w.destroy()
            if report.critical_issues:
                for issue in report.critical_issues:
                    tk.Label(self._crit_frame, text=f"• {issue}", bg=T.PANEL,
                             fg=T.FG2, font=T.FONT_SMALL,
                             wraplength=680, justify="left").pack(anchor="w", pady=2)
            else:
                tk.Label(self._crit_frame, text="✅ No critical issues detected.",
                         bg=T.PANEL, fg=T.SUCCESS, font=T.FONT_SMALL).pack(anchor="w")

            # Recommendations + full text
            for w in self._analysis_frame.winfo_children():
                w.destroy()

            if report.recommendations:
                tk.Label(self._analysis_frame, text="Top Recommendations:",
                         bg=T.PANEL, fg=T.FG, font=T.FONT_BOLD).pack(anchor="w", pady=(0, 4))
                for i, rec in enumerate(report.recommendations, 1):
                    tk.Label(self._analysis_frame, text=f"  {i}. {rec}",
                             bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                             wraplength=680, justify="left").pack(anchor="w", pady=2)

            if report.analysis_text:
                tk.Frame(self._analysis_frame, bg=T.BORDER, height=1
                         ).pack(fill="x", pady=10)
                tk.Label(self._analysis_frame, text="Full Analysis:",
                         bg=T.PANEL, fg=T.FG, font=T.FONT_BOLD).pack(anchor="w", pady=(0, 4))
                tk.Label(self._analysis_frame, text=report.analysis_text,
                         bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                         wraplength=680, justify="left").pack(anchor="w")

        except tk.TclError:
            pass
