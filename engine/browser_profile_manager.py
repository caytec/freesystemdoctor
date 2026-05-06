"""Browser Profile Manager — manage browser settings, extensions, and homepage."""

import json
import shutil
from pathlib import Path


class BrowserExtension:
    """Represents a browser extension."""
    def __init__(self, browser: str, name: str, id: str, enabled: bool, icon: str = ""):
        self.browser = browser
        self.name = name
        self.id = id
        self.enabled = enabled
        self.icon = icon


def _get_browser_paths() -> dict[str, Path]:
    """Get paths to browser profile directories."""
    home = Path.home()
    return {
        "Chrome": home / "AppData" / "Local" / "Google" / "Chrome" / "User Data",
        "Edge": home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data",
        "Firefox": home / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles",
    }


def detect_installed_browsers() -> list[str]:
    """Detect which browsers are installed."""
    paths = _get_browser_paths()
    installed = []

    for browser_name, browser_path in paths.items():
        if browser_path.exists():
            installed.append(browser_name)

    return installed


def get_browser_settings(browser: str) -> dict:
    """Get browser settings and preferences."""
    settings = {
        "homepage": "",
        "search_engine": "",
        "startup_type": "",
        "extensions_count": 0,
    }

    if browser == "Chrome" or browser == "Edge":
        prefs_path = _get_browser_paths()[browser] / "Default" / "Preferences"
        if prefs_path.exists():
            try:
                with open(prefs_path, encoding="utf-8") as f:
                    prefs = json.load(f)
                settings["homepage"] = prefs.get("homepage", "")
                settings["startup_type"] = prefs.get("session", {}).get("restore_on_startup", "")
            except Exception:
                pass

    elif browser == "Firefox":
        prefs_path = _get_browser_paths()[browser].glob("*/prefs.js")
        for pref_file in prefs_path:
            try:
                with open(pref_file, encoding="utf-8") as f:
                    content = f.read()
                    if "browser.startup.homepage" in content:
                        settings["homepage"] = "Custom"
            except Exception:
                pass

    return settings


def list_extensions(browser: str) -> list[BrowserExtension]:
    """List all extensions in a browser."""
    extensions = []
    browser_path = _get_browser_paths().get(browser)

    if not browser_path or not browser_path.exists():
        return extensions

    if browser in ("Chrome", "Edge"):
        try:
            extensions_dir = browser_path / "Default" / "Extensions"
            if extensions_dir.exists():
                for ext_dir in extensions_dir.iterdir():
                    if ext_dir.is_dir():
                        manifest_path = ext_dir / "manifest.json"
                        if not manifest_path.exists():
                            manifest_path = list(ext_dir.glob("*/manifest.json"))
                            if manifest_path:
                                manifest_path = manifest_path[0]

                        if manifest_path and manifest_path.exists():
                            try:
                                with open(manifest_path, encoding="utf-8") as f:
                                    manifest = json.load(f)
                                    name = manifest.get("name", ext_dir.name)
                                    icon = manifest.get("icons", {}).get("128", "")
                                    ext = BrowserExtension(
                                        browser=browser,
                                        name=name,
                                        id=ext_dir.name,
                                        enabled=True,
                                        icon=icon
                                    )
                                    extensions.append(ext)
                            except Exception:
                                pass
        except Exception:
            pass

    elif browser == "Firefox":
        try:
            for profile_dir in browser_path.iterdir():
                if profile_dir.is_dir():
                    extensions_json = profile_dir / "extensions.json"
                    if extensions_json.exists():
                        try:
                            with open(extensions_json, encoding="utf-8") as f:
                                ext_data = json.load(f)
                                for addon in ext_data.get("addons", []):
                                    ext = BrowserExtension(
                                        browser=browser,
                                        name=addon.get("name", ""),
                                        id=addon.get("id", ""),
                                        enabled=addon.get("active", False)
                                    )
                                    extensions.append(ext)
                        except Exception:
                            pass
        except Exception:
            pass

    return extensions


def detect_malicious_extensions(browser: str) -> list[BrowserExtension]:
    """Detect potentially malicious extensions."""
    all_extensions = list_extensions(browser)
    suspicious_keywords = [
        "ads", "toolbar", "coupon", "deal", "discount", "cashback",
        "crypto", "miner", "proxy", "vpn", "tracker", "analytics"
    ]

    malicious = []
    for ext in all_extensions:
        lower_name = ext.name.lower()
        if any(keyword in lower_name for keyword in suspicious_keywords):
            malicious.append(ext)

    return malicious


def remove_extension(browser: str, ext_id: str) -> bool:
    """Remove an extension from a browser."""
    browser_path = _get_browser_paths().get(browser)
    if not browser_path:
        return False

    try:
        if browser in ("Chrome", "Edge"):
            ext_path = browser_path / "Default" / "Extensions" / ext_id
            if ext_path.exists():
                shutil.rmtree(ext_path)
                return True
        elif browser == "Firefox":
            for profile_dir in browser_path.iterdir():
                if profile_dir.is_dir():
                    extensions_json = profile_dir / "extensions.json"
                    if extensions_json.exists():
                        with open(extensions_json, encoding="utf-8") as f:
                            ext_data = json.load(f)

                        ext_data["addons"] = [a for a in ext_data.get("addons", []) if a.get("id") != ext_id]

                        with open(extensions_json, "w", encoding="utf-8") as f:
                            json.dump(ext_data, f)
                        return True
    except Exception:
        pass

    return False


def set_browser_homepage(browser: str, homepage_url: str) -> bool:
    """Set browser homepage."""
    browser_path = _get_browser_paths().get(browser)
    if not browser_path:
        return False

    try:
        if browser in ("Chrome", "Edge"):
            prefs_path = browser_path / "Default" / "Preferences"
            if prefs_path.exists():
                with open(prefs_path, encoding="utf-8") as f:
                    prefs = json.load(f)

                prefs["homepage"] = homepage_url
                prefs["homepage_is_newtabpage"] = False

                with open(prefs_path, "w", encoding="utf-8") as f:
                    json.dump(prefs, f, indent=2)
                return True
    except Exception:
        pass

    return False


def get_browser_recommendations() -> list[str]:
    """Get recommendations for browser cleanup."""
    recommendations = []

    for browser in detect_installed_browsers():
        malicious = detect_malicious_extensions(browser)
        if malicious:
            recommendations.append(f"Remove {len(malicious)} suspicious extension(s) from {browser}")

        settings = get_browser_settings(browser)
        if settings.get("homepage") and "google" not in settings.get("homepage", "").lower():
            recommendations.append(f"Reset {browser} homepage to default")

    return recommendations
