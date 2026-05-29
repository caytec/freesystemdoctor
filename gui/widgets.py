"""Premium animated widgets — glassmorphism dark theme."""

import math
import tkinter as tk
from tkinter import ttk
from . import theme as T


# ── Card (glass panel) ────────────────────────────────────────────────────────

class Card(tk.Frame):
    """Glass-style card with optional animated border glow.

    Parameters
    ----------
    glow       : always-on pulsing border glow (original behaviour)
    hover_glow : glow activates only while the mouse is over the card,
                 then smoothly decays when the mouse leaves
    """

    def __init__(self, parent, glow: bool = False,
                 hover_glow: bool = False, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)
        self._glow       = glow
        self._hover_glow = hover_glow
        self._glow_phase = 0
        self._hg_active  = False   # True while mouse is inside
        self._hg_phase   = 0       # 0-30 → ramp up, then decay

        if glow:
            self._start_glow()
        if hover_glow:
            self.bind("<Enter>", self._hg_enter, add="+")
            self.bind("<Leave>", self._hg_leave, add="+")

    # ── always-on glow (original) ─────────────────────────────────────────────
    def _start_glow(self):
        self._glow_phase = (self._glow_phase + 1) % 60
        t = (math.sin(self._glow_phase * math.pi / 30) + 1) / 2
        color = T.lerp_color(T.BORDER, T.HIGHLIGHT, t * 0.5)
        self.config(highlightbackground=color, highlightthickness=1)
        self.after(50, self._start_glow)

    # ── hover glow ────────────────────────────────────────────────────────────
    def _hg_enter(self, _=None):
        self._hg_active = True
        self._hg_phase  = 0
        self._hg_step()

    def _hg_leave(self, _=None):
        self._hg_active = False
        # decay continues in _hg_step

    def _hg_step(self):
        max_phase = 30
        if self._hg_active:
            self._hg_phase = min(self._hg_phase + 2, max_phase)
        else:
            self._hg_phase = max(self._hg_phase - 2, 0)

        if self._hg_phase <= 0:
            try:
                self.config(highlightthickness=0)
            except tk.TclError:
                pass
            return

        t = self._hg_phase / max_phase
        color = T.lerp_color(T.BORDER, T.HIGHLIGHT, t * 0.65)
        try:
            self.config(highlightbackground=color, highlightthickness=1)
        except tk.TclError:
            return
        self.after(30, self._hg_step)


# ── Page header ───────────────────────────────────────────────────────────────

class PageHeader(tk.Frame):
    """Standardised 52 px page header bar — consistent across all pages.

    Layout (left→right):
        4 px colour accent strip | 10 px gap | icon (optional, 22 px emoji) |
        8 px gap | title (FONT_TITLE) | 12 px gap | subtitle (FONT_SMALL, FG2)

    Usage::
        PageHeader(page, title="Health Check", subtitle="Full system scan",
                   icon="❤", color=T.DANGER).pack(fill="x")
    """

    HEIGHT = 52

    def __init__(self, parent, title: str, subtitle: str = "",
                 icon: str = "", color: str = None, **kw):
        if color is None:
            color = T.HIGHLIGHT
        bg = T.lerp_color(T.ACCENT, color, 0.06)
        kw.setdefault("bg", bg)
        kw.setdefault("height", self.HEIGHT)
        super().__init__(parent, **kw)
        self.pack_propagate(False)

        # Left accent strip
        tk.Frame(self, bg=color, width=4).pack(side="left", fill="y")

        # Optional icon
        if icon:
            tk.Label(self, text=icon, bg=bg, fg=color,
                     font=(T.FONT_FAMILY, 18), padx=8).pack(side="left")

        # Title
        tk.Label(self, text=title, bg=bg, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=(8 if not icon else 0, 0))

        # Subtitle
        if subtitle:
            tk.Label(self, text=subtitle, bg=bg, fg=T.FG2,
                     font=T.FONT_SMALL).pack(side="left", padx=(10, 0))

        # Thin bottom border
        tk.Frame(self, bg=T.lerp_color(T.BORDER, color, 0.25),
                 height=1).place(relx=0, rely=1.0, relwidth=1, anchor="sw")


# ── Section label ─────────────────────────────────────────────────────────────

class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("fg", T.FG)
        kw.setdefault("font", T.FONT_H2)
        kw.setdefault("anchor", "w")
        super().__init__(parent, text=text, **kw)


# ── Action Button (animated glow) ─────────────────────────────────────────────

class ActionButton(tk.Canvas):
    """Premium button with gradient fill, hover glow, and click ripple."""
    HEIGHT = 36

    def __init__(self, parent, text: str, command=None, danger: bool = False,
                 secondary: bool = False, width: int = 0, **kw):
        try:
            parent_bg = parent.cget("bg") if hasattr(parent, "cget") else T.PANEL
            if not parent_bg or not parent_bg.startswith("#"):
                parent_bg = T.PANEL
        except Exception:
            parent_bg = T.PANEL
        kw.setdefault("bg", parent_bg)
        kw.setdefault("highlightthickness", 0)
        self._auto_width = (width == 0)
        super().__init__(parent, width=width, height=self.HEIGHT, **kw)

        self._text = text
        self._command = command
        self._hover = False
        self._pressed = False
        self._ripple = 0
        self._ripple_active = False
        self._enabled = True

        if danger:
            self._c1, self._c2 = "#cc2222", "#ee3333"
        elif secondary:
            self._c1, self._c2 = T.ACCENT, T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.3)
        else:
            self._c1, self._c2 = T.HIGHLIGHT_END, T.HIGHLIGHT

        self._draw()
        self.bind("<Enter>",          lambda e: self._on_enter())
        self.bind("<Leave>",          lambda e: self._on_leave())
        self.bind("<ButtonPress-1>",  lambda e: self._on_press())
        self.bind("<ButtonRelease-1>",lambda e: self._on_release())
        self.config(cursor="hand2")

    def _draw(self):
        self.delete("all")
        # Auto-size: measure text width and expand canvas if needed
        if self._auto_width:
            try:
                import tkinter.font as tkfont
                f = tkfont.Font(family=T.FONT_FAMILY, size=10, weight="bold")
                tw = f.measure(self._text)
            except Exception:
                tw = len(self._text) * 8
            needed = tw + 32
            cur = int(self.cget("width"))
            if cur != needed:
                self.config(width=needed)
        w = int(self.cget("width"))
        h = self.HEIGHT
        r = 6  # corner radius

        # Background gradient via horizontal strips
        if self._enabled:
            if self._pressed:
                c1, c2 = T.darken(self._c1, 0.2), T.darken(self._c2, 0.2)
            elif self._hover:
                c1, c2 = T.lighten(self._c1, 0.08), T.lighten(self._c2, 0.12)
            else:
                c1, c2 = self._c1, self._c2
        else:
            c1 = c2 = T.lerp_color(T.PANEL, T.BORDER, 0.5)

        steps = 20
        for i in range(steps):
            t = i / steps
            color = T.lerp_color(c1, c2, t)
            x0 = int(w * t / steps * steps)  # simplified: just cover width
            self.create_rectangle(i * w // steps, 0,
                                  (i + 1) * w // steps, h,
                                  fill=color, outline="")

        # Rounded corners (overdraw with background)
        bg = self.cget("bg")
        # Top-left / top-right / bottom-left / bottom-right corners
        for cx, cy in [(0, 0), (w, 0), (0, h), (w, h)]:
            self.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill=bg, outline="")
        self.create_oval(0, 0, r*2, r*2, fill=c1, outline="")
        self.create_oval(w-r*2, 0, w, r*2, fill=c2, outline="")
        self.create_oval(0, h-r*2, r*2, h, fill=c1, outline="")
        self.create_oval(w-r*2, h-r*2, w, h, fill=c2, outline="")

        # Subtle top shine
        if self._enabled and not self._pressed:
            shine = T.lerp_color(c2, "#ffffff", 0.18)
            self.create_rectangle(r, 1, w-r, h//2, fill=shine, outline="")
            self.create_rectangle(r, 1, w-r, h//4, fill=T.lighten(shine, 0.1), outline="")

        # Glow border on hover
        if self._hover and self._enabled:
            glow_c = T.lerp_color(self._c2, "#ffffff", 0.4)
            self.create_rectangle(1, 1, w-1, h-1, fill="", outline=glow_c)

        # Ripple
        if self._ripple_active and self._ripple < w:
            alpha = max(0, 0.3 - self._ripple / w * 0.3)
            ripple_c = T.lerp_color(c2, "#ffffff", 0.5)
            rr = self._ripple
            self.create_oval(w//2 - rr, h//2 - rr, w//2 + rr, h//2 + rr,
                             fill="", outline=ripple_c)

        # Text
        fg = "#ffffff" if self._enabled else T.FG2
        self.create_text(w//2, h//2, text=self._text,
                         fill=fg, font=T.FONT_BOLD)

    def _on_enter(self):
        if self._enabled:
            self._hover = True
            self._draw()

    def _on_leave(self):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self):
        if self._enabled:
            self._pressed = True
            self._ripple = 0
            self._ripple_active = True
            self._animate_ripple()
            self._draw()

    def _on_release(self):
        if self._enabled:
            self._pressed = False
            self._draw()
            if self._command:
                self._command()

    def _animate_ripple(self):
        if not self._ripple_active:
            return
        w = int(self.cget("width"))
        self._ripple += w // 8
        self._draw()
        if self._ripple >= w:
            self._ripple_active = False
            self._ripple = 0
        else:
            self.after(20, self._animate_ripple)

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.config(cursor="hand2" if enabled else "arrow")
        self._draw()

    # Compatibility shims for code using tk.Button API
    _BUTTON_ONLY_OPTS = {"font", "fg", "foreground", "padx", "pady",
                         "activebackground", "activeforeground",
                         "disabledforeground", "borderwidth", "bd",
                         "relief", "anchor", "justify", "wraplength",
                         "underline", "compound", "image"}

    def config(self, **kw):
        if "state" in kw:
            self._enabled = kw.pop("state") != "disabled"
            self._draw()
        if "text" in kw:
            self._text = kw.pop("text")
            self._draw()
        if "command" in kw:
            self._command = kw.pop("command")
        # Drop button-only options that Canvas doesn't accept
        for opt in list(kw.keys()):
            if opt in self._BUTTON_ONLY_OPTS:
                kw.pop(opt)
        if kw:
            try:
                super().config(**kw)
            except tk.TclError:
                pass

    def configure(self, **kw):
        self.config(**kw)

    def cget(self, key):
        if key == "state":
            return "normal" if self._enabled else "disabled"
        return super().cget(key)


# ── Status bar ────────────────────────────────────────────────────────────────

class StatusBar(tk.Frame):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.SIDEBAR)
        super().__init__(parent, **kw)
        self._icon = tk.Label(self, text="●", bg=T.SIDEBAR, fg=T.FG2,
                              font=T.FONT_MICRO, padx=8)
        self._icon.pack(side="left")
        self._lbl = tk.Label(self, text="Ready", bg=T.SIDEBAR, fg=T.FG2,
                             font=T.FONT_SMALL, anchor="w", pady=5)
        self._lbl.pack(side="left", fill="x", expand=True)
        self._animate_idle()

    def set(self, msg: str):
        self._lbl.config(text=f" {msg}", fg=T.FG)
        self._icon.config(fg=T.HIGHLIGHT)
        self.update_idletasks()
        self.after(3000, self._reset)

    def _reset(self):
        self._lbl.config(text="Ready", fg=T.FG2)
        self._icon.config(fg=T.FG2)

    def _animate_idle(self):
        pass  # kept for future use


# ── Progress bar ──────────────────────────────────────────────────────────────

class ProgressBar(tk.Frame):
    """Animated progress bar with shimmer effect."""
    HEIGHT = 8

    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.PANEL)
        super().__init__(parent, **kw)
        self._canvas = tk.Canvas(self, height=self.HEIGHT, bg=T.PANEL,
                                 highlightthickness=0, bd=0)
        self._canvas.pack(fill="x", expand=True)
        self._value = 0
        self._shimmer = 0
        self._shimmer_active = False
        self._indeterminate = False
        self._ind_pos = 0
        self._bind_width()

    def _bind_width(self):
        self._canvas.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        c = self._canvas
        c.delete("all")
        w = c.winfo_width() or 300
        h = self.HEIGHT
        r = h // 2

        # Track
        c.create_rectangle(r, 0, w-r, h, fill=T.BORDER, outline="")
        c.create_oval(0, 0, h, h, fill=T.BORDER, outline="")
        c.create_oval(w-h, 0, w, h, fill=T.BORDER, outline="")

        if self._indeterminate:
            # Bouncing segment
            seg_w = w // 3
            x = int(self._ind_pos)
            x = max(0, min(w - seg_w, x))
            c.create_rectangle(x, 0, x + seg_w, h, fill=T.HIGHLIGHT, outline="")
            c.create_oval(x, 0, x + h, h, fill=T.HIGHLIGHT, outline="")
            c.create_oval(x + seg_w - h, 0, x + seg_w, h, fill=T.HIGHLIGHT, outline="")
        else:
            fill_w = int(w * self._value / 100)
            if fill_w > 0:
                # Gradient fill
                steps = max(1, fill_w // 4)
                for i in range(steps):
                    t = i / steps
                    color = T.lerp_color(T.HIGHLIGHT_END, T.HIGHLIGHT, t)
                    self._canvas.create_rectangle(
                        r + i * (fill_w - h) // steps, 0,
                        r + (i + 1) * (fill_w - h) // steps + 1, h,
                        fill=color, outline=""
                    )
                # Caps
                c.create_oval(0, 0, h, h, fill=T.HIGHLIGHT_END, outline="")
                if fill_w >= h:
                    cap_x = fill_w
                    cap_c = T.lerp_color(T.HIGHLIGHT_END, T.HIGHLIGHT,
                                         fill_w / max(1, w))
                    c.create_oval(cap_x - h, 0, cap_x, h, fill=cap_c, outline="")

                # Shimmer
                if self._shimmer_active:
                    sx = int(self._shimmer * fill_w / 100)
                    c.create_rectangle(sx, 0, sx + 30, h,
                                       fill=T.lighten(T.HIGHLIGHT, 0.4), outline="")

    def set(self, value: float):
        self._value = max(0, min(100, value))
        self._indeterminate = False
        self._draw()

    set_value = set

    def indeterminate(self, start: bool = True):
        if start:
            self._indeterminate = True
            self._ind_pos = 0
            self._ind_dir = 1
            self._animate_ind()
        else:
            self._indeterminate = False
            self._ind_pos = 0
            self._value = 0
            self._draw()

    def _animate_ind(self):
        if not self._indeterminate:
            return
        w = self._canvas.winfo_width() or 300
        seg_w = w // 3
        self._ind_pos += self._ind_dir * 6
        if self._ind_pos >= w - seg_w:
            self._ind_dir = -1
        elif self._ind_pos <= 0:
            self._ind_dir = 1
        self._draw()
        self.after(16, self._animate_ind)


# ── Treeview style ────────────────────────────────────────────────────────────

def apply_treeview_style(tv=None):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
        background=T.PANEL, foreground=T.FG,
        fieldbackground=T.PANEL, rowheight=26, font=T.FONT_SMALL,
        borderwidth=0)
    style.configure("Treeview.Heading",
        background=T.ACCENT, foreground=T.HIGHLIGHT,
        font=T.FONT_BOLD, relief="flat", padding=(8, 5))
    style.map("Treeview",
        background=[("selected", T.lerp_color(T.HIGHLIGHT, T.BG, 0.6))],
        foreground=[("selected", T.HIGHLIGHT)])
    style.map("Treeview.Heading",
        relief=[("active", "flat")],
        background=[("active", T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.15))])


# ── Sidebar button ────────────────────────────────────────────────────────────

class SidebarButton(tk.Canvas):
    W, H = 72, 68

    def __init__(self, parent, icon: str, label: str, command=None,
                 notification: int = 0, **kw):
        kw.setdefault("bg", T.SIDEBAR)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self.W, height=self.H, **kw)
        self._icon = icon
        self._label = label
        self._command = command
        self._active = False
        self._hover = False
        self._notif = notification
        self._glow_phase = 0
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.config(cursor="hand2")

    def _draw(self):
        self.delete("all")
        w, h = self.W, self.H

        if self._active:
            # Active: glowing cyan accent bar on left + highlighted background
            bg = T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, 0.12)
            self.create_rectangle(0, 0, w, h, fill=bg, outline="")
            # Left accent bar with glow
            bar_c = T.HIGHLIGHT
            self.create_rectangle(0, 4, 3, h-4, fill=bar_c, outline="")
            # Soft glow behind bar
            glow = T.lerp_color(T.HIGHLIGHT, T.SIDEBAR, 0.6)
            self.create_rectangle(3, 4, 10, h-4, fill=glow, outline="")
            icon_fg = T.HIGHLIGHT
            text_fg = T.FG
        elif self._hover:
            bg = T.lerp_color(T.SIDEBAR, T.ACCENT, 0.7)
            self.create_rectangle(0, 0, w, h, fill=bg, outline="")
            # Subtle left bar
            self.create_rectangle(0, 8, 2, h-8,
                                  fill=T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, 0.5), outline="")
            icon_fg = T.lerp_color(T.FG2, T.FG, 0.7)
            text_fg = T.lerp_color(T.FG2, T.FG, 0.7)
        else:
            self.create_rectangle(0, 0, w, h, fill=T.SIDEBAR, outline="")
            icon_fg = T.FG2
            text_fg = T.FG2

        # Icon
        self.create_text(w//2, h//2 - 10, text=self._icon,
                         fill=icon_fg, font=T.FONT_ICON)
        # Label
        self.create_text(w//2, h//2 + 16, text=self._label,
                         fill=text_fg, font=(T.FONT_FAMILY, 7),
                         width=w - 4)

        # Notification dot
        if self._notif > 0:
            dot_x, dot_y = w - 10, 8
            dot_r = 7
            self.create_oval(dot_x - dot_r, dot_y - dot_r,
                             dot_x + dot_r, dot_y + dot_r,
                             fill=T.DANGER, outline="")
            txt = str(self._notif) if self._notif < 10 else "9+"
            self.create_text(dot_x, dot_y, text=txt,
                             fill="#ffffff", font=T.FONT_MICRO)

    def _on_click(self, e=None):
        if self._command:
            self._command()

    def _on_enter(self, e=None):
        if not self._active:
            self._hover = True
            self._draw()

    def _on_leave(self, e=None):
        self._hover = False
        self._draw()

    def set_active(self, active: bool):
        self._active = active
        self._hover = False
        self._draw()

    def set_notification(self, count: int):
        self._notif = count
        self._draw()


# ── Animated scan button ──────────────────────────────────────────────────────

class CircleScanButton(tk.Canvas):
    _SIZE = 200
    _GLOW_STEPS = 36

    def __init__(self, parent, command=None, **kw):
        kw.setdefault("bg", T.BG)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self._SIZE, height=self._SIZE, **kw)
        self._command  = command
        self._scanning = False
        self._glow_idx = 0
        self._pulse    = 0
        self._pulse_dir = 1
        self._hover    = False
        self._spin_angle = 0

        self._draw(0)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def _set_hover(self, h: bool):
        self._hover = h
        if not self._scanning:
            self._draw(self._pulse)

    def _draw(self, glow_step: int = 0):
        self.delete("all")
        cx = cy = self._SIZE // 2
        r_outer = cx - 8
        r_inner = r_outer - 14
        r_btn   = r_inner - 12

        t = glow_step / self._GLOW_STEPS

        # Outer glow rings (pulsing)
        for layer in range(4):
            expand = t * 8 * (layer + 1) * 0.5
            r = r_outer + expand
            alpha = max(0, 0.6 - layer * 0.15) * t
            ring_col = T.lerp_color(T.BG, T.HIGHLIGHT, alpha)
            self.create_oval(cx-r, cy-r, cx+r, cy+r,
                             outline=ring_col, width=max(1, 2 - layer * 0.5))

        # Outer ring
        ring_bg = T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.15 if self._hover else 0.05)
        self.create_oval(cx-r_outer, cy-r_outer, cx+r_outer, cy+r_outer,
                         fill=ring_bg, outline=T.lerp_color(T.BORDER, T.HIGHLIGHT, 0.3))

        # Spinning arcs when scanning
        if self._scanning:
            # Outer spinning arc
            start = self._spin_angle % 360
            arc_c = T.HIGHLIGHT
            self.create_arc(cx-r_outer+2, cy-r_outer+2, cx+r_outer-2, cy+r_outer-2,
                            start=start, extent=100, style="arc",
                            outline=arc_c, width=3)
            # Counter-rotating inner arc
            self.create_arc(cx-r_inner-4, cy-r_inner-4, cx+r_inner+4, cy+r_inner+4,
                            start=(-start*1.5)%360, extent=70, style="arc",
                            outline=T.PURPLE, width=2)
        else:
            # Progress-style ring indicator (idle)
            self.create_arc(cx-r_outer+2, cy-r_outer+2, cx+r_outer-2, cy+r_outer-2,
                            start=90, extent=int(-t*360), style="arc",
                            outline=T.lerp_color(T.BORDER, T.HIGHLIGHT, 0.4), width=2)

        # Inner button face
        face_c = T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.1 if not self._hover else 0.2)
        self.create_oval(cx-r_inner, cy-r_inner, cx+r_inner, cy+r_inner,
                         fill=face_c, outline=T.lerp_color(T.BORDER, T.HIGHLIGHT, 0.25))

        # Subtle shine arc on inner face
        shine = T.lerp_color(face_c, "#ffffff", 0.07)
        self.create_arc(cx-r_inner+4, cy-r_inner+4, cx+r_inner-4, cy+r_inner-4,
                        start=30, extent=120, style="arc",
                        outline=shine, width=8)

        # Text
        if self._scanning:
            self.create_text(cx, cy-12, text="SCANNING", fill=T.HIGHLIGHT, font=T.FONT_SCAN)
            self.create_text(cx, cy+12, text="Please wait…", fill=T.FG2, font=T.FONT_SMALL)
        else:
            label_color = T.HIGHLIGHT if self._hover else T.FG
            self.create_text(cx, cy-10, text="SCAN", fill=label_color, font=T.FONT_SCAN)
            self.create_text(cx, cy+14, text="Click to start", fill=T.FG2, font=T.FONT_SMALL)

    def _on_click(self, e=None):
        if not self._scanning and self._command:
            self._command()

    def set_scanning(self, scanning: bool):
        self._scanning = scanning
        if scanning:
            self._animate()
        else:
            self._pulse = 0
            self._spin_angle = 0
            self._draw(0)

    def _animate(self):
        if not self._scanning:
            return
        self._glow_idx = (self._glow_idx + 1) % self._GLOW_STEPS
        self._pulse   += self._pulse_dir
        self._spin_angle = (self._spin_angle + 4) % 360
        if self._pulse >= self._GLOW_STEPS - 1:
            self._pulse_dir = -1
        elif self._pulse <= 0:
            self._pulse_dir = 1
        self._draw(self._pulse)
        self.after(30, self._animate)


# ── Toggle switch ─────────────────────────────────────────────────────────────

class ToggleSwitch(tk.Canvas):
    W, H = 56, 28

    def __init__(self, parent, variable: tk.BooleanVar = None, command=None, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self.W, height=self.H, **kw)
        self._var     = variable if variable is not None else tk.BooleanVar(value=False)
        self._command = command
        self._knob_x  = None
        self._animating = False
        self._draw()
        self.bind("<Button-1>", self._toggle)
        self._var.trace_add("write", lambda *_: self._animate_toggle())
        self.config(cursor="hand2")

    def _draw(self, knob_x: float = None):
        self.delete("all")
        on = self._var.get()
        track = T.TOGGLE_ON if on else T.TOGGLE_OFF

        target_x = self.W - self.H//2 - 4 if on else self.H//2 + 4
        cx = knob_x if knob_x is not None else target_x

        # Track background
        self.create_oval(0, 0, self.H, self.H, fill=track, outline="")
        self.create_oval(self.W-self.H, 0, self.W, self.H, fill=track, outline="")
        self.create_rectangle(self.H//2, 0, self.W-self.H//2, self.H,
                              fill=track, outline="")

        # Glow when ON
        if on:
            glow = T.lerp_color(T.TOGGLE_ON, T.BG, 0.5)
            self.create_oval(-2, -2, self.H+2, self.H+2, fill="", outline=glow)
            self.create_oval(self.W-self.H-2, -2, self.W+2, self.H+2,
                             fill="", outline=glow)

        # Knob
        pad = 3
        kx = int(cx)
        knob_c = "#ffffff" if on else T.lerp_color(T.FG, T.FG2, 0.3)
        self.create_oval(kx - self.H//2 + pad, pad,
                         kx + self.H//2 - pad, self.H - pad,
                         fill=knob_c, outline="")
        # Shine
        kp = pad + 2
        shine = T.lerp_color(knob_c, "#ffffff", 0.4)
        self.create_oval(kx - self.H//2 + kp, kp + 1,
                         kx, self.H//2 - 1,
                         fill=shine, outline="")

    def _animate_toggle(self):
        if self._animating:
            return
        on = self._var.get()
        start_x = self.H//2 + 4 if on else self.W - self.H//2 - 4
        end_x   = self.W - self.H//2 - 4 if on else self.H//2 + 4
        steps = 8
        self._animating = True

        def step(i):
            if i > steps:
                self._animating = False
                self._draw()
                return
            t = i / steps
            # Ease out cubic
            t_ease = 1 - (1 - t) ** 3
            x = start_x + (end_x - start_x) * t_ease
            self._draw(x)
            self.after(12, lambda: step(i + 1))

        step(0)

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
        kw.setdefault("padx", 10)
        kw.setdefault("pady", 4)
        kw.setdefault("relief", "flat")
        super().__init__(parent, text="Checking…", **kw)
        self.set_warning("Checking…")

    def set_ok(self, text="Protected"):
        self.config(text=f"✓  {text}", bg=T.BADGE_OK, fg=T.SUCCESS)

    def set_error(self, text="At Risk"):
        self.config(text=f"✕  {text}", bg=T.BADGE_ERR, fg=T.DANGER)

    def set_warning(self, text="Checking…"):
        self.config(text=f"⚠  {text}", bg=T.BADGE_WARN, fg=T.WARNING)


# ── RAM arc gauge ─────────────────────────────────────────────────────────────

class RAMGauge(tk.Canvas):
    W, H = 220, 140

    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, width=self.W, height=self.H, **kw)
        self._current_pct = 0
        self._target_pct = 0
        self.update_gauge(0, "0 GB", "0 GB")

    def update_gauge(self, pct: float, used_str: str, total_str: str):
        self._target_pct = pct
        self._used_str = used_str
        self._total_str = total_str
        self._animate_to(pct)

    def _animate_to(self, target: float, current: float = None):
        if current is None:
            current = self._current_pct
        if abs(current - target) < 0.5:
            self._current_pct = target
            self._draw(target)
            return
        next_val = current + (target - current) * 0.15
        self._current_pct = next_val
        self._draw(next_val)
        self.after(20, lambda: self._animate_to(target, next_val))

    def _draw(self, pct: float):
        self.delete("all")
        cx, cy = self.W // 2, self.H - 10
        r = 90
        pct = max(0, min(100, pct))

        # Track glow
        self.create_arc(cx-r-2, cy-r-2, cx+r+2, cy+r+2,
                        start=0, extent=180, style="arc",
                        outline=T.lerp_color(T.BORDER, T.HIGHLIGHT, 0.1), width=18)
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
            # Glow under fill
            glow_c = T.lerp_color(color, T.BG, 0.5)
            self.create_arc(cx-r, cy-r, cx+r, cy+r,
                            start=0, extent=angle, style="arc",
                            outline=glow_c, width=20)
            self.create_arc(cx-r, cy-r, cx+r, cy+r,
                            start=0, extent=angle, style="arc",
                            outline=color, width=14)

        # Center text
        self.create_text(cx, cy-30, text=f"{pct:.0f}%",
                         fill=color, font=(T.FONT_FAMILY, 22, "bold"))
        self.create_text(cx, cy-8, text=f"{self._used_str} / {self._total_str}",
                         fill=T.FG2, font=T.FONT_SMALL)
        self.create_text(cx-r+8, cy+4, text="0%",   fill=T.FG2, font=T.FONT_MICRO)
        self.create_text(cx+r-8, cy+4, text="100%", fill=T.FG2, font=T.FONT_MICRO)


# ── Issue count badge ─────────────────────────────────────────────────────────

class IssueBadge(tk.Label):
    def __init__(self, parent, **kw):
        kw.setdefault("font", T.FONT_BOLD)
        kw.setdefault("padx", 12)
        kw.setdefault("pady", 4)
        super().__init__(parent, text="–", **kw)
        self._set("–", T.ACCENT, T.FG2)

    def _set(self, text, bg, fg=None):
        self.config(text=text, bg=bg, fg=fg or T.FG)

    def set_count(self, n: int):
        if n == 0:
            self._set("✓  All Clear", T.BADGE_OK, T.SUCCESS)
        elif n > 0:
            self._set(f"⚠  {n} issue{'s' if n != 1 else ''}", T.BADGE_ERR, T.DANGER)
        else:
            self._set("–", T.ACCENT, T.FG2)

    def set_scanning(self):
        self._set("⟳  Scanning…", T.BADGE_WARN, T.WARNING)

    def set_pending(self):
        self._set("–", T.ACCENT, T.FG2)


# ── Mini metric card ──────────────────────────────────────────────────────────

class MetricCard(tk.Frame):
    """Small card showing an icon, value and label — used in dashboard grids."""
    def __init__(self, parent, icon: str, label: str, value: str = "–",
                 color: str = None, **kw):
        kw.setdefault("bg", T.PANEL)
        kw.setdefault("padx", 12)
        kw.setdefault("pady", 10)
        super().__init__(parent, **kw)
        color = color or T.HIGHLIGHT

        self._icon_lbl = tk.Label(self, text=icon, bg=T.PANEL,
                                  fg=color, font=(T.FONT_FAMILY, 20))
        self._icon_lbl.pack(anchor="w")

        self._val_lbl = tk.Label(self, text=value, bg=T.PANEL,
                                 fg=T.FG, font=(T.FONT_FAMILY, 16, "bold"))
        self._val_lbl.pack(anchor="w")

        tk.Label(self, text=label, bg=T.PANEL,
                 fg=T.FG2, font=T.FONT_MICRO).pack(anchor="w")

        # Hover glow effect
        self._color = color
        for w in (self, self._icon_lbl, self._val_lbl):
            w.bind("<Enter>", lambda e: self._on_enter())
            w.bind("<Leave>", lambda e: self._on_leave())

    def _on_enter(self):
        glow_bg = T.lerp_color(T.PANEL, self._color, 0.08)
        self.config(bg=glow_bg)
        for child in self.winfo_children():
            try:
                child.config(bg=glow_bg)
            except Exception:
                pass

    def _on_leave(self):
        self.config(bg=T.PANEL)
        for child in self.winfo_children():
            try:
                child.config(bg=T.PANEL)
            except Exception:
                pass

    def update_value(self, value: str, color: str = None):
        self._val_lbl.config(text=value)
        if color:
            self._icon_lbl.config(fg=color)


# ── Notification toast ────────────────────────────────────────────────────────

class Toast:
    """Temporary floating notification in bottom-right corner."""
    _instances = []

    @classmethod
    def show(cls, parent_root, message: str, kind: str = "info", duration: int = 3500):
        toast = cls(parent_root, message, kind, duration)
        cls._instances.append(toast)

    def __init__(self, root, message: str, kind: str, duration: int):
        icons = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✕"}
        colors = {"info": T.HIGHLIGHT, "success": T.SUCCESS,
                  "warning": T.WARNING, "error": T.DANGER}
        icon   = icons.get(kind, "ℹ")
        color  = colors.get(kind, T.HIGHLIGHT)

        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.configure(bg=T.PANEL)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.0)

        frame = tk.Frame(self._win, bg=T.PANEL, padx=14, pady=10)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=icon, bg=T.PANEL, fg=color,
                 font=(T.FONT_FAMILY, 14, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(frame, text=message, bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, wraplength=260).pack(side="left")

        # Left accent bar
        tk.Frame(self._win, bg=color, width=3).place(x=0, y=0, relheight=1.0)

        # Position bottom-right
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        self._win.update_idletasks()
        ww = self._win.winfo_reqwidth() + 6
        wh = self._win.winfo_reqheight()

        # Stack toasts
        offset = len(Toast._instances) * (wh + 8)
        x = sw - ww - 20
        y = sh - 60 - wh - offset
        self._win.geometry(f"{ww}x{wh}+{x}+{y}")

        # Fade in
        self._fade_in(duration)

    def _fade_in(self, duration: int, alpha: float = 0.0):
        if alpha < 0.95:
            alpha = min(0.95, alpha + 0.07)
            self._win.attributes("-alpha", alpha)
            self._win.after(16, lambda: self._fade_in(duration, alpha))
        else:
            self._win.after(duration, self._fade_out)

    def _fade_out(self, alpha: float = 0.95):
        if alpha > 0.0:
            alpha = max(0.0, alpha - 0.06)
            self._win.attributes("-alpha", alpha)
            self._win.after(16, lambda: self._fade_out(alpha))
        else:
            try:
                Toast._instances.remove(self)
                self._win.destroy()
            except Exception:
                pass
