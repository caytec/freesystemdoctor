"""GitHub Releases publisher — uses gh CLI."""

import json
import shutil
import subprocess
from pathlib import Path

from ..release_builder import get_changelog_entry


def _gh_available() -> bool:
    return shutil.which("gh") is not None


def _gh_authed() -> bool:
    if not _gh_available():
        return False
    r = subprocess.run(["gh", "auth", "status"],
                        capture_output=True, text=True,
                        creationflags=0x08000000)
    return r.returncode == 0


def publish(manifest: dict) -> dict:
    """Create a GitHub release with all artifacts attached."""
    result = {"target": "github_releases", "ok": False, "url": "", "msg": ""}

    if not _gh_available():
        result["msg"] = "gh CLI not installed. Install from https://cli.github.com/"
        return result
    if not _gh_authed():
        result["msg"] = "gh not authenticated. Run: gh auth login"
        return result

    version = manifest["version"]
    tag = f"v{version}"
    title = f"{manifest['display_name']} {version}"
    notes = get_changelog_entry(version)
    artifact_paths = [a["path"] for a in manifest["artifacts"]]

    # Create / replace release
    repo = f"{manifest['github_owner']}/{manifest['github_repo']}"

    cmd = [
        "gh", "release", "create", tag,
        "--repo", repo,
        "--title", title,
        "--notes", notes,
    ] + artifact_paths

    r = subprocess.run(cmd, capture_output=True, text=True,
                        creationflags=0x08000000)

    if r.returncode == 0:
        result["ok"] = True
        result["url"] = (r.stdout or "").strip().splitlines()[-1] if r.stdout else \
                         f"https://github.com/{repo}/releases/tag/{tag}"
        result["msg"] = f"Released {tag}"
    elif "already exists" in (r.stderr or "").lower():
        # Release exists — upload assets to it
        upload = ["gh", "release", "upload", tag, "--clobber",
                   "--repo", repo] + artifact_paths
        u = subprocess.run(upload, capture_output=True, text=True,
                            creationflags=0x08000000)
        if u.returncode == 0:
            result["ok"] = True
            result["url"] = f"https://github.com/{repo}/releases/tag/{tag}"
            result["msg"] = f"Updated assets on existing release {tag}"
        else:
            result["msg"] = f"Asset upload failed: {(u.stderr or '')[-200:]}"
    else:
        result["msg"] = f"gh release create failed: {(r.stderr or '')[-300:]}"

    return result
