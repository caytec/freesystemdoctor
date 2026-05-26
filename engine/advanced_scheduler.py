"""Advanced Scheduler — cron-like scheduling for maintenance tasks."""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


class ScheduledTask:
    """Represents a scheduled maintenance task."""
    def __init__(self, task_id: str, name: str, action: str, schedule: str, enabled: bool = True):
        self.task_id = task_id
        self.name = name
        self.action = action
        self.schedule = schedule
        self.enabled = enabled
        self.last_run = None
        self.next_run = None


def _parse_cron_expression(cron: str) -> dict:
    """Parse simplified cron expression: 'minute hour day month day_of_week'."""
    try:
        parts = cron.split()
        if len(parts) != 5:
            return None

        minute, hour, day, month, dow = parts
        return {
            "minute": minute if minute != "*" else None,
            "hour": hour if hour != "*" else None,
            "day": day if day != "*" else None,
            "month": month if month != "*" else None,
            "dow": dow if dow != "*" else None,
        }
    except Exception:
        return None


def _matches_schedule(task: ScheduledTask, now: datetime) -> bool:
    """Check if task schedule matches current time."""
    cron = _parse_cron_expression(task.schedule)
    if not cron:
        return False

    # Simple matching logic
    if cron["minute"] and int(cron["minute"]) != now.minute:
        return False
    if cron["hour"] and int(cron["hour"]) != now.hour:
        return False
    if cron["day"] and int(cron["day"]) != now.day:
        return False
    if cron["month"] and int(cron["month"]) != now.month:
        return False
    if cron["dow"] and int(cron["dow"]) != now.weekday():
        return False

    return True


def _get_tasks_file() -> Path:
    """Get path to tasks configuration file."""
    config_dir = Path.home() / "AppData" / "Local" / "FreeSystemDoctor"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "scheduled_tasks.json"


def load_scheduled_tasks() -> list[ScheduledTask]:
    """Load scheduled tasks from configuration."""
    tasks_file = _get_tasks_file()

    if not tasks_file.exists():
        return []

    try:
        with open(tasks_file, "r") as f:
            data = json.load(f)

        tasks = []
        for task_data in data:
            task = ScheduledTask(
                task_id=task_data["id"],
                name=task_data["name"],
                action=task_data["action"],
                schedule=task_data["schedule"],
                enabled=task_data.get("enabled", True)
            )
            task.last_run = task_data.get("last_run")
            tasks.append(task)

        return tasks
    except Exception:
        return []


def save_scheduled_tasks(tasks: list[ScheduledTask]):
    """Save scheduled tasks to configuration."""
    tasks_file = _get_tasks_file()

    try:
        data = []
        for task in tasks:
            data.append({
                "id": task.task_id,
                "name": task.name,
                "action": task.action,
                "schedule": task.schedule,
                "enabled": task.enabled,
                "last_run": task.last_run,
            })

        with open(tasks_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def create_scheduled_task(name: str, action: str, schedule: str) -> ScheduledTask:
    """Create a new scheduled task."""
    import uuid
    task_id = str(uuid.uuid4())[:8]

    task = ScheduledTask(
        task_id=task_id,
        name=name,
        action=action,
        schedule=schedule,
        enabled=True
    )

    tasks = load_scheduled_tasks()
    tasks.append(task)
    save_scheduled_tasks(tasks)

    return task


def update_scheduled_task(task_id: str, **kwargs):
    """Update a scheduled task."""
    tasks = load_scheduled_tasks()

    for task in tasks:
        if task.task_id == task_id:
            if "name" in kwargs:
                task.name = kwargs["name"]
            if "action" in kwargs:
                task.action = kwargs["action"]
            if "schedule" in kwargs:
                task.schedule = kwargs["schedule"]
            if "enabled" in kwargs:
                task.enabled = kwargs["enabled"]

    save_scheduled_tasks(tasks)


def delete_scheduled_task(task_id: str):
    """Delete a scheduled task."""
    tasks = load_scheduled_tasks()
    tasks = [t for t in tasks if t.task_id != task_id]
    save_scheduled_tasks(tasks)


def run_scheduled_task(task: ScheduledTask) -> bool:
    """Execute a scheduled task."""
    try:
        if task.action == "disk_clean":
            subprocess.run(["python", "-m", "engine.disk_cleaner"], timeout=3600, capture_output=True, creationflags=0x08000000)
        elif task.action == "registry_clean":
            subprocess.run(["python", "-m", "engine.registry_cleaner"], timeout=600, capture_output=True, creationflags=0x08000000)
        elif task.action == "defrag":
            subprocess.run(["python", "-m", "engine.smart_defrag"], timeout=7200, capture_output=True, creationflags=0x08000000)
        elif task.action == "update_check":
            subprocess.run(["python", "-m", "engine.software_updater"], timeout=300, capture_output=True, creationflags=0x08000000)
        else:
            return False

        task.last_run = datetime.now().isoformat()
        return True
    except Exception:
        return False


def get_pending_tasks() -> list[ScheduledTask]:
    """Get tasks that are due to run."""
    tasks = load_scheduled_tasks()
    now = datetime.now()
    pending = []

    for task in tasks:
        if task.enabled and _matches_schedule(task, now):
            pending.append(task)

    return pending


def get_task_schedule_description(schedule: str) -> str:
    """Get human-readable schedule description."""
    cron = _parse_cron_expression(schedule)
    if not cron:
        return "Invalid schedule"

    parts = []
    if cron["minute"] is not None:
        parts.append(f"minute {cron['minute']}")
    if cron["hour"] is not None:
        parts.append(f"hour {cron['hour']}")
    if cron["day"] is not None:
        parts.append(f"day {cron['day']}")
    if cron["month"] is not None:
        parts.append(f"month {cron['month']}")
    if cron["dow"] is not None:
        dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_idx = int(cron["dow"])
        parts.append(dow_names[dow_idx] if dow_idx < 7 else "Unknown")

    if not parts:
        return "Every minute"

    return "At " + ", ".join(parts)


_PREDEFINED_SCHEDULES = {
    "Daily Midnight": "0 0 * * *",
    "Daily 3 AM": "0 3 * * *",
    "Daily 6 PM": "0 18 * * *",
    "Weekdays 2 AM": "0 2 * * 1-5",
    "Weekends 10 PM": "0 22 * * 0,6",
    "Weekly Sunday": "0 0 * * 0",
    "Monthly 1st": "0 0 1 * *",
    "Every 6 Hours": "0 */6 * * *",
}


def get_predefined_schedules() -> dict[str, str]:
    """Get predefined schedule presets."""
    return _PREDEFINED_SCHEDULES.copy()


_AVAILABLE_ACTIONS = {
    "disk_clean": "Disk Cleanup",
    "registry_clean": "Registry Cleanup",
    "defrag": "Disk Defrag/TRIM",
    "update_check": "Check for Updates",
}


def get_available_actions() -> dict[str, str]:
    """Get available maintenance actions."""
    return _AVAILABLE_ACTIONS.copy()
