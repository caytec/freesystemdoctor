"""AI Agent page — multi-mode LLM analysis: hardware advice, optimization scoring, gaming."""

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

# Recommended sub-1 GB models for Ollama
_OLLAMA_MODELS = [
    ("qwen2.5:0.5b",  "~394 MB — polecany (najlepszy poniżej 1 GB)"),
    ("tinyllama",     "~638 MB — alternatywa"),
    ("smollm2:1.7b",  "~990 MB — większy, dokładniejszy"),
    ("qwen2:0.5b",    "~352 MB — starszy Qwen2"),
]

_MODE_ICONS = {
    "full":     "🖥",
    "hardware": "🔩",
    "optimize": "⚡",
    "gaming":   "🎮",
    "security": "🔒",
}


from ._pro_gate import gate_or_build


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
        # Pro-feature gate — shows upsell for Free users
        if gate_or_build(self, "ai_agent", "AI Agent"):
            return
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🤖  AI Agent", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="LLM-powered hardware advice, optimization scoring & more",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
        ActionButton(hdr, "Configure APIs", command=self._open_config
                     ).pack(side="right", padx=6)
        ActionButton(hdr, "▶ Analyze", command=self._start_analysis
                     ).pack(side="right", padx=12)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=10)

        # ── top row: API status | mode selector | score gauges ────────────────
        top = tk.Frame(body, bg=T.BG)
        top.pack(fill="x", pady=(0, 10))

        self._build_api_card(top)
        self._build_mode_card(top)
        self._build_scores_card(top)

        # ── progress / status bar ─────────────────────────────────────────────
        stat_card = Card(body)
        stat_card.pack(fill="x", pady=(0, 10))
        st_row = tk.Frame(stat_card, bg=T.PANEL)
        st_row.pack(fill="x", padx=10, pady=(8, 2))
        SectionLabel(st_row, "Status").pack(side="left")
        self._api_lbl = tk.Label(st_row, text="", bg=T.PANEL,
                                  fg=T.HIGHLIGHT, font=T.FONT_SMALL)
        self._api_lbl.pack(side="right")
        self._status_lbl = tk.Label(stat_card, text="Ready — choose a mode and click Analyze",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._status_lbl.pack(anchor="w", padx=10, pady=(0, 4))
        self._progress = ProgressBar(stat_card, bg=T.PANEL)
        self._progress.pack(fill="x", padx=10, pady=(0, 8))

        # ── two-column area: issues + advice | full analysis ──────────────────
        mid = tk.Frame(body, bg=T.BG)
        mid.pack(fill="both", expand=True)

        left_col = tk.Frame(mid, bg=T.BG, width=340)
        left_col.pack(side="left", fill="y", padx=(0, 10))
        left_col.pack_propagate(False)

        right_col = tk.Frame(mid, bg=T.BG)
        right_col.pack(side="left", fill="both", expand=True)

        self._build_issues_card(left_col)
        self._build_hardware_card(left_col)
        self._build_analysis_card(right_col)

        self._refresh_api_status()

    # ── sub-cards ─────────────────────────────────────────────────────────────

    def _build_api_card(self, parent):
        card = Card(parent)
        card.pack(side="left", fill="y", padx=(0, 10))
        SectionLabel(card, "🔑 API / Local LLM").pack(anchor="w", padx=10, pady=(8, 4))

        # Ollama status row
        ollama_row = tk.Frame(card, bg=T.PANEL)
        ollama_row.pack(fill="x", padx=10, pady=(0, 2))
        self._ollama_dot = tk.Label(ollama_row, text="⬤", bg=T.PANEL,
                                    fg=T.FG2, font=T.FONT_SMALL)
        self._ollama_dot.pack(side="left")
        self._ollama_lbl = tk.Label(ollama_row, text="Ollama: sprawdzanie…",
                                    bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._ollama_lbl.pack(side="left", padx=4)

        # Ollama model selector
        model_row = tk.Frame(card, bg=T.PANEL)
        model_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(model_row, text="Model:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")
        self._ollama_model_var = tk.StringVar(value=ai_agent.OLLAMA_DEFAULT_MODEL)
        self._ollama_model_combo = ttk.Combobox(
            model_row, textvariable=self._ollama_model_var,
            values=[m for m, _ in _OLLAMA_MODELS],
            state="normal", width=16, font=T.FONT_SMALL,
        )
        self._ollama_model_combo.pack(side="left", padx=(4, 4))
        self._ollama_model_combo.bind("<<ComboboxSelected>>", self._on_ollama_model_changed)
        self._ollama_model_combo.bind("<Return>", self._on_ollama_model_changed)
        ActionButton(model_row, "⬇ Pobierz",
                     command=self._pull_ollama_model).pack(side="left")

        # Cloud API status
        self._config_status_lbl = tk.Label(card, text="", bg=T.PANEL,
                                            fg=T.FG2, font=T.FONT_SMALL, justify="left")
        self._config_status_lbl.pack(anchor="w", padx=10, pady=(4, 0))

        sel_row = tk.Frame(card, bg=T.PANEL)
        sel_row.pack(fill="x", padx=10, pady=(4, 10))
        tk.Label(sel_row, text="Preferred:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")
        self._pref_var = tk.StringVar(value="auto")
        self._pref_combo = ttk.Combobox(
            sel_row, textvariable=self._pref_var,
            values=["auto", "Ollama"] + [n for n, *_ in _APIS],
            state="readonly", width=14, font=T.FONT_SMALL,
        )
        self._pref_combo.pack(side="left", padx=(6, 0))
        self._pref_combo.bind("<<ComboboxSelected>>", self._on_pref_changed)

    def _build_mode_card(self, parent):
        card = Card(parent)
        card.pack(side="left", fill="y", padx=(0, 10))
        SectionLabel(card, "📋 Analysis Mode").pack(anchor="w", padx=10, pady=(8, 4))

        self._mode_var = tk.StringVar(value="full")
        for mode_key, mode_label in ai_agent.ANALYSIS_MODES.items():
            icon = _MODE_ICONS.get(mode_key, "•")
            rb = ttk.Radiobutton(card, text=f"{icon}  {mode_label}",
                                 variable=self._mode_var, value=mode_key)
            rb.pack(anchor="w", padx=14, pady=2)

        # Describe selected mode
        self._mode_desc = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2,
                                    font=T.FONT_SMALL, wraplength=200, justify="left")
        self._mode_desc.pack(anchor="w", padx=10, pady=(6, 10))
        self._mode_var.trace_add("write", lambda *_: self._update_mode_desc())
        self._update_mode_desc()

    def _build_scores_card(self, parent):
        card = Card(parent)
        card.pack(side="left", fill="both", expand=True)
        SectionLabel(card, "📊 AI Scores").pack(anchor="w", padx=10, pady=(8, 4))

        grid = tk.Frame(card, bg=T.PANEL)
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._score_widgets = {}
        score_defs = [
            ("overall",     "Overall",      T.HIGHLIGHT),
            ("hardware",    "Hardware",     T.SUCCESS),
            ("optimization","Optimization", T.WARNING),
            ("security",    "Security",     "#e74c3c"),
        ]

        for i, (key, label, color) in enumerate(score_defs):
            col_frame = tk.Frame(grid, bg=T.PANEL)
            col_frame.grid(row=0, column=i, padx=10, pady=6)

            num = tk.Label(col_frame, text="--", bg=T.PANEL, fg=color,
                           font=(T.FONT_FAMILY, 26, "bold"))
            num.pack()
            tk.Label(col_frame, text=label, bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL).pack()
            self._score_widgets[key] = num

        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def _build_issues_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 10))
        SectionLabel(card, "🔴 Critical Issues").pack(anchor="w", padx=10, pady=(8, 4))
        self._crit_frame = tk.Frame(card, bg=T.PANEL)
        self._crit_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(self._crit_frame, text="Run analysis to see issues.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

    def _build_hardware_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, "🔩 Hardware Advice").pack(anchor="w", padx=10, pady=(8, 4))
        self._hw_frame = tk.Frame(card, bg=T.PANEL)
        self._hw_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        tk.Label(self._hw_frame,
                 text="Run 'Hardware' or 'Full' analysis\nto see upgrade advice.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

    def _build_analysis_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)
        SectionLabel(card, "✅ Recommendations & Full Analysis"
                     ).pack(anchor="w", padx=10, pady=(8, 4))

        sf = tk.Frame(card, bg=T.PANEL)
        sf.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._canvas = tk.Canvas(sf, bg=T.PANEL, highlightthickness=0)
        vsb = tk.Scrollbar(sf, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._canvas.bind("<MouseWheel>", lambda e: self._canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

        self._analysis_frame = tk.Frame(self._canvas, bg=T.PANEL)
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self._analysis_frame, anchor="nw")
        self._analysis_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfig(self._canvas_win, width=e.width))

        tk.Label(self._analysis_frame, text="Select a mode and click ▶ Analyze",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _update_mode_desc(self):
        mode = self._mode_var.get()
        descs = {
            "full":     "All-in-one: health, hardware, software & security overview.",
            "hardware": "Evaluates CPU/GPU/RAM/disk specs and suggests specific upgrades.",
            "optimize": "Scores Windows optimization level and gives actionable tweaks.",
            "gaming":   "Estimates FPS, gaming bottlenecks, and per-game settings.",
            "security": "Audits Defender, firewall, telemetry, and privacy settings.",
        }
        self._mode_desc.config(text=descs.get(mode, ""))

    def _refresh_api_status(self):
        # Cloud API keys
        lines = []
        for name, env_key, *_ in _APIS:
            key = os.getenv(env_key, "")
            lines.append(f"{'✅' if key else '❌'} {name}: {key[:16]}…" if key else f"❌ {name}")
        self._config_status_lbl.config(text="\n".join(lines))
        # Ollama — check in background so UI doesn't freeze
        threading.Thread(target=self._check_ollama_bg, daemon=True).start()

    def _check_ollama_bg(self):
        running = ai_agent.ollama_is_running()
        models  = ai_agent.ollama_list_models() if running else []
        def _upd():
            try:
                if running:
                    model_txt = models[0] if models else "no model"
                    self._ollama_dot.config(fg=T.SUCCESS)
                    self._ollama_lbl.config(
                        text=f"Ollama: aktywny  [{len(models)} modeli]", fg=T.SUCCESS)
                    # Update combo with actual installed models + recommended
                    all_mdl = list(dict.fromkeys(
                        models + [m for m, _ in _OLLAMA_MODELS]))
                    self._ollama_model_combo.config(values=all_mdl)
                else:
                    self._ollama_dot.config(fg=T.DANGER)
                    self._ollama_lbl.config(
                        text="Ollama: brak — pobierz: ollama.com/download", fg=T.DANGER)
            except Exception:
                pass
        try:
            self.after(0, _upd)
        except Exception:
            pass

    def _on_ollama_model_changed(self, e=None):
        model = self._ollama_model_var.get().strip()
        if model:
            ai_agent.set_ollama_model(model)

    def _pull_ollama_model(self):
        """Download selected Ollama model in background with progress dialog."""
        model = self._ollama_model_var.get().strip()
        if not model:
            messagebox.showwarning("Model", "Wpisz lub wybierz nazwę modelu.")
            return
        if not ai_agent.ollama_is_running():
            messagebox.showerror(
                "Ollama nie działa",
                "Uruchom Ollama przed pobraniem modelu.\n"
                "Pobierz ze: https://ollama.com/download\n"
                "Następnie uruchom: ollama serve")
            return

        # Simple progress window
        win = tk.Toplevel(self)
        win.title(f"Pobieranie {model}")
        win.geometry("420x160")
        win.configure(bg=T.BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text=f"⬇ Pobieranie modelu: {model}",
                 bg=T.BG, fg=T.FG, font=T.FONT_BOLD).pack(pady=(16, 4))
        # Find size description if known
        size_note = next((desc for m, desc in _OLLAMA_MODELS if m == model), "")
        if size_note:
            tk.Label(win, text=size_note, bg=T.BG, fg=T.FG2,
                     font=T.FONT_SMALL).pack(pady=(0, 8))
        prog = ProgressBar(win, bg=T.BG)
        prog.pack(fill="x", padx=20, pady=4)
        status_lbl = tk.Label(win, text="Inicjalizacja…", bg=T.BG,
                              fg=T.FG2, font=T.FONT_SMALL)
        status_lbl.pack()

        def on_progress(pct, msg):
            try:
                win.after(0, lambda: (prog.set(pct), status_lbl.config(text=msg or "…")))
            except Exception:
                pass

        def worker():
            ok, msg = ai_agent.ollama_pull_model(model, progress_cb=on_progress)
            def done():
                try:
                    if ok:
                        prog.set(100)
                        status_lbl.config(text=f"✓ {msg}", fg=T.SUCCESS)
                        ai_agent.set_ollama_model(model)
                        self._ollama_model_var.set(model)
                        self._check_ollama_bg()
                        win.after(2000, win.destroy)
                    else:
                        status_lbl.config(text=f"✗ {msg}", fg=T.DANGER)
                except Exception:
                    pass
            try:
                win.after(0, done)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_pref_changed(self, e=None):
        ai_agent.set_preferred_api(self._pref_var.get())

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
        tk.Label(win,
                 text="Lokalne (Ollama) są używane bez klucza API — prywatnie, offline.\n"
                      "Chmurowe API jako zapasowy łańcuch gdy Ollama niedostępna.",
                 bg=T.BG, fg=T.FG2, font=T.FONT_SMALL).pack(pady=(0, 6))

        # ── Ollama section ────────────────────────────────────────────────────
        ollama_grp = tk.Frame(win, bg=T.PANEL)
        ollama_grp.pack(fill="x", padx=16, pady=(0, 6))
        hdr_ol = tk.Frame(ollama_grp, bg="#1a6b3c")
        hdr_ol.pack(fill="x")
        tk.Label(hdr_ol, text="  🦙 Ollama — lokalny LLM (zalecany, bez klucza API)",
                 bg="#1a6b3c", fg="#ffffff",
                 font=(T.FONT_FAMILY, 10, "bold")).pack(side="left", pady=6)
        tk.Label(hdr_ol, text="ollama.com/download",
                 bg="#1a6b3c", fg="#aaffcc", font=T.FONT_SMALL).pack(side="right", padx=10)

        ol_body = tk.Frame(ollama_grp, bg=T.PANEL)
        ol_body.pack(fill="x", padx=10, pady=8)

        running = ai_agent.ollama_is_running()
        models  = ai_agent.ollama_list_models() if running else []
        status_txt = (f"✅ Serwer aktywny | modele: {', '.join(models) or 'brak'}"
                      if running else
                      "❌ Ollama nie działa — pobierz ze: https://ollama.com/download")
        tk.Label(ol_body, text=status_txt,
                 bg=T.PANEL, fg=T.SUCCESS if running else T.DANGER,
                 font=T.FONT_SMALL, wraplength=560, justify="left").pack(anchor="w")

        ol_model_row = tk.Frame(ol_body, bg=T.PANEL)
        ol_model_row.pack(fill="x", pady=(6, 2))
        tk.Label(ol_model_row, text="Aktywny model (<1 GB):",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
        ol_model_var = tk.StringVar(value=ai_agent.OLLAMA_DEFAULT_MODEL)
        ol_model_cb  = ttk.Combobox(
            ol_model_row, textvariable=ol_model_var,
            values=list(dict.fromkeys(models + [m for m, _ in _OLLAMA_MODELS])),
            state="normal", width=20, font=T.FONT_SMALL,
        )
        ol_model_cb.pack(side="left", padx=(6, 0))
        for m, desc in _OLLAMA_MODELS:
            tk.Label(ol_body, text=f"  • {m} — {desc}",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")
        tk.Label(ol_body,
                 text="Instalacja: ollama pull qwen2.5:0.5b",
                 bg=T.PANEL, fg=T.HIGHLIGHT, font=T.FONT_SMALL).pack(anchor="w", pady=(4, 0))

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

        entries: dict[str, tuple] = {}
        for name, env_key, env_model, default_model, url in _APIS:
            grp = tk.Frame(inner, bg=T.PANEL)
            grp.pack(fill="x", pady=6)

            hdr = tk.Frame(grp, bg=T.HIGHLIGHT if name == "Anthropic" else T.ACCENT)
            hdr.pack(fill="x")
            tk.Label(hdr, text=f"  {name}", bg=hdr.cget("bg"), fg="#ffffff",
                     font=(T.FONT_FAMILY, 10, "bold")).pack(side="left", pady=6)
            tk.Label(hdr, text=url, bg=hdr.cget("bg"),
                     fg=T.lerp_color("#ffffff", hdr.cget("bg"), 0.35),
                     font=T.FONT_SMALL).pack(side="right", padx=10)

            tk.Label(grp, text="API Key:", bg=T.PANEL,
                     fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", padx=10, pady=(6, 0))
            e = tk.Entry(grp, width=72, bg=T.BG, fg=T.FG,
                         insertbackground=T.FG, font=T.FONT_SMALL, show="•", relief="flat")
            e.insert(0, os.getenv(env_key, ""))
            e.pack(anchor="w", padx=10, pady=(2, 6))
            entries[env_key] = (e, env_model, default_model)

            def _toggle(entry=e):
                entry.config(show="" if entry.cget("show") == "•" else "•")
            tk.Button(grp, text="Show/Hide", command=_toggle,
                      bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL,
                      relief="flat", cursor="hand2", padx=6).pack(anchor="w", padx=10, pady=(0, 8))

        btn_row = tk.Frame(win, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=12)

        def save():
            # Save Ollama model
            chosen_model = ol_model_var.get().strip()
            if chosen_model:
                ai_agent.set_ollama_model(chosen_model)
                self._ollama_model_var.set(chosen_model)
            # Save cloud API keys
            for env_key, (entry, env_model, default_model) in entries.items():
                val = entry.get().strip()
                if val:
                    os.environ[env_key]   = val
                    os.environ[env_model] = default_model
                else:
                    os.environ.pop(env_key, None)
            self._refresh_api_status()
            win.destroy()
            messagebox.showinfo("Zapisano",
                                "✅ Ustawienia zapisane.\n"
                                "Kliknij ▶ Analizuj aby uruchomić AI agenta.")

        ActionButton(btn_row, "Save & Close", command=save).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text="Cancel", command=win.destroy,
                  bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                  relief="flat", cursor="hand2", padx=10).pack(side="left")

    # ── analysis ──────────────────────────────────────────────────────────────

    def _start_analysis(self):
        if self._analyzing:
            messagebox.showinfo("Busy", "Analysis already in progress.")
            return

        ai_agent.set_preferred_api(self._pref_var.get())
        ai_agent.set_ollama_model(self._ollama_model_var.get().strip())

        # Check: at least one source available (Ollama or any cloud API key)
        has_cloud = any(os.getenv(env_key) for _, env_key, *_ in _APIS)
        has_ollama = ai_agent.ollama_is_running() and bool(ai_agent.ollama_list_models())
        if not has_cloud and not has_ollama:
            messagebox.showwarning(
                "Brak LLM",
                "❌ Brak dostępnego modelu AI.\n\n"
                "Opcja 1 (lokalna, bezpłatna):\n"
                "  1. Pobierz Ollama: https://ollama.com/download\n"
                "  2. Uruchom: ollama serve\n"
                "  3. Kliknij ⬇ Pobierz przy modelu qwen2.5:0.5b\n\n"
                "Opcja 2 (chmura): Kliknij 'Configure APIs' i dodaj klucz API.")
            return

        mode = self._mode_var.get()
        mode_label = ai_agent.ANALYSIS_MODES.get(mode, mode)
        icon = _MODE_ICONS.get(mode, "•")

        self._analyzing = True
        self._progress.indeterminate(True)
        pref = self._pref_var.get()
        chain_desc = pref if pref != "auto" else "Ollama → Anthropic → Cerebras → Groq → OpenRouter"
        self._status_lbl.config(
            text=f"🔄 {icon} {mode_label} in progress… ({chain_desc})", fg=T.FG2)
        self._api_lbl.config(text="")
        self._app._status.set(f"AI {mode_label}…")

        threading.Thread(target=self._do_analysis, args=(mode,), daemon=True).start()

    def _do_analysis(self, mode: str):
        def stream_cb(text):
            try:
                self.after(0, self._status_lbl.config,
                           {"text": f"📡 Received {len(text)} chars…"})
            except tk.TclError:
                pass

        report = ai_agent.analyze_system(stream_cb=stream_cb, mode=mode)
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

            mode_label = ai_agent.ANALYSIS_MODES.get(report.mode, report.mode)
            icon = _MODE_ICONS.get(report.mode, "•")

            self._status_lbl.config(text=f"✅ {icon} {mode_label} complete", fg=T.SUCCESS)
            self._api_lbl.config(text=f"via {report.api_used}", fg=T.HIGHLIGHT)
            self._app._status.set(f"AI {mode_label} — via {report.api_used}")

            # Update score gauges
            def _score_color(s: int) -> str:
                if s >= 80: return T.SUCCESS
                if s >= 60: return T.WARNING
                return T.DANGER

            scores = {
                "overall":      report.overall_score,
                "hardware":     report.hardware_score,
                "optimization": report.optimization_score,
                "security":     report.security_score,
            }
            for key, val in scores.items():
                lbl = self._score_widgets[key]
                text = str(val) if val else "--"
                color = _score_color(val) if val else T.FG2
                lbl.config(text=text, fg=color)

            # Critical issues
            for w in self._crit_frame.winfo_children():
                w.destroy()
            if report.critical_issues:
                for issue in report.critical_issues:
                    row = tk.Frame(self._crit_frame, bg=T.PANEL)
                    row.pack(fill="x", pady=2)
                    tk.Label(row, text="•", bg=T.PANEL, fg=T.DANGER,
                             font=T.FONT_BODY).pack(side="left")
                    tk.Label(row, text=issue, bg=T.PANEL, fg=T.FG2,
                             font=T.FONT_SMALL, wraplength=280,
                             justify="left").pack(side="left", padx=4)
            else:
                tk.Label(self._crit_frame, text="✅ No critical issues.",
                         bg=T.PANEL, fg=T.SUCCESS, font=T.FONT_SMALL).pack(anchor="w")

            # Hardware advice panel
            for w in self._hw_frame.winfo_children():
                w.destroy()

            hw_items = report.hardware_advice or report.bottlenecks
            if hw_items:
                for item in hw_items:
                    row = tk.Frame(self._hw_frame, bg=T.PANEL)
                    row.pack(fill="x", pady=2)
                    tk.Label(row, text="→", bg=T.PANEL, fg=T.HIGHLIGHT,
                             font=T.FONT_BODY).pack(side="left")
                    tk.Label(row, text=item, bg=T.PANEL, fg=T.FG2,
                             font=T.FONT_SMALL, wraplength=280,
                             justify="left").pack(side="left", padx=4)
            else:
                tk.Label(self._hw_frame,
                         text="No specific hardware advice for this mode.\nUse Hardware or Full analysis.",
                         bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

            # Full analysis scrollable area
            for w in self._analysis_frame.winfo_children():
                w.destroy()

            if report.recommendations:
                tk.Label(self._analysis_frame, text="Recommendations:",
                         bg=T.PANEL, fg=T.FG, font=T.FONT_BOLD).pack(anchor="w", pady=(0, 4))
                for i, rec in enumerate(report.recommendations, 1):
                    frame = tk.Frame(self._analysis_frame, bg=T.PANEL)
                    frame.pack(fill="x", pady=2)
                    tk.Label(frame, text=f"{i}.", bg=T.PANEL, fg=T.HIGHLIGHT,
                             font=T.FONT_BOLD, width=3).pack(side="left")
                    tk.Label(frame, text=rec, bg=T.PANEL, fg=T.FG2,
                             font=T.FONT_SMALL, wraplength=580,
                             justify="left").pack(side="left")

            if report.analysis_text:
                tk.Frame(self._analysis_frame, bg=T.BORDER, height=1).pack(fill="x", pady=10)
                tk.Label(self._analysis_frame, text="Full LLM Analysis:",
                         bg=T.PANEL, fg=T.FG, font=T.FONT_BOLD).pack(anchor="w", pady=(0, 4))
                # Render markdown-like sections
                for line in report.analysis_text.split("\n"):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("##"):
                        section_title = stripped.lstrip("#").strip()
                        tk.Label(self._analysis_frame, text=section_title,
                                 bg=T.PANEL, fg=T.HIGHLIGHT,
                                 font=T.FONT_BOLD).pack(anchor="w", pady=(8, 2))
                    elif stripped.startswith(("-", "•", "*")):
                        row = tk.Frame(self._analysis_frame, bg=T.PANEL)
                        row.pack(fill="x", pady=1)
                        tk.Label(row, text="•", bg=T.PANEL, fg=T.FG2,
                                 font=T.FONT_SMALL).pack(side="left")
                        tk.Label(row, text=stripped.lstrip("-•* "), bg=T.PANEL, fg=T.FG2,
                                 font=T.FONT_SMALL, wraplength=560,
                                 justify="left").pack(side="left", padx=4)
                    elif stripped[0].isdigit() and "." in stripped[:3]:
                        row = tk.Frame(self._analysis_frame, bg=T.PANEL)
                        row.pack(fill="x", pady=1)
                        tk.Label(row, text=stripped[:2], bg=T.PANEL, fg=T.HIGHLIGHT,
                                 font=T.FONT_SMALL, width=3).pack(side="left")
                        tk.Label(row, text=stripped[3:], bg=T.PANEL, fg=T.FG2,
                                 font=T.FONT_SMALL, wraplength=560,
                                 justify="left").pack(side="left")
                    else:
                        tk.Label(self._analysis_frame, text=stripped,
                                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                 wraplength=590, justify="left").pack(anchor="w", pady=1)

        except tk.TclError:
            pass
