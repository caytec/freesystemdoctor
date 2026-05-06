"""Theme Manager — custom color scheme management and persistence."""

import json
from pathlib import Path


class ColorTheme:
    """Represents a complete color theme."""
    def __init__(self, name: str, colors: dict):
        self.name = name
        self.colors = colors

    @property
    def bg(self) -> str:
        return self.colors.get("bg", "#1a1a1a")

    @property
    def fg(self) -> str:
        return self.colors.get("fg", "#ffffff")

    @property
    def fg2(self) -> str:
        return self.colors.get("fg2", "#b0b0b0")

    @property
    def accent(self) -> str:
        return self.colors.get("accent", "#2a2a2a")

    @property
    def panel(self) -> str:
        return self.colors.get("panel", "#252525")

    @property
    def border(self) -> str:
        return self.colors.get("border", "#333333")

    @property
    def highlight(self) -> str:
        return self.colors.get("highlight", "#0078d4")

    @property
    def success(self) -> str:
        return self.colors.get("success", "#28a745")

    @property
    def warning(self) -> str:
        return self.colors.get("warning", "#ffc107")

    @property
    def danger(self) -> str:
        return self.colors.get("danger", "#dc3545")

    @property
    def sidebar(self) -> str:
        return self.colors.get("sidebar", "#1e1e1e")


_PREDEFINED_THEMES = {
    "Dark (Default)": {
        "bg": "#1a1a1a",
        "fg": "#ffffff",
        "fg2": "#b0b0b0",
        "accent": "#2a2a2a",
        "panel": "#252525",
        "border": "#333333",
        "highlight": "#0078d4",
        "success": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "sidebar": "#1e1e1e",
    },
    "Light": {
        "bg": "#f5f5f5",
        "fg": "#1a1a1a",
        "fg2": "#666666",
        "accent": "#e8e8e8",
        "panel": "#ffffff",
        "border": "#d0d0d0",
        "highlight": "#0078d4",
        "success": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "sidebar": "#f0f0f0",
    },
    "Blue": {
        "bg": "#0d1b2a",
        "fg": "#e0e1dd",
        "fg2": "#a8dadc",
        "accent": "#1b4965",
        "panel": "#1b4965",
        "border": "#457b9d",
        "highlight": "#1d3557",
        "success": "#52b788",
        "warning": "#f4a261",
        "danger": "#e63946",
        "sidebar": "#0d1b2a",
    },
    "Green": {
        "bg": "#1a2e1a",
        "fg": "#e8f5e9",
        "fg2": "#81c784",
        "accent": "#2e5233",
        "panel": "#2e5233",
        "border": "#4caf50",
        "highlight": "#4caf50",
        "success": "#66bb6a",
        "warning": "#fbc02d",
        "danger": "#ef5350",
        "sidebar": "#1a2e1a",
    },
    "Purple": {
        "bg": "#1a0d2e",
        "fg": "#f0e6ff",
        "fg2": "#d9b3ff",
        "accent": "#3d1a5c",
        "panel": "#3d1a5c",
        "border": "#6a1b9a",
        "highlight": "#7b1fa2",
        "success": "#66bb6a",
        "warning": "#fbc02d",
        "danger": "#ef5350",
        "sidebar": "#1a0d2e",
    },
    "High Contrast": {
        "bg": "#000000",
        "fg": "#ffffff",
        "fg2": "#cccccc",
        "accent": "#222222",
        "panel": "#111111",
        "border": "#444444",
        "highlight": "#ffff00",
        "success": "#00ff00",
        "warning": "#ffaa00",
        "danger": "#ff0000",
        "sidebar": "#0a0a0a",
    },
}


def _get_theme_config_path() -> Path:
    """Get path to theme configuration file."""
    config_dir = Path.home() / "AppData" / "Local" / "FreeSystemDoctor"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "theme_config.json"


def get_predefined_themes() -> dict[str, ColorTheme]:
    """Get all predefined theme presets."""
    return {name: ColorTheme(name, colors) for name, colors in _PREDEFINED_THEMES.items()}


def load_current_theme() -> ColorTheme:
    """Load the currently active theme."""
    config_path = _get_theme_config_path()

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            theme_name = config.get("active_theme", "Dark (Default)")
            if theme_name in _PREDEFINED_THEMES:
                return ColorTheme(theme_name, _PREDEFINED_THEMES[theme_name])

            # Custom theme
            if "custom_colors" in config:
                return ColorTheme("Custom", config["custom_colors"])
        except Exception:
            pass

    # Default theme
    return ColorTheme("Dark (Default)", _PREDEFINED_THEMES["Dark (Default)"])


def save_theme(theme_name: str):
    """Save active theme selection."""
    config_path = _get_theme_config_path()

    try:
        config = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)

        config["active_theme"] = theme_name
        config["updated"] = __import__("datetime").datetime.now().isoformat()

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def save_custom_theme(name: str, colors: dict) -> bool:
    """Save a custom theme."""
    config_path = _get_theme_config_path()

    try:
        config = {}
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)

        if "custom_themes" not in config:
            config["custom_themes"] = {}

        config["custom_themes"][name] = colors
        config["active_theme"] = name

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        return True
    except Exception:
        return False


def delete_custom_theme(name: str) -> bool:
    """Delete a custom theme."""
    config_path = _get_theme_config_path()

    try:
        if not config_path.exists():
            return False

        with open(config_path, "r") as f:
            config = json.load(f)

        if "custom_themes" in config and name in config["custom_themes"]:
            del config["custom_themes"][name]

            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            return True
    except Exception:
        pass

    return False


def get_all_themes() -> dict[str, ColorTheme]:
    """Get all available themes (predefined + custom)."""
    all_themes = get_predefined_themes().copy()

    config_path = _get_theme_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            if "custom_themes" in config:
                for name, colors in config["custom_themes"].items():
                    all_themes[name] = ColorTheme(name, colors)
        except Exception:
            pass

    return all_themes


def validate_color(color: str) -> bool:
    """Validate hex color code."""
    if not color.startswith("#"):
        return False

    hex_str = color[1:]
    if len(hex_str) not in (3, 6):
        return False

    try:
        int(hex_str, 16)
        return True
    except ValueError:
        return False


def lerp_color_theme(theme1: ColorTheme, theme2: ColorTheme, t: float) -> ColorTheme:
    """Interpolate between two themes."""
    def lerp_hex(color1: str, color2: str, t: float) -> str:
        """Linear interpolation between two hex colors."""
        c1 = int(color1[1:], 16)
        c2 = int(color2[1:], 16)

        r1, g1, b1 = (c1 >> 16) & 0xff, (c1 >> 8) & 0xff, c1 & 0xff
        r2, g2, b2 = (c2 >> 16) & 0xff, (c2 >> 8) & 0xff, c2 & 0xff

        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)

        return f"#{r:02x}{g:02x}{b:02x}"

    interpolated = {}
    for key in theme1.colors:
        if key in theme2.colors:
            interpolated[key] = lerp_hex(theme1.colors[key], theme2.colors[key], t)
        else:
            interpolated[key] = theme1.colors[key]

    return ColorTheme("Interpolated", interpolated)
