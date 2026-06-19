"""Entry point for FreeSystemDoctor."""

import sys
import os

# Ensure repo root is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))


# ── Patch subprocess to never spawn visible console windows on Windows ────────
if sys.platform == "win32":
    import subprocess as _sp
    _CREATE_NO_WINDOW = 0x08000000
    _orig_popen = _sp.Popen.__init__

    def _silent_popen(self, *args, **kwargs):
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
        _orig_popen(self, *args, **kwargs)

    _sp.Popen.__init__ = _silent_popen


# ── Ensure we are running as administrator, re-launch with UAC if not ─────────
def _ensure_admin():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            return  # already elevated

        # Re-launch self with UAC elevation (runas)
        import ctypes.wintypes
        exe = sys.executable
        params = " ".join(f'"{a}"' for a in sys.argv)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1  # SW_SHOWNORMAL
        )
        if ret > 32:   # success — exit the un-elevated instance
            sys.exit(0)
        # If elevation was declined, continue without admin
    except Exception:
        pass


def _check_deps():
    missing = []
    try:
        import psutil  # noqa: F401
    except ImportError:
        missing.append("psutil")
    return missing


def main():
    _ensure_admin()

    missing = _check_deps()
    if missing:
        print("Missing dependencies:", ", ".join(missing))
        print("Install with:  pip install", " ".join(missing))
        sys.exit(1)

    # ──────────────────────────────────────────────────────────
    # Initialize license manager (Pro/Free tier detection)
    # ──────────────────────────────────────────────────────────
    from engine import license_manager as _lm
    _mgr  = _lm.get_manager()
    _tier = _mgr.get_tier()
    print(f"[License] Tier: {_tier}")

    # Windows DPI awareness for crisp text — independent of the system's
    # "Adjust for best performance" setting. Try Per-Monitor-V2 (sharpest),
    # then fall back through the older APIs.
    try:
        import ctypes
        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
            except Exception:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system-aware
    except Exception:
        pass

    # ──────────────────────────────────────────────────────────
    # Background tasks (license sync, autorun setup, etc)
    # ──────────────────────────────────────────────────────────
    import threading as _threading

    def _background_tasks():
        try:
            from engine import startup_manager
            startup_manager.register_autorun_on_first_run()
        except Exception:
            pass
        # Non-blocking license sync (validate cached key with server)
        try:
            _mgr.sync_background()
        except Exception:
            pass
        # Health-timeline launch snapshot (de-duped to once per day)
        try:
            from engine import health_check, system_info, health_timeline
            health_timeline.record_snapshot(
                health_check.get_health_scores(),
                system_info.get_live_metrics(),
                source="launch")
        except Exception:
            pass
        # Performance Guardian — continuous monitoring (read-only by default;
        # auto-actions are opt-in via its config).
        try:
            from engine import performance_guardian
            performance_guardian.start()
        except Exception:
            pass

    _threading.Thread(target=_background_tasks, daemon=True).start()

    # Mark app launch for monetization gating (Pro upsells respect 30 min
    # warm-up before triggering) and retry any pending newsletter submit.
    try:
        from gui import pro_upsell_smart
        pro_upsell_smart.mark_app_launched()
    except Exception:
        pass
    try:
        from engine import email_capture
        email_capture.retry_pending()
    except Exception:
        pass

    from gui.app import App
    App.run()


if __name__ == "__main__":
    main()
