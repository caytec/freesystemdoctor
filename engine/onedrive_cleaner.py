"""OneDrive Cleaner engine — Microsoft Graph API integration for OneDrive cleanup."""

import json
import os
import subprocess
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request as UrlRequest
from urllib.error import URLError

try:
    import urllib.request
    _URLLIB_AVAILABLE = True
except ImportError:
    _URLLIB_AVAILABLE = False

_CONFIG_DIR = Path(os.environ.get("TEMP", "C:\\Temp")) / "FreeSystemDoctor"
_TOKEN_PATH = _CONFIG_DIR / "onedrive_token.json"

# Public client ID for Microsoft Graph (device code flow — no secret needed)
# Users must register their own app or use a demo client ID
_CLIENT_ID = os.environ.get("ONEDRIVE_CLIENT_ID", "")
_SCOPES = "Files.ReadWrite offline_access"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_AUTH_BASE = "https://login.microsoftonline.com/common/oauth2/v2.0"


def _load_token() -> dict:
    try:
        if _TOKEN_PATH.exists():
            with open(_TOKEN_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_token(token: dict) -> None:
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_TOKEN_PATH, "w") as f:
            json.dump(token, f)
    except Exception:
        pass


def _refresh_token(token: dict) -> dict:
    """Refresh an expired access token using the refresh token."""
    if not token.get("refresh_token") or not _CLIENT_ID:
        return {}

    data = urlencode({
        "client_id": _CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": token["refresh_token"],
        "scope": _SCOPES,
    }).encode()

    try:
        req = UrlRequest(f"{_AUTH_BASE}/token", data=data)
        with urlopen(req, timeout=15) as resp:
            new_token = json.loads(resp.read())
            new_token["expires_at"] = (
                datetime.now().timestamp() + new_token.get("expires_in", 3600)
            )
            _save_token(new_token)
            return new_token
    except Exception:
        return {}


def _is_token_valid(token: dict) -> bool:
    if not token.get("access_token"):
        return False
    expires_at = token.get("expires_at", 0)
    return datetime.now().timestamp() < expires_at - 60


def get_access_token() -> str:
    """Return valid access token or empty string."""
    token = _load_token()

    if _is_token_valid(token):
        return token["access_token"]

    if token.get("refresh_token"):
        new_token = _refresh_token(token)
        if new_token.get("access_token"):
            return new_token["access_token"]

    return ""


def start_device_auth() -> dict:
    """Start device code flow. Returns {user_code, verification_url, device_code, interval}."""
    if not _CLIENT_ID:
        return {"error": "ONEDRIVE_CLIENT_ID environment variable not set"}

    data = urlencode({
        "client_id": _CLIENT_ID,
        "scope": _SCOPES,
    }).encode()

    try:
        req = UrlRequest(f"{_AUTH_BASE}/devicecode", data=data)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def poll_device_auth(device_code: str, interval: int = 5) -> bool:
    """Poll for device auth completion. Returns True when token obtained."""
    if not _CLIENT_ID:
        return False

    data = urlencode({
        "client_id": _CLIENT_ID,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
    }).encode()

    try:
        req = UrlRequest(f"{_AUTH_BASE}/token", data=data)
        with urlopen(req, timeout=15) as resp:
            token = json.loads(resp.read())
            if token.get("access_token"):
                token["expires_at"] = (
                    datetime.now().timestamp() + token.get("expires_in", 3600)
                )
                _save_token(token)
                return True
    except URLError:
        pass
    except Exception:
        pass

    return False


def _graph_get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to Microsoft Graph API."""
    token = get_access_token()
    if not token:
        return {}

    url = f"{_GRAPH_BASE}{path}"
    if params:
        url += "?" + urlencode(params)

    try:
        req = UrlRequest(url, headers={"Authorization": f"Bearer {token}"})
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except Exception:
        return {}


def _graph_delete(path: str) -> bool:
    """Make a DELETE request to Microsoft Graph API."""
    token = get_access_token()
    if not token:
        return False

    url = f"{_GRAPH_BASE}{path}"
    try:
        req = UrlRequest(url, method="DELETE",
                        headers={"Authorization": f"Bearer {token}"})
        with urlopen(req, timeout=20) as resp:
            return resp.status in (200, 204)
    except Exception:
        return False


def is_connected() -> bool:
    """Return True if a valid access token is available."""
    return bool(get_access_token())


def list_files(top: int = 200) -> list[dict]:
    """List files in OneDrive root and subfolders."""
    if not is_connected():
        return []

    result = _graph_get("/me/drive/root/children",
                        {"$top": top, "$select": "id,name,size,createdDateTime,lastModifiedDateTime,file"})
    items = result.get("value", [])

    files = []
    for item in items:
        if "file" not in item:
            continue
        size = item.get("size", 0)
        modified = item.get("lastModifiedDateTime", "")
        files.append({
            "id": item["id"],
            "name": item["name"],
            "size": size,
            "size_str": _fmt_bytes(size),
            "modified": modified,
            "created": item.get("createdDateTime", ""),
        })

    return sorted(files, key=lambda x: x["modified"], reverse=True)


def find_duplicates(files: list[dict]) -> list[tuple[list[dict], int]]:
    """Find duplicate files by name + size."""
    seen: dict[tuple, list[dict]] = {}
    for f in files:
        key = (f["name"], f["size"])
        seen.setdefault(key, []).append(f)

    result = [(lst, sum(x["size"] for x in lst))
              for lst in seen.values() if len(lst) > 1]
    return sorted(result, key=lambda x: x[1], reverse=True)


def find_old_files(files: list[dict], days: int = 90) -> list[dict]:
    """Find files not modified in N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [f for f in files if f.get("modified", "") < cutoff]


def find_large_files(files: list[dict], min_size_mb: int = 100) -> list[dict]:
    """Find files larger than N MB."""
    min_bytes = min_size_mb * 1024 * 1024
    return sorted([f for f in files if f["size"] >= min_bytes],
                  key=lambda x: x["size"], reverse=True)


def delete_file(file_id: str) -> bool:
    """Move a file to OneDrive recycle bin."""
    return _graph_delete(f"/me/drive/items/{file_id}")


def get_drive_usage() -> dict:
    """Get OneDrive storage quota."""
    if not is_connected():
        return {}

    result = _graph_get("/me/drive", {"$select": "quota"})
    quota = result.get("quota", {})
    total = quota.get("total", 0)
    used = quota.get("used", 0)
    free = total - used

    return {
        "total": total,
        "total_str": _fmt_bytes(total),
        "used": used,
        "used_str": _fmt_bytes(used),
        "free": free,
        "free_str": _fmt_bytes(free),
        "percent_used": (used / total * 100) if total > 0 else 0,
    }


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
