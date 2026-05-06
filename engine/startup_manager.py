"""Startup manager — reads, disables and enables startup entries."""

import os
import winreg
from pathlib import Path
from dataclasses import dataclass, field


_RUN_KEYS = [
    (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run",     "HKCU Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run",     "HKLM Run"),
    (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM RunOnce"),
]

_STARTUP_FOLDERS = [
    Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup",
    Path(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"),
]


@dataclass
class StartupEntry:
    name: str
    command: str
    source: str         # "HKCU Run" / "HKLM Run" / "Startup Folder"
    enabled: bool = True
    hkey: int = 0
    reg_path: str = ""
    folder_path: str = ""
    impact: str = "Unknown"  # Low / Medium / High


# ── read ─────────────────────────────────────────────────────────────────────

def get_startup_entries() -> list[StartupEntry]:
    entries: list[StartupEntry] = []

    # Registry
    for hkey, reg_path, label in _RUN_KEYS:
        try:
            with winreg.OpenKey(hkey, reg_path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        entries.append(StartupEntry(
                            name=name,
                            command=value,
                            source=label,
                            enabled=True,
                            hkey=hkey,
                            reg_path=reg_path,
                        ))
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass

    # Startup folders
    for folder in _STARTUP_FOLDERS:
        if not folder.exists():
            continue
        for item in folder.iterdir():
            if item.suffix.lower() in (".lnk", ".exe", ".bat", ".cmd", ".vbs"):
                entries.append(StartupEntry(
                    name=item.stem,
                    command=str(item),
                    source="Startup Folder",
                    enabled=not item.stem.endswith(".disabled"),
                    folder_path=str(item),
                ))

    return entries


# ── disable / enable ─────────────────────────────────────────────────────────

def disable_registry_entry(entry: StartupEntry) -> bool:
    """Move the value to a 'disabled' backup key so it can be re-enabled."""
    disabled_path = entry.reg_path.replace("\\Run", "\\Run-Disabled")
    try:
        # Remove from Run
        with winreg.OpenKey(entry.hkey, entry.reg_path, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, entry.name)
        # Save to disabled backup key
        with winreg.CreateKey(entry.hkey, disabled_path) as key:
            winreg.SetValueEx(key, entry.name, 0, winreg.REG_SZ, entry.command)
        return True
    except OSError:
        return False


def enable_registry_entry(entry: StartupEntry) -> bool:
    disabled_path = entry.reg_path.replace("\\Run", "\\Run-Disabled")
    try:
        with winreg.OpenKey(entry.hkey, disabled_path, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, entry.name)
        with winreg.OpenKey(entry.hkey, entry.reg_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, entry.name, 0, winreg.REG_SZ, entry.command)
        return True
    except OSError:
        return False


def disable_folder_entry(entry: StartupEntry) -> bool:
    src = Path(entry.folder_path)
    dst = src.with_name(src.name + ".disabled")
    try:
        src.rename(dst)
        return True
    except OSError:
        return False


def enable_folder_entry(entry: StartupEntry) -> bool:
    src = Path(entry.folder_path)
    if src.name.endswith(".disabled"):
        dst = src.with_name(src.name[: -len(".disabled")])
        try:
            src.rename(dst)
            return True
        except OSError:
            return False
    return False


def toggle_entry(entry: StartupEntry) -> bool:
    if entry.source == "Startup Folder":
        ok = disable_folder_entry(entry) if entry.enabled else enable_folder_entry(entry)
    else:
        ok = disable_registry_entry(entry) if entry.enabled else enable_registry_entry(entry)
    if ok:
        entry.enabled = not entry.enabled
    return ok


# ── impact scoring ────────────────────────────────────────────────────────────

# Known high-impact startup programs (fragment matches, case-insensitive)
_HIGH_IMPACT = {
    "teams", "slack", "discord", "zoom", "skype", "dropbox", "onedrive",
    "googledrive", "googledrivefs", "spotify", "steam", "epicgames",
    "adobeupdater", "acrobat", "ccleaner", "malwarebytes", "avast",
    "bitdefender", "kaspersky", "mcafee", "norton", "nvidia", "amdradeon",
    "igfxtray", "jusched", "java", "itunes", "icloud", "vmware", "virtualbox",
}

_LOW_IMPACT = {
    "ctfmon", "rundll32", "conhost", "dllhost", "sihost", "taskhostw",
    "runtimebroker", "searchindexer", "winlogon", "svchost",
}


def assess_impact(entry: StartupEntry) -> str:
    """Return 'High', 'Medium', or 'Low' startup impact estimate."""
    cmd_lower = (entry.command + " " + entry.name).lower()

    for fragment in _HIGH_IMPACT:
        if fragment in cmd_lower:
            return "High"

    for fragment in _LOW_IMPACT:
        if fragment in cmd_lower:
            return "Low"

    # Heuristics: large executables or system locations = Medium
    exe_path = _extract_exe_path(entry.command)
    if exe_path:
        try:
            size = os.path.getsize(exe_path)
            if size > 50 * 1024 * 1024:  # > 50 MB
                return "High"
            if size > 5 * 1024 * 1024:   # > 5 MB
                return "Medium"
            return "Low"
        except OSError:
            pass

    return "Medium"


def _extract_exe_path(command: str) -> str:
    """Extract the executable path from a command string."""
    command = command.strip()
    if command.startswith('"'):
        end = command.find('"', 1)
        if end != -1:
            return command[1:end]
    return command.split()[0] if command.split() else ""


def get_startup_entries_with_impact() -> list[StartupEntry]:
    """Return startup entries with impact field populated."""
    entries = get_startup_entries()
    for e in entries:
        e.impact = assess_impact(e)
    return entries
