"""
pro_upsell_smart.py — trigger-based Pro upgrade prompts.

WHEN we surface a Pro card (and only then):
  • After a Deep Clean that freed > IMPACT_GB_TRIGGER (default 10 GB).
  • After a Health Check that found > 20 issues at once.
  • After 3rd manual scan in a single calendar week (auto-schedule pitch).
  • After Game Booster runs for 5th time (per-game profile pitch).

We NEVER:
  • Pop modals over the user's current task.
  • Show more than one Pro prompt per 72 hours.
  • Show a Pro prompt within 30 min of app launch (give the user time
    to USE the product before pitching).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "FreeSystemDoctor"
STATE_FILE = CONFIG_DIR / "pro_upsell.json"

# Tuning knobs (keep conservative — annoyed users churn before they pay)
MIN_HOURS_BETWEEN_PROMPTS = 72
MIN_MINUTES_AFTER_LAUNCH  = 30
IMPACT_GB_TRIGGER         = 10.0
ISSUES_COUNT_TRIGGER      = 20
SCANS_PER_WEEK_TRIGGER    = 3
GAME_RUNS_TRIGGER         = 5


# ── persistence ──────────────────────────────────────────────────────────────

def _default() -> dict:
    return {
        "launched_at": datetime.now().isoformat(),
        "last_prompt_at": None,
        "scan_log": [],            # ISO timestamps
        "game_runs": 0,
        "dismissed_contexts": [],  # ["post-scan", "post-clean", ...]
    }


def _load() -> dict:
    if not STATE_FILE.exists():
        state = _default()
        _save(state)
        return state
    try:
        s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        for k, v in _default().items():
            s.setdefault(k, v)
        return s
    except Exception:
        return _default()


def _save(state: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def mark_app_launched() -> None:
    state = _load()
    state["launched_at"] = datetime.now().isoformat()
    _save(state)


def record_scan() -> None:
    state = _load()
    state.setdefault("scan_log", []).append(datetime.now().isoformat())
    state["scan_log"] = state["scan_log"][-50:]
    _save(state)


def record_game_run() -> None:
    state = _load()
    state["game_runs"] = state.get("game_runs", 0) + 1
    _save(state)


def dismiss_context(context: str) -> None:
    state = _load()
    dismissed = set(state.get("dismissed_contexts", []))
    dismissed.add(context)
    state["dismissed_contexts"] = sorted(dismissed)
    _save(state)


# ── trigger evaluation ───────────────────────────────────────────────────────

def _hours_since(iso: Optional[str]) -> float:
    if not iso:
        return 9999.0
    try:
        return (datetime.now() - datetime.fromisoformat(iso)).total_seconds() / 3600
    except ValueError:
        return 9999.0


def _scans_this_week() -> int:
    state = _load()
    cutoff = datetime.now() - timedelta(days=7)
    count = 0
    for iso in state.get("scan_log", []):
        try:
            if datetime.fromisoformat(iso) > cutoff:
                count += 1
        except ValueError:
            continue
    return count


def _eligible_to_show(context: str) -> bool:
    state = _load()
    if context in state.get("dismissed_contexts", []):
        return False
    if _hours_since(state.get("last_prompt_at")) < MIN_HOURS_BETWEEN_PROMPTS:
        return False
    launched = state.get("launched_at")
    if launched:
        try:
            elapsed = (datetime.now() - datetime.fromisoformat(launched)).total_seconds()
            if elapsed < MIN_MINUTES_AFTER_LAUNCH * 60:
                return False
        except ValueError:
            pass
    return True


def _mark_shown() -> None:
    state = _load()
    state["last_prompt_at"] = datetime.now().isoformat()
    _save(state)


# ── public decision API ──────────────────────────────────────────────────────

def should_show_post_clean(gb_freed: float) -> bool:
    if gb_freed < IMPACT_GB_TRIGGER:
        return False
    if not _eligible_to_show("post-clean"):
        return False
    _mark_shown()
    return True


def should_show_post_scan(issues_found: int) -> bool:
    record_scan()
    if issues_found < ISSUES_COUNT_TRIGGER:
        # Still consider the "frequent scanner" pitch
        if _scans_this_week() < SCANS_PER_WEEK_TRIGGER:
            return False
    if not _eligible_to_show("post-scan"):
        return False
    _mark_shown()
    return True


def should_show_post_game() -> bool:
    state = _load()
    if state.get("game_runs", 0) < GAME_RUNS_TRIGGER:
        return False
    if not _eligible_to_show("game"):
        return False
    _mark_shown()
    return True


def should_show_drivers(updates_count: int) -> bool:
    if updates_count < 5:
        return False
    if not _eligible_to_show("drivers"):
        return False
    _mark_shown()
    return True
