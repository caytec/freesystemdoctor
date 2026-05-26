"""System Repair — detect and fix common Windows issues automatically."""

import os
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


def _resolve_lnk_target(lnk_path: Path) -> str:
    """Resolve a .lnk shortcut's target path. Returns "" on failure."""
    try:
        # Use COM via WScript.Shell
        try:
            import win32com.client  # type: ignore
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortcut(str(lnk_path))
            return getattr(sc, "TargetPath", "") or ""
        except ImportError:
            pass

        # Fallback: parse .lnk binary directly
        return _parse_lnk_target(lnk_path)
    except Exception:
        return ""


def _parse_lnk_target(lnk_path: Path) -> str:
    """Minimal .lnk binary parser to extract LinkTargetIDList path."""
    try:
        with open(lnk_path, "rb") as f:
            data = f.read(8192)
        if len(data) < 0x4c or data[:4] != b"L\x00\x00\x00":
            return ""
        flags = int.from_bytes(data[20:24], "little")
        offset = 0x4c
        # Skip TargetIDList if present
        if flags & 0x01:
            id_list_size = int.from_bytes(data[offset:offset+2], "little")
            offset += 2 + id_list_size
        # Read LinkInfo
        if flags & 0x02 and offset + 4 < len(data):
            li_size = int.from_bytes(data[offset:offset+4], "little")
            li_header_size = int.from_bytes(data[offset+4:offset+8], "little")
            li_flags = int.from_bytes(data[offset+8:offset+12], "little")
            local_path_offset = int.from_bytes(data[offset+16:offset+20], "little")
            if li_flags & 0x01 and local_path_offset > 0:
                start = offset + local_path_offset
                end = data.find(b"\x00", start)
                if end > start:
                    return data[start:end].decode("mbcs", errors="ignore")
        return ""
    except Exception:
        return ""


def _check_broken_shortcuts() -> list[SystemIssue]:
    """Check for shortcuts whose target file/exe no longer exists.

    SAFETY: only flags shortcuts where we successfully resolved a target AND
    confirmed it doesn't exist. If we can't resolve the target, we leave it alone.
    """
    issues = []
    shortcut_locations = [
        Path.home() / "Desktop",
        Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path("C:/Users/Public/Desktop"),
        Path(os.environ.get("ProgramData", "C:/ProgramData")) /
            "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]

    seen = set()
    for location in shortcut_locations:
        if not location.exists():
            continue

        try:
            for lnk_file in location.rglob("*.lnk"):
                if str(lnk_file) in seen:
                    continue
                seen.add(str(lnk_file))
                try:
                    target = _resolve_lnk_target(lnk_file)
                    # Skip if we couldn't resolve — never delete what we don't understand
                    if not target:
                        continue
                    # Drop quotes / arguments (target sometimes has args)
                    target = target.strip().strip('"')
                    # Resolve env vars
                    target = os.path.expandvars(target)
                    if not target or target.lower().startswith(("http://", "https://")):
                        continue
                    target_path = Path(target)
                    if target_path.exists():
                        continue
                    # Definitely broken
                    issue = SystemIssue(
                        category="Shortcuts",
                        name=f"{lnk_file.stem}  →  {target_path.name}",
                        severity="LOW",
                        fixable=True,
                        fix_fn=lambda p=lnk_file: p.unlink(missing_ok=True),
                    )
                    issues.append(issue)
                except Exception:
                    pass
        except Exception:
            pass

    return issues


def _enumerate_installed_fonts() -> set[str]:
    """Lowercase set of font filenames installed in Windows Fonts."""
    out = set()
    fonts_dir = Path("C:/Windows/Fonts")
    if fonts_dir.exists():
        try:
            for f in fonts_dir.iterdir():
                if f.suffix.lower() in (".ttf", ".otf", ".ttc"):
                    out.add(f.name.lower())
        except Exception:
            pass
    # Also enumerate registry-installed fonts
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(k, i)
                    if isinstance(val, str):
                        out.add(Path(val).name.lower())
                    i += 1
                except OSError:
                    break
    except Exception:
        pass
    return out


def _check_missing_fonts() -> list[SystemIssue]:
    """Check for missing core system fonts (only Segoe UI is truly required)."""
    issues = []
    installed = _enumerate_installed_fonts()
    # Be conservative — only the absolute baseline
    truly_required = ["segoeui.ttf"]
    for font in truly_required:
        if font.lower() not in installed:
            issues.append(SystemIssue(
                category="Fonts", name=font, severity="MEDIUM", fixable=False))
    return issues


def _check_corrupted_registry_hives() -> list[SystemIssue]:
    """Check for corrupted Windows registry hives."""
    issues = []

    try:
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
                issues.append(SystemIssue(
                    category="Registry", name=hive_name,
                    severity="HIGH", fixable=False))
    except Exception:
        pass

    return issues


def _check_missing_dlls() -> list[SystemIssue]:
    """Check for critical missing DLLs."""
    issues = []
    critical_dlls = ["kernel32.dll", "ntdll.dll", "msvcrt.dll"]
    system_dir = Path("C:/Windows/System32")

    for dll in critical_dlls:
        dll_path = system_dir / dll
        if not dll_path.exists():
            issues.append(SystemIssue(
                category="System Files", name=dll,
                severity="CRITICAL", fixable=False))

    return issues


def _check_sfc_health() -> list[SystemIssue]:
    """Check Windows component store health using DISM and offer SFC repair."""
    issues = []
    try:
        r = subprocess.run(
            ["dism.exe", "/online", "/cleanup-image", "/checkhealth"],
            capture_output=True, text=True, timeout=60,
            creationflags=0x08000000,
        )
        if r.returncode == 0 and r.stdout:
            text = r.stdout.lower()
            if "repairable" in text or "component store is repairable" in text:
                issues.append(SystemIssue(
                    category="System Files",
                    name="Windows Component Store needs repair",
                    severity="HIGH",
                    fixable=True,
                    fix_fn=_dism_restore_health,
                ))
            elif "corruption detected" in text and "repairable" not in text:
                issues.append(SystemIssue(
                    category="System Files",
                    name="Component Store corruption (non-repairable)",
                    severity="CRITICAL",
                    fixable=False,
                ))
    except Exception:
        pass
    return issues


def _dism_restore_health() -> bool:
    try:
        r = subprocess.run(
            ["dism.exe", "/online", "/cleanup-image", "/restorehealth"],
            capture_output=True, timeout=900,
            creationflags=0x08000000,
        )
        return r.returncode == 0
    except Exception:
        return False


def _check_prefetch_corruption() -> list[SystemIssue]:
    """Check for excessive prefetch files."""
    issues = []
    prefetch_dir = Path("C:/Windows/Prefetch")

    if prefetch_dir.exists():
        try:
            prefetch_count = len(list(prefetch_dir.glob("*.pf")))
            if prefetch_count > 1000:
                issues.append(SystemIssue(
                    category="Prefetch",
                    name=f"Too many prefetch files ({prefetch_count})",
                    severity="LOW",
                    fixable=True,
                    fix_fn=_clear_prefetch,
                ))
        except Exception:
            pass

    return issues


def _clear_prefetch() -> bool:
    try:
        prefetch_dir = Path("C:/Windows/Prefetch")
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
    all_issues.extend(_check_sfc_health())
    all_issues.extend(_check_prefetch_corruption())
    return all_issues


def fix_issue(issue: SystemIssue) -> bool:
    if not issue.fixable or not issue.fix_fn:
        return False
    try:
        issue.fix_fn()
        issue.fixed = True
        return True
    except Exception:
        return False


def fix_multiple_issues(issues: list[SystemIssue]) -> tuple[int, int]:
    fixed = 0
    failed = 0
    for issue in issues:
        if fix_issue(issue):
            fixed += 1
        else:
            failed += 1
    return (fixed, failed)


def get_repair_recommendations() -> list[str]:
    recommendations = []
    issues = scan_for_issues()

    critical_count = sum(1 for i in issues if i.severity == "CRITICAL")
    high_count = sum(1 for i in issues if i.severity == "HIGH")
    medium_count = sum(1 for i in issues if i.severity == "MEDIUM")

    if critical_count > 0:
        recommendations.append(
            f"Found {critical_count} critical issue(s) — repair immediately")
    if high_count > 0:
        recommendations.append(
            f"Found {high_count} high-severity issue(s) — repair to improve stability")
    if medium_count > 0:
        recommendations.append(
            f"Found {medium_count} medium-severity issue(s) — optional repairs available")

    return recommendations
