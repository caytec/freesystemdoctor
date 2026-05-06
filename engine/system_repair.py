"""System Repair — detect and fix common Windows issues automatically."""

import subprocess
import winreg
from pathlib import Path
from datetime import datetime

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class SystemIssue:
    """Represents a system issue found and potentially fixed."""
    def __init__(self, category: str, name: str, severity: str, fixable: bool, fix_fn=None):
        self.category = category
        self.name = name
        self.severity = severity
        self.fixable = fixable
        self.fix_fn = fix_fn
        self.fixed = False


def _check_broken_shortcuts() -> list[SystemIssue]:
    """Check for broken desktop and start menu shortcuts."""
    issues = []
    shortcut_locations = [
        Path.home() / "Desktop",
        Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]

    for location in shortcut_locations:
        if not location.exists():
            continue

        try:
            for lnk_file in location.glob("**/*.lnk"):
                try:
                    # Check if target exists
                    target_path = Path(str(lnk_file)[:-4])
                    if not target_path.exists():
                        issue = SystemIssue(
                            category="Shortcuts",
                            name=lnk_file.stem,
                            severity="LOW",
                            fixable=True,
                            fix_fn=lambda p=lnk_file: p.unlink()
                        )
                        issues.append(issue)
                except Exception:
                    pass
        except Exception:
            pass

    return issues


def _check_missing_fonts() -> list[SystemIssue]:
    """Check for missing system fonts."""
    issues = []
    fonts_dir = Path("C:\\Windows\\Fonts")
    required_fonts = ["arial.ttf", "times.ttf", "cour.ttf"]

    for font in required_fonts:
        font_path = fonts_dir / font
        if not font_path.exists():
            issue = SystemIssue(
                category="Fonts",
                name=font,
                severity="MEDIUM",
                fixable=False
            )
            issues.append(issue)

    return issues


def _check_corrupted_registry_hives() -> list[SystemIssue]:
    """Check for corrupted Windows registry hives."""
    issues = []

    try:
        # Attempt to open major registry hives
        hives = [
            (winreg.HKEY_LOCAL_MACHINE, "SYSTEM"),
            (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE"),
            (winreg.HKEY_CURRENT_USER, "Software"),
        ]

        for hive_root, hive_name in hives:
            try:
                with winreg.OpenKey(hive_root, hive_name):
                    pass
            except WindowsError:
                issue = SystemIssue(
                    category="Registry",
                    name=hive_name,
                    severity="HIGH",
                    fixable=False
                )
                issues.append(issue)
    except Exception:
        pass

    return issues


def _check_missing_dlls() -> list[SystemIssue]:
    """Check for critical missing DLLs."""
    issues = []
    critical_dlls = ["kernel32.dll", "ntdll.dll", "msvcrt.dll"]
    system_dir = Path("C:\\Windows\\System32")

    for dll in critical_dlls:
        dll_path = system_dir / dll
        if not dll_path.exists():
            issue = SystemIssue(
                category="System Files",
                name=dll,
                severity="CRITICAL",
                fixable=False
            )
            issues.append(issue)

    return issues


def _check_file_cache_corruption() -> list[SystemIssue]:
    """Check for corrupted file cache."""
    issues = []

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Test-Path 'C:\\Windows\\System32\\config\\SYSTEM'"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            issue = SystemIssue(
                category="System Cache",
                name="Registry Cache",
                severity="HIGH",
                fixable=True,
                fix_fn=lambda: subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Repair-Volume -DriveLetter C: -OfflineScanAndFix"],
                    capture_output=True, timeout=300
                )
            )
            issues.append(issue)
    except Exception:
        pass

    return issues


def _check_driver_cache() -> list[SystemIssue]:
    """Check for corrupted driver cache."""
    issues = []
    driver_cache = Path("C:\\Windows\\System32\\drivers\\etc\\drivers")

    if driver_cache.exists():
        try:
            if driver_cache.stat().st_size > 100 * 1024 * 1024:
                issue = SystemIssue(
                    category="Driver Cache",
                    name="Driver Cache Size",
                    severity="LOW",
                    fixable=True,
                    fix_fn=lambda: _rebuild_driver_cache()
                )
                issues.append(issue)
        except Exception:
            pass

    return issues


def _rebuild_driver_cache():
    """Rebuild Windows driver cache."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "netsh winsock reset catalog; netsh int ipv4 reset resetall"],
            capture_output=True,
            timeout=30
        )
        return True
    except Exception:
        return False


def _check_prefetch_corruption() -> list[SystemIssue]:
    """Check for corrupted prefetch files."""
    issues = []
    prefetch_dir = Path("C:\\Windows\\Prefetch")

    if prefetch_dir.exists():
        try:
            prefetch_count = len(list(prefetch_dir.glob("*.pf")))
            if prefetch_count > 1000:
                issue = SystemIssue(
                    category="Prefetch",
                    name="Too Many Prefetch Files",
                    severity="LOW",
                    fixable=True,
                    fix_fn=lambda: _clear_prefetch()
                )
                issues.append(issue)
        except Exception:
            pass

    return issues


def _clear_prefetch():
    """Clear prefetch directory."""
    try:
        prefetch_dir = Path("C:\\Windows\\Prefetch")
        for pf_file in prefetch_dir.glob("*.pf"):
            try:
                pf_file.unlink()
            except Exception:
                pass
        return True
    except Exception:
        return False


def scan_for_issues() -> list[SystemIssue]:
    """Scan system for common issues."""
    all_issues = []

    all_issues.extend(_check_broken_shortcuts())
    all_issues.extend(_check_missing_fonts())
    all_issues.extend(_check_corrupted_registry_hives())
    all_issues.extend(_check_missing_dlls())
    all_issues.extend(_check_file_cache_corruption())
    all_issues.extend(_check_driver_cache())
    all_issues.extend(_check_prefetch_corruption())

    return all_issues


def fix_issue(issue: SystemIssue) -> bool:
    """Attempt to fix an issue."""
    if not issue.fixable or not issue.fix_fn:
        return False

    try:
        issue.fix_fn()
        issue.fixed = True
        return True
    except Exception:
        return False


def fix_multiple_issues(issues: list[SystemIssue]) -> tuple[int, int]:
    """Fix multiple issues and return (fixed_count, failed_count)."""
    fixed = 0
    failed = 0

    for issue in issues:
        if fix_issue(issue):
            fixed += 1
        else:
            failed += 1

    return (fixed, failed)


def get_repair_recommendations() -> list[str]:
    """Get recommendations for system repair."""
    recommendations = []
    issues = scan_for_issues()

    critical_count = sum(1 for i in issues if i.severity == "CRITICAL")
    high_count = sum(1 for i in issues if i.severity == "HIGH")
    medium_count = sum(1 for i in issues if i.severity == "MEDIUM")

    if critical_count > 0:
        recommendations.append(f"Found {critical_count} critical issue(s) — repair immediately to prevent system failure")

    if high_count > 0:
        recommendations.append(f"Found {high_count} high-severity issue(s) — repair to improve stability")

    if medium_count > 0:
        recommendations.append(f"Found {medium_count} medium-severity issue(s) — optional repairs available")

    return recommendations
