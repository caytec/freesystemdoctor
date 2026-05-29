"""Central colour / font constants — premium glassmorphism dark theme."""

# ── Backgrounds ───────────────────────────────────────────────────────────────
BG      = "#0d1117"   # deep space black
PANEL   = "#161b27"   # card / panel — slightly blue-tinted
ACCENT  = "#1c2438"   # header / elevated panels
SIDEBAR = "#0a0e1a"   # sidebar (deepest)

# ── Brand colours ─────────────────────────────────────────────────────────────
HIGHLIGHT     = "#00d4ff"   # electric cyan — premium feel
HIGHLIGHT_END = "#0099cc"   # gradient end
SCAN_GLOW     = "#40e0ff"   # bright cyan for glow effects
PURPLE        = "#7b61ff"   # secondary accent purple
PURPLE_END    = "#5a45cc"   # purple gradient end

# ── Semantic colours ──────────────────────────────────────────────────────────
SUCCESS = "#00e676"   # vivid green
WARNING = "#ffab40"   # warm amber
DANGER  = "#ff5252"   # vivid red
INFO    = "#40c4ff"   # info blue

# ── Badge backgrounds ─────────────────────────────────────────────────────────
BADGE_OK   = "#00311a"
BADGE_WARN = "#332200"
BADGE_ERR  = "#330d0d"

# ── Toggle ────────────────────────────────────────────────────────────────────
TOGGLE_ON  = "#00d4ff"
TOGGLE_OFF = "#1c2438"

# ── Text ──────────────────────────────────────────────────────────────────────
FG  = "#e8edf5"   # primary — crisp white-blue
FG2 = "#6b7a99"   # secondary / muted

# ── Borders / dividers ────────────────────────────────────────────────────────
BORDER     = "#1e2d45"
BORDER_GLOW = "#00d4ff"   # highlighted border

# ── Glass effect colors ───────────────────────────────────────────────────────
GLASS_BG   = "#161b27cc"  # semi-transparent panel
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
TRANSITION_MS = 120   # page crossfade total duration (ms)
STAGGER_MS    = 45    # per-item stagger delay in sidebar reveal (ms)


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
