"""
change_ledger.py — append-only journal of every change this app has applied.

Until now each module kept its own backup file in its own format, in three
different directories. Nothing recorded *when* a change happened or let the
user see everything in one place. This module is that record.

It stores only what is needed to show and undo a change; the actual old values
stay in the owning module's backup file, which remains the source of truth for
reverting. The ledger points at them.

Never raises — a failure to journal must never break the change itself.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_LEDGER = Path(os.path.expanduser("~")) / ".fsd" / "change_ledger.json"
_MAX_ENTRIES = 500
_lock = threading.Lock()

# module id → (import path, revert function name)
_REVERTERS = {
    "deep_optimize":  ("engine.deep_optimize", "revert_tweak"),
    "gpu_boost":      ("engine.gpu_boost", "revert_tweak"),
    "ram_master":     ("engine.ram_master", "revert_tweak"),
    "cpu_optimizer":  ("engine.cpu_optimizer", "revert_deep_tweak"),
}

_MODULE_LABELS = {
    "deep_optimize": "Deep Optimize",
    "gpu_boost":     "GPU Boost",
    "ram_master":    "RAM Master",
    "cpu_optimizer": "CPU Optimizer",
    "ultimate_boost": "Ultimate Boost",
}


def _read() -> list[dict]:
    try:
        if _LEDGER.exists():
            data = json.loads(_LEDGER.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _write(entries: list[dict]) -> None:
    try:
        _LEDGER.parent.mkdir(parents=True, exist_ok=True)
        tmp = _LEDGER.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries[-_MAX_ENTRIES:], indent=2),
                       encoding="utf-8")
        os.replace(tmp, _LEDGER)
    except Exception as exc:
        logger.debug("change_ledger._write: %s", exc)


def record(module: str, tweak_id: str, name: str, ok: bool,
           msg: str = "", reverted: bool = False) -> None:
    """Journal one applied change. Silent on failure by design."""
    try:
        with _lock:
            entries = _read()
            entries.append({
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "module": module,
                "tweak_id": tweak_id,
                "name": name,
                "ok": bool(ok),
                "msg": str(msg)[:200],
                "reverted": bool(reverted),
                "revertable": module in _REVERTERS,
            })
            _write(entries)
    except Exception:
        pass


def mark_reverted(ts: str, tweak_id: str) -> None:
    """Flag the matching entry as reverted (newest match wins)."""
    try:
        with _lock:
            entries = _read()
            for e in reversed(entries):
                if e.get("ts") == ts and e.get("tweak_id") == tweak_id:
                    e["reverted"] = True
                    break
            _write(entries)
    except Exception:
        pass


def get_entries(limit: int = 200, only_active: bool = False) -> list[dict]:
    """Newest first. only_active hides already-reverted and failed changes."""
    entries = _read()
    if only_active:
        entries = [e for e in entries
                   if e.get("ok") and not e.get("reverted")]
    entries = list(reversed(entries))[:limit]
    for e in entries:
        e["module_label"] = _MODULE_LABELS.get(e.get("module", ""),
                                               e.get("module", ""))
    return entries


def revert_entry(entry: dict) -> tuple[bool, str]:
    """Undo one journalled change by delegating to its owning module."""
    module = entry.get("module", "")
    tweak_id = entry.get("tweak_id", "")
    target = _REVERTERS.get(module)
    if not target:
        return False, f"{_MODULE_LABELS.get(module, module)} has no per-item undo"
    mod_path, fn_name = target
    try:
        import importlib
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, fn_name, None)
        if fn is None:
            return False, f"{mod_path}.{fn_name} is unavailable"
        ok, msg = fn(tweak_id)
        if ok:
            mark_reverted(entry.get("ts", ""), tweak_id)
        return bool(ok), str(msg)
    except Exception as exc:
        logger.exception("revert_entry(%s/%s)", module, tweak_id)
        return False, str(exc)


def revert_all(progress_cb: Optional[callable] = None) -> dict:
    """Undo every still-active change, newest first (reverse order of apply)."""
    active = get_entries(limit=_MAX_ENTRIES, only_active=True)
    done, failed = 0, []
    for i, entry in enumerate(active):
        if progress_cb:
            try:
                progress_cb(f"Reverting {entry.get('name', '?')}…",
                            int((i / max(1, len(active))) * 100))
            except Exception:
                pass
        ok, msg = revert_entry(entry)
        if ok:
            done += 1
        elif entry.get("revertable"):
            failed.append(f"{entry.get('name', '?')}: {msg}")
    if progress_cb:
        try:
            progress_cb("Done", 100)
        except Exception:
            pass
    return {"reverted": done, "failed": failed, "total": len(active)}


def clear_history() -> bool:
    """Forget the journal. Does not undo anything — backups stay intact."""
    try:
        with _lock:
            _write([])
        return True
    except Exception:
        return False
