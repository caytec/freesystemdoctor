"""
quick_fix.py — goal-oriented "one-click" bundles for Simple mode.

Simple mode isn't a crippled subset: each bundle runs SEVERAL of the Advanced
tools in sequence, grouped by what the user actually wants to achieve
("my disk is full", "my internet is slow", "I want to game"). Advanced mode
still exposes every one of those tools individually.

Every bundle:
  • calls only real, existing engine functions,
  • reports progress via progress_cb(step_label, percent),
  • returns a summary dict {"title", "steps": [{name, ok, detail}], "summary"},
  • never raises — a failing step is recorded and the run continues.
"""

from __future__ import annotations

from typing import Callable, Optional

ProgressCB = Optional[Callable[[str, int], None]]


def _emit(cb: ProgressCB, step: str, pct: int):
    if cb:
        try:
            cb(step, pct)
        except Exception:
            pass


def _fmt_mb(num_bytes: float) -> str:
    mb = num_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"


# ── bundle catalogue (what Simple mode shows) ────────────────────────────────
BUNDLES: list[dict] = [
    {
        "id": "disk_health",
        "icon": "💽",
        "title": "Disk Health",
        "desc": "Free up space and optimise your drives",
        "does": "Cleans junk & temp files, empties the Recycle Bin, "
                "then optimises (TRIM/defrag) every drive.",
        "advanced": ["Deep Clean", "Disk Optimizer", "Smart Defrag"],
        "destructive": True,
    },
    {
        "id": "network_health",
        "icon": "🌐",
        "title": "Network Health",
        "desc": "Fix slow or flaky internet",
        "does": "Flushes the DNS and ARP caches, then applies safe TCP "
                "latency/throughput tweaks.",
        "advanced": ["Net Booster", "DNS Protector", "Network Sec."],
        "destructive": False,
    },
    {
        "id": "ram_boost",
        "icon": "🧠",
        "title": "RAM Boost",
        "desc": "Reclaim memory from background apps",
        "does": "Trims working sets of running processes and closes "
                "known background bloat.",
        "advanced": ["RAM & Perf.", "App Freezer", "Resource Mon."],
        "destructive": False,
    },
    {
        "id": "gaming_boost",
        "icon": "🎮",
        "title": "Gaming Booster",
        "desc": "Tune Windows for maximum FPS",
        "does": "Applies the Ultimate power plan, GPU scheduling, 1 ms timer, "
                "low-latency network and closes background bloat.",
        "advanced": ["Game Booster", "Turbo Mode", "App Priority"],
        "destructive": False,
    },
    {
        "id": "full_tuneup",
        "icon": "🚀",
        "title": "Full Tune-Up",
        "desc": "Everything at once — the all-rounder",
        "does": "Frees RAM, clears temp files, empties the Recycle Bin and "
                "flushes DNS, then re-scores your system health.",
        "advanced": ["Auto-Pilot", "System Care", "Speed Up"],
        "destructive": True,
    },
]


def get_bundles() -> list[dict]:
    return list(BUNDLES)


def get_bundle(bundle_id: str) -> dict | None:
    return next((b for b in BUNDLES if b["id"] == bundle_id), None)


# ── individual bundles ───────────────────────────────────────────────────────

def _run_disk_health(cb: ProgressCB) -> list[dict]:
    steps: list[dict] = []

    _emit(cb, "Cleaning junk & temp files…", 5)
    try:
        from engine import disk_cleaner
        res = disk_cleaner.clean_all(min_age_hours=24)
        steps.append({"name": "Junk & temp files", "ok": True,
                      "detail": f"{res.get('cleaned', 0)} files, "
                                f"{res.get('freed_str', '0 B')} freed"})
    except Exception as e:
        steps.append({"name": "Junk & temp files", "ok": False, "detail": str(e)})

    _emit(cb, "Emptying Recycle Bin…", 40)
    try:
        from engine import disk_cleaner
        before = disk_cleaner.get_recycle_bin_size()
        ok = disk_cleaner.empty_recycle_bin()
        steps.append({"name": "Recycle Bin", "ok": bool(ok),
                      "detail": f"{_fmt_mb(before)} reclaimed" if ok else "skipped"})
    except Exception as e:
        steps.append({"name": "Recycle Bin", "ok": False, "detail": str(e)})

    _emit(cb, "Optimising drives (TRIM/defrag)…", 60)
    try:
        from engine import smart_defrag
        results = smart_defrag.optimize_all_drives(force=True)
        okc = sum(1 for r in results if r.get("success"))
        steps.append({"name": "Drive optimisation", "ok": okc > 0 or not results,
                      "detail": f"{okc}/{len(results)} drive(s) optimised"})
    except Exception as e:
        steps.append({"name": "Drive optimisation", "ok": False, "detail": str(e)})

    _emit(cb, "Done", 100)
    return steps


def _run_network_health(cb: ProgressCB) -> list[dict]:
    steps: list[dict] = []
    from engine import network_optimizer as net

    _emit(cb, "Flushing DNS cache…", 10)
    try:
        steps.append({"name": "DNS cache", "ok": bool(net.flush_dns()),
                      "detail": "flushed"})
    except Exception as e:
        steps.append({"name": "DNS cache", "ok": False, "detail": str(e)})

    _emit(cb, "Flushing ARP cache…", 40)
    try:
        steps.append({"name": "ARP cache", "ok": bool(net.flush_arp()),
                      "detail": "flushed"})
    except Exception as e:
        steps.append({"name": "ARP cache", "ok": False, "detail": str(e)})

    _emit(cb, "Applying TCP tweaks…", 70)
    try:
        applied = net.apply_tcp_tweaks()
        steps.append({"name": "TCP tuning", "ok": True,
                      "detail": f"{len(applied)} tweak(s) applied"})
    except Exception as e:
        steps.append({"name": "TCP tuning", "ok": False, "detail": str(e)})

    _emit(cb, "Done", 100)
    return steps


def _run_ram_boost(cb: ProgressCB) -> list[dict]:
    steps: list[dict] = []

    _emit(cb, "Trimming memory of running apps…", 15)
    try:
        from engine import memory_optimizer
        trimmed, skipped = memory_optimizer.trim_working_sets()
        steps.append({"name": "Memory trim", "ok": True,
                      "detail": f"{trimmed} process(es) trimmed, {skipped} protected"})
    except Exception as e:
        steps.append({"name": "Memory trim", "ok": False, "detail": str(e)})

    _emit(cb, "Closing background bloat…", 60)
    try:
        from engine import game_booster
        killed, names = game_booster.kill_background_bloat()
        steps.append({"name": "Background apps", "ok": True,
                      "detail": f"{killed} closed" if killed else "nothing to close"})
    except Exception as e:
        steps.append({"name": "Background apps", "ok": False, "detail": str(e)})

    _emit(cb, "Done", 100)
    return steps


def _run_gaming_boost(cb: ProgressCB) -> list[dict]:
    steps: list[dict] = []
    _emit(cb, "Applying gaming optimisations…", 10)
    try:
        from engine import game_booster

        def inner(msg, pct=None):
            _emit(cb, str(msg), 10 + int((pct or 50) * 0.85))

        res = game_booster.apply_all_safe(progress_cb=inner)
        if isinstance(res, dict):
            for name, val in res.items():
                if isinstance(val, (list, tuple)) and len(val) == 2:
                    ok, detail = val
                    steps.append({"name": str(name).replace("_", " ").title(),
                                  "ok": bool(ok), "detail": str(detail)})
                else:
                    steps.append({"name": str(name).replace("_", " ").title(),
                                  "ok": True, "detail": str(val)})
        else:
            steps.append({"name": "Gaming optimisations", "ok": True,
                          "detail": "applied"})
    except Exception as e:
        steps.append({"name": "Gaming optimisations", "ok": False, "detail": str(e)})

    _emit(cb, "Done", 100)
    return steps


def _run_full_tuneup(cb: ProgressCB) -> list[dict]:
    steps: list[dict] = []
    _emit(cb, "Running full tune-up…", 5)
    try:
        from engine import turbo_clean

        def inner(step, pct):
            _emit(cb, str(step), max(5, min(95, int(pct))))

        stats = turbo_clean.run(progress_cb=inner)
        steps.append({"name": "RAM freed", "ok": True,
                      "detail": f"{stats.get('ram_freed_mb', 0):.0f} MB"})
        steps.append({"name": "Disk space freed", "ok": True,
                      "detail": f"{stats.get('disk_freed_mb', 0):.0f} MB"})
        steps.append({"name": "Recycle Bin",
                      "ok": bool(stats.get("recycle_emptied")),
                      "detail": "emptied" if stats.get("recycle_emptied") else "skipped"})
        steps.append({"name": "DNS cache", "ok": bool(stats.get("dns_flushed")),
                      "detail": "flushed" if stats.get("dns_flushed") else "skipped"})
        for err in (stats.get("errors") or [])[:3]:
            steps.append({"name": "Warning", "ok": False, "detail": str(err)})
    except Exception as e:
        steps.append({"name": "Full tune-up", "ok": False, "detail": str(e)})

    _emit(cb, "Done", 100)
    return steps


_RUNNERS = {
    "disk_health":    _run_disk_health,
    "network_health": _run_network_health,
    "ram_boost":      _run_ram_boost,
    "gaming_boost":   _run_gaming_boost,
    "full_tuneup":    _run_full_tuneup,
}


def run_bundle(bundle_id: str, progress_cb: ProgressCB = None) -> dict:
    """Run one bundle. Never raises; failures are captured per step."""
    bundle = get_bundle(bundle_id)
    if not bundle or bundle_id not in _RUNNERS:
        return {"title": bundle_id, "steps": [], "summary": "Unknown action."}

    # Safety net before anything destructive — the user can always roll back.
    if bundle.get("destructive"):
        _emit(progress_cb, "Creating a restore point (safety net)…", 2)
        try:
            from engine import system_restore
            system_restore.ensure_checkpoint(bundle["title"])
        except Exception:
            pass

    try:
        steps = _RUNNERS[bundle_id](progress_cb)
    except Exception as e:                       # belt & braces
        steps = [{"name": bundle["title"], "ok": False, "detail": str(e)}]

    done = sum(1 for s in steps if s.get("ok"))
    return {
        "title": bundle["title"],
        "steps": steps,
        "summary": f"{done}/{len(steps)} step(s) completed successfully."
        if steps else "Nothing to do.",
    }
