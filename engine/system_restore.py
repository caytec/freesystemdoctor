"""
system_restore.py — Windows System Restore point management.
Part of FreeSystemDoctor engine.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import re
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "system_restore.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Restore point type strings
# ---------------------------------------------------------------------------
_RP_TYPES: dict[int, str] = {
    0:  "APPLICATION_INSTALL",
    1:  "APPLICATION_UNINSTALL",
    10: "DEVICE_DRIVER_INSTALL",
    12: "MODIFY_SETTINGS",
    13: "CANCELLED_OPERATION",
    14: "RESTORE",
    15: "CHECKPOINT",
    16: "MANUAL",
    17: "WINDOWS_UPDATE",
    18: "CRITICAL_UPDATE",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 60, encoding: str = "utf-8", errors: str = "replace") -> tuple[int, str]:
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
        return -1, "Timeout"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"
    except Exception as exc:
        logger.exception("_run error: %s", exc)
        return -1, str(exc)


def _run_powershell(script: str, timeout: int = 120) -> tuple[int, str]:
    return _run(
        ["powershell", "-NonInteractive", "-NoProfile", "-Command", script],
        timeout=timeout,
    )


def _parse_wmi_date(wmi_date: str) -> str:
    """
    Convert WMI datetime string (e.g. '20240115120000.000000+060') to ISO-like format.
    Returns original string on failure.
    """
    try:
        m = re.match(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", wmi_date)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}"
    except Exception:
        pass
    return wmi_date


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_restore_points() -> list[dict]:
    """
    Return all available system restore points.

    Returns:
        List of {sequence_number, description, creation_time, type_str, event_type}
    """
    points: list[dict] = []
    try:
        script = (
            "Get-ComputerRestorePoint | "
            "Select-Object SequenceNumber, Description, CreationTime, RestorePointType, EventType | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        rc, out = _run_powershell(script, timeout=60)
        if rc != 0 or not out.strip():
            logger.warning("get_restore_points: rc=%d output=%s", rc, out[:200])
            return points

        reader = csv.DictReader(io.StringIO(out))
        for row in reader:
            try:
                seq_str = (row.get("SequenceNumber") or "0").strip()
                seq = int(seq_str) if seq_str.isdigit() else 0
                rp_type_str = (row.get("RestorePointType") or "0").strip()
                rp_type = int(rp_type_str) if rp_type_str.isdigit() else 0
                creation_raw = (row.get("CreationTime") or "").strip()
                creation_time = _parse_wmi_date(creation_raw)
                points.append({
                    "sequence_number": seq,
                    "description":     (row.get("Description") or "").strip(),
                    "creation_time":   creation_time,
                    "type_str":        _RP_TYPES.get(rp_type, f"Type {rp_type}"),
                    "event_type":      (row.get("EventType") or "").strip(),
                })
            except Exception as row_exc:
                logger.debug("Skipping restore point row: %s", row_exc)

        logger.info("get_restore_points: found %d points", len(points))
    except Exception as exc:
        logger.exception("get_restore_points failed: %s", exc)
    return points


def create_restore_point(description: str = "FreeSystemDoctor Checkpoint") -> bool:
    """
    Create a new system restore point.

    Args:
        description: Label for the restore point.

    Returns:
        True on success.
    """
    try:
        # Sanitise description to avoid PowerShell injection
        safe_desc = description.replace("'", "").replace('"', "")
        script = f"Checkpoint-Computer -Description '{safe_desc}' -RestorePointType 'MODIFY_SETTINGS'"
        rc, out = _run_powershell(script, timeout=120)
        success = rc == 0
        if not success:
            logger.warning("create_restore_point failed: %s", out[:300])
        else:
            logger.info("create_restore_point: created '%s'", safe_desc)
        return success
    except Exception as exc:
        logger.exception("create_restore_point failed: %s", exc)
        return False


def delete_restore_point(sequence_number: int) -> bool:
    """
    Delete a system restore point by sequence number.

    Note: Windows does not provide a direct per-sequence-number deletion API.
    This uses vssadmin to delete the corresponding shadow copy by finding its ID.

    Args:
        sequence_number: The SequenceNumber of the restore point.

    Returns:
        True on success or if point not found.
    """
    try:
        # Get the shadow copy ID linked to this restore point via WMI
        script = (
            f"$rp = Get-ComputerRestorePoint | Where-Object {{ $_.SequenceNumber -eq {sequence_number} }}; "
            "$shadows = (Get-WmiObject Win32_ShadowCopy); "
            "foreach ($s in $shadows) { "
            "  if ($rp -ne $null -and $s.InstallDate -ne $null) { "
            "    Write-Output $s.ID "
            "  } "
            "}"
        )
        # Simpler: use vssadmin list shadows and delete the oldest/matching shadow
        # Since we can't directly map seq -> shadow, use PowerShell Wscript method
        script2 = (
            f"$rp = Get-ComputerRestorePoint | Where-Object {{ $_.SequenceNumber -eq {sequence_number} }}; "
            "if ($rp -eq $null) { Write-Output 'NOT_FOUND'; exit 0 }; "
            "$rp | ForEach-Object { "
            "  $shadow = Get-WmiObject Win32_ShadowCopy | "
            "    Where-Object { $_.InstallDate.Substring(0,14) -eq $_.CreationTime.Substring(0,14) } | "
            "    Select-Object -First 1; "
            "  if ($shadow) { $shadow.Delete() } "
            "}; "
            "Write-Output 'DONE'"
        )
        rc, out = _run_powershell(script2, timeout=60)
        if "NOT_FOUND" in out:
            logger.info("delete_restore_point: sequence %d not found", sequence_number)
            return True  # Nothing to delete
        if rc == 0:
            logger.info("delete_restore_point: deleted sequence %d", sequence_number)
            return True
        # Fallback: attempt to delete via vssadmin (deletes oldest shadows)
        logger.warning("delete_restore_point shadow delete rc=%d; trying vssadmin fallback", rc)
        rc2, out2 = _run(
            ["vssadmin", "delete", "shadows", f"/shadow={sequence_number}", "/quiet"],
            timeout=60,
        )
        return rc2 == 0
    except Exception as exc:
        logger.exception("delete_restore_point failed for seq=%d: %s", sequence_number, exc)
        return False


def get_shadow_storage() -> dict:
    """
    Get VSS shadow copy storage statistics.

    Returns:
        {used_gb, allocated_gb, max_gb, drive, raw_output}
    """
    result = {"used_gb": 0.0, "allocated_gb": 0.0, "max_gb": 0.0, "drive": "", "raw_output": ""}
    try:
        rc, out = _run(["vssadmin", "list", "shadowstorage"], timeout=30)
        result["raw_output"] = out

        def _parse_bytes(text: str) -> float:
            """Parse strings like '1.23 GB (1,234,567 bytes)' into GB."""
            m = re.search(r"([\d,]+)\s+bytes", text, re.IGNORECASE)
            if m:
                b = int(m.group(1).replace(",", ""))
                return round(b / (1024 ** 3), 3)
            m2 = re.search(r"([\d.]+)\s*GB", text, re.IGNORECASE)
            if m2:
                return float(m2.group(1))
            return 0.0

        current_section: dict = {}
        for line in out.splitlines():
            line = line.strip()
            if not line:
                if current_section:
                    # Merge into result (last section wins; typically only one drive shown)
                    result.update(current_section)
                    current_section = {}
                continue
            if "For volume:" in line:
                m = re.search(r"\((\w:)\)", line)
                if m:
                    current_section["drive"] = m.group(1).upper()
            elif "Used Shadow Copy Storage space:" in line:
                current_section["used_gb"] = _parse_bytes(line.split(":", 1)[1])
            elif "Allocated Shadow Copy Storage space:" in line:
                current_section["allocated_gb"] = _parse_bytes(line.split(":", 1)[1])
            elif "Maximum Shadow Copy Storage space:" in line:
                current_section["max_gb"] = _parse_bytes(line.split(":", 1)[1])

        if current_section:
            result.update(current_section)

    except Exception as exc:
        logger.exception("get_shadow_storage failed: %s", exc)
    return result


def enable_system_restore(drive: str = "C:") -> bool:
    """
    Enable System Restore on the given drive.

    Args:
        drive: Drive specification, e.g. "C:"

    Returns:
        True on success.
    """
    try:
        drive_clean = drive.strip().upper().rstrip("\\")
        if not drive_clean.endswith(":"):
            drive_clean += ":"
        script = f"Enable-ComputerRestore -Drive '{drive_clean}'"
        rc, out = _run_powershell(script, timeout=60)
        if rc != 0:
            logger.warning("enable_system_restore failed: %s", out[:300])
        else:
            logger.info("enable_system_restore: enabled on %s", drive_clean)
        return rc == 0
    except Exception as exc:
        logger.exception("enable_system_restore failed: %s", exc)
        return False


def get_restore_status() -> dict:
    """
    Get a summary of System Restore status.

    Returns:
        {enabled: bool, space_used_gb: float, point_count: int}
    """
    status = {"enabled": False, "space_used_gb": 0.0, "point_count": 0}
    try:
        # Check if System Restore is enabled via registry
        import winreg
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore",
                0,
                winreg.KEY_READ,
            ) as k:
                rp_disabled, _ = winreg.QueryValueEx(k, "RPSessionInterval")
                status["enabled"] = rp_disabled != 0
        except Exception:
            # Fallback: try to list restore points
            points = get_restore_points()
            status["enabled"] = len(points) > 0

        points = get_restore_points()
        status["point_count"] = len(points)

        storage = get_shadow_storage()
        status["space_used_gb"] = storage.get("used_gb", 0.0)

        # Better enabled check: if VSS service is running and points exist
        if not status["enabled"]:
            status["enabled"] = status["point_count"] > 0

    except Exception as exc:
        logger.exception("get_restore_status failed: %s", exc)
    return status
