"""Browser-assisted submission to manual sites.

For sites without a public API, opens the submission URL in the user's
default browser AND copies the submission text to the clipboard so the
user can paste-and-go.
"""

import urllib.parse
from pathlib import Path


def _format_url(template: str, manifest: dict) -> str:
    """Substitute placeholders, URL-encoding values."""
    download_url = ""
    for a in manifest["artifacts"]:
        if a["type"] == "portable-exe":
            download_url = (
                f"https://github.com/{manifest['github_owner']}/"
                f"{manifest['github_repo']}/releases/download/"
                f"v{manifest['version']}/{a['filename']}")
            break

    placeholders = {
        "name":         manifest["name"],
        "version":      manifest["version"],
        "homepage":     manifest["homepage"],
        "summary":      manifest["summary"],
        "tags":         ", ".join(manifest.get("tags", [])),
        "download_url": download_url,
        "email":        "coopaisolutions@gmail.com",
        "owner":        manifest["github_owner"],
        "repo":         manifest["github_repo"],
    }

    # URL-encode each placeholder value
    encoded = {k: urllib.parse.quote(str(v), safe="") for k, v in placeholders.items()}

    out = template
    for k, v in encoded.items():
        out = out.replace("{" + k + "}", v)
    return out


def build_submission_text(manifest: dict, locale: str = "en") -> str:
    """Build a paste-ready description block."""
    if locale == "pl":
        body = f"""Nazwa programu: {manifest['display_name']}
Wersja: {manifest['version']}
Wydawca: {manifest['publisher']}
Strona główna: {manifest['homepage']}
Licencja: {manifest['license']} (open source, darmowe)
Platforma: Windows 10/11 (x64)
Język: angielski, polski

Krótki opis:
{manifest['summary']}

Pełny opis:
{manifest['description']}

Tagi: {', '.join(manifest.get('tags', []))}

Link do pobrania: """ + (next((
    f"https://github.com/{manifest['github_owner']}/"
    f"{manifest['github_repo']}/releases/download/"
    f"v{manifest['version']}/{a['filename']}"
    for a in manifest['artifacts'] if a['type'] == 'portable-exe'), ""))
    else:
        body = f"""Software name: {manifest['display_name']}
Version: {manifest['version']}
Publisher: {manifest['publisher']}
Homepage: {manifest['homepage']}
License: {manifest['license']} (open source, free)
Platform: Windows 10/11 (x64)
Languages: English, Polish

Short description:
{manifest['summary']}

Full description:
{manifest['description']}

Tags: {', '.join(manifest.get('tags', []))}

Download URL: """ + (next((
    f"https://github.com/{manifest['github_owner']}/"
    f"{manifest['github_repo']}/releases/download/"
    f"v{manifest['version']}/{a['filename']}"
    for a in manifest['artifacts'] if a['type'] == 'portable-exe'), ""))

    return body


def copy_to_clipboard(text: str) -> bool:
    """Copy text to Windows clipboard via PowerShell (no extra deps)."""
    try:
        import subprocess
        # Use Set-Clipboard for reliability
        ps = f'$t = @"\n{text}\n"@; Set-Clipboard -Value $t'
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,
        )
        return r.returncode == 0
    except Exception:
        return False


def submit(target: dict, manifest: dict, locale: str = "en") -> dict:
    """Prepare submission by formatting URL and building submission text."""
    result = {"target": target["id"], "ok": False, "url": "", "msg": ""}

    try:
        url = _format_url(target["submit_url"], manifest)
        result["url"] = url
    except Exception as e:
        result["msg"] = f"URL formatting failed: {e}"
        return result

    # Build text
    text = build_submission_text(manifest, locale=locale)
    result["submission_text"] = text

    result["ok"] = True
    result["msg"] = f"Ready: {target['label']}"
    return result


def submit_all_manual(manifest: dict, region: str = None,
                       open_browser: bool = True,
                       delay_sec: float = 1.5) -> list[dict]:
    """Open submission forms for every manual target. Stagger by delay_sec."""
    import time
    from .directory import list_targets

    results = []
    targets = [t for t in list_targets(region=region) if t["type"] == "manual"]

    # Copy text once at the start
    text = build_submission_text(manifest,
                                   locale="pl" if region == "poland" else "en")
    copy_to_clipboard(text)

    for t in targets:
        r = submit(t, manifest, locale="pl" if t["region"] == "poland" else "en")
        results.append(r)
        if open_browser:
            time.sleep(delay_sec)

    return results


class ManualSubmissionQueue:
    """Queue-based manager for manual site submissions."""

    def __init__(self, manifest: dict, region: str = None):
        from .directory import list_targets

        self.manifest = manifest
        self.region = region
        self.targets = [t for t in list_targets(region=region) if t["type"] == "manual"]
        self.current_index = 0
        self.results = {}
        self.submitted_count = 0
        self.skipped_count = 0

        # Pre-determine locale based on first target region or provided region
        if region == "poland":
            self.locale = "pl"
        else:
            self.locale = "en"

        # Build and cache submission text
        self.submission_text = build_submission_text(manifest, locale=self.locale)
        copy_to_clipboard(self.submission_text)

    def get_current_target(self) -> dict:
        """Return current target in queue."""
        if self.current_index < len(self.targets):
            return self.targets[self.current_index]
        return None

    def get_current_url(self) -> str:
        """Return formatted submission URL for current target."""
        target = self.get_current_target()
        if target:
            return _format_url(target["submit_url"], self.manifest)
        return ""

    def get_current_label(self) -> str:
        """Return label of current target."""
        target = self.get_current_target()
        return target["label"] if target else ""

    def advance(self) -> bool:
        """Mark current as submitted and move to next. Returns True if more targets."""
        if self.current_index < len(self.targets):
            target_id = self.targets[self.current_index]["id"]
            self.results[target_id] = "submitted"
            self.submitted_count += 1
        self.current_index += 1
        return self.current_index < len(self.targets)

    def skip(self) -> bool:
        """Mark current as skipped and move to next. Returns True if more targets."""
        if self.current_index < len(self.targets):
            target_id = self.targets[self.current_index]["id"]
            self.results[target_id] = "skipped"
            self.skipped_count += 1
        self.current_index += 1
        return self.current_index < len(self.targets)

    def get_progress(self) -> tuple[int, int]:
        """Return (current_index, total_count)."""
        return (self.current_index + 1, len(self.targets))

    def is_done(self) -> bool:
        """Check if queue is exhausted."""
        return self.current_index >= len(self.targets)
