"""Registry cleaner — scans for orphaned/invalid entries (read-only scan by default)."""

import os
import winreg
from dataclasses import dataclass


@dataclass
class RegIssue:
    category: str
    hive: str
    key_path: str
    value_name: str
    value_data: str
    reason: str
    safe_to_remove: bool = True


def _hive_str(hkey: int) -> str:
    return {
        winreg.HKEY_CURRENT_USER: "HKCU",
        winreg.HKEY_LOCAL_MACHINE: "HKLM",
    }.get(hkey, "?")


def _path_exists(path_str: str) -> bool:
    """Check if a file-system path referenced in a registry value exists."""
    if not path_str:
        return True
    # Strip quotes and arguments
    clean = path_str.strip().strip('"').split('"')[0].split(' ')[0]
    clean = os.path.expandvars(clean)
    if not clean:
        return True
    # Wildcards → assume ok
    if '*' in clean or '?' in clean:
        return True
    return os.path.exists(clean)


# ── scan functions ────────────────────────────────────────────────────────────

def _scan_run_keys() -> list[RegIssue]:
    issues = []
    run_keys = [
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    ]
    for hkey, path in run_keys:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        if not _path_exists(value):
                            issues.append(RegIssue(
                                category="Invalid Startup Entry",
                                hive=_hive_str(hkey),
                                key_path=path,
                                value_name=name,
                                value_data=value,
                                reason="Executable not found",
                            ))
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
    return issues


def _scan_uninstall_keys() -> list[RegIssue]:
    issues = []
    uninst_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hkey, path in uninst_keys:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_name) as sub:
                            try:
                                install_loc, _ = winreg.QueryValueEx(sub, "InstallLocation")
                                if install_loc and not os.path.exists(install_loc):
                                    try:
                                        display, _ = winreg.QueryValueEx(sub, "DisplayName")
                                    except OSError:
                                        display = sub_name
                                    issues.append(RegIssue(
                                        category="Orphaned Uninstall Entry",
                                        hive=_hive_str(hkey),
                                        key_path=f"{path}\\{sub_name}",
                                        value_name="InstallLocation",
                                        value_data=install_loc,
                                        reason=f"Install folder missing ({display})",
                                        safe_to_remove=False,  # conservative
                                    ))
                            except OSError:
                                pass
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
    return issues


def _scan_shared_dlls() -> list[RegIssue]:
    issues = []
    try:
        path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\SharedDLLs"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ) as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    if not os.path.exists(os.path.expandvars(name)):
                        issues.append(RegIssue(
                            category="Missing Shared DLL",
                            hive="HKLM",
                            key_path=path,
                            value_name=name,
                            value_data=str(value),
                            reason="DLL file not found on disk",
                        ))
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    return issues


# ── public API ────────────────────────────────────────────────────────────────

def scan_registry(progress_cb=None) -> list[RegIssue]:
    all_issues: list[RegIssue] = []

    if progress_cb:
        progress_cb("Scanning startup keys...")
    all_issues.extend(_scan_run_keys())

    if progress_cb:
        progress_cb("Scanning uninstall entries...")
    all_issues.extend(_scan_uninstall_keys())

    if progress_cb:
        progress_cb("Scanning shared DLLs...")
    all_issues.extend(_scan_shared_dlls())

    return all_issues


def remove_issue(issue: RegIssue) -> bool:
    """Delete the registry value identified by the issue. Use with care."""
    hkey_map = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }
    hkey = hkey_map.get(issue.hive)
    if hkey is None:
        return False
    try:
        with winreg.OpenKey(hkey, issue.key_path, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, issue.value_name)
        return True
    except OSError:
        return False
