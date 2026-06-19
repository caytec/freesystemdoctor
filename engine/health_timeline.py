"""
Health Timeline — persist system-health snapshots over time and expose them for
trend charting + regression alerts.

Storage: ~/.fsd/health_history.json  (atomic writes, process-local lock).
Pure engine module — no tkinter, no heavy deps.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, date, timedelta
from pathlib import Path

SCHEMA_VERSION = 1
_MAX_SNAPSHOTS = 2000

_DIR = Path(os.path.expanduser("~")) / ".fsd"
_FILE = _DIR / "health_history.json"
_lock = threading.Lock()

# canonical metric keys usable by the chart
SCORE_KEYS = ("overall", "privacy", "space", "speed", "security")
METRIC_KEYS = ("cpu_pct", "ram_pct", "disk_pct")


# ── normalization ─────────────────────────────────────────────────────────────
def _norm_scores(scores: dict) -> dict:
    """Accept the get_health_scores() dict (with *_score and short aliases) and
    return a compact {overall,privacy,space,speed,security} of ints."""
    scores = scores or {}

    def pick(*names):
        for n in names:
            if n in scores and scores[n] is not None:
                try:
                    return int(round(float(scores[n])))
                except (TypeError, ValueError):
                    pass
        return 0

    return {
        "overall":  pick("overall", "overall_score"),
        "privacy":  pick("privacy", "privacy_score"),
        "space":    pick("space", "space_score"),
        "speed":    pick("speed", "speed_score"),
        "security": pick("security", "security_score"),
    }


def _norm_metrics(metrics: dict | None) -> dict:
    metrics = metrics or {}

    def pick(*names):
        for n in names:
            if n in metrics and metrics[n] is not None:
                try:
                    return round(float(metrics[n]), 1)
                except (TypeError, ValueError):
                    pass
        return None

    out = {
        "cpu_pct":  pick("cpu_pct", "cpu", "cpu_percent"),
        "ram_pct":  pick("ram_pct", "ram", "memory_percent", "mem_percent"),
        "disk_pct": pick("disk_pct", "disk", "disk_percent"),
    }
    return {k: v for k, v in out.items() if v is not None}


# ── storage ─────────────────────────────────────────────────────────────────
def _read_raw() -> dict:
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("snapshots"), list):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        pass
    return {"version": SCHEMA_VERSION, "snapshots": []}


def _write_raw(data: dict) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    tmp = _FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _FILE)


def load_history() -> list[dict]:
    """Return snapshots sorted ascending by timestamp. [] on missing/corrupt."""
    data = _read_raw()
    snaps = data.get("snapshots", [])
    try:
        snaps.sort(key=lambda s: s.get("ts", ""))
    except Exception:
        pass
    return snaps


def record_snapshot(scores: dict, metrics: dict | None = None,
                    source: str = "launch") -> dict | None:
    """Append a snapshot. For source='launch' de-dupe to one per calendar day so
    repeated launches don't flood the file. Returns the stored snapshot (or None)."""
    snap = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "scores": _norm_scores(scores),
        "metrics": _norm_metrics(metrics),
    }
    with _lock:
        data = _read_raw()
        snaps = data.get("snapshots", [])

        if source == "launch":
            today = date.today().isoformat()
            for s in snaps:
                if s.get("source") == "launch" and str(s.get("ts", "")).startswith(today):
                    return None  # already have a launch snapshot today

        snaps.append(snap)
        if len(snaps) > _MAX_SNAPSHOTS:
            snaps = snaps[-_MAX_SNAPSHOTS:]
        data["snapshots"] = snaps
        data["version"] = SCHEMA_VERSION
        try:
            _write_raw(data)
        except OSError:
            return None
    return snap


def get_series(metric_key: str, days: int = 30) -> list[tuple[str, float]]:
    """Return [(iso_ts, value)] for a metric over the last `days`.
    metric_key in SCORE_KEYS or METRIC_KEYS."""
    cutoff = datetime.now() - timedelta(days=days)
    out: list[tuple[str, float]] = []
    for s in load_history():
        ts = s.get("ts", "")
        try:
            when = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if when < cutoff:
            continue
        if metric_key in SCORE_KEYS:
            bucket = s.get("scores", {})
        else:
            bucket = s.get("metrics", {})
        if metric_key in bucket and bucket[metric_key] is not None:
            out.append((ts, float(bucket[metric_key])))
    return out


def get_daily_series(metric_key: str, days: int = 30) -> list[tuple[date, float]]:
    """Per-day mean of a metric over the last `days`, ascending by date."""
    buckets: dict[date, list[float]] = {}
    for ts, val in get_series(metric_key, days):
        try:
            d = datetime.fromisoformat(ts).date()
        except ValueError:
            continue
        buckets.setdefault(d, []).append(val)
    return [(d, sum(v) / len(v)) for d, v in sorted(buckets.items())]


def detect_regression(metric_key: str = "overall",
                      drop_threshold: int = 10,
                      window: int = 7) -> dict | None:
    """Compare the newest snapshot value to the mean of the prior `window` points.
    Returns an alert dict if the latest dropped >= drop_threshold, else None."""
    series = get_series(metric_key, days=60)
    if len(series) < 3:
        return None
    values = [v for _, v in series]
    latest = values[-1]
    prior = values[-(window + 1):-1] if len(values) > 1 else []
    if not prior:
        return None
    baseline = sum(prior) / len(prior)
    drop = baseline - latest
    if drop >= drop_threshold:
        return {
            "metric": metric_key,
            "latest": round(latest, 1),
            "baseline": round(baseline, 1),
            "drop": round(drop, 1),
            "severity": "DANGER" if drop >= drop_threshold * 2 else "WARNING",
        }
    return None
