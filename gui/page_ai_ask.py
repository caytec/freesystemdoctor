"""
Ask your PC — chat-style natural-language assistant.

Sends the user's question (+ system context) to engine/ai_ask.answer() on a worker
thread and renders a plain-language answer with an optional "Open <tool>" button.
"""

from __future__ import annotations

import threading
import tkinter as tk

from . import theme as T
from . import nav_registry
from .widgets import Card, PageHeader, ActionButton, ProgressBar


class AIAskPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._busy = False
        self._thinking = None
        self._installing = False
        self._build_ui()
        self._refresh_local_status()
        self._greet()

    def _build_ui(self):
        PageHeader(self, title="Ask your PC",
                   subtitle="Describe a problem in plain words — get an answer + the right tool",
                   icon="💬", color=T.PURPLE).pack(fill="x")

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._local_card = Card(body)
        self._local_card.pack(fill="x", pady=(0, 10))
        row = tk.Frame(self._local_card, bg=T.PANEL)
        row.pack(fill="x", padx=12, pady=10)
        self._local_dot = tk.Label(row, text="○", bg=T.PANEL, fg=T.FG2,
                                   font=(T.FONT_FAMILY, 12))
        self._local_dot.pack(side="left", padx=(0, 6))
        self._local_lbl = tk.Label(row, text="Checking local AI…", bg=T.PANEL,
                                   fg=T.FG2, font=T.FONT_SMALL, anchor="w")
        self._local_lbl.pack(side="left", fill="x", expand=True)
        self._local_btn = ActionButton(row, text="Install (≈490 MB)", width=170,
                                       command=self._install_local)
        self._local_prog = ProgressBar(self._local_card)
        # packed on demand in _install_local

        # Scrollable chat area
        wrap = tk.Frame(body, bg=T.BG)
        wrap.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(wrap, bg=T.BG, highlightthickness=0, bd=0)
        self._canvas.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(wrap, orient="vertical", command=self._canvas.yview)
        sb.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=sb.set)
        self._chat = tk.Frame(self._canvas, bg=T.BG)
        self._chat_win = self._canvas.create_window((0, 0), window=self._chat, anchor="nw")
        self._chat.bind("<Configure>",
                        lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._chat_win, width=e.width))

        # Input bar
        bar = tk.Frame(body, bg=T.BG)
        bar.pack(fill="x", pady=(10, 0))
        self._entry = tk.Entry(bar, bg=T.ACCENT, fg=T.FG, insertbackground=T.HIGHLIGHT,
                               relief="flat", font=T.FONT_BODY)
        self._entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self._entry.bind("<Return>", lambda e: self._send())
        self._ask_btn = ActionButton(bar, text="Ask", width=90, command=self._send)
        self._ask_btn.pack(side="left")

    # ── local AI status / install ───────────────────────────────────────────
    def _refresh_local_status(self):
        def work():
            try:
                from engine import local_llm
                status = local_llm.get_status()
            except Exception as e:
                status = {"installed": False, "running": False, "error": str(e)}
            self.after(0, self._apply_local_status, status)

        threading.Thread(target=work, daemon=True).start()

    def _apply_local_status(self, status: dict):
        if status.get("installed"):
            self._local_dot.config(fg=T.SUCCESS, text="●")
            self._local_lbl.config(
                text=f"Local AI installed ({status.get('model_name', 'model')}) "
                     "— works fully offline.", fg=T.FG)
            self._local_btn.pack_forget()
        else:
            self._local_dot.config(fg=T.FG2, text="○")
            self._local_lbl.config(
                text="No local AI yet — answers use the cloud (or nothing, "
                     "if offline). Install a small model that runs entirely "
                     "on this PC.", fg=T.FG2)
            if not self._installing:
                self._local_btn.pack(side="right")

    def _install_local(self):
        if self._installing:
            return
        self._installing = True
        self._local_btn.pack_forget()
        self._local_lbl.config(text="Downloading local AI…", fg=T.FG2)
        self._local_prog.pack(fill="x", padx=12, pady=(0, 10))
        self._local_prog.set(0)

        def progress(pct, msg):
            self.after(0, lambda: (self._local_prog.set(pct),
                                   self._local_lbl.config(text=str(msg))))

        def work():
            try:
                from engine import local_llm
                ok, msg = local_llm.download_and_install(progress_cb=progress)
                if ok:
                    local_llm.start_server()
            except Exception as e:
                ok, msg = False, str(e)
            self.after(0, self._install_done, ok, msg)

        threading.Thread(target=work, daemon=True).start()

    def _install_done(self, ok: bool, msg: str):
        self._installing = False
        self._local_prog.pack_forget()
        self._local_lbl.config(text=msg, fg=T.SUCCESS if ok else T.DANGER)
        self._refresh_local_status()

    def _greet(self):
        self._bubble(
            "Hi! Ask me anything about your PC — e.g. “why is my PC slow?”, "
            "“how do I free up disk space?”, or “is my webcam safe?”. "
            "I'll explain and point you to the right tool.",
            who="assistant")

    # ── send / receive ─────────────────────────────────────────────────────
    def _send(self, _=None):
        if self._busy:
            return
        query = self._entry.get().strip()
        if not query:
            return
        self._entry.delete(0, tk.END)
        self._bubble(query, who="user")
        self._busy = True
        self._thinking = self._thinking_bubble()
        threading.Thread(target=self._worker, args=(query,), daemon=True).start()

    def _worker(self, query: str):
        try:
            from engine import ai_ask
            result = ai_ask.answer(query)
        except Exception as e:
            result = {"text": "", "suggested_key": None,
                      "suggested_label": None, "error": str(e)}
        self.after(0, self._render_answer, result)

    def _render_answer(self, result: dict):
        self._busy = False
        if self._thinking is not None:
            try:
                self._thinking.destroy()
            except tk.TclError:
                pass
            self._thinking = None

        if result.get("error") and not result.get("text"):
            self._bubble(
                "I couldn't reach an AI model. Install the local AI above "
                "(no internet needed once installed), or set a cloud API key "
                "(ANTHROPIC_API_KEY / GROQ_API_KEY / …). "
                "Details: " + str(result["error"]),
                who="assistant", error=True,
                suggested_key=result.get("suggested_key"))
            return

        self._bubble(result.get("text", "(no answer)"), who="assistant",
                     suggested_key=result.get("suggested_key"),
                     suggested_label=result.get("suggested_label"))

    # ── bubbles ──────────────────────────────────────────────────────────────
    def _bubble(self, text: str, who: str = "assistant", error: bool = False,
                suggested_key: str | None = None, suggested_label: str | None = None):
        outer = tk.Frame(self._chat, bg=T.BG)
        outer.pack(fill="x", padx=6, pady=5)

        if who == "user":
            tint = T.lerp_color(T.PANEL, T.HIGHLIGHT, 0.16)
            anchor, side = "e", "right"
        else:
            tint = T.lerp_color(T.PANEL, T.DANGER, 0.14) if error else T.PANEL
            anchor, side = "w", "left"

        bubble = tk.Frame(outer, bg=tint)
        bubble.pack(anchor=anchor, side=side, padx=4)
        tk.Label(bubble, text=text, bg=tint, fg=T.FG, font=T.FONT_BODY,
                 wraplength=560, justify="left").pack(anchor="w", padx=12, pady=8)

        # Optional "Open <tool>" button — validate key against the live registry
        if who == "assistant" and suggested_key:
            valid = {e.key for e in nav_registry.get_registry() if e.has_page}
            valid |= {"tools", "toolbox", "memory", "clean_tools"}
            if suggested_key in valid:
                label = suggested_label or suggested_key
                ActionButton(bubble, text=f"Open: {label}", width=0,
                             command=lambda k=suggested_key: self._app.activate_key(k)
                             ).pack(anchor="w", padx=12, pady=(0, 10))

        self._scroll_bottom()
        return outer

    def _thinking_bubble(self):
        outer = tk.Frame(self._chat, bg=T.BG)
        outer.pack(fill="x", padx=6, pady=5)
        bubble = tk.Frame(outer, bg=T.PANEL)
        bubble.pack(anchor="w", side="left", padx=4)
        tk.Label(bubble, text="Thinking…", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(anchor="w", padx=12, pady=(8, 2))
        pb = ProgressBar(bubble)
        pb.pack(fill="x", padx=12, pady=(0, 10))
        pb.configure(width=220)
        pb.indeterminate(True)
        self._scroll_bottom()
        return outer

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        try:
            self._canvas.yview_moveto(1.0)
        except tk.TclError:
            pass
