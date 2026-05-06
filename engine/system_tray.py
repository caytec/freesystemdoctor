"""System Tray Icon — live CPU/RAM display with context menu."""

import threading
import os
from pathlib import Path

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    _TRAY_AVAILABLE = True
except ImportError:
    _TRAY_AVAILABLE = False

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_icon_instance = None
_app_ref = None
_stop_event = threading.Event()


def _make_icon_image(cpu: float, ram: float) -> "Image.Image":
    """Generate a 64x64 tray icon image showing CPU/RAM as colored bars."""
    img = Image.new("RGBA", (64, 64), (14, 21, 37, 255))  # T.SIDEBAR color
    draw = ImageDraw.Draw(img)

    # Background circle
    draw.ellipse([2, 2, 62, 62], fill=(30, 45, 74, 255))  # T.ACCENT

    # CPU bar (left half) — blue
    cpu_h = int(44 * (cpu / 100))
    draw.rectangle([8, 52 - cpu_h, 26, 52], fill=(79, 126, 248, 255))  # T.HIGHLIGHT

    # RAM bar (right half) — green/orange/red based on usage
    ram_h = int(44 * (ram / 100))
    ram_color = (61, 220, 132, 255) if ram < 70 else (245, 166, 35, 255) if ram < 85 else (224, 92, 92, 255)
    draw.rectangle([38, 52 - ram_h, 56, 52], fill=ram_color)

    # Labels
    draw.text((4, 4), "C", fill=(232, 234, 240, 200))
    draw.text((40, 4), "R", fill=(232, 234, 240, 200))

    return img


def _get_metrics() -> tuple[float, float]:
    if not _PSUTIL:
        return 0.0, 0.0
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        return cpu, ram
    except Exception:
        return 0.0, 0.0


def _update_loop(icon):
    """Background thread: updates tray icon image every 3 seconds."""
    while not _stop_event.is_set():
        cpu, ram = _get_metrics()
        try:
            icon.icon = _make_icon_image(cpu, ram)
            icon.title = f"FreeSystemDoctor\nCPU: {cpu:.0f}%  RAM: {ram:.0f}%"
        except Exception:
            pass
        _stop_event.wait(3)


def _on_open(icon, item):
    """Show the main application window."""
    if _app_ref:
        try:
            _app_ref.deiconify()
            _app_ref.lift()
            _app_ref.focus_force()
        except Exception:
            pass


def _on_scan(icon, item):
    """Trigger a quick scan from tray."""
    try:
        from engine import smart_notifications as sn
        threading.Thread(target=sn.scan_now_and_notify, daemon=True).start()
    except Exception:
        pass


def _on_exit(icon, item):
    """Exit the application from tray."""
    _stop_event.set()
    icon.stop()
    if _app_ref:
        try:
            _app_ref.quit()
            _app_ref.destroy()
        except Exception:
            pass


def start_tray(app=None) -> bool:
    """Start the system tray icon. Returns True if started successfully."""
    global _icon_instance, _app_ref

    if not _TRAY_AVAILABLE:
        return False

    _app_ref = app
    _stop_event.clear()

    cpu, ram = _get_metrics()
    image = _make_icon_image(cpu, ram)

    menu = pystray.Menu(
        pystray.MenuItem("Open FreeSystemDoctor", _on_open, default=True),
        pystray.MenuItem("Scan Now", _on_scan),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", _on_exit),
    )

    _icon_instance = pystray.Icon(
        name="FreeSystemDoctor",
        icon=image,
        title=f"FreeSystemDoctor  CPU: {cpu:.0f}%  RAM: {ram:.0f}%",
        menu=menu,
    )

    # Update loop in background thread
    update_thread = threading.Thread(
        target=_update_loop, args=(_icon_instance,), daemon=True
    )
    update_thread.start()

    # Run tray icon in its own thread
    tray_thread = threading.Thread(target=_icon_instance.run, daemon=True)
    tray_thread.start()

    return True


def stop_tray():
    """Stop the system tray icon."""
    global _icon_instance
    _stop_event.set()
    if _icon_instance:
        try:
            _icon_instance.stop()
        except Exception:
            pass
        _icon_instance = None


def is_running() -> bool:
    return _icon_instance is not None and not _stop_event.is_set()
