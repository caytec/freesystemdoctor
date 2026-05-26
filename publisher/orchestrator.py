"""Top-level publish orchestrator + state tracking."""

import importlib
import json
from datetime import datetime
from pathlib import Path

from .config import RELEASE_CONFIG, ROOT
from .directory import SUBMISSION_TARGETS, get_target

STATE_DIR = ROOT / "releases" / "_state"


def _state_file(version: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"v{version}.json"


def _load_state(version: str) -> dict:
    sf = _state_file(version)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": version, "submitted": {}}


def _save_state(state: dict):
    sf = _state_file(state["version"])
    sf.write_text(json.dumps(state, indent=2), encoding="utf-8")


def publish_to(target_id: str, manifest: dict,
                 open_browser: bool = True) -> dict:
    """Publish to a single target by ID."""
    target = get_target(target_id)
    if not target:
        return {"target": target_id, "ok": False,
                 "msg": f"Unknown target: {target_id}"}

    result = {}
    if target["type"] == "api":
        try:
            mod_name = f"publisher.api_publishers.{target['api_module']}"
            mod = importlib.import_module(mod_name)
            result = mod.publish(manifest)
        except Exception as e:
            result = {"target": target_id, "ok": False,
                       "msg": f"Publisher import/run failed: {e}"}
    else:
        from .manual_submitter import submit
        result = submit(target, manifest,
                         locale="pl" if target["region"] == "poland" else "en")

    # Update state
    state = _load_state(manifest["version"])
    state["submitted"][target_id] = {
        "timestamp": datetime.now().isoformat(),
        "ok":        result.get("ok", False),
        "url":       result.get("url", ""),
        "msg":       result.get("msg", ""),
    }
    _save_state(state)

    return result


def publish_all(manifest: dict,
                  include_apis: bool = True,
                  include_manual: bool = False,
                  region: str = None,
                  progress_cb=None) -> list[dict]:
    """Publish to all targets matching filters."""
    results = []
    targets = SUBMISSION_TARGETS
    if region:
        targets = [t for t in targets if t["region"] == region]

    for i, target in enumerate(targets):
        if target["type"] == "api" and not include_apis:
            continue
        if target["type"] == "manual" and not include_manual:
            continue

        if progress_cb:
            try:
                progress_cb(i, len(targets), target["label"])
            except Exception:
                pass

        result = publish_to(target["id"], manifest, open_browser=False)
        result["target_label"] = target["label"]
        results.append(result)

    return results


def get_status(version: str) -> dict:
    """Return submission status for the given version."""
    return _load_state(version)


def open_dashboard_url(version: str) -> str:
    """Generate a quick HTML status dashboard."""
    state = _load_state(version)
    status_dir = STATE_DIR.parent / f"v{version}"
    status_dir.mkdir(parents=True, exist_ok=True)
    out = status_dir / "publish-status.html"

    rows = []
    for tgt in SUBMISSION_TARGETS:
        sub = state["submitted"].get(tgt["id"], {})
        ok = sub.get("ok", False)
        ts = sub.get("timestamp", "")
        url = sub.get("url", "")
        msg = sub.get("msg", "")
        status_icon = "✅" if ok else ("⚪" if not ts else "❌")
        url_html = f'<a href="{url}">{url}</a>' if url else ""
        rows.append(
            f"<tr><td>{status_icon}</td><td>{tgt['label']}</td>"
            f"<td>{tgt['region']}</td><td>{tgt['type']}</td>"
            f"<td>{ts[:19] if ts else '—'}</td>"
            f"<td>{url_html}</td><td>{msg}</td></tr>")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>FSD v{version} Publish Status</title>
<style>
body {{ font: 14px Segoe UI, sans-serif; background: #0d1117; color: #e8edf5;
        padding: 24px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ padding: 8px 12px; border-bottom: 1px solid #1e2d45; text-align: left; }}
th {{ color: #00d4ff; }}
a {{ color: #00d4ff; }}
</style></head><body>
<h1>FreeSystemDoctor v{version} — Publish Status</h1>
<p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<table>
<tr><th></th><th>Target</th><th>Region</th><th>Type</th>
    <th>Last submitted</th><th>URL</th><th>Status</th></tr>
{''.join(rows)}
</table></body></html>"""

    out.write_text(html, encoding="utf-8")
    return str(out)
