"""Browser Plugin Manager — list and toggle Chrome/Edge/Firefox extensions."""

import json
import os
from pathlib import Path


_BROWSERS = {
    "Chrome": {
        "profile_base": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
        "exe": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    },
    "Edge": {
        "profile_base": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data",
        "exe": Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    },
    "Firefox": {
        "profile_base": Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles",
        "exe": Path("C:/Program Files/Mozilla Firefox/firefox.exe"),
        "is_firefox": True,
    },
}


def get_installed_browsers() -> list[str]:
    """Return list of detected browser names."""
    found = []
    for name, cfg in _BROWSERS.items():
        if cfg["exe"].exists() or cfg["profile_base"].exists():
            found.append(name)
    return found


def get_extensions(browser: str) -> list[dict]:
    """Return list of extensions for the given browser.
    Each dict: id, name, version, enabled, description, browser, profile."""
    cfg = _BROWSERS.get(browser)
    if not cfg:
        return []

    if cfg.get("is_firefox"):
        return _get_firefox_extensions(cfg["profile_base"], browser)
    return _get_chromium_extensions(cfg["profile_base"], browser)


def _get_chromium_extensions(profile_base: Path, browser: str) -> list[dict]:
    """Read Chrome/Edge extensions from Extensions folder in each profile."""
    results = []
    if not profile_base.exists():
        return results

    # Scan all profiles (Default, Profile 1, Profile 2, ...)
    profiles = [profile_base / "Default"] + list(profile_base.glob("Profile *"))

    for profile_dir in profiles:
        ext_root = profile_dir / "Extensions"
        prefs_file = profile_dir / "Preferences"
        if not ext_root.exists():
            continue

        # Read enabled/disabled state from Preferences JSON
        enabled_ids: set[str] = set()
        disabled_ids: set[str] = set()
        try:
            with open(prefs_file, "r", encoding="utf-8", errors="ignore") as f:
                prefs = json.load(f)
            ext_settings = prefs.get("extensions", {}).get("settings", {})
            for ext_id, ext_data in ext_settings.items():
                state = ext_data.get("state", 1)
                if state == 1:
                    enabled_ids.add(ext_id)
                else:
                    disabled_ids.add(ext_id)
        except Exception:
            pass

        for ext_id_dir in ext_root.iterdir():
            if not ext_id_dir.is_dir():
                continue
            ext_id = ext_id_dir.name
            # Skip internal Chrome extensions
            if len(ext_id) != 32:
                continue

            manifest = _read_chromium_manifest(ext_id_dir)
            if not manifest:
                continue

            name = manifest.get("name", ext_id)
            # Resolve __MSG_ references
            if name.startswith("__MSG_"):
                name = _resolve_msg(ext_id_dir, name) or name

            enabled = ext_id in enabled_ids or ext_id not in disabled_ids

            results.append({
                "id": ext_id,
                "name": name,
                "version": manifest.get("version", ""),
                "description": manifest.get("description", ""),
                "enabled": enabled,
                "browser": browser,
                "profile": profile_dir.name,
                "manifest_path": str(ext_id_dir),
            })

    # Deduplicate by id, prefer enabled=True entries
    seen: dict[str, dict] = {}
    for ext in results:
        if ext["id"] not in seen or ext["enabled"]:
            seen[ext["id"]] = ext

    return sorted(seen.values(), key=lambda x: x["name"].lower())


def _read_chromium_manifest(ext_dir: Path) -> dict:
    """Read manifest.json from the latest version subfolder."""
    try:
        version_dirs = sorted(ext_dir.iterdir(), reverse=True)
        for vdir in version_dirs:
            manifest_file = vdir / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file, "r", encoding="utf-8", errors="ignore") as f:
                    return json.load(f)
    except Exception:
        pass
    return {}


def _resolve_msg(ext_dir: Path, msg_key: str) -> str:
    """Resolve a __MSG_key__ string from _locales/en/messages.json."""
    key = msg_key.strip("_").replace("MSG_", "").lower()
    try:
        for locale in ("en", "en_US", "en_GB"):
            msg_file = ext_dir / "_locales" / locale / "messages.json"
            if not msg_file.exists():
                # try subdirs
                for vdir in ext_dir.iterdir():
                    msg_file = vdir / "_locales" / locale / "messages.json"
                    if msg_file.exists():
                        break
            if msg_file.exists():
                with open(msg_file, "r", encoding="utf-8", errors="ignore") as f:
                    msgs = json.load(f)
                for k, v in msgs.items():
                    if k.lower() == key:
                        return v.get("message", "")
    except Exception:
        pass
    return ""


def _get_firefox_extensions(profiles_dir: Path, browser: str) -> list[dict]:
    """Read Firefox extensions from extensions.json in each profile."""
    results = []
    if not profiles_dir.exists():
        return results

    for profile_dir in profiles_dir.iterdir():
        if not profile_dir.is_dir():
            continue
        ext_file = profile_dir / "extensions.json"
        if not ext_file.exists():
            continue

        try:
            with open(ext_file, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            for addon in data.get("addons", []):
                if addon.get("type") != "extension":
                    continue
                if addon.get("location") not in ("app-profile", "app-global", None):
                    pass

                name = addon.get("defaultLocale", {}).get("name", addon.get("id", ""))
                description = addon.get("defaultLocale", {}).get("description", "")
                enabled = addon.get("active", True) and not addon.get("userDisabled", False)

                results.append({
                    "id": addon.get("id", ""),
                    "name": name,
                    "version": addon.get("version", ""),
                    "description": description,
                    "enabled": enabled,
                    "browser": browser,
                    "profile": profile_dir.name,
                    "manifest_path": str(profile_dir),
                })
        except Exception:
            pass

    return sorted(results, key=lambda x: x["name"].lower())


def set_extension_enabled(ext: dict, enabled: bool) -> tuple[bool, str]:
    """Enable or disable a browser extension.
    Returns (success, message). Chrome/Edge require browser restart to take effect."""
    browser = ext.get("browser", "")
    cfg = _BROWSERS.get(browser)
    if not cfg:
        return False, "Unknown browser"

    if cfg.get("is_firefox"):
        return False, "Firefox extension state changes require browser restart via profile editing"

    # Chromium: update Preferences file
    profile_base = cfg["profile_base"]
    profile_name = ext.get("profile", "Default")
    prefs_file = profile_base / profile_name / "Preferences"

    if not prefs_file.exists():
        return False, "Preferences file not found"

    try:
        with open(prefs_file, "r", encoding="utf-8", errors="ignore") as f:
            prefs = json.load(f)

        ext_id = ext["id"]
        if "extensions" not in prefs:
            prefs["extensions"] = {}
        if "settings" not in prefs["extensions"]:
            prefs["extensions"]["settings"] = {}

        if ext_id not in prefs["extensions"]["settings"]:
            prefs["extensions"]["settings"][ext_id] = {}

        prefs["extensions"]["settings"][ext_id]["state"] = 1 if enabled else 0

        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, separators=(",", ":"))

        action = "enabled" if enabled else "disabled"
        return True, f"Extension {action}. Restart {browser} to apply."
    except PermissionError:
        return False, f"Cannot modify Preferences while {browser} is running. Close the browser first."
    except Exception as e:
        return False, str(e)


def get_all_extensions() -> list[dict]:
    """Return extensions from all detected browsers."""
    results = []
    for browser in get_installed_browsers():
        results.extend(get_extensions(browser))
    return results
