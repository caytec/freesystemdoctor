"""Shared performance helpers — caching, hidden subprocess, lazy imports.

Used across engine modules to avoid:
- Flashing console windows from subprocess.run (CREATE_NO_WINDOW)
- Repeated expensive PowerShell/WMI calls (TTL cache)
- Slow startup from eager wmi/psutil imports
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Any, Callable

# CREATE_NO_WINDOW prevents flashing console windows on Windows
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def run_hidden(cmd: list[str], timeout: int = 30,
               text: bool = True) -> subprocess.CompletedProcess:
    """subprocess.run with no console window, sane defaults, exception-safe."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=text,
            timeout=timeout,
            encoding="utf-8" if text else None,
            errors="replace" if text else None,
            creationflags=NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        # Return a sentinel CompletedProcess-like object
        return subprocess.CompletedProcess(cmd, -1, "", "Timeout")
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, -1, "",
                                            f"Command not found: {cmd[0]}")
    except Exception as e:
        return subprocess.CompletedProcess(cmd, -1, "", str(e))


def run_powershell(script: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a PowerShell -Command silently, no profile load."""
    return run_hidden(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=timeout,
    )


# ── TTL cache ─────────────────────────────────────────────────────────────────

class TTLCache:
    """Thread-safe single-key TTL cache."""

    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._value: Any = None
        self._expires: float = 0
        self._lock = threading.Lock()

    def get_or_compute(self, compute_fn: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            if self._value is not None and now < self._expires:
                return self._value
        # Compute outside the lock
        result = compute_fn()
        with self._lock:
            self._value = result
            self._expires = time.monotonic() + self._ttl
        return result

    def invalidate(self):
        with self._lock:
            self._value = None
            self._expires = 0


def ttl_cache(ttl_seconds: float):
    """Decorator: cache the result of a zero-arg function for ttl seconds."""
    def decorator(fn):
        cache = TTLCache(ttl_seconds)
        def wrapper(*args, **kwargs):
            if args or kwargs:
                # Args present — bypass cache
                return fn(*args, **kwargs)
            return cache.get_or_compute(lambda: fn())
        wrapper.invalidate = cache.invalidate  # type: ignore[attr-defined]
        return wrapper
    return decorator


# ── Lazy imports ──────────────────────────────────────────────────────────────

_psutil = None
_psutil_lock = threading.Lock()


def get_psutil():
    """Lazy-load psutil. Returns None if not installed."""
    global _psutil
    if _psutil is False:
        return None
    if _psutil is not None:
        return _psutil
    with _psutil_lock:
        if _psutil is None:
            try:
                import psutil  # type: ignore
                _psutil = psutil
            except ImportError:
                _psutil = False
                return None
    return _psutil if _psutil is not False else None
