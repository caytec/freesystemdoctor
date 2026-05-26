"""Chocolatey package generator + publisher.

Builds .nuspec + tools/chocolateyinstall.ps1, runs `choco pack` and
`choco push` if CHOCO_API_KEY env is set.
"""

import os
import shutil
import subprocess
from pathlib import Path


def _choco_available() -> bool:
    return shutil.which("choco") is not None


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def generate_package(manifest: dict, out_dir: Path) -> Path:
    version = manifest["version"]
    pkg_id = _slugify(manifest["name"])
    publisher = manifest["publisher"].split(" / ")[0]

    # Find exe asset for download URL
    exe_asset = next((a for a in manifest["artifacts"]
                       if a["type"] == "portable-exe"), None)
    if not exe_asset:
        raise ValueError("No exe artifact")

    download_url = (f"https://github.com/{manifest['github_owner']}/"
                    f"{manifest['github_repo']}/releases/download/"
                    f"v{version}/{exe_asset['filename']}")
    sha256 = exe_asset["sha256"]
    desc = manifest["description"]
    homepage = manifest["homepage"]
    license_url = f"{homepage}/blob/main/LICENSE"
    tags_str = " ".join(manifest.get("tags", []))

    nuspec = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd">
  <metadata>
    <id>{pkg_id}</id>
    <version>{version}</version>
    <packageSourceUrl>{homepage}</packageSourceUrl>
    <owners>{publisher}</owners>
    <title>{manifest['display_name']}</title>
    <authors>{publisher}</authors>
    <projectUrl>{homepage}</projectUrl>
    <iconUrl>{homepage}/raw/main/gui/icon.ico</iconUrl>
    <licenseUrl>{license_url}</licenseUrl>
    <requireLicenseAcceptance>false</requireLicenseAcceptance>
    <projectSourceUrl>{homepage}</projectSourceUrl>
    <bugTrackerUrl>{homepage}/issues</bugTrackerUrl>
    <tags>{tags_str}</tags>
    <summary>{manifest['summary']}</summary>
    <description>{desc}</description>
    <releaseNotes>{homepage}/releases/tag/v{version}</releaseNotes>
  </metadata>
  <files>
    <file src="tools\\**" target="tools" />
  </files>
</package>
"""

    install_ps1 = f"""$ErrorActionPreference = 'Stop';
$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$packageArgs = @{{
  packageName    = '{pkg_id}'
  unzipLocation  = $toolsDir
  fileType       = 'exe'
  url64bit       = '{download_url}'
  softwareName   = '{manifest['display_name']}*'
  checksum64     = '{sha256}'
  checksumType64 = 'sha256'
  silentArgs     = ''
  validExitCodes = @(0)
}}
Get-ChocolateyWebFile @packageArgs
Install-ChocolateyShortcut -ShortcutFilePath "$([System.Environment]::GetFolderPath('CommonDesktopDirectory'))\\{manifest['display_name']}.lnk" -TargetPath "$toolsDir\\{exe_asset['filename']}"
"""

    uninstall_ps1 = f"""$ErrorActionPreference = 'Stop';
$shortcut = "$([System.Environment]::GetFolderPath('CommonDesktopDirectory'))\\{manifest['display_name']}.lnk"
if (Test-Path $shortcut) {{ Remove-Item $shortcut -Force }}
"""

    pkg_dir = out_dir / pkg_id
    (pkg_dir / "tools").mkdir(parents=True, exist_ok=True)
    (pkg_dir / f"{pkg_id}.nuspec").write_text(nuspec, encoding="utf-8")
    (pkg_dir / "tools" / "chocolateyinstall.ps1").write_text(install_ps1, encoding="utf-8")
    (pkg_dir / "tools" / "chocolateyuninstall.ps1").write_text(uninstall_ps1, encoding="utf-8")
    return pkg_dir


def publish(manifest: dict) -> dict:
    result = {"target": "chocolatey", "ok": False, "url": "", "msg": ""}

    from ..config import ROOT
    out_dir = Path(ROOT) / "releases" / f"v{manifest['version']}" / "chocolatey"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        pkg_dir = generate_package(manifest, out_dir)
    except Exception as e:
        result["msg"] = f"Package generation failed: {e}"
        return result

    if not _choco_available():
        result["ok"] = True
        result["url"] = str(pkg_dir)
        result["msg"] = (f"Package files generated at {pkg_dir}. "
                          f"Install Chocolatey to auto-pack and push.")
        return result

    # Pack
    pack = subprocess.run(["choco", "pack"], cwd=str(pkg_dir),
                           capture_output=True, text=True,
                           creationflags=0x08000000)
    if pack.returncode != 0:
        result["msg"] = f"choco pack failed: {(pack.stderr or pack.stdout)[-200:]}"
        return result

    nupkg = next(pkg_dir.glob("*.nupkg"), None)
    if not nupkg:
        result["msg"] = "No .nupkg produced"
        return result

    api_key = os.environ.get("CHOCO_API_KEY")
    if not api_key:
        result["ok"] = True
        result["url"] = str(nupkg)
        result["msg"] = (f"Built {nupkg.name}. Set CHOCO_API_KEY to auto-push, "
                          f"or run: choco push {nupkg.name} --api-key=YOUR_KEY")
        return result

    push = subprocess.run(["choco", "push", str(nupkg),
                            "--source", "https://push.chocolatey.org/",
                            "--api-key", api_key],
                            capture_output=True, text=True,
                            creationflags=0x08000000)
    if push.returncode == 0:
        result["ok"] = True
        result["url"] = f"https://community.chocolatey.org/packages/{nupkg.stem.split('.')[0]}"
        result["msg"] = "Pushed to Chocolatey community feed (awaiting moderation)"
    else:
        result["msg"] = f"choco push failed: {(push.stderr or push.stdout)[-200:]}"
    return result
