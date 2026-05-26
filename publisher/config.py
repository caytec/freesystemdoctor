"""Release configuration — read from version.json + git remote."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "version.json"


def _default_config() -> dict:
    return {
        "version":       "2.2.0",
        "name":          "FreeSystemDoctor",
        "display_name":  "FreeSystemDoctor",
        "publisher":     "Kajetan / caytec",
        "publisher_email": "coopaisolutions@gmail.com",
        "homepage":      "https://github.com/caytec/freesystemdoctor",
        "license":       "MIT",
        "license_url":   "https://github.com/caytec/freesystemdoctor/blob/main/LICENSE",
        "summary":       "Free Windows system optimizer and cleaner",
        "description":   (
            "FreeSystemDoctor is a comprehensive, 100% free Windows "
            "optimization and maintenance suite. Includes 50+ tools: disk "
            "cleaner, registry cleaner, game booster, AI-powered analysis, "
            "DNS protector, hardware monitor, smart defrag, file recovery, "
            "auto-shutdown, browser auto-clean and more. No telemetry, no "
            "ads, no premium tier — everything is free."
        ),
        "tags": [
            "system-optimizer", "pc-cleaner", "windows-tweaker",
            "registry-cleaner", "game-booster", "free-software",
            "open-source", "performance", "maintenance", "privacy",
        ],
        "category": "system-utilities",
        "platforms": ["Windows 10", "Windows 11"],
        "min_os":     "Windows 10 64-bit",
        "languages":  ["English", "Polish"],
        "icon":       "gui/icon.ico",
        "screenshots_dir": "publisher/assets/screenshots",
        "changelog_file":  "CHANGELOG.md",
        "github_owner":    "caytec",
        "github_repo":     "freesystemdoctor",
        "exe_name":        "FreeSystemDoctor.exe",
    }


def get_repo() -> tuple[str, str]:
    """Return (owner, repo) from git remote."""
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
            cwd=str(ROOT),
            creationflags=0x08000000,
        )
        url = (r.stdout or "").strip()
        # https://github.com/owner/repo.git or git@github.com:owner/repo.git
        if "github.com" in url:
            tail = url.split("github.com", 1)[1].lstrip(":/")
            tail = tail.removesuffix(".git")
            parts = tail.split("/")
            if len(parts) >= 2:
                return (parts[0], parts[1])
    except Exception:
        pass
    cfg = _default_config()
    return (cfg["github_owner"], cfg["github_repo"])


def load_config() -> dict:
    """Load release config, merging version.json overrides over defaults."""
    cfg = _default_config()
    if VERSION_FILE.exists():
        try:
            user = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
            cfg.update(user)
        except Exception:
            pass
    owner, repo = get_repo()
    cfg["github_owner"] = owner
    cfg["github_repo"] = repo
    return cfg


def get_version() -> str:
    return load_config()["version"]


def save_version(new_version: str):
    cfg = {}
    if VERSION_FILE.exists():
        try:
            cfg = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg["version"] = new_version
    VERSION_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


RELEASE_CONFIG = load_config()
