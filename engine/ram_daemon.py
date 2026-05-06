"""Smart RAM Daemon — background auto-clean thread."""

import threading
import time
from datetime import datetime

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    from engine.memory_optimizer import trim_working_sets
except ImportError:
    from .memory_optimizer import trim_working_sets


class RamDaemon:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.enabled = False
        self.threshold_pct: float = 80.0
        self.interval_sec: int = 60
        self.last_clean_time: datetime | None = None
        self.last_freed_mb: int = 0
        self.total_freed_mb: int = 0
        self.clean_count: int = 0
        self.on_clean_callback = None  # callable(freed_mb)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="RamDaemon")
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── background loop ───────────────────────────────────────────────────────

    def _run(self):
        while not self._stop_event.wait(self.interval_sec):
            if not self.enabled or not _PSUTIL:
                continue
            try:
                pct = psutil.virtual_memory().percent
                if pct >= self.threshold_pct:
                    self._do_clean()
            except Exception:
                pass

    def _do_clean(self):
        if not _PSUTIL:
            return
        before = psutil.virtual_memory().used
        trim_working_sets()
        time.sleep(0.4)
        after = psutil.virtual_memory().used
        freed_mb = max(0, (before - after) // (1024 * 1024))
        self.last_freed_mb = freed_mb
        self.total_freed_mb += freed_mb
        self.clean_count += 1
        self.last_clean_time = datetime.now()
        if self.on_clean_callback:
            try:
                self.on_clean_callback(freed_mb)
            except Exception:
                pass

    # ── one-shot trigger ──────────────────────────────────────────────────────

    def trigger_now(self) -> int:
        """Immediate trim, returns MB freed (approximate)."""
        if not _PSUTIL:
            return 0
        before = psutil.virtual_memory().used
        trim_working_sets()
        time.sleep(0.5)
        after = psutil.virtual_memory().used
        freed_mb = max(0, (before - after) // (1024 * 1024))
        self.last_freed_mb = freed_mb
        self.total_freed_mb += freed_mb
        self.clean_count += 1
        self.last_clean_time = datetime.now()
        return freed_mb

    # ── status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        if not _PSUTIL:
            return {}
        m = psutil.virtual_memory()
        return {
            "ram_pct":   m.percent,
            "ram_used":  m.used,
            "ram_total": m.total,
            "enabled":   self.enabled,
            "threshold": self.threshold_pct,
            "interval":  self.interval_sec,
            "last_clean": self.last_clean_time.strftime("%H:%M:%S") if self.last_clean_time else "Never",
            "last_freed_mb": self.last_freed_mb,
            "total_freed_mb": self.total_freed_mb,
            "clean_count": self.clean_count,
        }


# Module-level singleton
daemon = RamDaemon()
daemon.start()
