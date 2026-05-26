"""
first_run_dialog.py — friendly opt-in prompt for installing LibreHardwareMonitor.

Shown at startup ONLY when:
- LHM is not installed
- User hasn't previously declined
- HW Monitor / Real-time pages would benefit from it

Honest framing — user can:
- Install now (downloads ~5 MB from GitHub Releases)
- Install later (closes dialog)
- Don't ask again (sets persistent flag)
"""

import threading
import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import ActionButton, ProgressBar
from engine import dependency_installer as di


class FirstRunDialog(tk.Toplevel):
    """Non-modal opt-in installer prompt."""

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("Pierwsze uruchomienie — opcjonalne zależności")
        self.configure(bg=T.BG)
        self.geometry("560x460")
        self.transient(master)
        self.resizable(False, False)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 560) // 2
        y = (self.winfo_screenheight() - 460) // 2
        self.geometry(f"+{x}+{y}")

        self._installing = False
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=T.ACCENT, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="🔧 Opcjonalna zależność",
            bg=T.ACCENT, fg=T.FG, font=T.FONT_TITLE,
        ).pack(side="left", padx=16, pady=14)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Title
        tk.Label(
            body,
            text="Zainstalować LibreHardwareMonitor?",
            bg=T.BG, fg=T.FG,
            font=(T.FONT_FAMILY, 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # Explanation
        explanation = (
            "Bez tej zależności strony 'Hardware Monitor' i 'Real-time Dashboard'\n"
            "nie pokażą temperatury CPU/dysku (GPU NVIDIA działa bez tego).\n\n"
            "📦  LibreHardwareMonitor — open source, MIT license, GitHub\n"
            "💾  ~5 MB, pobrane z oficjalnego GitHub Releases\n"
            "🛡️  Zero telemetrii, zero reklam, kod publiczny\n"
            "📁  Instalacja do: %APPDATA%\\FreeSystemDoctor\\LibreHardwareMonitor\\\n"
            "🚀  Opcjonalnie: auto-start w tle przy każdym logowaniu\n\n"
            "Możesz to też pominąć — aplikacja działa bez tego, tylko bez temp."
        )
        tk.Label(
            body, text=explanation,
            bg=T.BG, fg=T.FG2, font=T.FONT_BODY,
            justify="left", anchor="w",
        ).pack(anchor="w", pady=(0, 14))

        # Autostart checkbox
        self._autostart_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            body, text="Uruchamiaj LHM automatycznie przy logowaniu (zalecane)",
            variable=self._autostart_var,
            bg=T.BG, fg=T.FG, selectcolor=T.ACCENT,
            activebackground=T.BG, font=T.FONT_BODY,
        ).pack(anchor="w", pady=(0, 12))

        # Progress (hidden initially)
        self._progress_frame = tk.Frame(body, bg=T.BG)
        self._progress_lbl = tk.Label(
            self._progress_frame, text="",
            bg=T.BG, fg=T.HIGHLIGHT, font=T.FONT_SMALL, anchor="w",
        )
        self._progress_lbl.pack(fill="x")
        self._progress = ProgressBar(self._progress_frame)
        self._progress.pack(fill="x", pady=(2, 8))

        # Button row
        btn_row = tk.Frame(body, bg=T.BG)
        btn_row.pack(fill="x", side="bottom")

        self._install_btn = ActionButton(
            btn_row, text="✓ Zainstaluj teraz", command=self._on_install,
        )
        self._install_btn.config(font=T.FONT_BOLD, pady=10)
        self._install_btn.pack(side="left", padx=(0, 8))

        ActionButton(btn_row, text="Później", command=self._on_later).pack(side="left", padx=4)

        ActionButton(btn_row, text="Nie pytaj ponownie",
                     command=self._on_never).pack(side="right")

    def _on_install(self):
        if self._installing:
            return
        self._installing = True
        self._install_btn.config(state="disabled")
        self._progress_frame.pack(fill="x", pady=(0, 8))
        self._progress.set(0)
        self._progress_lbl.config(text="Inicjalizacja...")

        def progress(pct: int, msg: str):
            self.after(0, lambda: (self._progress.set(pct),
                                    self._progress_lbl.config(text=msg)))

        def worker():
            ok, msg = di.download_and_install_lhm(progress_cb=progress)
            if ok and self._autostart_var.get():
                di.ensure_lhm_autostart(True)
            if ok:
                di.start_lhm_background()
            self.after(0, lambda: self._done(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, ok: bool, msg: str):
        self._installing = False
        if ok:
            self._progress.set(100)
            self._progress_lbl.config(
                text="✓ " + msg,
                fg=T.SUCCESS,
            )
            self._install_btn.config(text="✓ Gotowe", state="disabled")
            # Auto-close after 2 sec
            self.after(2000, self.destroy)
        else:
            self._progress_lbl.config(text="✗ " + msg, fg=T.DANGER)
            self._install_btn.config(state="normal", text="Spróbuj ponownie")

    def _on_later(self):
        self.destroy()

    def _on_never(self):
        di.mark_lhm_declined()
        self.destroy()


def maybe_show_first_run_dialog(root: tk.Tk) -> bool:
    """Show dialog if appropriate. Returns True if dialog was shown."""
    summary = di.get_dependency_summary()
    if not summary["should_prompt"]:
        return False
    # Show after 1.5 sec so main UI loads first
    root.after(1500, lambda: FirstRunDialog(root))
    return True
