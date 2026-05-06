"""
empty_folder_finder.py — Find and remove truly empty directory trees.
Part of FreeSystemDoctor engine.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "empty_folder_finder.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Protected path patterns (case-insensitive substring checks)
# ---------------------------------------------------------------------------
_PROTECTED_SUBSTRINGS: tuple[str, ...] = (
    "\\windows\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\programdata\\",
    "\\appdata\\roaming\\microsoft\\",
    "\\appdata\\local\\microsoft\\",
    "\\appdata\\locallow\\",
    "\\system32\\",
    "\\syswow64\\",
    "\\boot\\",
    "\\recovery\\",
    "\\$recycle.bin\\",
    "\\system volume information\\",
)

# Root directories we must never touch (after normalisation to lower-case)
_PROTECTED_ROOTS: tuple[str, ...] = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\$recycle.bin",
    "c:\\system volume information",
    "c:\\recovery",
    "c:\\boot",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_safe_to_delete(path: str) -> bool:
    """
    Return True if the path is NOT in a protected system location.

    Args:
        path: Absolute directory path.

    Returns:
        True if deletion is considered safe.
    """
    try:
        norm = os.path.normcase(os.path.abspath(path))
        norm_slash = norm + "\\"

        # Exact match against known protected roots
        for root in _PROTECTED_ROOTS:
            root_check = os.path.normcase(root)
            if norm == root_check or norm_slash.startswith(root_check + "\\"):
                return False

        # Substring match
        for substr in _PROTECTED_SUBSTRINGS:
            if substr in norm + "\\":
                return False

        # Never delete drive roots
        if len(norm.rstrip("\\")) <= 3:  # e.g. "c:\"
            return False

        return True
    except Exception as exc:
        logger.debug("is_safe_to_delete(%s) error: %s", path, exc)
        return False


def _is_truly_empty(path: str) -> bool:
    """
    Return True if the directory tree at *path* contains zero files
    (subdirectories without any files are treated as empty).
    """
    try:
        for _root, _dirs, files in os.walk(path):
            if files:
                return False
        return True
    except Exception:
        return False


def _get_size_on_disk(path: str) -> int:
    """Return total size in bytes of a directory tree (files only). 0 on error."""
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            for fname in files:
                try:
                    total += os.path.getsize(os.path.join(root, fname))
                except Exception:
                    pass
    except Exception:
        pass
    return total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_empty_folders(
    root: Optional[str] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> list[dict]:
    """
    Recursively scan for truly empty folders (no files in the entire subtree).

    Args:
        root: Directory to start scanning. Defaults to the user's home directory.
        progress_cb: Optional callable receiving the current path being scanned.

    Returns:
        List of {path, size_on_disk, is_safe}
    """
    results: list[dict] = []

    if root is None:
        root = os.path.expanduser("~")

    root = os.path.abspath(root)

    if not os.path.isdir(root):
        logger.warning("scan_empty_folders: root does not exist: %s", root)
        return results

    logger.info("scan_empty_folders: starting at %s", root)

    try:
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=None):
            # Skip the root itself
            if os.path.normcase(dirpath) == os.path.normcase(root):
                # Filter out protected subdirectories from traversal
                dirnames[:] = [
                    d for d in dirnames
                    if is_safe_to_delete(os.path.join(dirpath, d))
                    or not _is_protected_root_subdir(os.path.join(dirpath, d))
                ]
                continue

            if progress_cb:
                try:
                    progress_cb(dirpath)
                except Exception:
                    pass

            # Check if this directory (and its whole subtree) is empty
            if not filenames and _is_truly_empty(dirpath):
                safe = is_safe_to_delete(dirpath)
                size = _get_size_on_disk(dirpath)
                results.append({
                    "path": dirpath,
                    "size_on_disk": size,
                    "is_safe": safe,
                })
                logger.debug("Empty folder found: %s (safe=%s)", dirpath, safe)
                # Don't descend into it (it's empty anyway)
                dirnames.clear()

    except Exception as exc:
        logger.exception("scan_empty_folders error: %s", exc)

    logger.info("scan_empty_folders: found %d empty folders", len(results))
    return results


def _is_protected_root_subdir(path: str) -> bool:
    """Return True if the path starts with a known protected prefix."""
    norm = os.path.normcase(os.path.abspath(path)) + "\\"
    for root in _PROTECTED_ROOTS:
        if norm.startswith(os.path.normcase(root) + "\\"):
            return True
    return False


def delete_folders(
    paths: list[str],
    progress_cb: Optional[Callable[[str], None]] = None,
) -> tuple[int, int]:
    """
    Delete a list of folder paths.

    Only deletes paths that pass `is_safe_to_delete`.

    Args:
        paths: List of absolute folder paths to delete.
        progress_cb: Optional callable receiving each path as it is processed.

    Returns:
        (deleted_count, error_count) tuple.
    """
    deleted = 0
    errors = 0

    for path in paths:
        if progress_cb:
            try:
                progress_cb(path)
            except Exception:
                pass

        try:
            if not os.path.exists(path):
                logger.debug("delete_folders: already gone: %s", path)
                continue

            if not is_safe_to_delete(path):
                logger.warning("delete_folders: skipping protected path: %s", path)
                errors += 1
                continue

            if not _is_truly_empty(path):
                logger.warning("delete_folders: skipping non-empty path: %s", path)
                errors += 1
                continue

            shutil.rmtree(path, ignore_errors=False)
            deleted += 1
            logger.info("delete_folders: deleted %s", path)

        except PermissionError as exc:
            logger.warning("delete_folders: permission denied for %s: %s", path, exc)
            errors += 1
        except FileNotFoundError:
            # Already gone — count as success
            deleted += 1
        except Exception as exc:
            logger.warning("delete_folders: error deleting %s: %s", path, exc)
            errors += 1

    logger.info("delete_folders: deleted=%d errors=%d", deleted, errors)
    return deleted, errors
