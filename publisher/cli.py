"""CLI for publisher — runnable as `python -m publisher.cli ...`.

Examples:
  python -m publisher.cli build              # Build artifacts only
  python -m publisher.cli release             # Build + publish to all APIs
  python -m publisher.cli release --manual    # Build + publish APIs + open all manual sites
  python -m publisher.cli release --version 2.3.0
  python -m publisher.cli status              # Show submission status
  python -m publisher.cli targets             # List all targets
"""

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .config import RELEASE_CONFIG, get_version, save_version
from .release_builder import build_release_artifacts
from .orchestrator import publish_all, publish_to, get_status, open_dashboard_url
from .directory import SUBMISSION_TARGETS, list_targets, count_by_type


def cmd_build(args):
    print(f"[build] Building release artifacts for v{args.version or get_version()}")
    if args.version:
        save_version(args.version)
    manifest = build_release_artifacts(version=args.version,
                                         skip_build=args.skip_build)
    print(f"[build] Done. {len(manifest['artifacts'])} artifacts in {manifest['release_dir']}")
    for a in manifest["artifacts"]:
        size_mb = a["size"] / 1024 / 1024
        print(f"        {a['filename']:50s} {size_mb:6.2f} MB  sha256:{a['sha256'][:16]}…")
    return manifest


def cmd_release(args):
    manifest = cmd_build(args)
    print()
    print(f"[release] Publishing to API targets…")
    api_results = publish_all(manifest, include_apis=True,
                                include_manual=False)
    for r in api_results:
        icon = "✓" if r["ok"] else "✗"
        print(f"  {icon} {r.get('target_label', r['target']):24s} — {r.get('msg', '')[:80]}")
        if r.get("url"):
            print(f"      → {r['url']}")

    if args.manual:
        print()
        print(f"[release] Opening manual submission sites in browser…")
        from .manual_submitter import submit_all_manual
        manual_results = submit_all_manual(manifest, region=args.region)
        for r in manual_results:
            icon = "✓" if r["ok"] else "✗"
            print(f"  {icon} {r['target']}")

    dash = open_dashboard_url(manifest["version"])
    print()
    print(f"[release] Status dashboard: {dash}")
    if args.open_dashboard:
        webbrowser.open(f"file:///{dash}")


def cmd_status(args):
    version = args.version or get_version()
    state = get_status(version)
    print(f"Status for v{version}:")
    submitted = state.get("submitted", {})
    for target in SUBMISSION_TARGETS:
        sub = submitted.get(target["id"], {})
        if sub:
            icon = "✓" if sub.get("ok") else "✗"
            print(f"  {icon} {target['label']:30s} — {sub.get('msg', '')[:60]}")
        else:
            print(f"  · {target['label']:30s} — not yet submitted")


def cmd_targets(args):
    counts = count_by_type()
    print(f"Submission targets ({counts.get('api', 0)} API + "
          f"{counts.get('manual', 0)} manual = {len(SUBMISSION_TARGETS)} total):")
    print()
    for t in SUBMISSION_TARGETS:
        if args.region and t["region"] != args.region:
            continue
        if args.auto_only and not t.get("auto"):
            continue
        flag = "[API ]" if t["type"] == "api" else "[MAN ]"
        region = f"({t['region']})"
        print(f"  {flag} {region:10s} {t['id']:24s} — {t['label']}")
        if t.get("notes"):
            print(f"                                 {t['notes']}")


def cmd_open_dashboard(args):
    version = args.version or get_version()
    dash = open_dashboard_url(version)
    print(f"Dashboard: {dash}")
    webbrowser.open(f"file:///{dash}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="publisher")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Build release artifacts")
    p_build.add_argument("--version", help="Override version")
    p_build.add_argument("--skip-build", action="store_true",
                          help="Reuse existing exe in dist/")
    p_build.set_defaults(func=cmd_build)

    p_rel = sub.add_parser("release", help="Build + publish to all targets")
    p_rel.add_argument("--version", help="Override version")
    p_rel.add_argument("--skip-build", action="store_true")
    p_rel.add_argument("--manual", action="store_true",
                        help="Also open manual submission sites in browser")
    p_rel.add_argument("--region", choices=["global", "poland"])
    p_rel.add_argument("--open-dashboard", action="store_true")
    p_rel.set_defaults(func=cmd_release)

    p_st = sub.add_parser("status", help="Show submission status")
    p_st.add_argument("--version")
    p_st.set_defaults(func=cmd_status)

    p_tg = sub.add_parser("targets", help="List submission targets")
    p_tg.add_argument("--region", choices=["global", "poland"])
    p_tg.add_argument("--auto-only", action="store_true")
    p_tg.set_defaults(func=cmd_targets)

    p_db = sub.add_parser("dashboard", help="Open status dashboard")
    p_db.add_argument("--version")
    p_db.set_defaults(func=cmd_open_dashboard)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
