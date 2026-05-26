"""
dependency_installer.py — automatyczna instalacja zależności przy starcie.

Zarządza opcjonalnymi komponentami, które rozszerzają funkcjonalność:

1. LibreHardwareMonitor — wymagany do CPU/disk temperature monitoring
   Download: GitHub Releases (MIT license)
   Install: %APPDATA%\\FreeSystemDoctor\\LHM\\
   Optional: service mode (requires admin)

2. nvidia-smi check — w PATH (dostarczany ze sterownikami NVIDIA, samo działa)

3. DISM availability — system component, zawsze dostępne

Wszystko jest opcjonalne — aplikacja działa nawet jeśli żadna z zależności
nie zostanie zainstalowana. User decyduje przez dialog czy chce auto-install.
"""

from __future__ import annotations

import os
import sys
import json
import shutil
import subprocess
import threading
import zipfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

APPDATA = Path(os.environ.get("APPDATA", Path.home())) / "FreeSystemDoctor"
LHM_DIR = APPDATA / "LibreHardwareMonitor"
LHM_EXE = LHM_DIR / "LibreHardwareMonitor.exe"

CONFIG_FILE = APPDATA / "dependencies.json"


# ── state ────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict):
    APPDATA.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── LHM detection ────────────────────────────────────────────────────────────

def is_lhm_installed() -> dict:
    """Check if LibreHardwareMonitor is installed and accessible.

    Returns dict with:
        installed: bool         — is the EXE present somewhere?
        running: bool           — is the process currently running (WMI active)?
        path: str               — where the EXE lives
        source: str             — 'bundled' | 'app-data' | 'program-files' | 'none'
    """
    # 1. Our managed copy
    if LHM_EXE.exists():
        return {
            "installed": True,
            "running": _is_lhm_process_running(),
            "path": str(LHM_EXE),
            "source": "app-data",
        }

    # 2. Standard install locations
    for candidate in [
        r"C:\Program Files\LibreHardwareMonitor\LibreHardwareMonitor.exe",
        r"C:\Program Files (x86)\LibreHardwareMonitor\LibreHardwareMonitor.exe",
    ]:
        if Path(candidate).exists():
            return {
                "installed": True,
                "running": _is_lhm_process_running(),
                "path": candidate,
                "source": "program-files",
            }

    return {"installed": False, "running": False, "path": "", "source": "none"}


def _is_lhm_process_running() -> bool:
    """Check if LHM process is currently in memory (WMI provider active)."""
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            if (p.info["name"] or "").lower() == "librehardwaremonitor.exe":
                return True
    except Exception:
        pass
    return False


# ── LHM download + install ───────────────────────────────────────────────────

LHM_GITHUB_API = "https://api.github.com/repos/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest"


def _get_lhm_download_url() -> str | None:
    """Query GitHub API for the latest release zip."""
    try:
        req = Request(LHM_GITHUB_API, headers={"User-Agent": "FreeSystemDoctor"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        for asset in data.get("assets", []):
            name = asset.get("name", "").lower()
            if name.endswith(".zip") and "librehardware" in name:
                return asset.get("browser_download_url")
    except Exception:
        pass
    return None


def download_and_install_lhm(progress_cb=None) -> tuple[bool, str]:
    """Download latest LHM, extract to APPDATA. Returns (success, message)."""
    if progress_cb:
        progress_cb(5, "Pobieram informacje o najnowszej wersji...")

    url = _get_lhm_download_url()
    if not url:
        return False, "Nie można pobrać URL z GitHub API (offline?)"

    if progress_cb:
        progress_cb(15, "Pobieram LibreHardwareMonitor...")

    # Download zip
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = Path(tmp.name)
    try:
        req = Request(url, headers={"User-Agent": "FreeSystemDoctor"})
        with urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total:
                        pct = 15 + int((downloaded / total) * 60)
                        progress_cb(pct, f"Pobrano {downloaded//1024} KB / {total//1024} KB")

        if progress_cb:
            progress_cb(80, "Rozpakowuję...")

        # Extract
        LHM_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(LHM_DIR)

        # Some LHM zips wrap content in subfolder; flatten if needed
        _flatten_lhm_dir()

        if not LHM_EXE.exists():
            return False, f"Po rozpakowaniu nie znaleziono {LHM_EXE.name}"

        # Save state
        state = _load_state()
        state["lhm"] = {
            "installed_at":  __import__("datetime").datetime.now().isoformat(),
            "path":          str(LHM_EXE),
            "source_url":    url,
        }
        _save_state(state)

        if progress_cb:
            progress_cb(100, "Zainstalowano")
        return True, f"LibreHardwareMonitor zainstalowany w {LHM_DIR}"

    except Exception as e:
        return False, f"Błąd: {e}"
    finally:
        try:
            zip_path.unlink()
        except Exception:
            pass


def _flatten_lhm_dir():
    """If LHM zip extracted into a single subfolder, move contents up one level."""
    items = list(LHM_DIR.iterdir())
    # If exactly one folder and it contains the EXE
    if len(items) == 1 and items[0].is_dir():
        inner = items[0]
        if (inner / "LibreHardwareMonitor.exe").exists():
            for child in inner.iterdir():
                dst = LHM_DIR / child.name
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                shutil.move(str(child), str(dst))
            inner.rmdir()


def start_lhm_background() -> bool:
    """Launch LHM minimized + ensure WMI provider is enabled."""
    info = is_lhm_installed()
    if not info["installed"]:
        return False
    if info["running"]:
        return True

    try:
        # Start with --minimized so user sees nothing intrusive
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 7   # SW_SHOWMINNOACTIVE
        subprocess.Popen(
            [info["path"], "--minimized"],
            cwd=str(Path(info["path"]).parent),
            startupinfo=startupinfo,
            creationflags=_CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def ensure_lhm_autostart(enable: bool = True) -> bool:
    """Add LHM to user-level autostart so WMI temps always work after reboot."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enable:
                info = is_lhm_installed()
                if not info["installed"]:
                    return False
                winreg.SetValueEx(
                    k, "LibreHardwareMonitor", 0, winreg.REG_SZ,
                    f'"{info["path"]}" --minimized',
                )
            else:
                try:
                    winreg.DeleteValue(k, "LibreHardwareMonitor")
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


# ── public API for startup orchestration ─────────────────────────────────────

def check_all_dependencies() -> dict:
    """Quick read of which deps are present. Non-blocking."""
    return {
        "lhm":         is_lhm_installed(),
        "nvidia_smi":  _has_in_path("nvidia-smi"),
        "wmi_module":  _has_python_module("wmi"),
        "psutil":      _has_python_module("psutil"),
    }


def _has_in_path(name: str) -> bool:
    return shutil.which(name) is not None


def _has_python_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def get_dependency_summary() -> dict:
    """Human-readable summary for the UI."""
    deps = check_all_dependencies()
    return {
        "lhm_status":         "✓ Zainstalowane" if deps["lhm"]["installed"] else "✗ Brak (zalecane)",
        "lhm_running":         "✓ W tle" if deps["lhm"]["running"] else "✗ Nie uruchomione",
        "nvidia_smi":          "✓ GPU NVIDIA wykryte" if deps["nvidia_smi"] else "—",
        "wmi":                  "✓ OK" if deps["wmi_module"] else "✗ Brak (PyInstaller)",
        "psutil":               "✓ OK" if deps["psutil"] else "✗ Brak (krytyczne)",
        "can_install_lhm":     not deps["lhm"]["installed"],
        "should_prompt":        not deps["lhm"]["installed"] and _was_not_declined(),
    }


def _was_not_declined() -> bool:
    """Don't nag user after they explicitly said 'no'."""
    state = _load_state()
    return not state.get("lhm_declined_by_user", False)


def mark_lhm_declined():
    """User clicked 'No thanks' — don't ask again until they enable manually."""
    state = _load_state()
    state["lhm_declined_by_user"] = True
    _save_state(state)


def reset_lhm_declined():
    state = _load_state()
    state.pop("lhm_declined_by_user", None)
    _save_state(state)


# ── orchestrator (called from main.py on startup) ────────────────────────────

def run_first_time_setup_async(on_complete=None):
    """Background thread: install missing deps without blocking UI."""
    def worker():
        summary = get_dependency_summary()
        if on_complete:
            on_complete(summary)
    threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    import json
    print(json.dumps(check_all_dependencies(), indent=2, default=str))
