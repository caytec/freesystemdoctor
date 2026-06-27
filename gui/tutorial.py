"""
tutorial.py — interactive first-run walkthrough (coachmark tour).

A short, step-by-step tour that spotlights real UI elements: each step draws a
bright highlight ring around a target widget and shows a callout bubble with a
title, description, step counter, and Back / Next / Skip controls.

Robust on Windows/Tk: the highlight is four thin top-most strips framing the
target (no alpha / transparent-color tricks needed), so it never covers or
dims the element it points at. Steps with no target show a centred callout.

Shown once on first run (persisted via app_settings "tutorial_seen"); can be
re-run anytime from Settings → Take a tour.
"""

import tkinter as tk

from . import theme as T
from .widgets import ActionButton

try:
    from engine import app_settings
except Exception:  # pragma: no cover
    app_settings = None


def _steps(app):
    """Tour steps. target is a callable returning a widget (or None = centred).
    action runs before the step is shown (e.g. navigate to a page)."""
    return [
        dict(target=None,
             title="Welcome to FreeSystemDoctor",
             text="Let's take a quick 60-second tour of the app. "
                  "You can skip anytime."),
        dict(target=lambda: getattr(app, "_titlebar", None),
             title="The top bar",
             text="Your app title and a live CPU / RAM / Disk readout always sit here."),
        dict(target=lambda: getattr(app, "_sidebar", None),
             title="Your toolbox",
             text="All tools live here, grouped by category. Click a category "
                  "icon to slide out its tools, then pick one."),
        dict(target=lambda: getattr(app, "_content_wrapper", None),
             action=lambda: app._switch_page("autopilot"),
             title="1-Click Auto-Pilot",
             text="New here? Start with Auto-Pilot — it scans your PC and fixes "
                  "the common issues in a single click. Tools always open in "
                  "this area."),
        dict(target=lambda: getattr(app, "_content_wrapper", None),
             key="Ctrl + K",
             title="Find anything instantly",
             text="Press Ctrl + K at any time to search all 60+ tools by name "
                  "and jump straight to one."),
        dict(target=lambda: getattr(app, "_status", None),
             title="Status & view mode",
             text="Status messages and tips show along the bottom. Prefer fewer "
                  "options? Turn on Simple mode in Settings → Appearance."),
        dict(target=lambda: getattr(app, "_aipol_brand", None),
             title="Made by AiPOL SA",
             text="FreeSystemDoctor is brought to you by AiPOL SA. "
                  "Click the corner logo to visit aipol.com.pl."),
        dict(target=None,
             title="You're all set!",
             text="That's it. You can replay this tour anytime from "
                  "Settings → Take a tour. Enjoy a faster, cleaner PC!"),
    ]


class InteractiveTutorial:
    PAD = 5            # gap between target and the highlight ring
    TH = 3            # ring thickness
    CALLOUT_W = 340

    def __init__(self, app):
        self._app = app
        self._steps = _steps(app)
        self._i = 0
        self._bars = []           # 4 highlight strip Toplevels
        self._callout = None      # callout Toplevel
        self._pulse_job = None
        self._reposition_job = None

    # ── lifecycle ───────────────────────────────────────────────────────────
    def start(self):
        self._i = 0
        self._build_callout()
        self._show_step()
        try:
            self._app.bind("<Escape>", lambda e: self._finish(), add="+")
            self._app.bind("<Configure>", self._on_app_configure, add="+")
        except tk.TclError:
            pass

    def _on_app_configure(self, _e=None):
        # Debounced re-position so the ring follows window moves/resizes.
        if self._reposition_job:
            try:
                self._app.after_cancel(self._reposition_job)
            except Exception:
                pass
        self._reposition_job = self._app.after(80, self._position_current)

    # ── steps ───────────────────────────────────────────────────────────────
    def _show_step(self):
        step = self._steps[self._i]
        action = step.get("action")
        if action:
            try:
                action()
            except Exception:
                pass
        # Let any navigation settle, then render highlight + callout.
        self._app.after(60, self._render_step)

    def _render_step(self):
        self._fill_callout()
        self._position_current()
        if self._callout:
            try:
                self._callout.deiconify()
                self._callout.lift()
                self._callout.attributes("-topmost", True)
            except tk.TclError:
                pass

    def _position_current(self):
        step = self._steps[self._i]
        target = None
        getter = step.get("target")
        if getter:
            try:
                target = getter()
            except Exception:
                target = None
        bbox = self._widget_bbox(target)
        self._draw_ring(bbox)
        self._place_callout(bbox)

    @staticmethod
    def _widget_bbox(widget):
        if widget is None:
            return None
        try:
            if not widget.winfo_exists() or not widget.winfo_ismapped():
                return None
            return (widget.winfo_rootx(), widget.winfo_rooty(),
                    widget.winfo_width(), widget.winfo_height())
        except tk.TclError:
            return None

    # ── highlight ring (4 strips) ───────────────────────────────────────────
    def _ensure_bars(self):
        if self._bars:
            return
        for _ in range(4):
            try:
                b = tk.Toplevel(self._app)
                b.overrideredirect(True)
                b.attributes("-topmost", True)
                b.configure(bg=T.HIGHLIGHT)
                b.withdraw()
                self._bars.append(b)
            except tk.TclError:
                pass

    def _draw_ring(self, bbox):
        self._ensure_bars()
        if not self._bars:
            return
        if bbox is None:
            for b in self._bars:
                try:
                    b.withdraw()
                except tk.TclError:
                    pass
            return
        L, Tp, W, H = bbox
        p, th = self.PAD, self.TH
        x0, y0 = L - p, Tp - p
        w, h = W + 2 * p, H + 2 * p
        rects = [
            (x0, y0, w, th),                 # top
            (x0, y0 + h - th, w, th),        # bottom
            (x0, y0, th, h),                 # left
            (x0 + w - th, y0, th, h),        # right
        ]
        for b, (rx, ry, rw, rh) in zip(self._bars, rects):
            try:
                b.geometry(f"{max(1, rw)}x{max(1, rh)}+{rx}+{ry}")
                b.deiconify()
                b.lift()
                b.attributes("-topmost", True)
            except tk.TclError:
                pass

    # ── callout bubble ──────────────────────────────────────────────────────
    def _build_callout(self):
        try:
            c = tk.Toplevel(self._app)
        except tk.TclError:
            return
        c.overrideredirect(True)
        c.attributes("-topmost", True)
        c.configure(bg=T.BORDER)        # 1px border feel
        c.withdraw()
        inner = tk.Frame(c, bg=T.PANEL)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        # accent strip
        tk.Frame(inner, bg=T.HIGHLIGHT, height=3).pack(fill="x")
        self._body = tk.Frame(inner, bg=T.PANEL, padx=16, pady=14)
        self._body.pack(fill="both", expand=True)
        self._callout = c

    def _fill_callout(self):
        if not self._callout:
            return
        for w in self._body.winfo_children():
            w.destroy()
        step = self._steps[self._i]
        total = len(self._steps)

        head = tk.Frame(self._body, bg=T.PANEL)
        head.pack(fill="x")
        tk.Label(head, text=f"Step {self._i + 1} of {total}", bg=T.PANEL,
                 fg=T.HIGHLIGHT, font=T.FONT_MICRO).pack(side="left")
        tk.Label(head, text="✕  Skip", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_MICRO, cursor="hand2").pack(side="right")
        head.winfo_children()[-1].bind("<Button-1>", lambda e: self._finish())

        tk.Label(self._body, text=step["title"], bg=T.PANEL, fg=T.FG,
                 font=(T.FONT_FAMILY, 13, "bold"), anchor="w",
                 justify="left", wraplength=self.CALLOUT_W - 32).pack(
                 fill="x", pady=(6, 2))
        tk.Label(self._body, text=step["text"], bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL, anchor="w", justify="left",
                 wraplength=self.CALLOUT_W - 32).pack(fill="x")

        if step.get("key"):
            chip = tk.Frame(self._body, bg=T.ACCENT)
            chip.pack(anchor="w", pady=(8, 0))
            tk.Label(chip, text=f" {step['key']} ", bg=T.ACCENT, fg=T.HIGHLIGHT,
                     font=T.FONT_BOLD, padx=6, pady=2).pack()

        # ── progress dots ────────────────────────────────────────────────
        dots = tk.Frame(self._body, bg=T.PANEL)
        dots.pack(anchor="w", pady=(12, 8))
        for d in range(total):
            tk.Label(dots, text="●", bg=T.PANEL,
                     fg=T.HIGHLIGHT if d == self._i else T.BORDER,
                     font=("Segoe UI", 8)).pack(side="left", padx=1)

        # ── buttons ──────────────────────────────────────────────────────
        btns = tk.Frame(self._body, bg=T.PANEL)
        btns.pack(fill="x")
        last = self._i == total - 1
        first = self._i == 0
        if not first:
            ActionButton(btns, text="Back", command=self._back,
                         secondary=True, width=80).pack(side="left")
        ActionButton(btns, text=("Finish" if last else "Next  ▶"),
                     command=self._next, width=110).pack(side="right")

    def _place_callout(self, bbox):
        if not self._callout:
            return
        try:
            self._callout.update_idletasks()
            cw = max(self.CALLOUT_W, self._callout.winfo_reqwidth())
            ch = self._callout.winfo_reqheight()
            sw = self._app.winfo_screenwidth()
            sh = self._app.winfo_screenheight()
            if bbox is None:
                # centre on the app window
                ax, ay = self._app.winfo_rootx(), self._app.winfo_rooty()
                aw, ah = self._app.winfo_width(), self._app.winfo_height()
                x = ax + (aw - cw) // 2
                y = ay + (ah - ch) // 2
            else:
                L, Tp, W, H = bbox
                x = L + W + 18           # prefer right of the target
                y = Tp
                if x + cw > sw - 12:     # no room right → below
                    x, y = L, Tp + H + 18
                if y + ch > sh - 12:     # no room below → above
                    y = max(12, Tp - ch - 18)
            x = max(12, min(x, sw - cw - 12))
            y = max(12, min(y, sh - ch - 12))
            self._callout.geometry(f"{cw}x{ch}+{x}+{y}")
        except tk.TclError:
            pass

    # ── navigation ──────────────────────────────────────────────────────────
    def _next(self):
        if self._i >= len(self._steps) - 1:
            self._finish()
            return
        self._i += 1
        self._show_step()

    def _back(self):
        if self._i > 0:
            self._i -= 1
            self._show_step()

    def _finish(self):
        if app_settings is not None:
            try:
                app_settings.set_and_save("tutorial_seen", True)
            except Exception:
                pass
        try:
            self._app.unbind("<Escape>")
        except Exception:
            pass
        for b in self._bars:
            try:
                b.destroy()
            except tk.TclError:
                pass
        self._bars = []
        if self._callout:
            try:
                self._callout.destroy()
            except tk.TclError:
                pass
            self._callout = None


def start_tutorial(app):
    """Force-start the tour (e.g. from Settings → Take a tour)."""
    try:
        InteractiveTutorial(app).start()
        return True
    except Exception:
        return False


def maybe_show_tutorial(app) -> bool:
    """Start the tour once on first run. Returns True if it will show."""
    if app_settings is None:
        return False
    try:
        if app_settings.get("tutorial_seen", False):
            return False
    except Exception:
        return False
    app.after(500, lambda: start_tutorial(app))
    return True
