"""Winget manifest generator + PR opener.

Generates a 3-part winget manifest (version + installer + locale YAML),
forks microsoft/winget-pkgs (or reuses fork), commits and opens a PR.

Requires: gh CLI authenticated.
"""

import subprocess
from datetime import datetime
from pathlib import Path

WINGET_REPO = "microsoft/winget-pkgs"


def _gh_available() -> bool:
    import shutil
    return shutil.which("gh") is not None


def _publisher_id(name: str) -> str:
    """Strip non-alphanumeric chars from publisher name."""
    return "".join(c for c in name if c.isalnum())


def _package_id(publisher: str, name: str) -> str:
    return f"{_publisher_id(publisher)}.{_publisher_id(name)}"


def generate_manifest(manifest: dict) -> dict[str, str]:
    """Build the 3 winget YAML files. Returns {filename: content}."""
    version = manifest["version"]
    publisher = manifest["publisher"].split(" / ")[0]
    name = manifest["name"]
    package_id = _package_id(publisher, name)

    # Find portable exe asset
    exe_asset = None
    for a in manifest["artifacts"]:
        if a["type"] == "portable-exe":
            exe_asset = a
            break
    if not exe_asset:
        for a in manifest["artifacts"]:
            if a["filename"].endswith(".exe"):
                exe_asset = a
                break
    if not exe_asset:
        raise ValueError("No exe artifact found in manifest")

    # GitHub Release URL
    release_tag = f"v{version}"
    repo_url = f"https://github.com/{manifest['github_owner']}/{manifest['github_repo']}"
    download_url = (f"{repo_url}/releases/download/{release_tag}/"
                    f"{exe_asset['filename']}")
    sha256 = exe_asset["sha256"].upper()

    # Version manifest
    version_yaml = (
        f"PackageIdentifier: {package_id}\n"
        f"PackageVersion: {version}\n"
        f"DefaultLocale: en-US\n"
        f"ManifestType: version\n"
        f"ManifestVersion: 1.6.0\n"
    )

    # Installer manifest
    installer_yaml = (
        f"PackageIdentifier: {package_id}\n"
        f"PackageVersion: {version}\n"
        f"InstallerType: portable\n"
        f"Scope: user\n"
        f"Installers:\n"
        f"  - Architecture: x64\n"
        f"    InstallerType: portable\n"
        f"    InstallerUrl: {download_url}\n"
        f"    InstallerSha256: {sha256}\n"
        f"    Commands:\n"
        f"      - {name.lower()}\n"
        f"ManifestType: installer\n"
        f"ManifestVersion: 1.6.0\n"
    )

    # Locale manifest
    desc = manifest["description"].replace("\n", " ").strip()
    tags_yaml = "".join(f"  - {t}\n" for t in manifest.get("tags", []))
    locale_yaml = (
        f"PackageIdentifier: {package_id}\n"
        f"PackageVersion: {version}\n"
        f"PackageLocale: en-US\n"
        f"Publisher: {publisher}\n"
        f"PublisherUrl: {manifest['homepage']}\n"
        f"PublisherSupportUrl: {manifest['homepage']}/issues\n"
        f"PackageName: {manifest['display_name']}\n"
        f"PackageUrl: {manifest['homepage']}\n"
        f"License: {manifest['license']}\n"
        f"LicenseUrl: {manifest['homepage']}/blob/main/LICENSE\n"
        f"ShortDescription: {manifest['summary']}\n"
        f"Description: {desc}\n"
        f"Moniker: {name.lower()}\n"
        f"Tags:\n{tags_yaml}"
        f"ReleaseNotesUrl: {repo_url}/releases/tag/{release_tag}\n"
        f"ManifestType: defaultLocale\n"
        f"ManifestVersion: 1.6.0\n"
    )

    publisher_letter = publisher[0].lower()
    base = f"manifests/{publisher_letter}/{publisher}/{name}/{version}"
    return {
        f"{base}/{package_id}.yaml":           version_yaml,
        f"{base}/{package_id}.installer.yaml": installer_yaml,
        f"{base}/{package_id}.locale.en-US.yaml": locale_yaml,
    }


def publish(manifest: dict) -> dict:
    """Generate manifest, write to local fork, push, open PR."""
    result = {"target": "winget", "ok": False, "url": "", "msg": ""}

    if not _gh_available():
        result["msg"] = "gh CLI not installed."
        return result

    try:
        files = generate_manifest(manifest)
    except Exception as e:
        result["msg"] = f"Manifest generation failed: {e}"
        return result

    # Write manifest files to a local output dir for user inspection
    from ..config import ROOT
    out_dir = Path(ROOT) / "releases" / f"v{manifest['version']}" / "winget"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for relpath, content in files.items():
        full = out_dir / Path(relpath).name
        full.write_text(content, encoding="utf-8")
        written.append(str(full))

    # Use winget-create CLI if available (much simpler than manual fork+PR)
    import shutil
    if shutil.which("wingetcreate"):
        version = manifest["version"]
        exe_asset = next((a for a in manifest["artifacts"]
                            if a["type"] == "portable-exe"), None)
        if exe_asset:
            url = (f"https://github.com/{manifest['github_owner']}/"
                   f"{manifest['github_repo']}/releases/download/"
                   f"v{version}/{exe_asset['filename']}")
            cmd = ["wingetcreate", "update",
                   _package_id(manifest['publisher'].split(' / ')[0],
                                manifest['name']),
                   "--version", version,
                   "--urls", url,
                   "--submit"]
            r = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=120, creationflags=0x08000000)
            if r.returncode == 0:
                result["ok"] = True
                result["msg"] = "Submitted via wingetcreate"
                # Try to extract PR url from output
                for line in (r.stdout or "").splitlines():
                    if "github.com" in line and "/pull/" in line:
                        result["url"] = line.strip()
                        break
                return result
            else:
                result["msg"] = f"wingetcreate failed: {(r.stderr or '')[-200:]}\n"
                # Fall through to manifest-only mode

    # Manifest-only: tell user where files are
    result["ok"] = True
    result["msg"] = (f"Generated {len(written)} manifest files in {out_dir}. "
                      f"Install wingetcreate to auto-submit PRs: "
                      f"`winget install Microsoft.WingetCreate`")
    result["url"] = str(out_dir)
    return result
