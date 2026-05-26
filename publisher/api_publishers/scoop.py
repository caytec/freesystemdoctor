"""Scoop bucket manifest generator + git push."""

import json
import shutil
import subprocess
from pathlib import Path


def generate_manifest(manifest: dict) -> dict:
    version = manifest["version"]
    exe_asset = next((a for a in manifest["artifacts"]
                       if a["type"] == "portable-exe"), None)
    if not exe_asset:
        raise ValueError("No exe artifact")
    download_url = (f"https://github.com/{manifest['github_owner']}/"
                    f"{manifest['github_repo']}/releases/download/"
                    f"v{version}/{exe_asset['filename']}")

    return {
        "version": version,
        "description": manifest["summary"],
        "homepage": manifest["homepage"],
        "license": manifest["license"],
        "url": download_url,
        "hash": exe_asset["sha256"].lower(),
        "bin": exe_asset["filename"],
        "shortcuts": [
            [exe_asset["filename"], manifest["display_name"]]
        ],
        "checkver": "github",
        "autoupdate": {
            "url": (f"https://github.com/{manifest['github_owner']}/"
                    f"{manifest['github_repo']}/releases/download/"
                    f"v$version/FreeSystemDoctor-$version.exe"),
        },
    }


def publish(manifest: dict) -> dict:
    result = {"target": "scoop", "ok": False, "url": "", "msg": ""}

    from ..config import ROOT
    out_dir = Path(ROOT) / "releases" / f"v{manifest['version']}" / "scoop"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        scoop_manifest = generate_manifest(manifest)
    except Exception as e:
        result["msg"] = f"Manifest generation failed: {e}"
        return result

    pkg_id = manifest["name"].lower()
    out_file = out_dir / f"{pkg_id}.json"
    out_file.write_text(json.dumps(scoop_manifest, indent=2), encoding="utf-8")

    # Try to push to a scoop-bucket repo if it exists
    bucket_repo = f"{manifest['github_owner']}/scoop-bucket"
    if shutil.which("gh"):
        check = subprocess.run(["gh", "repo", "view", bucket_repo],
                                capture_output=True, text=True,
                                creationflags=0x08000000)
        if check.returncode == 0:
            # Clone, copy, commit, push
            tmp = Path(ROOT) / "releases" / f"v{manifest['version']}" / "_scoop_clone"
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)
            clone = subprocess.run(
                ["gh", "repo", "clone", bucket_repo, str(tmp)],
                capture_output=True, text=True,
                creationflags=0x08000000)
            if clone.returncode == 0:
                bucket_dir = tmp / "bucket"
                bucket_dir.mkdir(exist_ok=True)
                shutil.copy2(out_file, bucket_dir / out_file.name)
                for cmd in [
                    ["git", "add", "."],
                    ["git", "commit", "-m",
                     f"Update {pkg_id} to {manifest['version']}"],
                    ["git", "push"],
                ]:
                    subprocess.run(cmd, cwd=str(tmp),
                                    capture_output=True, text=True,
                                    creationflags=0x08000000)
                shutil.rmtree(tmp, ignore_errors=True)
                result["ok"] = True
                result["url"] = f"https://github.com/{bucket_repo}/blob/main/bucket/{pkg_id}.json"
                result["msg"] = (
                    f"Pushed to scoop bucket. Users install with:\n"
                    f"  scoop bucket add {manifest['github_owner']} "
                    f"https://github.com/{bucket_repo}\n"
                    f"  scoop install {pkg_id}")
                return result

    # Fallback: manifest file generated locally
    result["ok"] = True
    result["url"] = str(out_file)
    result["msg"] = (
        f"Generated Scoop manifest at {out_file}. "
        f"To distribute: create a github.com/{manifest['github_owner']}/"
        f"scoop-bucket repo with bucket/{pkg_id}.json")
    return result
