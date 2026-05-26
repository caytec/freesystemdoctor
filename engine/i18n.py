"""Internationalization — EN/PL language support."""

import json
import os
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("TEMP", "C:\\Temp")) / "FreeSystemDoctor"
_LANG_FILE = _CONFIG_DIR / "language.json"

_CURRENT_LANG = "en"

_TRANSLATIONS = {
    "en": {
        "app_title": "FreeSystemDoctor — Advanced Windows Optimizer",
        "health_check": "Health Check",
        "care": "Care",
        "speedup": "Speed Up",
        "protect": "Protect",
        "software": "Software",
        "action_center": "Action Center",
        "ai_agent": "AI Agent",
        "disk_analyzer": "Disk Analyzer",
        "disk_optimizer": "Disk Optimizer",
        "internet_booster": "Internet Booster",
        "turbo_mode": "Turbo Mode",
        "driver_updater": "Driver Updater",
        "system_restore": "System Restore",
        "empty_folders": "Empty Folders",
        "cloud_cleaner": "Cloud Cleaner",
        "file_recovery": "File Recovery",
        "app_priority": "App Priority",
        "app_freezer": "App Freezer",
        "webcam_guard": "Webcam Guard",
        "smart_alerts": "Smart Alerts",
        "browser_plugins": "Browser Plugins",
        "benchmark": "Benchmark",
        "scheduled_clean": "Scheduled Clean",
        "drive_wipe": "Drive Wipe",
        "browser_history": "Browser History",
        "bandwidth": "Bandwidth",
        "reg_backup": "Reg Backup",
        "speedup_wizard": "Speedup Wizard",
        "settings": "Settings",
        "all_tools": "All Tools",
        "scan": "Scan",
        "clean": "Clean",
        "refresh": "Refresh",
        "cancel": "Cancel",
        "close": "Close",
        "save": "Save",
        "delete": "Delete",
        "restore": "Restore",
        "enable": "Enable",
        "disable": "Disable",
        "yes": "Yes",
        "no": "No",
        "error": "Error",
        "warning": "Warning",
        "success": "Success",
        "loading": "Loading...",
        "scanning": "Scanning...",
        "done": "Done",
        "no_selection": "No selection",
        "select_first": "Select an item first",
        "confirm": "Confirm",
        "export_report": "Export Report",
        "language": "Language",
        "theme": "Theme",
        "dark_theme": "Dark Theme",
        "light_theme": "Light Theme",
    },
    "pl": {
        "app_title": "FreeSystemDoctor — Zaawansowany Optymalizator Windows",
        "health_check": "Sprawdzenie stanu",
        "care": "Pielegnacja",
        "speedup": "Przyspieszenie",
        "protect": "Ochrona",
        "software": "Oprogramowanie",
        "action_center": "Centrum akcji",
        "ai_agent": "Agent AI",
        "disk_analyzer": "Analizator dysku",
        "disk_optimizer": "Optymalizator dysku",
        "internet_booster": "Akcelerator internetu",
        "turbo_mode": "Tryb turbo",
        "driver_updater": "Aktualizacja sterownikow",
        "system_restore": "Przywracanie systemu",
        "empty_folders": "Puste foldery",
        "cloud_cleaner": "Czyszczenie chmury",
        "file_recovery": "Odzyskiwanie plikow",
        "app_priority": "Priorytet aplikacji",
        "app_freezer": "Zamrazanie aplikacji",
        "webcam_guard": "Ochrona kamery",
        "smart_alerts": "Inteligentne powiadomienia",
        "browser_plugins": "Wtyczki przegladarek",
        "benchmark": "Benchmark",
        "scheduled_clean": "Planowane czyszczenie",
        "drive_wipe": "Wycieranie dysku",
        "browser_history": "Historia przegladarek",
        "bandwidth": "Pasmo",
        "reg_backup": "Kopia rejestru",
        "speedup_wizard": "Kreator przyspieszania",
        "settings": "Ustawienia",
        "all_tools": "Wszystkie narzedzia",
        "scan": "Skanuj",
        "clean": "Wyczysc",
        "refresh": "Odswiez",
        "cancel": "Anuluj",
        "close": "Zamknij",
        "save": "Zapisz",
        "delete": "Usun",
        "restore": "Przywroc",
        "enable": "Wlacz",
        "disable": "Wylacz",
        "yes": "Tak",
        "no": "Nie",
        "error": "Blad",
        "warning": "Ostrzezenie",
        "success": "Sukces",
        "loading": "Ladowanie...",
        "scanning": "Skanowanie...",
        "done": "Gotowe",
        "no_selection": "Brak zaznaczenia",
        "select_first": "Najpierw zaznacz element",
        "confirm": "Potwierdz",
        "export_report": "Eksportuj raport",
        "language": "Jezyk",
        "theme": "Motyw",
        "dark_theme": "Ciemny motyw",
        "light_theme": "Jasny motyw",
    }
}


def get_language() -> str:
    global _CURRENT_LANG
    try:
        if _LANG_FILE.exists():
            with open(_LANG_FILE) as f:
                data = json.load(f)
                _CURRENT_LANG = data.get("language", "en")
    except Exception:
        pass
    return _CURRENT_LANG


def set_language(lang: str):
    global _CURRENT_LANG
    if lang in _TRANSLATIONS:
        _CURRENT_LANG = lang
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(_LANG_FILE, "w") as f:
                json.dump({"language": lang}, f)
        except Exception:
            pass


def t(key: str) -> str:
    """Translate a key to the current language."""
    lang = _CURRENT_LANG or get_language()
    return _TRANSLATIONS.get(lang, {}).get(key) or _TRANSLATIONS["en"].get(key, key)


def available_languages() -> list[tuple[str, str]]:
    """Return list of (code, display_name) tuples."""
    return [("en", "English"), ("pl", "Polski")]
