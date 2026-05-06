"""
scheduled_cleaner.py — Windows Task Scheduler integration for automated cleaning.
Part of FreeSystemDoctor engine.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "scheduled_cleaner.log"), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_TASK_NAME      = "FreeSystemDoctor_AutoClean"
_SCHEDULE_FILE  = os.path.join(_LOG_DIR, "schedule_config.json")
_AUTOCLEAN_LOG  = os.path.join(_LOG_DIR, "autoclean_results.json")

# Detect main.py path relative to this file
_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_ENGINE_DIR)
_MAIN_PY = os.path.join(_PROJECT_DIR, "main.py")

# Default modules that auto-clean will run
_DEFAULT_MODULES: list[str] = ["disk_cleaner", "registry_cleaner", "empty_folder_finder"]

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


def _run_powershell(script: str, timeout: int = 60) -> tuple[int, str]:
    return _run(
        ["powershell", "-NonInteractive", "-NoProfile", "-Command", script],
        timeout=timeout,
    )


def _load_schedule() -> dict:
    """Load schedule config from disk. Returns empty dict on failure."""
    try:
        if os.path.exists(_SCHEDULE_FILE):
            with open(_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        logger.warning("_load_schedule: %s", exc)
    return {}


def _save_schedule(config: dict) -> None:
    try:
        with open(_SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as exc:
        logger.warning("_save_schedule: %s", exc)


def _get_task_info() -> dict:
    """
    Query the Windows Task Scheduler for the FreeSystemDoctor task.
    Returns dict with task info or empty dict if not found.
    """
    info: dict = {}
    try:
        script = (
            f"$t = Get-ScheduledTask -TaskName '{_TASK_NAME}' -ErrorAction SilentlyContinue; "
            "if ($t) { "
            "  $info = Get-ScheduledTaskInfo -TaskName $t.TaskName -ErrorAction SilentlyContinue; "
            "  $trigger = $t.Triggers | Select-Object -First 1; "
            "  [PSCustomObject]@{ "
            "    State = $t.State; "
            "    LastRunTime = if ($info) { $info.LastRunTime } else { '' }; "
            "    NextRunTime = if ($info) { $info.NextRunTime } else { '' }; "
            "    TriggerType = $trigger.CimClass.CimClassName; "
            "    StartBoundary = if ($trigger) { $trigger.StartBoundary } else { '' }; "
            "  } | ConvertTo-Json "
            "} else { Write-Output '{}' }"
        )
        rc, out = _run_powershell(script, timeout=30)
        if rc == 0 and out.strip() and out.strip() != "{}":
            data = json.loads(out.strip())
            info = {
                "state":        str(data.get("State", "")),
                "last_run":     str(data.get("LastRunTime", "")),
                "next_run":     str(data.get("NextRunTime", "")),
                "trigger_type": str(data.get("TriggerType", "")),
                "start_boundary": str(data.get("StartBoundary", "")),
            }
    except json.JSONDecodeError:
        pass  # Task not found or malformed output
    except Exception as exc:
        logger.debug("_get_task_info error: %s", exc)
    return info


def _frequency_to_schtasks(frequency: str) -> str:
    """Map frequency string to schtasks /sc parameter."""
    mapping = {
        "daily":   "DAILY",
        "weekly":  "WEEKLY",
        "monthly": "MONTHLY",
    }
    return mapping.get(frequency.lower(), "DAILY")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_schedule() -> dict:
    """
    Return the current auto-clean schedule configuration.

    Returns:
        {enabled, frequency, time, last_run, next_run, modules: list}
    """
    config = _load_schedule()
    task_info = _get_task_info()

    return {
        "enabled":   config.get("enabled", bool(task_info)),
        "frequency": config.get("frequency", "daily"),
        "time":      config.get("time", "03:00"),
        "last_run":  task_info.get("last_run", config.get("last_run", "")),
        "next_run":  task_info.get("next_run", config.get("next_run", "")),
        "modules":   config.get("modules", _DEFAULT_MODULES),
    }


def set_schedule(
    enabled: bool,
    frequency: str,
    time_str: str,
    modules: list[str],
) -> bool:
    """
    Create or update the Windows scheduled task for auto-cleaning.

    Args:
        enabled:    Whether to enable the schedule.
        frequency:  "daily", "weekly", or "monthly"
        time_str:   Time in "HH:MM" format (24-hour)
        modules:    List of module names to run (e.g. ["disk_cleaner", "registry_cleaner"])

    Returns:
        True on success.
    """
    try:
        # Save config regardless
        config = {
            "enabled":   enabled,
            "frequency": frequency,
            "time":      time_str,
            "modules":   modules,
        }
        _save_schedule(config)

        if not enabled:
            # Remove the task if disabling
            return delete_schedule()

        python_exe = sys.executable or "python"
        modules_arg = ",".join(modules)
        task_run = f'"{python_exe}" "{_MAIN_PY}" --auto-clean --modules "{modules_arg}"'
        sc_freq = _frequency_to_schtasks(frequency)

        # Delete existing task first to avoid duplication
        _run(["schtasks", "/delete", "/tn", _TASK_NAME, "/f"], timeout=20)

        cmd = [
            "schtasks", "/create",
            "/tn", _TASK_NAME,
            "/tr", task_run,
            "/sc", sc_freq,
            "/st", time_str,
            "/ru", "SYSTEM",
            "/rl", "HIGHEST",
            "/f",   # Force overwrite
        ]
        rc, out = _run(cmd, timeout=30)
        success = rc == 0
        if not success:
            logger.warning("set_schedule schtasks create failed: %s", out)
        else:
            logger.info("set_schedule: created task %s (%s at %s)", _TASK_NAME, sc_freq, time_str)
        return success

    except Exception as exc:
        logger.exception("set_schedule failed: %s", exc)
        return False


def delete_schedule() -> bool:
    """
    Remove the FreeSystemDoctor auto-clean scheduled task.

    Returns:
        True on success (or if task did not exist).
    """
    try:
        rc, out = _run(
            ["schtasks", "/delete", "/tn", _TASK_NAME, "/f"],
            timeout=20,
        )
        # rc 1 means task not found — treat as success
        success = rc in (0, 1)
        if success:
            # Clear enabled flag in config
            config = _load_schedule()
            config["enabled"] = False
            _save_schedule(config)
            logger.info("delete_schedule: task %s removed", _TASK_NAME)
        else:
            logger.warning("delete_schedule failed: %s", out)
        return success
    except Exception as exc:
        logger.exception("delete_schedule failed: %s", exc)
        return False


def run_auto_clean(modules: Optional[list[str]] = None) -> dict:
    """
    Run the specified cleaning modules silently and return a summary.

    Args:
        modules: List of module names. If None, reads from saved schedule config.
                 Supported: "disk_cleaner", "registry_cleaner", "empty_folder_finder"

    Returns:
        {modules_run: list, issues_fixed: int, errors: list, timestamp: str}
    """
    import importlib
    import traceback

    if modules is None:
        config = _load_schedule()
        modules = config.get("modules", _DEFAULT_MODULES)

    summary: dict = {
        "modules_run": [],
        "issues_fixed": 0,
        "errors": [],
        "timestamp": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }

    # Map of module name -> (module_path, callable_name, kwargs)
    _MODULE_MAP: dict[str, tuple[str, str, dict]] = {
        "disk_cleaner": (
            "engine.disk_cleaner",
            "clean_all",
            {},
        ),
        "registry_cleaner": (
            "engine.registry_cleaner",
            "clean_registry",
            {},
        ),
        "empty_folder_finder": (
            "engine.empty_folder_finder",
            "scan_empty_folders",
            {},
        ),
    }

    for module_name in modules:
        try:
            if module_name not in _MODULE_MAP:
                summary["errors"].append(f"Unknown module: {module_name}")
                logger.warning("run_auto_clean: unknown module %s", module_name)
                continue

            mod_path, func_name, kwargs = _MODULE_MAP[module_name]
            mod = importlib.import_module(mod_path)
            func = getattr(mod, func_name)

            logger.info("run_auto_clean: running %s.%s", mod_path, func_name)
            result = func(**kwargs)
            summary["modules_run"].append(module_name)

            # Extract numeric count of fixed issues from result (best-effort)
            if isinstance(result, (list, tuple)):
                summary["issues_fixed"] += len(result)
            elif isinstance(result, dict):
                for key in ("cleaned", "fixed", "deleted", "items_cleaned", "count"):
                    if key in result and isinstance(result[key], (int, float)):
                        summary["issues_fixed"] += int(result[key])
                        break

        except ImportError as exc:
            msg = f"Module {module_name} not available: {exc}"
            summary["errors"].append(msg)
            logger.warning("run_auto_clean: %s", msg)
        except Exception as exc:
            msg = f"Error in {module_name}: {exc}"
            summary["errors"].append(msg)
            logger.error("run_auto_clean: %s\n%s", msg, traceback.format_exc())

    # Persist results for UI retrieval
    try:
        with open(_AUTOCLEAN_LOG, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    except Exception as exc:
        logger.warning("run_auto_clean: could not save results: %s", exc)

    logger.info(
        "run_auto_clean complete: modules=%s fixed=%d errors=%d",
        summary["modules_run"],
        summary["issues_fixed"],
        len(summary["errors"]),
    )
    return summary
