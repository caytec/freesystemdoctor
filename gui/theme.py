"""Central colour / font constants — AiPOL SA corporate AI navy/blue theme.

Palette aligned with AiPOL SA (aipol.com.pl): deep navy backgrounds with an
electric-blue primary accent and a teal secondary accent.
"""

# ── Backgrounds ───────────────────────────────────────────────────────────────
BG      = "#0a1020"   # deep navy
PANEL   = "#111a2e"   # card / panel
ACCENT  = "#1a2640"   # header / elevated panels
SIDEBAR = "#070c18"   # sidebar (deepest navy)

# ── Brand colours ─────────────────────────────────────────────────────────────
HIGHLIGHT     = "#2f6bff"   # electric blue — AiPOL primary accent
HIGHLIGHT_END = "#1e50d8"   # gradient end (deeper blue)
SCAN_GLOW     = "#5b86ff"   # bright blue for glow effects
PURPLE        = "#19c3c3"   # secondary accent — teal (AiPOL)
PURPLE_END    = "#0f9a9a"   # teal gradient end

# ── Semantic colours ──────────────────────────────────────────────────────────
SUCCESS = "#18c08f"   # teal-green
WARNING = "#f5a623"   # amber
DANGER  = "#ff5c5c"   # red
INFO    = "#4d8bff"   # info blue

# ── Badge backgrounds ─────────────────────────────────────────────────────────
BADGE_OK   = "#0c2e24"
BADGE_WARN = "#332600"
BADGE_ERR  = "#3a1414"

# ── Toggle ────────────────────────────────────────────────────────────────────
TOGGLE_ON  = "#2f6bff"
TOGGLE_OFF = "#1a2640"

# ── Text ──────────────────────────────────────────────────────────────────────
FG  = "#eaf0fb"   # primary — crisp white-blue
FG2 = "#8d99ba"   # secondary / muted (readable on navy)

# ── Borders / dividers ────────────────────────────────────────────────────────
BORDER     = "#1e2c4a"
BORDER_GLOW = "#2f6bff"   # highlighted border

# ── Glass effect colors ───────────────────────────────────────────────────────
GLASS_BG   = "#111a2ecc"  # semi-transparent panel
GLASS_EDGE = "#ffffff14"  # subtle glass rim

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"
FONT_BODY   = (FONT_FAMILY, 10)
FONT_SMALL  = (FONT_FAMILY, 9)
FONT_BOLD   = (FONT_FAMILY, 10, "bold")
FONT_TITLE  = (FONT_FAMILY, 13, "bold")
FONT_H2     = (FONT_FAMILY, 11, "bold")
FONT_H3     = (FONT_FAMILY, 10, "bold")
FONT_SCORE  = (FONT_FAMILY, 40, "bold")
FONT_ICON   = (FONT_FAMILY, 18)
FONT_SCAN   = (FONT_FAMILY, 20, "bold")
FONT_MICRO  = (FONT_FAMILY, 8)
FONT_LARGE  = (FONT_FAMILY, 15, "bold")


# ── Utilities ─────────────────────────────────────────────────────────────────

# ── Animation timing ──────────────────────────────────────────────────────────
TRANSITION_MS = 220   # page reveal total duration (ms)
STAGGER_MS    = 38    # per-item stagger delay in sidebar reveal (ms)
FRAME_MS      = 16    # ~60 fps animation frame interval


# ── Easing functions ──────────────────────────────────────────────────────────
# All take t in [0, 1] and return an eased value (usually in [0, 1]).

def ease_linear(t: float) -> float:
    return t


def ease_out_quad(t: float) -> float:
    return 1 - (1 - t) * (1 - t)


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_cubic(t: float) -> float:
    return t * t * t


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t: float) -> float:
    """Overshoots slightly past 1.0 then settles — gives a 'springy' pop."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


# ── Reusable tween engine ─────────────────────────────────────────────────────

# Animations are an APP-level decision, deliberately decoupled from the Windows
# "Adjust for best performance" / reduced-motion settings: the app stays smooth
# and animated even when the OS is tuned for performance. Default ON; only an
# explicit in-app toggle changes it.
ANIMATIONS_ENABLED = True


def set_animations_enabled(enabled: bool):
    global ANIMATIONS_ENABLED
    ANIMATIONS_ENABLED = bool(enabled)


def animations_enabled() -> bool:
    return ANIMATIONS_ENABLED


def animate(widget, duration_ms: int, on_step, on_done=None,
            easing=ease_out_cubic):
    """Drive a smooth, frame-rate-independent animation via Tk's event loop.

    Parameters
    ----------
    widget      : any Tk widget — used for ``after`` scheduling and liveness.
    duration_ms : total animation length in milliseconds.
    on_step     : callable(eased_t) invoked each frame with the eased progress
                  (0.0 → 1.0). Raise nothing; TclError is swallowed.
    on_done     : optional callable() invoked once when the animation completes.
    easing      : easing function mapping linear t → eased t.

    Returns
    -------
    A cancel() callable that stops the animation early.
    """
    # Animations disabled → jump straight to the final state, no frames.
    if not ANIMATIONS_ENABLED:
        try:
            on_step(1.0)
        except Exception:
            pass
        if on_done:
            try:
                on_done()
            except Exception:
                pass
        return lambda: None

    import time
    start = time.perf_counter()
    state = {"cancelled": False, "after_id": None}

    def cancel():
        state["cancelled"] = True
        if state["after_id"] is not None:
            try:
                widget.after_cancel(state["after_id"])
            except Exception:
                pass

    def frame():
        if state["cancelled"]:
            return
        elapsed = (time.perf_counter() - start) * 1000.0
        t = min(1.0, elapsed / max(1, duration_ms))
        try:
            on_step(easing(t))
        except tk_err():
            return
        except Exception:
            return
        if t >= 1.0:
            if on_done:
                try:
                    on_done()
                except Exception:
                    pass
            return
        state["after_id"] = widget.after(FRAME_MS, frame)

    try:
        frame()
    except Exception:
        pass
    return cancel


def tk_err():
    """Return tkinter.TclError lazily (avoids a hard import at module top)."""
    import tkinter
    return tkinter.TclError


def score_color(score: int) -> str:
    if score >= 80:
        return SUCCESS
    if score >= 50:
        return WARNING
    return DANGER


def lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colours."""
    t = max(0.0, min(1.0, t))
    c1 = c1[:7]  # strip alpha if present
    c2 = c2[:7]
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"


def lighten(color: str, amount: float = 0.12) -> str:
    return lerp_color(color, "#ffffff", amount)


def darken(color: str, amount: float = 0.15) -> str:
    return lerp_color(color, "#000000", amount)


# ── Active indicator colour (defined after lerp_color) ────────────────────────
ACTIVE_GLOW = lerp_color(HIGHLIGHT, SIDEBAR, 0.55)   # sidebar active dot glow
