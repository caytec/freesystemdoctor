"""
driver_updater.py — Driver inventory, problem detection, and update utilities.
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
from typing import Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "driver_updater.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Error code descriptions (Device Manager codes)
# ---------------------------------------------------------------------------
_CM_ERROR_DESCRIPTIONS: dict[int, str] = {
    1:  "This device is not configured correctly. (Code 1)",
    3:  "The driver for this device might be corrupted. (Code 3)",
    10: "This device cannot start. Try upgrading the device drivers. (Code 10)",
    12: "This device cannot find enough free resources. (Code 12)",
    14: "This device cannot work properly until you restart. (Code 14)",
    18: "Reinstall the drivers for this device. (Code 18)",
    19: "Your registry might be corrupted. (Code 19)",
    21: "Windows is removing this device. (Code 21)",
    22: "This device is disabled. (Code 22)",
    24: "This device is not present or working. (Code 24)",
    28: "The drivers for this device are not installed. (Code 28)",
    29: "This device is disabled because the firmware did not provide the required resources. (Code 29)",
    31: "This device is not working properly because Windows cannot load the drivers required. (Code 31)",
    32: "A driver (service) for this device has been disabled. (Code 32)",
    33: "Windows cannot determine which resources are required. (Code 33)",
    34: "Windows cannot determine the settings for this device. (Code 34)",
    35: "Your computer's system firmware does not include enough information. (Code 35)",
    36: "This device is requesting a PCI interrupt but is configured for an ISA interrupt. (Code 36)",
    37: "Windows cannot initialize the device driver for this hardware. (Code 37)",
    38: "Windows cannot load the device driver because a previous instance is still in memory. (Code 38)",
    39: "Windows cannot load the device driver. The driver may be corrupted or missing. (Code 39)",
    40: "Windows cannot access this hardware because its service key information is missing. (Code 40)",
    41: "Windows cannot load the device driver for this hardware. (Code 41)",
    42: "Windows cannot load the device driver because there is a duplicate device. (Code 42)",
    43: "Windows has stopped this device because it has reported problems. (Code 43)",
    44: "An application or service has shut down this hardware device. (Code 44)",
    45: "Currently, this hardware device is not connected to the computer. (Code 45)",
    46: "Windows cannot gain access to this hardware device because the OS is shutting down. (Code 46)",
    47: "Windows cannot use this hardware device because it has been prepared for 'safe removal'. (Code 47)",
    48: "The software for this device has been blocked from starting. (Code 48)",
    49: "Windows cannot start new hardware devices because the system hive is too large. (Code 49)",
    52: "Windows cannot verify the digital signature for the drivers. (Code 52)",
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


def _parse_csv_output(out: str) -> list[dict]:
    """Parse CSV output from PowerShell ConvertTo-Csv, returning list of dicts."""
    rows: list[dict] = []
    try:
        reader = csv.DictReader(io.StringIO(out))
        for row in reader:
            rows.append({k: (v or "").strip() for k, v in row.items()})
    except Exception as exc:
        logger.debug("_parse_csv_output error: %s", exc)
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_installed_drivers() -> list[dict]:
    """
    Return all installed PnP signed drivers.

    Returns:
        List of {name, version, manufacturer, device_class, date, inf_name, device_id}
    """
    drivers: list[dict] = []
    try:
        script = (
            "Get-WmiObject Win32_PnPSignedDriver | "
            "Select-Object DeviceName, DriverVersion, Manufacturer, DeviceClass, DriverDate, InfName, DeviceID | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        rc, out = _run_powershell(script, timeout=90)
        if rc != 0 or not out.strip():
            logger.warning("get_installed_drivers: PowerShell returned rc=%d", rc)
            return drivers

        for row in _parse_csv_output(out):
            drivers.append({
                "name":         row.get("DeviceName", ""),
                "version":      row.get("DriverVersion", ""),
                "manufacturer": row.get("Manufacturer", ""),
                "device_class": row.get("DeviceClass", ""),
                "date":         row.get("DriverDate", ""),
                "inf_name":     row.get("InfName", ""),
                "device_id":    row.get("DeviceID", ""),
            })

        logger.info("get_installed_drivers: found %d drivers", len(drivers))
    except Exception as exc:
        logger.exception("get_installed_drivers failed: %s", exc)
    return drivers


def find_problematic_drivers() -> list[dict]:
    """
    Return drivers/devices with non-zero ConfigManagerErrorCode (Device Manager errors).

    Returns:
        List of {name, error_code, error_description, device_id, status}
    """
    problems: list[dict] = []
    try:
        script = (
            "Get-WmiObject Win32_PnPEntity | "
            "Where-Object { $_.ConfigManagerErrorCode -ne 0 } | "
            "Select-Object Name, ConfigManagerErrorCode, DeviceID, Status | "
            "ConvertTo-Csv -NoTypeInformation"
        )
        rc, out = _run_powershell(script, timeout=60)
        if rc != 0 or not out.strip():
            return problems

        for row in _parse_csv_output(out):
            try:
                code_str = row.get("ConfigManagerErrorCode", "0")
                code = int(code_str) if code_str.isdigit() else 0
            except ValueError:
                code = 0

            problems.append({
                "name":              row.get("Name", "Unknown Device"),
                "error_code":        code,
                "error_description": _CM_ERROR_DESCRIPTIONS.get(code, f"Unknown error code {code}"),
                "device_id":         row.get("DeviceID", ""),
                "status":            row.get("Status", ""),
            })

        logger.info("find_problematic_drivers: found %d problems", len(problems))
    except Exception as exc:
        logger.exception("find_problematic_drivers failed: %s", exc)
    return problems


# Known driver-related keywords to filter winget results
_DRIVER_KEYWORDS = [
    "driver", "firmware", "intel", "amd", "nvidia", "realtek",
    "broadcom", "qualcomm", "marvell", "atheros", "via", "silicon labs",
    "prolific", "ftdi", "logitech", "razer", "corsair", "steelseries",
    "asus", "gigabyte", "msi", "dell", "hp", "lenovo", "acer",
]


def check_driver_updates_winget() -> list[dict]:
    """
    Check for available driver/firmware updates via winget.

    Returns:
        List of {name, installed, available, winget_id}
    """
    updates: list[dict] = []
    try:
        rc, out = _run(
            ["winget", "upgrade", "--include-unknown", "--disable-interactivity"],
            timeout=120,
        )
        if rc not in (0, 1) or not out:
            logger.warning("check_driver_updates_winget: winget returned rc=%d", rc)
            return updates

        lines = out.splitlines()
        # Find header line
        header_idx = -1
        for i, line in enumerate(lines):
            if re.search(r"\bId\b.*\bVersion\b.*Available", line, re.IGNORECASE):
                header_idx = i
                break

        if header_idx == -1:
            return updates

        # Try to detect column positions from header
        header = lines[header_idx]
        name_pos    = header.upper().find("NAME")
        id_pos      = header.upper().find("ID")
        ver_pos     = header.upper().find("VERSION")
        avail_pos   = header.upper().find("AVAILABLE")

        for line in lines[header_idx + 2:]:
            if not line.strip() or line.startswith("-"):
                continue
            try:
                line_lower = line.lower()
                if not any(kw in line_lower for kw in _DRIVER_KEYWORDS):
                    continue

                # Extract fields by column position
                def _col(start: int, end: int = -1) -> str:
                    if start < 0:
                        return ""
                    segment = line[start:end] if end > start else line[start:]
                    return segment.strip().split("  ")[0].strip()

                name      = _col(name_pos, id_pos) if id_pos > name_pos else line[:40].strip()
                winget_id = _col(id_pos, ver_pos)  if ver_pos > id_pos  else ""
                installed = _col(ver_pos, avail_pos) if avail_pos > ver_pos else ""
                available = _col(avail_pos) if avail_pos >= 0 else ""

                if winget_id and available:
                    updates.append({
                        "name":      name,
                        "installed": installed,
                        "available": available,
                        "winget_id": winget_id,
                    })
            except Exception as row_exc:
                logger.debug("winget row parse error: %s | line: %s", row_exc, line)

        logger.info("check_driver_updates_winget: found %d driver updates", len(updates))
    except Exception as exc:
        logger.exception("check_driver_updates_winget failed: %s", exc)
    return updates


def update_driver_winget(winget_id: str) -> bool:
    """
    Update a specific package by winget ID silently.

    Args:
        winget_id: The winget package identifier.

    Returns:
        True on success.
    """
    try:
        rc, out = _run(
            ["winget", "upgrade", "--id", winget_id, "--silent", "--disable-interactivity", "--accept-package-agreements", "--accept-source-agreements"],
            timeout=300,
        )
        success = rc == 0
        logger.info("update_driver_winget %s: rc=%d", winget_id, rc)
        return success
    except Exception as exc:
        logger.exception("update_driver_winget failed for %s: %s", winget_id, exc)
        return False


def open_device_manager() -> None:
    """Open Windows Device Manager (devmgmt.msc)."""
    try:
        subprocess.Popen(
            ["mmc", "devmgmt.msc"],
            creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, "DETACHED_PROCESS") else 0,
        )
        logger.info("open_device_manager: launched devmgmt.msc")
    except Exception as exc:
        logger.exception("open_device_manager failed: %s", exc)


def export_driver_report(path: str) -> bool:
    """
    Export the installed driver list to a CSV file.

    Args:
        path: Absolute path of the output CSV file.

    Returns:
        True on success.
    """
    try:
        drivers = get_installed_drivers()
        if not drivers:
            logger.warning("export_driver_report: no drivers to export")
            return False

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        fieldnames = ["name", "version", "manufacturer", "device_class", "date", "inf_name", "device_id"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(drivers)

        logger.info("export_driver_report: wrote %d rows to %s", len(drivers), path)
        return True
    except Exception as exc:
        logger.exception("export_driver_report failed: %s", exc)
        return False
