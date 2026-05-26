"""Scheduled Task Manager — list, enable, disable, delete Windows tasks."""

import subprocess
import csv
import io
from dataclasses import dataclass


@dataclass
class ScheduledTask:
    name: str
    path: str
    status: str       # Ready / Running / Disabled
    next_run: str
    last_run: str
    author: str = ""
    safe_to_disable: bool = False
    note: str = ""


_SAFE_TO_DISABLE = {
    r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser":
        "Sends app compatibility data to Microsoft",
    r"\Microsoft\Windows\Application Experience\ProgramDataUpdater":
        "Updates program database for compatibility",
    r"\Microsoft\Windows\Autochk\Proxy":
        "Proxy for auto-check diagnostics",
    r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator":
        "Collects CEIP data",
    r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip":
        "Collects USB CEIP data",
    r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector":
        "Collects disk diagnostic data",
    r"\Microsoft\Windows\PI\Sqm-Tasks":
        "Software Quality Metrics collection",
    r"\Microsoft\Windows\Windows Error Reporting\QueueReporting":
        "Queues error reports to Microsoft",
    r"\Microsoft\Windows\Feedback\Siuf\DmClient":
        "Device metadata feedback client",
}


def list_tasks(progress_cb=None) -> list[ScheduledTask]:
    r = subprocess.run(
        ["schtasks", "/query", "/v", "/fo", "csv"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=0x08000000)
    if r.returncode != 0:
        return []

    tasks = []
    seen = set()
    try:
        reader = csv.DictReader(io.StringIO(r.stdout))
        for row in reader:
            task_name = row.get("TaskName", "").strip()
            if not task_name or task_name in seen or task_name == "TaskName":
                continue
            seen.add(task_name)

            status = row.get("Status", "").strip()
            safe = task_name in _SAFE_TO_DISABLE
            note = _SAFE_TO_DISABLE.get(task_name, "")

            tasks.append(ScheduledTask(
                name=task_name.rsplit("\\", 1)[-1],
                path=task_name,
                status=status,
                next_run=row.get("Next Run Time", "").strip(),
                last_run=row.get("Last Run Time", "").strip(),
                author=row.get("Author", "").strip()[:40],
                safe_to_disable=safe,
                note=note,
            ))
    except Exception:
        pass

    return tasks


def enable_task(path: str) -> bool:
    r = subprocess.run(["schtasks", "/change", "/tn", path, "/enable"],
                       capture_output=True, creationflags=0x08000000)
    return r.returncode == 0


def disable_task(path: str) -> bool:
    r = subprocess.run(["schtasks", "/change", "/tn", path, "/disable"],
                       capture_output=True, creationflags=0x08000000)
    return r.returncode == 0


def delete_task(path: str) -> bool:
    r = subprocess.run(["schtasks", "/delete", "/tn", path, "/f"],
                       capture_output=True, creationflags=0x08000000)
    return r.returncode == 0


def run_task_now(path: str) -> bool:
    r = subprocess.run(["schtasks", "/run", "/tn", path],
                       capture_output=True, creationflags=0x08000000)
    return r.returncode == 0


def get_safe_to_disable() -> list[str]:
    return list(_SAFE_TO_DISABLE.keys())
