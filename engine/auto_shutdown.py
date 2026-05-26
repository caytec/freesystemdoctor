"""Auto-Shutdown Scheduler — schedule shutdown / restart / sleep / hibernate.

Inspired by Wise Care 365 Pro and Glary Utilities Pro auto-shutdown feature.
"""

import os
import json
import threading
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

_CFG_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "FreeSystemDoctor"
_CFG_FILE = _CFG_DIR / "auto_shutdown.json"

ACTIONS = {
    "shutdown":  ("shutdown.exe", ["/s", "/t", "0", "/f"]),
    "restart":   ("shutdown.exe", ["/r", "/t", "0", "/f"]),
    "logoff":    ("shutdown.exe", ["/l"]),
    # Sleep needs hibernate disabled first (else SetSuspendState hibernates).
    # We invoke via cmd /c so the rundll32 args are passed as a single string.
    "sleep":     ("cmd.exe", ["/c", "powercfg -h off & "
                                       "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"]),
    "hibernate": ("shutdown.exe", ["/h"]),
}


_active_thread: threading.Thread = None
_cancel_event = threading.Event()


def _save(state: dict):
    _CFG_DIR.mkdir(parents=True, exist_ok=True)
    _CFG_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load() -> dict:
    if _CFG_FILE.exists():
        try:
            return json.loads(_CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"active": False}


def is_active() -> bool:
    return _active_thread is not None and _active_thread.is_alive()


def get_state() -> dict:
    state = _load()
    if state.get("active"):
        try:
            target = datetime.fromisoformat(state.get("target", ""))
            remaining = max(0, int((target - datetime.now()).total_seconds()))
            state["remaining_seconds"] = remaining
        except Exception:
            state["remaining_seconds"] = 0
    return state


def schedule(action: str, when_dt: datetime, on_tick=None, on_done=None) -> bool:
    """Schedule an action at a specific datetime. Cancels prior."""
    global _active_thread

    if action not in ACTIONS:
        return False
    cancel()

    target = when_dt
    _save({
        "active":  True,
        "action":  action,
        "target":  target.isoformat(),
    })

    _cancel_event.clear()

    def _run():
        while not _cancel_event.is_set():
            now = datetime.now()
            if now >= target:
                _execute(action)
                if on_done:
                    try: on_done(action)
                    except Exception: pass
                _save({"active": False})
                return
            remaining = (target - now).total_seconds()
            if on_tick:
                try: on_tick(int(remaining))
                except Exception: pass
            _cancel_event.wait(min(1.0, remaining))
        _save({"active": False})

    _active_thread = threading.Thread(target=_run, daemon=True)
    _active_thread.start()
    return True


def schedule_in(action: str, minutes: float, on_tick=None, on_done=None) -> bool:
    return schedule(action,
                     datetime.now() + timedelta(minutes=minutes),
                     on_tick, on_done)


def cancel() -> bool:
    global _active_thread
    _cancel_event.set()
    if _active_thread and _active_thread.is_alive():
        _active_thread.join(timeout=2)
    _active_thread = None
    _save({"active": False})
    return True


def _execute(action: str):
    exe, args = ACTIONS[action]
    try:
        subprocess.Popen([exe] + args, creationflags=0x08000000)
    except Exception:
        pass


def execute_now(action: str) -> bool:
    if action not in ACTIONS:
        return False
    _execute(action)
    return True
