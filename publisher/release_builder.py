"""Release artifact builder — produces zip + checksums + manifest.

Pipeline:
  1. (Optional) PyInstaller build to dist/FreeSystemDoctor.exe
  2. Pack EXE + LICENSE + README into FreeSystemDoctor-X.Y.Z-portable.zip
  3. SHA256 hash every artifact
  4. Write release-manifest.json describing the release
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .config import RELEASE_CONFIG, get_version

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
RELEASES = ROOT / "releases"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_pyinstaller(force: bool = False) -> Path:
    """Run PyInstaller. Returns path to built exe.

    Skipped if dist/FreeSystemDoctor.exe is newer than main.py and force=False.
    """
    spec = ROOT / "FreeSystemDoctor.spec"
    exe = DIST / RELEASE_CONFIG["exe_name"]

    if not force and exe.exists():
        try:
            main_mtime = (ROOT / "main.py").stat().st_mtime
            if exe.stat().st_mtime > main_mtime:
                return exe
        except OSError:
            pass

    cmd = ["python", "-m", "PyInstaller", str(spec),
           "--clean", "--noconfirm"]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                        creationflags=0x08000000)
    if r.returncode != 0:
        raise RuntimeError(f"PyInstaller failed: {r.stderr[-500:]}")
    if not exe.exists():
        # Find any matching exe
        candidates = list(DIST.glob("FreeSystemDoctor*.exe"))
        if not candidates:
            raise RuntimeError(f"No FreeSystemDoctor exe found in {DIST}")
        exe = candidates[-1]
    return exe


def build_release_artifacts(version: str = None,
                              skip_build: bool = False) -> dict:
    """Create release artifacts and manifest. Returns the manifest dict."""
    version = version or get_version()
    RELEASES.mkdir(exist_ok=True)
    out_dir = RELEASES / f"v{version}"
    out_dir.mkdir(exist_ok=True)

    artifacts: list[dict] = []

    # 1. Build the exe (or reuse existing)
    if skip_build:
        exe_candidates = sorted(DIST.glob("FreeSystemDoctor*.exe"),
                                  key=lambda p: p.stat().st_mtime,
                                  reverse=True)
        if not exe_candidates:
            raise RuntimeError("No prebuilt exe found in dist/")
        exe_path = exe_candidates[0]
    else:
        exe_path = build_pyinstaller()

    # 2. Copy raw exe
    target_exe = out_dir / f"FreeSystemDoctor-{version}.exe"
    shutil.copy2(exe_path, target_exe)
    artifacts.append({
        "filename": target_exe.name,
        "path":     str(target_exe),
        "size":     target_exe.stat().st_size,
        "sha256":   _sha256(target_exe),
        "type":     "portable-exe",
    })

    # 3. Pack portable zip
    zip_path = out_dir / f"FreeSystemDoctor-{version}-portable.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(target_exe, arcname="FreeSystemDoctor.exe")
        for extra in ("LICENSE", "README.md", "CHANGELOG.md"):
            extra_path = ROOT / extra
            if extra_path.exists():
                zf.write(extra_path, arcname=extra)
    artifacts.append({
        "filename": zip_path.name,
        "path":     str(zip_path),
        "size":     zip_path.stat().st_size,
        "sha256":   _sha256(zip_path),
        "type":     "portable-zip",
    })

    # 4. Write SHA256SUMS file
    sums_path = out_dir / "SHA256SUMS.txt"
    with open(sums_path, "w", encoding="utf-8") as f:
        for a in artifacts:
            f.write(f"{a['sha256']}  {a['filename']}\n")

    # 5. Manifest
    manifest = {
        "name":         RELEASE_CONFIG["name"],
        "display_name": RELEASE_CONFIG["display_name"],
        "version":      version,
        "release_date": datetime.now(timezone.utc).isoformat(),
        "publisher":    RELEASE_CONFIG["publisher"],
        "homepage":     RELEASE_CONFIG["homepage"],
        "license":      RELEASE_CONFIG["license"],
        "summary":      RELEASE_CONFIG["summary"],
        "description":  RELEASE_CONFIG["description"],
        "tags":         RELEASE_CONFIG["tags"],
        "artifacts":    artifacts,
        "github_owner": RELEASE_CONFIG["github_owner"],
        "github_repo":  RELEASE_CONFIG["github_repo"],
    }
    manifest_path = out_dir / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    manifest["release_dir"] = str(out_dir)

    return manifest


def get_changelog_entry(version: str) -> str:
    """Read changelog entry for the given version, or generate a default."""
    cl = ROOT / RELEASE_CONFIG["changelog_file"]
    if not cl.exists():
        return f"FreeSystemDoctor {version} — see commits for full changelog."
    text = cl.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Find heading like "## [2.2.0]" or "## 2.2.0"
    target = f"## [{version}]"
    target2 = f"## {version}"
    start = -1
    for i, line in enumerate(lines):
        ls = line.strip()
        if ls.startswith(target) or ls.startswith(target2):
            start = i + 1
            break
    if start < 0:
        return f"FreeSystemDoctor {version}"

    # Capture until next ## heading
    out = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        out.append(line)
    return "\n".join(out).strip() or f"FreeSystemDoctor {version}"
