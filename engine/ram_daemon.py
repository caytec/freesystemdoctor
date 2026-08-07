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

        # ── ISLC-style standby policy (opt-in, OFF by default) ────────────
        # The standby list is a disk cache, not waste. Purging it too eagerly
        # forces re-reads from disk and makes things slower, which is why this
        # is off unless the user turns it on. When on, it only fires under
        # genuine pressure: little free RAM *and* a large standby list to
        # reclaim.
        self.standby_policy_enabled: bool = False
        self.standby_free_below_mb: int = 1024
        self.standby_above_mb: int = 1024
        self.standby_purge_count: int = 0
        self.last_standby_freed_mb: int = 0
        self._load_policy()

    # ── persisted policy ──────────────────────────────────────────────────────

    def _load_policy(self):
        try:
            from engine import app_settings
            self.standby_policy_enabled = bool(
                app_settings.get("ram_standby_policy_enabled", False))
            self.standby_free_below_mb = int(
                app_settings.get("ram_standby_free_below_mb", 1024))
            self.standby_above_mb = int(
                app_settings.get("ram_standby_above_mb", 1024))
        except Exception:
            pass

    def save_policy(self, enabled: bool, free_below_mb: int,
                    standby_above_mb: int) -> None:
        self.standby_policy_enabled = bool(enabled)
        self.standby_free_below_mb = max(128, int(free_below_mb))
        self.standby_above_mb = max(128, int(standby_above_mb))
        try:
            from engine import app_settings
            app_settings.set("ram_standby_policy_enabled",
                             self.standby_policy_enabled)
            app_settings.set("ram_standby_free_below_mb",
                             self.standby_free_below_mb)
            app_settings.set("ram_standby_above_mb", self.standby_above_mb)
        except Exception:
            pass

    def _check_standby_policy(self):
        """Purge the standby list only under real memory pressure."""
        if not self.standby_policy_enabled:
            return
        try:
            from engine import ram_master
            comp = ram_master.get_memory_composition()
            standby = comp.get("standby_mb")
            if standby is None:
                return  # counters unavailable — never guess
            free_mb = comp.get("free_mb", 0)
            if (free_mb < self.standby_free_below_mb
                    and standby > self.standby_above_mb):
                before = psutil.virtual_memory().available
                ram_master._set_memory_list(
                    ram_master.MEMORY_PURGE_STANDBY_LIST)
                time.sleep(0.4)
                after = psutil.virtual_memory().available
                self.last_standby_freed_mb = max(
                    0, (after - before) // (1024 * 1024))
                self.standby_purge_count += 1
        except Exception:
            pass

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
            if not _PSUTIL:
                continue
            try:
                if self.enabled:
                    pct = psutil.virtual_memory().percent
                    if pct >= self.threshold_pct:
                        self._do_clean()
                # Independent of the %-trim above: the standby policy has its
                # own opt-in flag and its own pressure test.
                self._check_standby_policy()
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
            "standby_policy_enabled": self.standby_policy_enabled,
            "standby_free_below_mb": self.standby_free_below_mb,
            "standby_above_mb": self.standby_above_mb,
            "standby_purge_count": self.standby_purge_count,
            "last_standby_freed_mb": self.last_standby_freed_mb,
        }


# Module-level singleton
daemon = RamDaemon()
daemon.start()
