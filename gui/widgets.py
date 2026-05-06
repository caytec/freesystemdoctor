"""Reusable custom widgets — refined aesthetic."""

import math
import tkinter as tk
from tkinter import ttk
from . import theme as T


# ── Card ──────────────────────────────────────────────────────────────────────

class Card(tk.Frame):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)


# ── Section label ─────────────────────────────────────────────────────────────

class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("fg", T.FG)
        kw.setdefault("font", T.FONT_H2)
        kw.setdefault("anchor", "w")
        super().__init__(parent, text=text, **kw)


# ── Action Button ─────────────────────────────────────────────────────────────

class ActionButton(tk.Button):
    """
    Styled button with soft colour, hover/press feedback, and readable white text.
    danger=True uses a muted red instead of the primary blue.
    """
    def __init__(self, parent, text: str, command=None, danger: bool = False, **kw):
        if danger:
            self._base   = "#b03030"   # muted red
            self._hover  = "#c94040"
            self._press  = "#8a2020"
        else:
            self._base   = T.HIGHLIGHT       # soft blue
            self._hover  = T.lighten(T.HIGHLIGHT, 0.12)
            self._press  = T.HIGHLIGHT_END

        kw.setdefault("bg",              self._base)
        kw.setdefault("fg",              "#ffffff")
        kw.setdefault("font",            T.FONT_BOLD)
        kw.setdefault("relief",          "flat")
        kw.setdefault("cursor",          "hand2")
        kw.setdefault("padx",            14)
        kw.setdefault("pady",            6)
        kw.setdefault("activebackground", self._hover)
        kw.setdefault("activeforeground", "#ffffff")
        kw.setdefault("borderwidth",     0)
        super().__init__(parent, text=text, command=command, **kw)

        self.bind("<Enter>",           lambda e: self._on_enter())
        self.bind("<Leave>",           lambda e: self._on_leave())
        self.bind("<ButtonPress-1>",   lambda e: self._on_press())
        self.bind("<ButtonRelease-1>", lambda e: self._on_release())

    def _on_enter(self):
        if str(self.cget("state")) != "disabled":
            self.config(bg=self._hover)

    def _on_leave(self):
        if str(self.cget("state")) != "disabled":
            self.config(bg=self._base)

    def _on_press(self):
        if str(self.cget("state")) != "disabled":
            self.config(bg=self._press)

    def _on_release(self):
        if str(self.cget("state")) != "disabled":
            self.config(bg=self._hover)


# ── Status bar ────────────────────────────────────────────────────────────────

class StatusBar(tk.Label):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.SIDEBAR)
        kw.setdefault("fg", T.FG2)
        kw.setdefault("font", T.FONT_SMALL)
        kw.setdefault("anchor", "w")
        kw.setdefault("padx", 12)
        kw.setdefault("pady", 5)
        super().__init__(parent, text="Ready", **kw)

    def set(self, msg: str):
        self.config(text=f"  {msg}")
        self.update_idletasks()


# ── Progress bar ──────────────────────────────────────────────────────────────

class ProgressBar(tk.Frame):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.PANEL)
        super().__init__(parent, **kw)
        self._bar = ttk.Progressbar(self, mode="determinate", length=300)
        self._bar.pack(fill="x", expand=True)

    def set(self, value: float):
        self._bar["value"] = value

    set_value = set

    def indeterminate(self, start: bool = True):
        self._bar.config(mode="indeterminate")
        if start:
            self._bar.start(15)
        else:
            self._bar.stop()
            self._bar.config(mode="determinate")
            self._bar["value"] = 0


# ── Treeview style ────────────────────────────────────────────────────────────

def apply_treeview_style(tv=None):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
        background=T.PANEL, foreground=T.FG,
        fieldbackground=T.PANEL, rowheight=24, font=T.FONT_SMALL,
        borderwidth=0)
    style.configure("Treeview.Heading",
        background=T.ACCENT, foreground=T.FG,
        font=T.FONT_BOLD, relief="flat", padding=(6, 4))
    style.map("Treeview",
        background=[("selected", T.HIGHLIGHT)],
        foreground=[("selected", "#ffffff")])
    style.map("Treeview.Heading",
        relief=[("active", "flat")],
        background=[("active", T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.2))])


# ── Sidebar button ────────────────────────────────────────────────────────────

class SidebarButton(tk.Frame):
    def __init__(self, parent, icon: str, label: str, command=None, **kw):
        kw.setdefault("bg", T.SIDEBAR)
        kw.setdefault("cursor", "hand2")
        super().__init__(parent, **kw)
        self._command = command
        self._active  = False

        self._accent_bar = tk.Frame(self, bg=T.SIDEBAR, width=3)
        self._accent_bar.pack(side="left", fill="y")

        content = tk.Frame(self, bg=T.SIDEBAR)
        content.pack(side="left", fill="both", expand=True)

        self._icon_lbl = tk.Label(content, text=icon, bg=T.SIDEBAR, fg=T.FG2,
                                   font=T.FONT_ICON)
        self._icon_lbl.pack(pady=(10, 0))
        self._text_lbl = tk.Label(content, text=label, bg=T.SIDEBAR, fg=T.FG2,
                                   font=(T.FONT_FAMILY, 8))
        self._text_lbl.pack(pady=(1, 10))

        self._content = content
        for w in (self, content, self._icon_lbl, self._text_lbl, self._accent_bar):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>",    self._on_enter)
            w.bind("<Leave>",    self._on_leave)

    def _on_click(self, e=None):
        if self._command:
            self._command()

    def _on_enter(self, e=None):
        if not self._active:
            hover_bg = T.lerp_color(T.SIDEBAR, T.ACCENT, 0.6)
            self._set_colors(hover_bg, T.FG, T.SIDEBAR)

    def _on_leave(self, e=None):
        if not self._active:
            self._set_colors(T.SIDEBAR, T.FG2, T.SIDEBAR)

    def set_active(self, active: bool):
        self._active = active
        if active:
            self._set_colors(T.ACCENT, T.FG, T.HIGHLIGHT)
        else:
            self._set_colors(T.SIDEBAR, T.FG2, T.SIDEBAR)

    def _set_colors(self, bg: str, fg: str, bar: str):
        self.config(bg=bg)
        self._content.config(bg=bg)
        self._icon_lbl.config(bg=bg, fg=fg)
        self._text_lbl.config(bg=bg, fg=fg)
        self._accent_bar.config(bg=bar)


# ── Animated scan button ──────────────────────────────────────────────────────

class CircleScanButton(tk.Canvas):
    _SIZE = 200
    _GLOW_STEPS = 24

    def __init__(self, parent, command=None, **kw):
        kw.setdefault("bg", T.BG)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self._SIZE, height=self._SIZE, **kw)
        self._command  = command
        self._scanning = False
        self._glow_idx = 0
        self._pulse    = 0
        self._pulse_dir = 1

        self._glow_colors = [
            T.lerp_color(T.ACCENT, T.SCAN_GLOW, i / (self._GLOW_STEPS - 1))
            for i in range(self._GLOW_STEPS)
        ]

        self._draw(0)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self._draw(self._pulse, hover=True))
        self.bind("<Leave>", lambda e: self._draw(self._pulse, hover=False))

    def _draw(self, glow_step: int = 0, hover: bool = False, scanning: bool = False):
        self.delete("all")
        cx = cy = self._SIZE // 2
        r_outer = cx - 6
        r_inner = r_outer - 12
        r_btn   = r_inner - 10

        # Outer glow rings
        for layer in range(3):
            expand = (glow_step / self._GLOW_STEPS) * 6 * (layer + 1)
            r = r_outer + expand
            ci = min(int(glow_step * (len(self._glow_colors)-1) / self._GLOW_STEPS),
                     len(self._glow_colors)-1)
            ring_col = T.lerp_color(self._glow_colors[ci], T.BG, layer * 0.4)
            self.create_oval(cx-r, cy-r, cx+r, cy+r,
                             outline=ring_col, width=max(1, 2 - layer))

        # Ring background
        ring_bg = T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.18) if hover else T.ACCENT
        self.create_oval(cx-r_outer, cy-r_outer, cx+r_outer, cy+r_outer,
                         fill=ring_bg, outline="")

        # Spinning arc
        if scanning:
            start = (self._glow_idx * 15) % 360
            self.create_arc(cx-r_outer, cy-r_outer, cx+r_outer, cy+r_outer,
                            start=start, extent=110, style="arc",
                            outline=T.SCAN_GLOW, width=3)

        # Inner button face — gradient via two overlapping ovals
        face_base = T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.08 if not hover else 0.2)
        face_top  = T.lerp_color(face_base, "#ffffff", 0.06)
        self.create_oval(cx-r_inner, cy-r_inner, cx+r_inner, cy+r_inner,
                         fill=face_base, outline=T.BORDER, width=1)
        # Subtle top-half shine
        self.create_arc(cx-r_inner+2, cy-r_inner+2, cx+r_inner-2, cy+r_inner-2,
                        start=30, extent=120, style="arc",
                        outline=face_top, width=6)

        # Text
        if scanning:
            self.create_text(cx, cy-8, text="SCANNING", fill=T.FG, font=T.FONT_SCAN)
            self.create_text(cx, cy+16, text="Please wait…", fill=T.FG2, font=T.FONT_SMALL)
        else:
            label_color = T.HIGHLIGHT if hover else T.FG
            self.create_text(cx, cy-8, text="SCAN", fill=label_color, font=T.FONT_SCAN)
            self.create_text(cx, cy+16, text="Click to start", fill=T.FG2, font=T.FONT_SMALL)

    def _on_click(self, e=None):
        if not self._scanning and self._command:
            self._command()

    def set_scanning(self, scanning: bool):
        self._scanning = scanning
        if scanning:
            self._animate()
        else:
            self._pulse = 0
            self._draw(0)

    def _animate(self):
        if not self._scanning:
            return
        self._glow_idx = (self._glow_idx + 1) % self._GLOW_STEPS
        self._pulse   += self._pulse_dir
        if self._pulse >= self._GLOW_STEPS - 1:
            self._pulse_dir = -1
        elif self._pulse <= 0:
            self._pulse_dir = 1
        self._draw(self._pulse, scanning=True)
        self.after(60, self._animate)


# ── Toggle switch ─────────────────────────────────────────────────────────────

class ToggleSwitch(tk.Canvas):
    W, H = 52, 26

    def __init__(self, parent, variable: tk.BooleanVar = None, command=None, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self.W, height=self.H, **kw)
        self._var     = variable if variable is not None else tk.BooleanVar(value=False)
        self._command = command
        self._draw()
        self.bind("<Button-1>", self._toggle)
        self._var.trace_add("write", lambda *_: self._draw())

    def _draw(self):
        self.delete("all")
        on = self._var.get()
        track = T.TOGGLE_ON if on else T.TOGGLE_OFF
        cx    = self.W - 13 if on else 13

        # Track
        self.create_oval(0, 0, self.H, self.H, fill=track, outline="")
        self.create_oval(self.W-self.H, 0, self.W, self.H, fill=track, outline="")
        self.create_rectangle(self.H//2, 0, self.W-self.H//2, self.H,
                              fill=track, outline="")

        # Knob with subtle gradient
        pad = 3
        knob_col = T.FG if on else T.lerp_color(T.FG, T.FG2, 0.4)
        self.create_oval(cx-self.H//2+pad, pad,
                         cx+self.H//2-pad, self.H-pad,
                         fill=knob_col, outline="")
        # Tiny shine on knob
        shine = T.lerp_color(knob_col, "#ffffff", 0.35)
        kp = pad + 2
        self.create_oval(cx-self.H//2+kp, kp+1,
                         cx, self.H//2,
                         fill=shine, outline="")

    def _toggle(self, e=None):
        self._var.set(not self._var.get())
        if self._command:
            self._command()

    @property
    def value(self) -> bool:
        return self._var.get()

    def set(self, val: bool):
        self._var.set(val)


# ── Status badge ──────────────────────────────────────────────────────────────

class StatusBadge(tk.Label):
    def __init__(self, parent, **kw):
        kw.setdefault("font", T.FONT_SMALL)
        kw.setdefault("padx", 8)
        kw.setdefault("pady", 3)
        kw.setdefault("relief", "flat")
        super().__init__(parent, text="Checking…", **kw)
        self.set_warning("Checking…")

    def set_ok(self, text="Protected"):
        self.config(text=text, bg=T.BADGE_OK, fg="#a8e6c0")

    def set_error(self, text="At Risk"):
        self.config(text=text, bg=T.BADGE_ERR, fg="#f4a0a0")

    def set_warning(self, text="Checking…"):
        self.config(text=text, bg=T.BADGE_WARN, fg="#f5c68a")


# ── RAM arc gauge ─────────────────────────────────────────────────────────────

class RAMGauge(tk.Canvas):
    W, H = 220, 130

    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self.W, height=self.H, **kw)
        self.update_gauge(0, "0 GB", "0 GB")

    def update_gauge(self, pct: float, used_str: str, total_str: str):
        self.delete("all")
        cx, cy = self.W // 2, self.H - 10
        r = 88
        pct = max(0, min(100, pct))

        # Track
        self.create_arc(cx-r, cy-r, cx+r, cy+r,
                        start=0, extent=180, style="arc",
                        outline=T.BORDER, width=14)
        # Fill
        if pct < 60:
            color = T.lerp_color(T.SUCCESS, T.WARNING, pct / 60)
        else:
            color = T.lerp_color(T.WARNING, T.DANGER, (pct - 60) / 40)
        angle = int(pct / 100 * 180)
        if angle > 0:
            self.create_arc(cx-r, cy-r, cx+r, cy+r,
                            start=0, extent=angle, style="arc",
                            outline=color, width=14)

        self.create_text(cx, cy-26, text=f"{pct:.0f}%",
                         fill=color, font=T.FONT_TITLE)
        self.create_text(cx, cy-6, text=f"{used_str} / {total_str}",
                         fill=T.FG2, font=T.FONT_SMALL)
        self.create_text(cx-r+8, cy+4, text="0%",   fill=T.FG2, font=T.FONT_SMALL)
        self.create_text(cx+r-8, cy+4, text="100%", fill=T.FG2, font=T.FONT_SMALL)


# ── Issue count badge ─────────────────────────────────────────────────────────

class IssueBadge(tk.Label):
    def __init__(self, parent, **kw):
        kw.setdefault("font", T.FONT_BOLD)
        kw.setdefault("padx", 10)
        kw.setdefault("pady", 3)
        super().__init__(parent, text="–", **kw)
        self._set("–", T.ACCENT, T.FG2)

    def _set(self, text, bg, fg=None):
        self.config(text=text, bg=bg, fg=fg or T.FG)

    def set_count(self, n: int):
        if n == 0:
            self._set("✓ OK", T.BADGE_OK, "#a8e6c0")
        elif n > 0:
            self._set(f"{n} issue{'s' if n != 1 else ''}", T.BADGE_ERR, "#f4a0a0")
        else:
            self._set("–", T.ACCENT, T.FG2)

    def set_scanning(self):
        self._set("Scanning…", T.BADGE_WARN, "#f5c68a")

    def set_pending(self):
        self._set("–", T.ACCENT, T.FG2)
