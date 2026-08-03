"""
debloat.py — remove preinstalled Windows Store (UWP/Appx) apps.

The classic uninstaller only sees Win32 programs in the registry, so Xbox, Bing
News/Weather, Solitaire and friends were previously untouchable. This module
covers that gap — the single biggest reason people reach for a "debloater".

SAFETY FIRST
  • PROTECTED packages (runtimes, Store infrastructure, security, sign-in,
    lock screen…) are NEVER offered and are refused even if requested directly —
    removing them can break Windows.
  • Only packages we can name and explain are marked "recommended".
  • Removal is per-user (Remove-AppxPackage) and most apps can be reinstalled
    from the Microsoft Store afterwards.
"""

from __future__ import annotations

import json
import subprocess
from typing import Callable, Optional

_NO_WINDOW = 0x08000000

# ── Never remove: breaks Windows or core UX ──────────────────────────────────
PROTECTED_PREFIXES: tuple[str, ...] = (
    "Microsoft.NET.Native",           # .NET runtimes for Store apps
    "Microsoft.VCLibs",               # C++ runtimes
    "Microsoft.UI.Xaml",              # XAML framework
    "Microsoft.WindowsStore",         # the Store itself
    "Microsoft.StorePurchaseApp",
    "Microsoft.DesktopAppInstaller",  # winget lives here
    "Microsoft.SecHealthUI",          # Windows Security UI
    "Microsoft.AccountsControl",      # sign-in dialogs
    "Microsoft.AAD.BrokerPlugin",     # work/school sign-in
    "Microsoft.CredDialogHost",
    "Microsoft.BioEnrollment",        # Windows Hello
    "Microsoft.LockApp",              # lock screen
    "Microsoft.Windows.",             # ShellExperienceHost, StartMenu, Search…
    "Microsoft.MicrosoftEdge",        # removing breaks WebView-dependent apps
    "Microsoft.Services.Store",
    "Microsoft.AsyncTextService",     # typing / IME
    "Microsoft.ECApp",
    "Microsoft.HEIFImageExtension",   # image codecs
    "Microsoft.WebpImageExtension",
    "Microsoft.VP9VideoExtensions",
    "Microsoft.WebMediaExtensions",
    "MicrosoftWindows.",
    "Windows.",
    "c5e2524a", "1527c705", "E2A4F912", "F46D4000",   # inbox system packages
)

# ── Known bloat: safe to remove, with a plain-language explanation ───────────
KNOWN_BLOAT: dict[str, tuple[str, str]] = {
    "Microsoft.BingNews":                  ("News", "Microsoft News feed app"),
    "Microsoft.BingWeather":               ("Weather", "Weather app"),
    "Microsoft.BingSearch":                ("Bing Search", "Bing web search in Start"),
    "Microsoft.GamingApp":                 ("Xbox", "Xbox app & Game Pass"),
    "Microsoft.XboxGamingOverlay":         ("Xbox Game Bar", "Win+G overlay"),
    "Microsoft.XboxGameOverlay":           ("Xbox Game Overlay", "Legacy game overlay"),
    "Microsoft.XboxIdentityProvider":      ("Xbox Sign-in", "Xbox account helper"),
    "Microsoft.XboxSpeechToTextOverlay":   ("Xbox Speech", "Xbox speech-to-text"),
    "Microsoft.Xbox.TCUI":                 ("Xbox UI", "Xbox shared UI"),
    "Microsoft.MicrosoftSolitaireCollection": ("Solitaire", "Card games (with ads)"),
    "Microsoft.MicrosoftOfficeHub":        ("Office Hub", "Office promo/launcher tile"),
    "Microsoft.OutlookForWindows":         ("New Outlook", "New Outlook mail app"),
    "Microsoft.Todos":                     ("To Do", "Microsoft To Do"),
    "Microsoft.People":                    ("People", "Contacts app"),
    "Microsoft.GetHelp":                   ("Get Help", "Microsoft support app"),
    "Microsoft.Getstarted":                ("Tips", "Windows tips / get started"),
    "Microsoft.ZuneMusic":                 ("Media Player", "Groove/Media Player"),
    "Microsoft.ZuneVideo":                 ("Movies & TV", "Films & TV app"),
    "Microsoft.WindowsMaps":               ("Maps", "Windows Maps"),
    "Microsoft.WindowsFeedbackHub":        ("Feedback Hub", "Send feedback to Microsoft"),
    "Microsoft.MixedReality.Portal":       ("Mixed Reality", "VR portal (rarely used)"),
    "Microsoft.SkypeApp":                  ("Skype", "Preinstalled Skype"),
    "Microsoft.YourPhone":                 ("Phone Link", "Phone companion"),
    "Microsoft.PowerAutomateDesktop":      ("Power Automate", "Desktop automation"),
    "Microsoft.MicrosoftStickyNotes":      ("Sticky Notes", "Desktop notes"),
    "Microsoft.Paint":                     ("Paint", "Modern Paint app"),
    "Microsoft.ScreenSketch":              ("Snipping Tool", "Screenshot tool"),
    "Microsoft.549981C3F5F10":             ("Cortana", "Cortana assistant"),
    "Clipchamp.Clipchamp":                 ("Clipchamp", "Video editor"),
    "Microsoft.Copilot":                   ("Copilot", "Windows Copilot AI assistant"),
    "MicrosoftTeams":                      ("Teams (personal)", "Chat / Teams consumer"),
    "Microsoft.Wallet":                    ("Wallet", "Microsoft Wallet"),
    "Microsoft.3DBuilder":                 ("3D Builder", "3D modelling app"),
    "Microsoft.Print3D":                   ("Print 3D", "3D printing app"),
    "Microsoft.OneConnect":                ("Mobile Plans", "Paid Wi-Fi / mobile plans"),
}


def is_protected(name: str) -> bool:
    """True if the package must never be removed."""
    return any(name.startswith(p) for p in PROTECTED_PREFIXES)


def _ps(script: str, timeout: int = 120) -> tuple[int, str]:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                           capture_output=True, text=True, timeout=timeout,
                           creationflags=_NO_WINDOW)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as exc:
        return 1, str(exc)


def list_removable_apps(include_unknown: bool = True) -> list[dict]:
    """Enumerate installed Store/UWP apps that may be removed.

    Returns a list of dicts:
        {name, full_name, friendly, description, recommended, publisher}
    ``recommended`` marks packages from KNOWN_BLOAT — the ones we can explain.
    Protected system packages are never returned.
    """
    script = (
        "Get-AppxPackage | "
        "Select-Object Name,PackageFullName,Publisher,NonRemovable | "
        "ConvertTo-Json -Compress -Depth 2"
    )
    rc, out = _ps(script, timeout=120)
    if rc != 0 or not out.strip():
        return []

    try:
        start = out.find("[")
        if start == -1:
            start = out.find("{")
        data = json.loads(out[start:]) if start != -1 else []
    except Exception:
        return []
    if isinstance(data, dict):
        data = [data]

    apps: list[dict] = []
    seen: set[str] = set()
    for pkg in data:
        name = (pkg.get("Name") or "").strip()
        full = (pkg.get("PackageFullName") or "").strip()
        if not name or not full or name in seen:
            continue
        if pkg.get("NonRemovable") is True or is_protected(name):
            continue
        seen.add(name)
        known = KNOWN_BLOAT.get(name)
        apps.append({
            "name": name,
            "full_name": full,
            "friendly": known[0] if known else name,
            "description": known[1] if known else "Third-party or unrecognised app",
            "recommended": known is not None,
            "publisher": (pkg.get("Publisher") or "")[:60],
        })

    if not include_unknown:
        apps = [a for a in apps if a["recommended"]]
    apps.sort(key=lambda a: (not a["recommended"], a["friendly"].lower()))
    return apps


def remove_app(name: str, full_name: str = "") -> tuple[bool, str]:
    """Remove one Store/UWP app for the current user.

    Refuses protected packages even when called directly.
    """
    if not name or is_protected(name):
        return False, f"{name or 'package'} is protected and cannot be removed."

    target = full_name or name
    script = (
        f"$ErrorActionPreference='Stop'; "
        f"Get-AppxPackage -Name '{name}' | Remove-AppxPackage -ErrorAction Stop"
        if not full_name else
        f"$ErrorActionPreference='Stop'; "
        f"Remove-AppxPackage -Package '{full_name}' -ErrorAction Stop"
    )
    rc, out = _ps(script, timeout=180)
    if rc == 0:
        return True, f"{name} removed."
    msg = (out or "").strip().splitlines()
    return False, (msg[-1][:200] if msg else f"Could not remove {name}.")


def remove_apps(names: list[tuple[str, str]],
                progress_cb: Optional[Callable[[str, int], None]] = None) -> dict:
    """Remove several apps. names = [(name, full_name), …].

    Returns {removed, failed, details:[{name, ok, msg}]}.
    """
    details = []
    removed = failed = 0
    total = max(1, len(names))
    for i, (name, full) in enumerate(names):
        if progress_cb:
            try:
                progress_cb(f"Removing {name}…", int(i / total * 100))
            except Exception:
                pass
        ok, msg = remove_app(name, full)
        details.append({"name": name, "ok": ok, "msg": msg})
        removed += 1 if ok else 0
        failed += 0 if ok else 1
    if progress_cb:
        try:
            progress_cb("Done", 100)
        except Exception:
            pass
    return {"removed": removed, "failed": failed, "details": details}
