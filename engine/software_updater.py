"""Software Updater — detect installed software and check for updates via winget + known DB."""

import subprocess
import winreg
import re
import webbrowser
import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

# Setup logging for background operations
_LOG_DIR = Path(os.getenv("TEMP", "C:\\Temp")) / "FreeSystemDoctor"
_LOG_DIR.mkdir(exist_ok=True, parents=True)
_LOG_FILE = _LOG_DIR / "software_updater.log"

logging.basicConfig(
    filename=str(_LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


@dataclass
class SoftwareEntry:
    name: str
    installed_version: str
    latest_version: str = ""
    winget_id: str = ""
    download_url: str = ""
    publisher: str = ""
    status: str = "unknown"   # outdated | up_to_date | unknown


# ── Known versions database ───────────────────────────────────────────────────

KNOWN_APPS: dict[str, dict] = {
    "google chrome":          {"latest": "136.0",   "winget_id": "Google.Chrome",            "url": "https://www.google.com/chrome/"},
    "mozilla firefox":        {"latest": "138.0",   "winget_id": "Mozilla.Firefox",          "url": "https://www.mozilla.org/firefox/"},
    "microsoft edge":         {"latest": "136.0",   "winget_id": "Microsoft.Edge",           "url": "https://www.microsoft.com/edge"},
    "vlc":                    {"latest": "3.0.21",  "winget_id": "VideoLAN.VLC",             "url": "https://www.videolan.org/vlc/"},
    "7-zip":                  {"latest": "24.09",   "winget_id": "7zip.7zip",               "url": "https://www.7-zip.org/"},
    "notepad++":              {"latest": "8.7.5",   "winget_id": "Notepad++.Notepad++",      "url": "https://notepad-plus-plus.org/"},
    "python":                 {"latest": "3.13.0",  "winget_id": "Python.Python.3",          "url": "https://www.python.org/downloads/"},
    "git":                    {"latest": "2.47.0",  "winget_id": "Git.Git",                  "url": "https://git-scm.com/"},
    "node.js":                {"latest": "22.12.0", "winget_id": "OpenJS.NodeJS.LTS",        "url": "https://nodejs.org/"},
    "winrar":                 {"latest": "7.10",    "winget_id": "RARLab.WinRAR",            "url": "https://www.rarlab.com/"},
    "adobe acrobat reader":   {"latest": "25.001",  "winget_id": "Adobe.Acrobat.Reader.64-bit","url": "https://get.adobe.com/reader/"},
    "zoom":                   {"latest": "6.3.0",   "winget_id": "Zoom.Zoom",               "url": "https://zoom.us/download"},
    "spotify":                {"latest": "1.2.50",  "winget_id": "Spotify.Spotify",          "url": "https://www.spotify.com/download/"},
    "discord":                {"latest": "1.0.9173","winget_id": "Discord.Discord",          "url": "https://discord.com/download"},
    "steam":                  {"latest": "current", "winget_id": "Valve.Steam",              "url": "https://store.steampowered.com/about/"},
    "obs studio":             {"latest": "31.0.0",  "winget_id": "OBSProject.OBSStudio",    "url": "https://obsproject.com/"},
    "gimp":                   {"latest": "2.10.38", "winget_id": "GIMP.GIMP",               "url": "https://www.gimp.org/downloads/"},
    "putty":                  {"latest": "0.82",    "winget_id": "PuTTY.PuTTY",             "url": "https://www.putty.org/"},
    "winpcap":                {"latest": "4.1.3",   "winget_id": "",                         "url": "https://www.winpcap.org/"},
    "teamviewer":             {"latest": "15.0",    "winget_id": "TeamViewer.TeamViewer",    "url": "https://www.teamviewer.com/"},
    "anydesk":                {"latest": "8.0",     "winget_id": "AnyDesk.AnyDesk",         "url": "https://anydesk.com/"},
    "audacity":               {"latest": "3.7.1",   "winget_id": "Audacity.Audacity",       "url": "https://www.audacityteam.org/"},
    "handbrake":              {"latest": "1.9.0",   "winget_id": "HandBrake.HandBrake",     "url": "https://handbrake.fr/"},
    "libreoffice":            {"latest": "24.8.4",  "winget_id": "TheDocumentFoundation.LibreOffice","url": "https://www.libreoffice.org/"},
    "microsoft teams":        {"latest": "25.0",    "winget_id": "Microsoft.Teams",         "url": "https://teams.microsoft.com/"},
    "skype":                  {"latest": "8.0",     "winget_id": "Microsoft.Skype",         "url": "https://www.skype.com/"},
    "slack":                  {"latest": "4.42",    "winget_id": "SlackTechnologies.Slack",  "url": "https://slack.com/downloads/"},
    "paint.net":              {"latest": "5.1",     "winget_id": "dotPDN.PaintDotNet",       "url": "https://www.getpaint.net/"},
    "inkscape":               {"latest": "1.4",     "winget_id": "Inkscape.Inkscape",       "url": "https://inkscape.org/"},
    "blender":                {"latest": "4.3",     "winget_id": "BlenderFoundation.Blender","url": "https://www.blender.org/"},
    "winmerge":               {"latest": "2.16.44", "winget_id": "WinMerge.WinMerge",      "url": "https://winmerge.org/"},
    "cpu-z":                  {"latest": "2.12",    "winget_id": "CPUID.CPU-Z",             "url": "https://www.cpuid.com/softwares/cpu-z.html"},
    "hwmonitor":              {"latest": "1.56",    "winget_id": "CPUID.HWMonitor",         "url": "https://www.cpuid.com/softwares/hwmonitor.html"},
    "malwarebytes":           {"latest": "5.2",     "winget_id": "Malwarebytes.Malwarebytes","url": "https://www.malwarebytes.com/"},
    "sharex":                 {"latest": "16.1",    "winget_id": "ShareX.ShareX",           "url": "https://getsharex.com/"},
    # Extended database
    "brave":                  {"latest": "1.75",    "winget_id": "Brave.Brave",             "url": "https://brave.com/download/"},
    "opera":                  {"latest": "117.0",   "winget_id": "Opera.Opera",             "url": "https://www.opera.com/"},
    "vivaldi":                {"latest": "7.2",     "winget_id": "VivaldiTechnologies.Vivaldi","url": "https://vivaldi.com/"},
    "thunderbird":            {"latest": "128.0",   "winget_id": "Mozilla.Thunderbird",     "url": "https://www.thunderbird.net/"},
    "signal":                 {"latest": "7.45",    "winget_id": "OpenWhisperSystems.Signal","url": "https://signal.org/"},
    "telegram":               {"latest": "5.12",    "winget_id": "Telegram.TelegramDesktop","url": "https://telegram.org/"},
    "whatsapp":               {"latest": "2.2450",  "winget_id": "WhatsApp.WhatsApp",       "url": "https://www.whatsapp.com/download/"},
    "microsoft office":       {"latest": "current", "winget_id": "Microsoft.Office",        "url": "https://office.com/"},
    "onedrive":               {"latest": "current", "winget_id": "Microsoft.OneDrive",      "url": "https://onedrive.com/"},
    "dropbox":                {"latest": "current", "winget_id": "Dropbox.Dropbox",         "url": "https://www.dropbox.com/"},
    "google drive":           {"latest": "current", "winget_id": "Google.GoogleDrive",      "url": "https://drive.google.com/"},
    "winzip":                 {"latest": "28.0",    "winget_id": "Corel.WinZip",            "url": "https://www.winzip.com/"},
    "powershell":             {"latest": "7.4",     "winget_id": "Microsoft.PowerShell",    "url": "https://github.com/PowerShell/PowerShell"},
    "windows terminal":       {"latest": "1.21",    "winget_id": "Microsoft.WindowsTerminal","url": "https://aka.ms/terminal"},
    "visual studio code":     {"latest": "1.97",    "winget_id": "Microsoft.VisualStudioCode","url": "https://code.visualstudio.com/"},
    "pycharm":                {"latest": "2024.3",  "winget_id": "JetBrains.PyCharm.Community","url": "https://www.jetbrains.com/pycharm/"},
    "intellij idea":          {"latest": "2024.3",  "winget_id": "JetBrains.IntelliJIDEA.Community","url": "https://www.jetbrains.com/idea/"},
    "docker desktop":         {"latest": "4.37",    "winget_id": "Docker.DockerDesktop",    "url": "https://www.docker.com/products/docker-desktop/"},
    "postman":                {"latest": "11.0",    "winget_id": "Postman.Postman",         "url": "https://www.postman.com/"},
    "filezilla":              {"latest": "3.68",    "winget_id": "TimKosse.FileZilla.Client","url": "https://filezilla-project.org/"},
    "winscp":                 {"latest": "6.3",     "winget_id": "WinSCP.WinSCP",           "url": "https://winscp.net/"},
    "itunes":                 {"latest": "12.13",   "winget_id": "Apple.iTunes",            "url": "https://www.apple.com/itunes/"},
    "icloud":                 {"latest": "7.21",    "winget_id": "Apple.iCloud",            "url": "https://support.apple.com/icloud"},
    "avast":                  {"latest": "current", "winget_id": "AVAST.AVASTFreeAntivirus","url": "https://www.avast.com/"},
    "avg":                    {"latest": "current", "winget_id": "AVG.AVGAntiVirus",        "url": "https://www.avg.com/"},
    "kaspersky":              {"latest": "current", "winget_id": "",                        "url": "https://www.kaspersky.com/"},
    "nvidia geforce experience":{"latest": "current","winget_id": "Nvidia.GeForceExperience","url": "https://www.nvidia.com/geforce/geforce-experience/"},
    "msi afterburner":        {"latest": "4.6.5",  "winget_id": "MSI.Afterburner",         "url": "https://www.msi.com/Landing/afterburner/"},
    "ccleaner":               {"latest": "6.33",   "winget_id": "Piriform.CCleaner",       "url": "https://www.ccleaner.com/"},
    "crystaldiskinfo":        {"latest": "9.4",    "winget_id": "CrystalDewWorld.CrystalDiskInfo","url": "https://crystalmark.info/"},
    "crystaldiskmark":        {"latest": "8.0",    "winget_id": "CrystalDewWorld.CrystalDiskMark","url": "https://crystalmark.info/"},
    "rufus":                  {"latest": "4.6",    "winget_id": "Rufus.Rufus",             "url": "https://rufus.ie/"},
    "etcher":                 {"latest": "2.1",    "winget_id": "Balena.Etcher",           "url": "https://etcher.balena.io/"},
    "virtualbox":             {"latest": "7.1",    "winget_id": "Oracle.VirtualBox",       "url": "https://www.virtualbox.org/"},
    "qbittorrent":            {"latest": "5.0",    "winget_id": "qBittorrent.qBittorrent", "url": "https://www.qbittorrent.org/"},
    "stremio":                {"latest": "4.4",    "winget_id": "Stremio.Stremio",         "url": "https://www.stremio.com/"},
    "mpv":                    {"latest": "0.39",   "winget_id": "mpv-player.mpv",          "url": "https://mpv.io/"},
    "foobar2000":             {"latest": "2.1",    "winget_id": "PeterPawlowski.foobar2000","url": "https://www.foobar2000.org/"},
    "irfanview":              {"latest": "4.70",   "winget_id": "IrfanSkiljan.IrfanView",  "url": "https://www.irfanview.com/"},
}


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.lower().strip()
                  .replace("(64-bit)", "").replace("(32-bit)", "")
                  .replace(" for windows", "").replace(" x64", "")
                  .replace(" x86", ""))


def match_known(name: str) -> dict | None:
    n = _normalize(name)
    # Exact
    if n in KNOWN_APPS:
        return KNOWN_APPS[n]
    # Substring
    for key, val in KNOWN_APPS.items():
        if key in n or n in key:
            return val
    return None


# ── version comparison ────────────────────────────────────────────────────────

def _parse_ver(v: str) -> list[int]:
    parts = re.findall(r"\d+", v)
    return [int(x) for x in parts[:4]] if parts else [0]


def version_lt(v1: str, v2: str) -> bool:
    """Returns True if v1 < v2 (installed < latest = outdated)."""
    if not v1 or not v2 or v2.lower() in ("current", "latest", ""):
        return False
    a, b = _parse_ver(v1), _parse_ver(v2)
    # Compare to depth of shorter
    depth = min(len(a), len(b), 2)  # only first 2 segments for accuracy
    return a[:depth] < b[:depth]


# ── winget integration ────────────────────────────────────────────────────────

def check_winget() -> bool:
    """Check if winget is available with error logging."""
    try:
        r = subprocess.run(
            ["winget", "--version"],
            capture_output=True,
            timeout=5,
            encoding="utf-8",
            errors="replace"
        )
        ok = r.returncode == 0
        if ok:
            logging.info(f"winget available: {r.stdout.strip()}")
        else:
            logging.warning(f"winget check failed: {r.stderr.strip()}")
        return ok
    except FileNotFoundError:
        logging.warning("winget not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        logging.warning("winget --version timed out")
        return False
    except Exception as e:
        logging.error(f"check_winget error: {e}")
        return False


def get_winget_upgrades(progress_cb: Callable = None) -> dict[str, dict]:
    """
    Run winget upgrade, parse output.
    Returns dict: {normalized_name: {available, id}}
    Handles errors gracefully with logging.
    """
    if progress_cb:
        try:
            progress_cb("Running winget upgrade scan...")
        except Exception as e:
            logging.warning(f"progress_cb error: {e}")
    try:
        logging.info("Starting winget upgrade scan")
        r = subprocess.run(
            ["winget", "upgrade", "--include-unknown", "--accept-source-agreements"],
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace"
        )
        if r.returncode != 0:
            logging.warning(f"winget upgrade exit code {r.returncode}: {r.stderr[:200]}")
        result = _parse_winget_output(r.stdout)
        logging.info(f"winget scan found {len(result)} upgradeable packages")
        return result
    except subprocess.TimeoutExpired:
        logging.error("winget upgrade timed out (60s)")
        return {}
    except FileNotFoundError:
        logging.error("winget executable not found")
        return {}
    except Exception as e:
        logging.error(f"get_winget_upgrades error: {type(e).__name__}: {e}")
        return {}


def _parse_winget_output(text: str) -> dict[str, dict]:
    results = {}
    lines = text.splitlines()
    header_idx = None
    col_positions = {}

    for i, line in enumerate(lines):
        if re.search(r"\bName\b.*\bId\b.*\bVersion\b.*\bAvailable\b", line, re.I):
            header_idx = i
            # Find column starts
            for col in ("Name", "Id", "Version", "Available"):
                m = re.search(col, line, re.I)
                if m:
                    col_positions[col] = m.start()
            break

    if header_idx is None:
        return results

    # Skip separator line
    data_start = header_idx + 2
    for line in lines[data_start:]:
        if not line.strip() or line.strip().startswith("-"):
            continue
        try:
            name_end = col_positions.get("Id", 30)
            id_end   = col_positions.get("Version", 60)
            ver_end  = col_positions.get("Available", 90)
            avail_end = col_positions.get("Source", 120)

            name      = line[:name_end].strip()
            pkg_id    = line[name_end:id_end].strip()
            # version   = line[id_end:ver_end].strip()
            available = line[ver_end:avail_end].strip()

            if name and available and available not in ("", "-"):
                results[_normalize(name)] = {
                    "available": available,
                    "winget_id": pkg_id,
                }
        except Exception:
            continue
    return results


# ── registry software list ────────────────────────────────────────────────────

def get_installed_software() -> list[dict]:
    """Scan registry for installed software with comprehensive error handling."""
    programs = []
    paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    seen: set[str] = set()

    for hkey, path in paths:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, sub) as sk:
                                def qv(n, default=""):
                                    try:
                                        v, _ = winreg.QueryValueEx(sk, n)
                                        return str(v).strip()
                                    except (OSError, TypeError):
                                        return default

                                name = qv("DisplayName")
                                if not name or name in seen:
                                    i += 1
                                    continue
                                # Skip system components and updates
                                if qv("SystemComponent", "0") == "1":
                                    i += 1
                                    continue
                                if name.startswith("KB") and len(name) < 12:
                                    i += 1
                                    continue
                                seen.add(name)
                                programs.append({
                                    "name":      name,
                                    "version":   qv("DisplayVersion"),
                                    "publisher": qv("Publisher"),
                                })
                        except (OSError, Exception) as e:
                            logging.debug(f"Error reading subkey {sub}: {e}")
                        i += 1
                    except OSError:
                        break
        except OSError as e:
            logging.debug(f"Cannot access registry path {path}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error scanning {path}: {type(e).__name__}: {e}")

    logging.info(f"Found {len(programs)} installed programs")
    return sorted(programs, key=lambda x: x["name"].lower())


# ── main API ──────────────────────────────────────────────────────────────────

def get_installed_with_updates(progress_cb: Callable = None) -> list[SoftwareEntry]:
    """
    Get all installed software with update information.
    Handles all errors gracefully and logs them.
    """
    try:
        if progress_cb:
            try:
                progress_cb("Reading installed software...", 0)
            except Exception as e:
                logging.warning(f"progress_cb error: {e}")

        installed = get_installed_software()
        logging.info(f"Scanning {len(installed)} installed programs for updates")

        winget_ok = check_winget()
        winget_data: dict[str, dict] = {}
        if winget_ok:
            def wg_cb(msg):
                if progress_cb:
                    try:
                        progress_cb(msg, 30)
                    except Exception as e:
                        logging.warning(f"progress_cb error: {e}")
            winget_data = get_winget_upgrades(progress_cb=wg_cb)

        entries: list[SoftwareEntry] = []
        total = len(installed)
        for idx, prog in enumerate(installed):
            try:
                if progress_cb and idx % 20 == 0:
                    try:
                        pct = 30 + int(idx / max(total, 1) * 70)
                        progress_cb(f"Checking {prog['name'][:40]}...", pct)
                    except Exception as e:
                        logging.warning(f"progress_cb error: {e}")

                name_n = _normalize(prog["name"])
                entry = SoftwareEntry(
                    name=prog["name"],
                    installed_version=prog["version"],
                    publisher=prog["publisher"],
                )

                # Try winget match
                wg = winget_data.get(name_n)
                if not wg:
                    for k, v in winget_data.items():
                        if k in name_n or name_n in k:
                            wg = v
                            break

                if wg:
                    entry.latest_version = wg["available"]
                    entry.winget_id = wg.get("winget_id", "")
                    entry.status = "outdated"
                else:
                    # Try known apps DB
                    known = match_known(prog["name"])
                    if known:
                        entry.latest_version = known["latest"]
                        entry.winget_id = known.get("winget_id", "")
                        entry.download_url = known.get("url", "")
                        if known["latest"].lower() in ("current", "latest"):
                            entry.status = "up_to_date"
                        elif version_lt(prog["version"], known["latest"]):
                            entry.status = "outdated"
                        elif prog["version"]:
                            entry.status = "up_to_date"
                        else:
                            entry.status = "unknown"
                    else:
                        entry.status = "unknown"

                entries.append(entry)
            except Exception as e:
                logging.error(f"Error processing {prog.get('name', 'unknown')}: {type(e).__name__}: {e}")
                continue

        # Sort: outdated first, then unknown, then up_to_date
        order = {"outdated": 0, "unknown": 1, "up_to_date": 2}
        entries.sort(key=lambda e: (order.get(e.status, 1), e.name.lower()))
        logging.info(f"Scan complete: {len(entries)} programs analyzed")
        return entries
    except Exception as e:
        logging.error(f"get_installed_with_updates fatal error: {type(e).__name__}: {e}")
        return []


def get_outdated_count() -> int:
    """Quick scan — returns number of outdated apps."""
    entries = get_installed_with_updates()
    return sum(1 for e in entries if e.status == "outdated")


# ── Chocolatey integration ────────────────────────────────────────────────────

def check_chocolatey() -> bool:
    """Check if Chocolatey (choco) is available."""
    try:
        r = subprocess.run(["choco", "--version"], capture_output=True, timeout=5,
                           encoding="utf-8", errors="replace")
        return r.returncode == 0
    except Exception:
        return False


def get_choco_outdated() -> list[dict]:
    """Run choco outdated and return list of outdated packages."""
    try:
        r = subprocess.run(
            ["choco", "outdated", "--no-color", "--no-progress"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace"
        )
        results = []
        for line in r.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 3 and parts[0].strip() and parts[0].strip() != "Output":
                name = parts[0].strip()
                current = parts[1].strip() if len(parts) > 1 else ""
                available = parts[2].strip() if len(parts) > 2 else ""
                if name and available and available != current:
                    results.append({
                        "name": name,
                        "installed_version": current,
                        "latest_version": available,
                        "source": "chocolatey",
                    })
        return results
    except Exception:
        return []


def update_choco_package(package_name: str) -> bool:
    """Update a single Chocolatey package."""
    try:
        subprocess.Popen(
            ["choco", "upgrade", package_name, "-y", "--no-progress"],
            creationflags=0x08000000,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def get_all_outdated_merged() -> list[SoftwareEntry]:
    """Get outdated apps from both winget and Chocolatey, merged and deduplicated."""
    entries = get_installed_with_updates()
    outdated = [e for e in entries if e.status == "outdated"]

    if check_chocolatey():
        choco_pkgs = get_choco_outdated()
        existing_names = {_normalize(e.name) for e in outdated}
        for pkg in choco_pkgs:
            norm = _normalize(pkg["name"])
            if norm not in existing_names:
                outdated.append(SoftwareEntry(
                    name=pkg["name"],
                    installed_version=pkg["installed_version"],
                    latest_version=pkg["latest_version"],
                    winget_id="",
                    status="outdated",
                ))

    return outdated


def launch_update(entry: SoftwareEntry) -> bool:
    """Launch update for a software entry with comprehensive error handling."""
    try:
        if entry.winget_id:
            try:
                logging.info(f"Starting winget update for {entry.name} ({entry.winget_id})")
                subprocess.Popen(
                    ["winget", "upgrade", "--id", entry.winget_id,
                     "--silent", "--accept-source-agreements", "--accept-package-agreements"],
                    creationflags=0x08000000,  # CREATE_NO_WINDOW
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
                logging.info(f"Update launched for {entry.name}")
                return True
            except FileNotFoundError:
                logging.warning(f"winget not found for updating {entry.name}")
            except Exception as e:
                logging.error(f"winget update failed for {entry.name}: {type(e).__name__}: {e}")

        if entry.download_url:
            try:
                logging.info(f"Opening download URL for {entry.name}: {entry.download_url}")
                webbrowser.open(entry.download_url)
                return True
            except Exception as e:
                logging.error(f"Failed to open browser for {entry.name}: {type(e).__name__}: {e}")
                return False

        logging.warning(f"No update method available for {entry.name}")
        return False
    except Exception as e:
        logging.error(f"launch_update fatal error for {entry.name}: {type(e).__name__}: {e}")
        return False
