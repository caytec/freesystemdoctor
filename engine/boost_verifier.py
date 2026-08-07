"""
boost_verifier.py — measure, then keep or revert. Nobody else does this.

Every optimizer on the market applies tweaks and asserts they helped. None of
them check. This module measures the machine before a change, applies it,
measures again, and **automatically reverts the change if it made things
worse**.

The honest part is the noise margin. Two runs of the same benchmark on an idle
machine differ by a few percent; on a busy one, much more. So instead of
guessing a threshold, we take several baseline samples and derive the margin
from their actual spread. A change only counts as "worse" when it moves a
metric further than the machine's own measured noise.

Metrics, in order of trustworthiness:
  • timer_ms        — NtQueryTimerResolution, exact and deterministic
  • ram_available_mb— psutil, stable
  • cpu_ops_per_sec — benchmark.cpu_benchmark, real work but thermally noisy
  • dpc_pct         — kernel DPC time, meaningful but genuinely jittery
"""

from __future__ import annotations

import logging
import statistics
from typing import Callable, Optional

logger = logging.getLogger(__name__)

ProgressCb = Optional[Callable[[str, int], None]]

# metric key → (higher_is_better, human label, unit)
_METRICS = {
    "timer_ms":         (False, "Kernel timer", "ms"),
    "ram_available_mb": (True,  "Available RAM", "MB"),
    "cpu_ops_per_sec":  (True,  "CPU throughput", "ops/s"),
    "dpc_pct":          (False, "DPC latency", "%"),
}

# A metric must move more than this fraction *and* beyond the measured noise
# before we call it a real change. Guards against acting on rounding.
_MIN_RELATIVE_CHANGE = 0.02


def measure_profile(with_cpu: bool = True, cpu_seconds: int = 3) -> dict:
    """One measurement sweep. Keys match _METRICS (missing ones are omitted)."""
    profile: dict[str, float] = {}

    try:
        from . import cpu_optimizer
        tr = cpu_optimizer.get_timer_resolution()
        if tr.get("ok"):
            profile["timer_ms"] = float(tr["current_ms"])
    except Exception as exc:
        logger.debug("measure_profile timer: %s", exc)

    try:
        from . import _perf
        psutil = _perf.get_psutil()
        if psutil:
            profile["ram_available_mb"] = float(
                psutil.virtual_memory().available / (1024 * 1024))
    except Exception as exc:
        logger.debug("measure_profile ram: %s", exc)

    try:
        from . import deep_optimize
        d = deep_optimize.measure_dpc_latency(seconds=2)
        if d.get("ok"):
            profile["dpc_pct"] = float(d["dpc_time_pct"])
    except Exception as exc:
        logger.debug("measure_profile dpc: %s", exc)

    if with_cpu:
        try:
            from . import benchmark
            res = benchmark.cpu_benchmark(duration_sec=cpu_seconds)
            # benchmark falls back to threads when process spawn fails, which
            # changes the scale entirely — comparing across paths is invalid.
            if not res.get("error") and res.get("ops_per_sec"):
                profile["cpu_ops_per_sec"] = float(res["ops_per_sec"])
        except Exception as exc:
            logger.debug("measure_profile cpu: %s", exc)

    return profile


def _sample(n: int, with_cpu: bool, progress_cb: ProgressCb,
            base_pct: int, span: int, label: str) -> list[dict]:
    samples = []
    for i in range(n):
        if progress_cb:
            try:
                progress_cb(f"{label} ({i + 1}/{n})…",
                            base_pct + int((i / max(1, n)) * span))
            except Exception:
                pass
        samples.append(measure_profile(with_cpu=with_cpu))
    return samples


def _median_and_noise(samples: list[dict]) -> tuple[dict, dict]:
    """Median per metric, plus the observed spread used as the noise floor."""
    medians: dict[str, float] = {}
    noise: dict[str, float] = {}
    keys = set().union(*(s.keys() for s in samples)) if samples else set()
    for key in keys:
        vals = [s[key] for s in samples if key in s]
        if not vals:
            continue
        medians[key] = statistics.median(vals)
        # Full observed range is a conservative, assumption-free noise floor.
        noise[key] = (max(vals) - min(vals)) if len(vals) > 1 else 0.0
    return medians, noise


def compare(before: dict, noise: dict, after: dict) -> dict:
    """Classify each metric as better / worse / unchanged.

    A metric counts as changed only when it moves beyond BOTH the measured
    noise floor and a minimum relative change.
    """
    deltas = {}
    worse, better = [], []
    for key, (higher_better, label, unit) in _METRICS.items():
        if key not in before or key not in after:
            continue
        b, a = before[key], after[key]
        diff = a - b
        floor = max(noise.get(key, 0.0), abs(b) * _MIN_RELATIVE_CHANGE)
        if abs(diff) <= floor:
            verdict = "unchanged"
        elif (diff > 0) == higher_better:
            verdict = "better"
            better.append(label)
        else:
            verdict = "worse"
            worse.append(label)
        deltas[key] = {"label": label, "unit": unit, "before": round(b, 3),
                       "after": round(a, 3), "diff": round(diff, 3),
                       "noise_floor": round(floor, 3), "verdict": verdict}
    return {"metrics": deltas, "worse": worse, "better": better}


def verify(apply_fn: Callable[[], tuple], name: str,
           revert_fn: Optional[Callable[[], tuple]] = None,
           samples: int = 3, with_cpu: bool = True,
           progress_cb: ProgressCb = None) -> dict:
    """Apply a change, measure it, and revert it if it made things worse.

    Returns {applied, name, verdict, reverted, apply_msg, revert_msg,
             comparison, summary}

    verdict is one of: improved | no_change | worse_reverted | worse_kept
                     | apply_failed
    """
    if progress_cb:
        try:
            progress_cb(f"Measuring baseline for “{name}”…", 2)
        except Exception:
            pass

    before_samples = _sample(samples, with_cpu, progress_cb, 5, 35,
                             "Baseline")
    before, noise = _median_and_noise(before_samples)

    if progress_cb:
        try:
            progress_cb(f"Applying “{name}”…", 45)
        except Exception:
            pass
    try:
        res = apply_fn()
        applied, apply_msg = res if isinstance(res, tuple) else (bool(res), str(res))
    except Exception as exc:
        applied, apply_msg = False, str(exc)

    if not applied:
        return {"applied": False, "name": name, "verdict": "apply_failed",
                "reverted": False, "apply_msg": apply_msg, "revert_msg": "",
                "comparison": {}, "summary": f"Could not apply: {apply_msg}"}

    after_samples = _sample(samples, with_cpu, progress_cb, 55, 35, "Re-measuring")
    after, _ = _median_and_noise(after_samples)

    comparison = compare(before, noise, after)
    worse, better = comparison["worse"], comparison["better"]

    reverted, revert_msg, verdict = False, "", ""
    # Revert only when something got worse and nothing got better — a tweak
    # that trades one metric for another is a judgement call, not a regression.
    if worse and not better:
        if revert_fn is not None:
            if progress_cb:
                try:
                    progress_cb(f"“{name}” made things worse — reverting…", 92)
                except Exception:
                    pass
            try:
                r = revert_fn()
                reverted, revert_msg = r if isinstance(r, tuple) else (bool(r), str(r))
            except Exception as exc:
                reverted, revert_msg = False, str(exc)
            verdict = "worse_reverted" if reverted else "worse_kept"
        else:
            verdict = "worse_kept"
    elif better:
        verdict = "improved"
    else:
        verdict = "no_change"

    summaries = {
        "improved": f"Improved: {', '.join(better)}",
        "no_change": "No measurable change (within this machine's noise)",
        "worse_reverted": f"Made {', '.join(worse)} worse — automatically reverted",
        "worse_kept": f"Made {', '.join(worse)} worse — could not revert automatically",
    }
    if progress_cb:
        try:
            progress_cb("Done", 100)
        except Exception:
            pass
    return {"applied": True, "name": name, "verdict": verdict,
            "reverted": reverted, "apply_msg": apply_msg,
            "revert_msg": revert_msg, "comparison": comparison,
            "summary": summaries.get(verdict, verdict)}


def verify_tweak(module_name: str, tweak_id: str, name: str,
                 samples: int = 3, with_cpu: bool = True,
                 progress_cb: ProgressCb = None) -> dict:
    """verify() for any module following the apply_tweak/revert_tweak contract."""
    import importlib
    mod = importlib.import_module(f"engine.{module_name}")
    apply_name = "apply_deep_tweak" if module_name == "cpu_optimizer" else "apply_tweak"
    revert_name = "revert_deep_tweak" if module_name == "cpu_optimizer" else "revert_tweak"
    apply_fn = getattr(mod, apply_name)
    revert_fn = getattr(mod, revert_name, None)
    return verify(lambda: apply_fn(tweak_id), name,
                  revert_fn=(lambda: revert_fn(tweak_id)) if revert_fn else None,
                  samples=samples, with_cpu=with_cpu, progress_cb=progress_cb)
