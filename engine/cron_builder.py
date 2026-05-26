"""Cron Builder — visual cron expression builder with validation and suggestions."""

from datetime import datetime, timedelta


class CronExpression:
    """Represents a parsed cron expression."""
    def __init__(self, minute="*", hour="*", day="*", month="*", dow="*"):
        self.minute = minute
        self.hour = hour
        self.day = day
        self.month = month
        self.dow = dow

    @property
    def expression(self) -> str:
        """Get full cron expression string."""
        return f"{self.minute} {self.hour} {self.day} {self.month} {self.dow}"

    @staticmethod
    def from_string(cron_str: str) -> "CronExpression":
        """Parse cron string into expression."""
        parts = cron_str.strip().split()
        if len(parts) != 5:
            return None

        return CronExpression(*parts)

    def to_description(self) -> str:
        """Convert to human-readable description."""
        parts = []

        if self.minute != "*":
            parts.append(f"at minute {self.minute}")
        if self.hour != "*":
            parts.append(f"of hour {self.hour}")
        if self.day != "*":
            parts.append(f"on day {self.day}")
        if self.month != "*":
            parts.append(f"of month {self.month}")
        if self.dow != "*":
            dow_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            if self.dow.isdigit():
                parts.append(f"on {dow_names[int(self.dow)]}")
            else:
                parts.append(f"on day {self.dow}")

        if not parts:
            return "Every minute"

        return " ".join(parts).capitalize()

    def next_run(self) -> datetime:
        """Calculate next scheduled run time."""
        now = datetime.now()

        # Simple approximation: next matching hour/minute
        if self.hour != "*" and self.minute != "*":
            try:
                target_hour = int(self.hour)
                target_minute = int(self.minute)

                next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)

                return next_run
            except ValueError:
                pass

        return now + timedelta(hours=1)


_COMMON_PATTERNS = {
    "Every Minute": "* * * * *",
    "Every 5 Minutes": "*/5 * * * *",
    "Every 15 Minutes": "*/15 * * * *",
    "Every 30 Minutes": "*/30 * * * *",
    "Every Hour": "0 * * * *",
    "Every 6 Hours": "0 */6 * * *",
    "Every 12 Hours": "0 */12 * * *",
    "Daily at Midnight": "0 0 * * *",
    "Daily at 3 AM": "0 3 * * *",
    "Daily at 6 AM": "0 6 * * *",
    "Daily at Noon": "0 12 * * *",
    "Daily at 6 PM": "0 18 * * *",
    "Daily at 9 PM": "0 21 * * *",
    "Weekdays at 9 AM": "0 9 * * 1-5",
    "Weekdays at 5 PM": "0 17 * * 1-5",
    "Weekends at 10 AM": "0 10 * * 0,6",
    "Weekly on Monday": "0 0 * * 1",
    "Weekly on Sunday": "0 0 * * 0",
    "Bi-weekly": "0 0 * * 0/2",
    "Monthly on 1st": "0 0 1 * *",
    "Monthly on 15th": "0 0 15 * *",
    "Quarterly (1st, 4th, 7th, 10th)": "0 0 1 1,4,7,10 *",
}


def get_common_patterns() -> dict[str, str]:
    """Get predefined cron patterns."""
    return _COMMON_PATTERNS.copy()


def validate_cron(cron_str: str) -> tuple[bool, str]:
    """Validate cron expression.
    Returns (is_valid, error_message)"""

    parts = cron_str.strip().split()
    if len(parts) != 5:
        return False, "Must have exactly 5 fields (minute hour day month dow)"

    minute, hour, day, month, dow = parts

    # Basic validation
    def validate_field(value: str, field_name: str, min_val: int, max_val: int) -> tuple[bool, str]:
        if value == "*":
            return True, ""

        if value.startswith("*/"):
            try:
                step = int(value[2:])
                if step <= 0:
                    return False, f"{field_name}: step must be positive"
                return True, ""
            except ValueError:
                return False, f"{field_name}: invalid step value"

        if "-" in value:  # Range
            try:
                start, end = value.split("-")
                s, e = int(start), int(end)
                if not (min_val <= s <= max_val and min_val <= e <= max_val and s <= e):
                    return False, f"{field_name}: range {s}-{e} out of bounds [{min_val}, {max_val}]"
                return True, ""
            except ValueError:
                return False, f"{field_name}: invalid range"

        if "," in value:  # List
            try:
                vals = [int(v) for v in value.split(",")]
                for v in vals:
                    if not (min_val <= v <= max_val):
                        return False, f"{field_name}: value {v} out of bounds [{min_val}, {max_val}]"
                return True, ""
            except ValueError:
                return False, f"{field_name}: invalid list"

        try:
            val = int(value)
            if not (min_val <= val <= max_val):
                return False, f"{field_name}: value {val} out of bounds [{min_val}, {max_val}]"
            return True, ""
        except ValueError:
            return False, f"{field_name}: must be number or * or range/list"

    # Validate each field
    valid, msg = validate_field(minute, "Minute", 0, 59)
    if not valid:
        return False, msg

    valid, msg = validate_field(hour, "Hour", 0, 23)
    if not valid:
        return False, msg

    valid, msg = validate_field(day, "Day", 1, 31)
    if not valid:
        return False, msg

    valid, msg = validate_field(month, "Month", 1, 12)
    if not valid:
        return False, msg

    valid, msg = validate_field(dow, "Dow", 0, 6)
    if not valid:
        return False, msg

    return True, ""


def build_simple_schedule(frequency: str, time_of_day: str = "00:00", days: list = None) -> str:
    """Build cron expression from simple parameters.
    frequency: 'daily', 'weekly', 'monthly', 'hourly', 'custom'
    time_of_day: 'HH:MM'
    days: for weekly, list of day numbers (0=Sunday, 6=Saturday)"""

    try:
        hour, minute = map(int, time_of_day.split(":"))
    except ValueError:
        return None

    if frequency == "hourly":
        return f"{minute} * * * *"

    elif frequency == "daily":
        return f"{minute} {hour} * * *"

    elif frequency == "weekly":
        if not days:
            days = [0]  # Default: Sunday
        dow_str = ",".join(str(d) for d in days)
        return f"{minute} {hour} * * {dow_str}"

    elif frequency == "monthly":
        return f"{minute} {hour} 1 * *"

    elif frequency == "quarterly":
        return f"{minute} {hour} 1 1,4,7,10 *"

    return None


def schedule_with_interval(frequency: str, interval: int, start_hour: int = 0) -> str:
    """Create repeating schedule every N time units.
    frequency: 'minutes', 'hours', 'days'
    interval: repeat every N (1-59 for minutes, 1-23 for hours, 1-6 for days)"""

    if frequency == "minutes":
        if 1 <= interval <= 59:
            return f"*/{interval} * * * *"

    elif frequency == "hours":
        if 1 <= interval <= 23:
            return f"0 */{interval} * * *"

    elif frequency == "days":
        if 1 <= interval <= 6:
            return f"0 {start_hour} */{interval} * *"

    return None


def suggest_next_runtime(cron_str: str) -> str:
    """Suggest when the next execution will occur."""
    expr = CronExpression.from_string(cron_str)
    if not expr:
        return "Invalid expression"

    next_run = expr.next_run()
    return next_run.strftime("%a, %b %d at %H:%M:%S")


def explain_cron(cron_str: str) -> str:
    """Get detailed explanation of cron expression."""
    expr = CronExpression.from_string(cron_str)
    if not expr:
        return "Invalid expression"

    explanations = []

    if expr.minute != "*":
        if expr.minute.isdigit():
            explanations.append(f"at minute {expr.minute}")
        else:
            explanations.append(f"every {expr.minute} minutes")

    if expr.hour != "*":
        if expr.hour.isdigit():
            hour_val = int(expr.hour)
            hour_12 = (hour_val - 1) % 12 + 1 if hour_val != 0 else 12
            am_pm = "AM" if hour_val < 12 else "PM"
            explanations.append(f"at {hour_12}:00 {am_pm}")
        else:
            explanations.append(f"every {expr.hour} hours")

    if expr.day != "*" and expr.day != "1":
        explanations.append(f"on day {expr.day}")
    elif expr.day == "1":
        explanations.append("on the 1st day of month")

    if expr.month != "*":
        explanations.append(f"in month(s) {expr.month}")

    if expr.dow != "*":
        dow_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        if expr.dow.isdigit():
            explanations.append(f"on {dow_names[int(expr.dow)]}")
        else:
            explanations.append(f"on day(s) {expr.dow}")

    if not explanations:
        return "Every minute"

    return " ".join(explanations) + "."
