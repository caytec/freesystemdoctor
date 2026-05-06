"""Entry point for FreeSystemDoctor."""

import sys
import os

# Ensure repo root is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))


def _check_deps():
    missing = []
    try:
        import psutil  # noqa: F401
    except ImportError:
        missing.append("psutil")
    return missing


def main():
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

    from gui.app import App
    App.run()


if __name__ == "__main__":
    main()
