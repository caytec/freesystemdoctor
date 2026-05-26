"""SourceForge File Release System publisher.

Uses scp + SF's File Release System (FRS).
Requires: SF_USER and SF_PROJECT env vars; SSH key configured for SF.
"""

import os
import shutil
import subprocess
from pathlib import Path


def publish(manifest: dict) -> dict:
    result = {"target": "sourceforge", "ok": False, "url": "", "msg": ""}

    sf_user    = os.environ.get("SF_USER")
    sf_project = os.environ.get("SF_PROJECT", manifest["name"].lower())

    if not sf_user:
        result["msg"] = ("Set SF_USER env var (your SourceForge username) and "
                          "SF_PROJECT (defaults to package name). "
                          "Requires SSH key registered at SourceForge.")
        return result

    if not shutil.which("scp"):
        result["msg"] = "scp not available — install OpenSSH or use Git Bash"
        return result

    version = manifest["version"]
    remote_path = f"{sf_user}@frs.sourceforge.net:/home/frs/project/{sf_project}/v{version}/"

    artifacts = [a["path"] for a in manifest["artifacts"]]

    # Create directory + upload via scp
    cmd = ["scp", "-B"] + artifacts + [remote_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                        creationflags=0x08000000)
    if r.returncode == 0:
        result["ok"] = True
        result["url"] = f"https://sourceforge.net/projects/{sf_project}/files/v{version}/"
        result["msg"] = f"Uploaded {len(artifacts)} files to SourceForge"
    else:
        result["msg"] = f"scp upload failed: {(r.stderr or '')[-200:]}"
    return result
