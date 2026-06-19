"""Central application settings store.

A single JSON-backed key/value store for user preferences that must survive
across runs (window geometry, last open page, HUD position/alpha/visibility,
theme, language, etc.).

Stored at ``~/.fsd/settings.json`` — deliberately NOT under %TEMP%, because
FreeSystemDoctor's own Turbo Clean wipes the temp folder and would otherwise
destroy the user's settings on every clean.

Design notes
------------
* Thread-safe: all reads/writes go through a module-level lock.
* Atomic writes: write to ``.tmp`` then ``os.replace`` so a crash mid-write
  never corrupts the file.
* Tolerant: a missing or corrupt file degrades to empty defaults, never raises.
* In-memory cache: the file is read once on first access; ``save()`` flushes.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(os.path.expanduser("~")) / ".fsd"
_SETTINGS_FILE = _CONFIG_DIR / "settings.json"

_VERSION = 1
_lock = threading.RLock()
_cache: dict[str, Any] | None = None
_dirty = False


# ── internal ────────────────────────────────────────────────────────────────

def _load() -> dict[str, Any]:
    """Load settings from disk into the cache (once). Never raises."""
    global _cache
    if _cache is not None:
        return _cache
    data: dict[str, Any] = {}
    try:
        if _SETTINGS_FILE.exists():
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                # Unwrap {"version":1, "settings":{...}} envelope if present
                inner = raw.get("settings")
                data = inner if isinstance(inner, dict) else raw
    except Exception:
        data = {}
    _cache = data
    return _cache


# ── public API ──────────────────────────────────────────────────────────────

def get(key: str, default: Any = None) -> Any:
    """Return the stored value for *key*, or *default* if unset."""
    with _lock:
        return _load().get(key, default)


def set(key: str, value: Any) -> None:
    """Set *key* to *value* in memory (call :func:`save` to persist)."""
    global _dirty
    with _lock:
        cache = _load()
        if cache.get(key) != value:
            cache[key] = value
            _dirty = True


def set_many(values: dict[str, Any]) -> None:
    """Update several keys at once (in memory)."""
    global _dirty
    with _lock:
        cache = _load()
        for k, v in values.items():
            if cache.get(k) != v:
                cache[k] = v
                _dirty = True


def all() -> dict[str, Any]:
    """Return a shallow copy of all stored settings."""
    with _lock:
        return dict(_load())


def save(force: bool = False) -> bool:
    """Flush settings to disk atomically. Returns True on success.

    No-op (returns True) when nothing changed since the last save, unless
    *force* is set. Never raises.
    """
    global _dirty
    with _lock:
        if _cache is None or (not _dirty and not force):
            return True
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            payload = {"version": _VERSION, "settings": _cache}
            tmp = _SETTINGS_FILE.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp, _SETTINGS_FILE)
            _dirty = False
            return True
        except Exception:
            return False


def set_and_save(key: str, value: Any) -> bool:
    """Convenience: set a single key and immediately persist it."""
    set(key, value)
    return save()
