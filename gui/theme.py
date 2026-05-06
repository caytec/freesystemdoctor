"""Central colour / font constants — refined dark theme."""

# ── Backgrounds ───────────────────────────────────────────────────────────────
BG      = "#12172b"   # deep navy
PANEL   = "#1a2035"   # card / panel
ACCENT  = "#1e2d4a"   # header / sidebar accent
SIDEBAR = "#0e1525"   # sidebar (darkest)

# ── Brand colours ─────────────────────────────────────────────────────────────
# Replaced aggressive coral-red with a softer indigo-blue primary
HIGHLIGHT     = "#4f7ef8"   # soft blue — active state, primary buttons
HIGHLIGHT_END = "#3a5fd4"   # gradient end (slightly deeper)
SCAN_GLOW     = "#6b9dff"   # lighter highlight for glow rings

# ── Semantic colours ──────────────────────────────────────────────────────────
SUCCESS = "#3ddc84"   # fresh green
WARNING = "#f5a623"   # amber
DANGER  = "#e05c5c"   # muted red (less aggressive than #f44336)
INFO    = "#4f7ef8"   # same as highlight

# ── Badge backgrounds ─────────────────────────────────────────────────────────
BADGE_OK   = "#1a3d2b"
BADGE_WARN = "#3d2b00"
BADGE_ERR  = "#3d1a1a"

# ── Toggle ────────────────────────────────────────────────────────────────────
TOGGLE_ON  = "#3ddc84"
TOGGLE_OFF = "#2a3050"

# ── Text ──────────────────────────────────────────────────────────────────────
FG  = "#e8eaf0"   # primary — brighter, warmer white
FG2 = "#8a93b0"   # secondary / muted

# ── Borders / dividers ────────────────────────────────────────────────────────
BORDER = "#253050"

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"
FONT_BODY   = (FONT_FAMILY, 10)
FONT_SMALL  = (FONT_FAMILY, 9)
FONT_BOLD   = (FONT_FAMILY, 10, "bold")
FONT_TITLE  = (FONT_FAMILY, 13, "bold")
FONT_H2     = (FONT_FAMILY, 11, "bold")
FONT_H3     = (FONT_FAMILY, 10, "bold")
FONT_SCORE  = (FONT_FAMILY, 40, "bold")
FONT_ICON   = (FONT_FAMILY, 17)
FONT_SCAN   = (FONT_FAMILY, 20, "bold")


# ── Utilities ─────────────────────────────────────────────────────────────────

def score_color(score: int) -> str:
    if score >= 80:
        return SUCCESS
    if score >= 50:
        return WARNING
    return DANGER


def lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colours."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"


def lighten(color: str, amount: float = 0.12) -> str:
    """Lighten a hex colour towards white."""
    return lerp_color(color, "#ffffff", amount)


def darken(color: str, amount: float = 0.15) -> str:
    """Darken a hex colour towards black."""
    return lerp_color(color, "#000000", amount)
