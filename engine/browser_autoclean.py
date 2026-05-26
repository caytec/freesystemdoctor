"""Browser Auto-Clean — watches browsers and cleans cache/history when they exit.

Inspired by CCleaner Pro's "Automatic Browser Cleaning". Background daemon
polls running processes every 8s. When a watched browser stops running,
selected categories are wiped from its profile.
"""

import os
import json
import shutil
import threading
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None


_CFG_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "FreeSystemDoctor"
_CFG_FILE = _CFG_DIR / "browser_autoclean.json"

# (process_name, profile_dir, [(category, relative_paths)])
_BROWSER_PROFILES = {
    "chrome.exe": {
        "label": "Google Chrome",
        "root": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Default",
        "categories": {
            "cache":    ["Cache", "Code Cache", "GPUCache"],
            "history":  ["History", "History-journal", "Visited Links"],
            "cookies":  ["Network/Cookies", "Network/Cookies-journal"],
            "downloads":["History"],   # downloads live in History DB
            "sessions": ["Sessions", "Session Storage"],
        },
    },
    "msedge.exe": {
        "label": "Microsoft Edge",
        "root": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data" / "Default",
        "categories": {
            "cache":    ["Cache", "Code Cache", "GPUCache"],
            "history":  ["History", "History-journal", "Visited Links"],
            "cookies":  ["Network/Cookies", "Network/Cookies-journal"],
            "downloads":["History"],
            "sessions": ["Sessions", "Session Storage"],
        },
    },
    "brave.exe": {
        "label": "Brave",
        "root": Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default",
        "categories": {
            "cache":    ["Cache", "Code Cache", "GPUCache"],
            "history":  ["History", "History-journal"],
            "cookies":  ["Network/Cookies"],
            "sessions": ["Sessions"],
        },
    },
    "firefox.exe": {
        "label": "Firefox",
        "root": Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles",
        "categories": {
            "cache":   ["cache2"],
            "history": ["places.sqlite", "places.sqlite-wal", "places.sqlite-shm"],
            "cookies": ["cookies.sqlite"],
            "sessions":["sessionstore.jsonlz4", "sessionstore-backups"],
        },
    },
}


def _load_cfg() -> dict:
    if _CFG_FILE.exists():
        try:
            return json.loads(_CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "enabled": False,
        "browsers": {},   # process_name -> [categories]
    }


def _save_cfg(cfg: dict):
    _CFG_DIR.mkdir(parents=True, exist_ok=True)
    _CFG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def list_browsers() -> list[dict]:
    """Return browsers we know how to handle, with installed/missing flag."""
    out = []
    for proc, info in _BROWSER_PROFILES.items():
        installed = info["root"].exists() if info["root"] else False
        out.append({
            "process":   proc,
            "label":     info["label"],
            "root":      str(info["root"]),
            "installed": installed,
            "categories": list(info["categories"].keys()),
        })
    return out


def get_config() -> dict:
    return _load_cfg()


def set_browser_categories(process: str, categories: list[str]):
    cfg = _load_cfg()
    cfg.setdefault("browsers", {})[process] = list(categories)
    _save_cfg(cfg)


def _profile_dirs_for(proc: str) -> list[Path]:
    info = _BROWSER_PROFILES.get(proc)
    if not info:
        return []
    root = info["root"]
    if not root.exists():
        return []
    if proc == "firefox.exe":
        return [p for p in root.glob("*.default*") if p.is_dir()]
    return [root]


def _delete_path(p: Path) -> int:
    """Remove file or directory tree. Returns bytes freed."""
    freed = 0
    try:
        if p.is_file():
            try:
                freed = p.stat().st_size
            except Exception:
                pass
            p.unlink(missing_ok=True)
        elif p.is_dir():
            for f in p.rglob("*"):
                try:
                    if f.is_file():
                        freed += f.stat().st_size
                except Exception:
                    pass
            shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass
    return freed


def clean_browser(process: str, categories: list[str]) -> dict:
    """Clean selected categories for one browser. Returns stats."""
    info = _BROWSER_PROFILES.get(process)
    if not info:
        return {"ok": False, "freed": 0, "removed": 0, "error": "Unknown browser"}

    if _is_running(process):
        return {"ok": False, "freed": 0, "removed": 0,
                "error": "Browser is running — close it first or wait for auto-clean"}

    freed = 0
    removed = 0
    for prof in _profile_dirs_for(process):
        for cat in categories:
            for rel in info["categories"].get(cat, []):
                target = prof / rel
                if target.exists():
                    f = _delete_path(target)
                    if f:
                        freed += f
                        removed += 1

    return {"ok": True, "freed": freed, "removed": removed}


def _is_running(process: str) -> bool:
    if not psutil:
        return False
    try:
        for p in psutil.process_iter(["name"]):
            if p.info.get("name", "").lower() == process.lower():
                return True
    except Exception:
        pass
    return False


# ── Background daemon ─────────────────────────────────────────────────────────

class _AutoCleanDaemon:
    _thread: threading.Thread = None
    _stop_event = threading.Event()
    _was_running: dict = {}
    _on_clean = None

    @classmethod
    def start(cls, on_clean=None):
        cls._on_clean = on_clean
        if cls._thread and cls._thread.is_alive():
            return
        cls._stop_event.clear()
        cls._was_running = {}
        cls._thread = threading.Thread(target=cls._loop, daemon=True)
        cls._thread.start()

    @classmethod
    def stop(cls):
        cls._stop_event.set()

    @classmethod
    def is_running(cls) -> bool:
        return cls._thread is not None and cls._thread.is_alive()

    @classmethod
    def _loop(cls):
        while not cls._stop_event.is_set():
            try:
                cfg = _load_cfg()
                if not cfg.get("enabled"):
                    cls._stop_event.wait(8)
                    continue

                for proc, cats in cfg.get("browsers", {}).items():
                    if not cats:
                        continue
                    running = _is_running(proc)
                    if cls._was_running.get(proc) and not running:
                        # Just exited — clean!
                        result = clean_browser(proc, cats)
                        if cls._on_clean:
                            try: cls._on_clean(proc, result)
                            except Exception: pass
                    cls._was_running[proc] = running
            except Exception:
                pass
            cls._stop_event.wait(8)


def enable(on_clean=None):
    cfg = _load_cfg()
    cfg["enabled"] = True
    _save_cfg(cfg)
    _AutoCleanDaemon.start(on_clean)


def disable():
    cfg = _load_cfg()
    cfg["enabled"] = False
    _save_cfg(cfg)
    _AutoCleanDaemon.stop()


def is_enabled() -> bool:
    return _load_cfg().get("enabled", False)


def is_daemon_running() -> bool:
    return _AutoCleanDaemon.is_running()
