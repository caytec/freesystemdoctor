"""
disk_optimizer.py — Disk defrag, TRIM, and health check utilities.
Part of FreeSystemDoctor engine.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "disk_optimizer.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 120, encoding: str = "utf-8", errors: str = "replace") -> tuple[int, str]:
    """Run a subprocess command, return (returncode, combined_output)."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding=encoding,
            errors=errors,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return result.returncode, result.stdout or ""
    except subprocess.TimeoutExpired:
        logger.warning("Command timed out: %s", cmd)
        return -1, "Timeout expired"
    except FileNotFoundError:
        logger.warning("Command not found: %s", cmd)
        return -1, f"Command not found: {cmd[0]}"
    except Exception as exc:
        logger.exception("Unexpected error running %s: %s", cmd, exc)
        return -1, str(exc)


def _run_powershell(script: str, timeout: int = 120) -> tuple[int, str]:
    """Run a PowerShell one-liner/script, return (returncode, output)."""
    return _run(
        ["powershell", "-NonInteractive", "-NoProfile", "-Command", script],
        timeout=timeout,
    )


def _detect_ssd_drives() -> set[str]:
    """Return a set of drive letters (upper-case, no colon) that are SSDs."""
    ssd_letters: set[str] = set()
    try:
        script = (
            "Get-PhysicalDisk | ForEach-Object { "
            "  $pd = $_; "
            "  $partitions = $pd | Get-Disk | Get-Partition; "
            "  foreach ($p in $partitions) { "
            "    Write-Output ($p.DriveLetter + ' ' + $pd.MediaType) "
            "  } "
            "}"
        )
        rc, out = _run_powershell(script, timeout=60)
        if rc == 0:
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1].lower() in ("ssd", "solid state"):
                    letter = parts[0].strip().upper().rstrip(":")
                    if letter and letter.isalpha():
                        ssd_letters.add(letter)
    except Exception as exc:
        logger.warning("SSD detection failed: %s", exc)
    return ssd_letters


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_drives() -> list[dict]:
    """
    Return a list of local disk drives with metadata and defrag recommendation.

    Each dict contains:
        letter, label, fs, total_gb, free_gb, free_pct, needs_defrag, is_ssd, recommendation
    """
    drives: list[dict] = []
    try:
        ssd_letters = _detect_ssd_drives()

        script = (
            "Get-PSDrive -PSProvider FileSystem | "
            "Where-Object { $_.Root -match '^[A-Z]:\\\\$' } | "
            "Select-Object Name, Root, Description, @{N='Total';E={$_.Used+$_.Free}}, Free | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        rc, out = _run_powershell(script, timeout=30)

        import csv, io
        if rc == 0 and out.strip():
            reader = csv.DictReader(io.StringIO(out))
            for row in reader:
                try:
                    letter = (row.get("Name") or "").strip().upper()
                    if not letter:
                        continue
                    total_bytes = int(row.get("Total") or 0)
                    free_bytes = int(row.get("Free") or 0)
                    total_gb = round(total_bytes / (1024 ** 3), 2) if total_bytes else 0.0
                    free_gb = round(free_bytes / (1024 ** 3), 2) if free_bytes else 0.0
                    free_pct = round((free_bytes / total_bytes * 100), 1) if total_bytes else 0.0
                    is_ssd = letter in ssd_letters

                    # Quick fragmentation check (analyse only, won't defrag)
                    needs_defrag = False
                    if not is_ssd:
                        needs_defrag = _check_needs_defrag(letter)

                    recommendation = "trim" if is_ssd else ("defrag" if needs_defrag else "ok")

                    drives.append({
                        "letter": letter,
                        "label": (row.get("Description") or "").strip(),
                        "fs": "",          # populated below
                        "total_gb": total_gb,
                        "free_gb": free_gb,
                        "free_pct": free_pct,
                        "needs_defrag": needs_defrag,
                        "is_ssd": is_ssd,
                        "recommendation": recommendation,
                    })
                except Exception as row_exc:
                    logger.debug("Skipping drive row due to error: %s", row_exc)

        # Enrich with filesystem type via WMI
        fs_script = (
            "Get-WmiObject Win32_LogicalDisk | "
            "Select-Object DeviceID, FileSystem | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        rc2, out2 = _run_powershell(fs_script, timeout=30)
        fs_map: dict[str, str] = {}
        if rc2 == 0 and out2.strip():
            reader2 = csv.DictReader(io.StringIO(out2))
            for row2 in reader2:
                dev = (row2.get("DeviceID") or "").strip().upper().rstrip(":")
                fs_map[dev] = (row2.get("FileSystem") or "").strip()
        for d in drives:
            d["fs"] = fs_map.get(d["letter"], "")

    except Exception as exc:
        logger.exception("get_drives failed: %s", exc)

    return drives


def _check_needs_defrag(letter: str) -> bool:
    """
    Run defrag analyse-only and return True if fragmentation is recommended.
    Returns False on any error (fail-safe).
    """
    try:
        rc, out = _run(
            ["defrag", f"{letter}:", "/A", "/U"],
            timeout=120,
        )
        lower = out.lower()
        # defrag outputs "you should defragment" when fragmentation is significant
        if "you should defragment" in lower or "fragmentation: " in lower:
            for line in out.splitlines():
                if "% fragmented" in line.lower():
                    try:
                        pct_str = line.split("%")[0].strip().split()[-1]
                        pct = float(pct_str)
                        return pct >= 5.0
                    except Exception:
                        pass
            return "you should defragment" in lower
        return False
    except Exception as exc:
        logger.debug("_check_needs_defrag error for %s: %s", letter, exc)
        return False


def defrag_drive(letter: str, progress_cb: Optional[Callable[[str], None]] = None) -> dict:
    """
    Defragment a drive (HDD only recommended).

    Args:
        letter: Single drive letter, e.g. "C"
        progress_cb: Optional callable receiving output lines as they arrive.

    Returns:
        {success: bool, output: str, duration_sec: float}
    """
    result = {"success": False, "output": "", "duration_sec": 0.0}
    try:
        letter = letter.strip().upper().rstrip(":")
        start = time.monotonic()
        output_lines: list[str] = []

        proc = subprocess.Popen(
            ["defrag", f"{letter}:", "/U", "/V"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )

        for line in proc.stdout:  # type: ignore[union-attr]
            stripped = line.rstrip("\n\r")
            output_lines.append(stripped)
            if progress_cb:
                try:
                    progress_cb(stripped)
                except Exception:
                    pass

        proc.wait(timeout=3600)
        duration = time.monotonic() - start
        full_output = "\n".join(output_lines)
        success = proc.returncode == 0

        result = {"success": success, "output": full_output, "duration_sec": round(duration, 2)}
        logger.info("defrag_drive %s: success=%s duration=%.1fs", letter, success, duration)
    except subprocess.TimeoutExpired:
        result["output"] = "Defrag timed out after 1 hour."
        logger.warning("defrag_drive timed out for drive %s", letter)
    except Exception as exc:
        result["output"] = str(exc)
        logger.exception("defrag_drive failed for %s: %s", letter, exc)
    return result


def trim_drive(letter: str) -> dict:
    """
    Run TRIM/Retrim optimisation on an SSD drive via PowerShell Optimize-Volume.

    Args:
        letter: Single drive letter, e.g. "C"

    Returns:
        {success: bool, output: str}
    """
    result = {"success": False, "output": ""}
    try:
        letter = letter.strip().upper().rstrip(":")
        script = f"Optimize-Volume -DriveLetter {letter} -ReTrim -Verbose"
        rc, out = _run_powershell(script, timeout=300)
        result["success"] = rc == 0
        result["output"] = out
        logger.info("trim_drive %s: rc=%d", letter, rc)
    except Exception as exc:
        result["output"] = str(exc)
        logger.exception("trim_drive failed for %s: %s", letter, exc)
    return result


def get_drive_health(letter: str) -> dict:
    """
    Check a drive for filesystem errors using chkdsk /scan (online, non-destructive).

    Args:
        letter: Single drive letter, e.g. "C"

    Returns:
        {errors_found: bool, status: str, output: str}
    """
    result = {"errors_found": False, "status": "unknown", "output": ""}
    try:
        letter = letter.strip().upper().rstrip(":")
        rc, out = _run(
            ["chkdsk", f"{letter}:", "/scan"],
            timeout=600,
        )
        result["output"] = out
        lower = out.lower()

        if "no problems" in lower or "windows has scanned the file system and found no problems" in lower:
            result["errors_found"] = False
            result["status"] = "healthy"
        elif "errors found" in lower or "corrupt" in lower or "bad sector" in lower or rc != 0:
            result["errors_found"] = True
            result["status"] = "errors_detected"
        else:
            result["status"] = "scan_complete"

        logger.info("get_drive_health %s: status=%s rc=%d", letter, result["status"], rc)
    except Exception as exc:
        result["output"] = str(exc)
        result["status"] = "error"
        logger.exception("get_drive_health failed for %s: %s", letter, exc)
    return result
