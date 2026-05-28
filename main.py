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

    # Windows DPI awareness for crisp text
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Auto-register startup task on first run (background — don't block UI)
    import threading as _threading
    def _setup_autorun():
        try:
            from engine import startup_manager
            startup_manager.register_autorun_on_first_run()
        except Exception:
            pass
    _threading.Thread(target=_setup_autorun, daemon=True).start()

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
