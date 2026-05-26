"""Cloud Drive Cleaner engine — Google Drive cleanup with OAuth2."""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google.oauth2.credentials import Credentials as UserCredentials
    from google.auth.oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False


SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_PATH = Path(os.environ.get("TEMP", ".")) / "FreeSystemDoctor" / "gdrive_token.json"
TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_service():
    """Get authenticated Google Drive service."""
    if not _GOOGLE_AVAILABLE:
        raise ImportError("Google Drive libraries not installed. Run: pip install google-auth-oauthlib google-api-python-client")

    creds = None
    if TOKEN_PATH.exists():
        creds = UserCredentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # For now, return None — user will need to authenticate manually
            return None

    return build("drive", "v3", credentials=creds)


def list_files(page_size: int = 100) -> list[dict]:
    """List files in Google Drive."""
    try:
        service = get_service()
        if not service:
            return []

        results = service.files().list(
            pageSize=page_size,
            fields="files(id, name, size, mimeType, createdTime, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc"
        ).execute()

        files = results.get("files", [])
        return [
            {
                "id": f["id"],
                "name": f["name"],
                "size": int(f.get("size", 0)),
                "size_str": _fmt_bytes(int(f.get("size", 0))),
                "mime_type": f.get("mimeType", ""),
                "created": f.get("createdTime", ""),
                "modified": f.get("modifiedTime", ""),
                "link": f.get("webViewLink", ""),
            }
            for f in files
        ]
    except HttpError as e:
        raise Exception(f"Google Drive API error: {e}")


def find_duplicates(files: list[dict]) -> list[tuple[list[dict], int]]:
    """Find duplicate files by name + size."""
    duplicates = []
    seen = {}

    for f in files:
        key = (f["name"], f["size"])
        if key in seen:
            seen[key].append(f)
        else:
            seen[key] = [f]

    for key, file_list in seen.items():
        if len(file_list) > 1:
            total_size = sum(f["size"] for f in file_list)
            duplicates.append((file_list, total_size))

    return sorted(duplicates, key=lambda x: x[1], reverse=True)


def find_old_files(files: list[dict], days: int = 90) -> list[dict]:
    """Find files not modified in N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return [f for f in files if f.get("modified", "") < cutoff]


def find_large_files(files: list[dict], min_size_mb: int = 100) -> list[dict]:
    """Find files larger than N MB."""
    min_bytes = min_size_mb * 1024 * 1024
    return sorted([f for f in files if f["size"] >= min_bytes],
                  key=lambda x: x["size"], reverse=True)


def delete_file(file_id: str) -> bool:
    """Delete a file from Google Drive."""
    try:
        service = get_service()
        if not service:
            return False
        service.files().delete(fileId=file_id).execute()
        return True
    except HttpError as e:
        raise Exception(f"Failed to delete file: {e}")


def get_drive_usage() -> dict:
    """Get total drive usage statistics."""
    try:
        service = get_service()
        if not service:
            return {}

        about = service.about().get(fields="storageQuota").execute()
        quota = about.get("storageQuota", {})

        total = int(quota.get("limit", 0))
        used = int(quota.get("usage", 0))
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
    except Exception:
        return {}


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"
