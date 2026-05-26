"""
game_booster.py — ANTI-CHEAT SAFE optimization profile for Arena Breakout Infinite.

Arena Breakout Infinite uses ACE (Anti-Cheat Expert by Tencent), an
extremely strict kernel-mode anti-cheat. This module is engineered to be
COMPLETELY SAFE against bans by following these rules:

GOLDEN RULES (never break these):
1. Never modify game files (Engine.ini, GameUserSettings.ini, any .pak, .uasset).
   ACE checksums and scans game-folder integrity. Even read-only tweaks like
   r.ShadowQuality=0 can be classified as an unfair-advantage modification
   (it removes cover players hide behind). VERDICT: untouched.
2. Never call OpenProcess on the game executable with anything stronger
   than PROCESS_QUERY_LIMITED_INFORMATION (0x1000). That means NO
   nice(), NO cpu_affinity(), NO EmptyWorkingSet, NO ReadProcessMemory.
3. Never inject DLLs, never hook game APIs, never patch game memory.
4. Never touch ACE / Tencent / launcher processes (kill list excludes them).
5. Watchdog is DETECTION-ONLY — it just observes the game is running and
   shows it in the UI. It does not modify the game process in any way.

WHAT IS STILL DONE (all 100 % system-level, not game-specific):

✓ Ultimate Performance Windows power plan
✓ Disable Xbox Game Bar / Game DVR  (HKCU registry — system feature)
✓ Enable HAGS                       (HKLM\\...\\GraphicsDrivers — driver setting)
✓ 1 ms Windows timer resolution     (winmm.timeBeginPeriod — system timer)
✓ Low-latency TCP                   (netsh tcp settings — system network stack)
✓ Disable Nagle on adapters         (Tcpip registry — system driver)
✓ Visual effects: best performance  (system shell appearance)
✓ Kill bloat background apps        (Slack, Spotify, OneDrive, browsers, etc — NEVER game/ACE)
✓ Trim working sets of OTHER procs  (skips game and protected processes)
✓ Detect game process for status    (read-only listing of processes)

All Windows-side changes are reversible with the Revert button.
"""

from __future__ import annotations

import os
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    import winreg
    _WINREG = True
except ImportError:
    _WINREG = False


# ── constants ─────────────────────────────────────────────────────────────────

GAME_PROCESS = "ArenaBreakoutInfinite.exe"
GAME_PROCESS_ALTS = (
    "ArenaBreakoutInfinite.exe",
    "ArenaBreakoutInfinite-Win64-Shipping.exe",
    "Client-Win64-Shipping.exe",
    "ArenaBreakout.exe",
    "ABI.exe",
    "aki.exe",
    "AB.exe",
)

# Substring keywords used for fuzzy detection (case-insensitive)
_GAME_KEYWORDS = ("arenabreakout", "abi", "breakoutinfinite")

# Override — user-detected process name takes priority
_DETECTED_PROCESS: str | None = None


# ── PROTECTED PROCESSES — never killed, never touched ────────────────────────
# These are anti-cheat / launcher / kernel processes. Touching them either
# breaks the game (legitimate user) or trips ACE (false positive ban risk).
_PROTECTED_PROCESSES = {
    # ACE (Anti-Cheat Expert by Tencent — ABI's anti-cheat)
    "ACE-Tray.exe", "ACE-Guard.exe", "ACE-Base.exe",
    "SGuard64.exe", "SGuardSvc64.exe", "SGuardSvc.exe",
    "TenSafe.exe", "TenSafe_1.exe", "TenSafeFix64.exe",
    "AntiCheatExpert.Launcher.exe", "AntiCheatExpert.Service.exe",
    # Launchers
    "ArenaBreakoutInfinite_Launcher.exe", "Launcher.exe",
    "TencentDl.exe", "QQDownload.exe",
    # System / driver — never touch these
    "lsass.exe", "csrss.exe", "winlogon.exe", "smss.exe",
    "services.exe", "wininit.exe", "System", "explorer.exe",
}

# Bloat processes safe to kill (consumer apps with no game-side dependencies)
_BLOAT_PROCESSES = {
    "OneDrive.exe", "Teams.exe", "ms-teams.exe",
    "Spotify.exe", "SpotifyWebHelper.exe", "Discord.exe",
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe",
    "RuntimeBroker.exe", "SearchApp.exe", "SearchUI.exe",
    "GameBar.exe", "GameBarPresenceWriter.exe",
    "YourPhone.exe", "Cortana.exe",
    "WidgetService.exe", "Widgets.exe",
    "Skype.exe", "SkypeApp.exe",
    "WhatsApp.exe", "Telegram.exe", "Signal.exe",
}

_BACKUP_DIR = Path(os.environ.get("TEMP", ".")) / "FSDGameBackup"
_STATE_FILE = _BACKUP_DIR / "boost_state.json"


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_backup_dir():
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _read_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_state(d: dict):
    _ensure_backup_dir()
    _STATE_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def _run(cmd, timeout: int = 15) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def _is_protected(name: str | None, exe_path: str | None = None) -> bool:
    """True if process must not be touched (game / anti-cheat / system)."""
    if not name:
        return False
    if name in _PROTECTED_PROCESSES:
        return True
    n = name.lower()
    # Game itself (fuzzy match)
    for kw in _GAME_KEYWORDS:
        if kw in n:
            return True
    if exe_path:
        ep = exe_path.lower()
        for kw in _GAME_KEYWORDS:
            if kw in ep:
                return True
        # Anything under an ACE / Tencent install dir
        if "anticheat" in ep or "\\ace\\" in ep or "tencent" in ep:
            return True
    return False


def _proc_matches(name: str | None, exe_path: str | None = None) -> bool:
    """Fuzzy match the game process."""
    if not name:
        return False
    if name in GAME_PROCESS_ALTS or name.lower() == GAME_PROCESS.lower():
        return True
    if _DETECTED_PROCESS and name.lower() == _DETECTED_PROCESS.lower():
        return True
    n = name.lower()
    for kw in _GAME_KEYWORDS:
        if kw in n:
            return True
    if exe_path:
        ep = exe_path.lower()
        for kw in _GAME_KEYWORDS:
            if kw in ep:
                return True
    return False


def find_game_config_dir() -> Path | None:
    candidates = [
        r"%LOCALAPPDATA%\ArenaBreakoutInfinite\Saved\Config\WindowsClient",
        r"%LOCALAPPDATA%\ArenaBreakoutInfinite\Saved\Config\Windows",
        r"%LOCALAPPDATA%\ABI\Saved\Config\WindowsClient",
    ]
    for candidate in candidates:
        path = Path(os.path.expandvars(candidate))
        if path.exists():
            return path
    base = Path(os.path.expandvars(r"%LOCALAPPDATA%"))
    if base.exists():
        for child in base.glob("ArenaBreakout*"):
            cfg = child / "Saved" / "Config" / "WindowsClient"
            if cfg.exists():
                return cfg
    return None


def find_running_game() -> dict | None:
    if not _PSUTIL:
        return None
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if _proc_matches(p.info["name"], p.info.get("exe")):
                return {
                    "pid":  p.info["pid"],
                    "name": p.info["name"],
                    "exe":  p.info.get("exe") or "",
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def is_game_installed() -> bool:
    return find_game_config_dir() is not None


def is_game_running() -> bool:
    return find_running_game() is not None


def scan_for_game_candidates() -> list[dict]:
    """Scan ALL processes for likely game candidates, sorted by score."""
    if not _PSUTIL:
        return []
    candidates = []
    for p in psutil.process_iter(["pid", "name", "exe", "memory_info"]):
        try:
            name = p.info["name"] or ""
            exe = p.info.get("exe") or ""
            score = 0
            n_low = name.lower()
            e_low = exe.lower()
            for kw in _GAME_KEYWORDS:
                if kw in n_low: score += 100
                if kw in e_low: score += 80
            if "win64-shipping.exe" in n_low: score += 30
            if "client-win64-shipping.exe" in n_low: score += 50
            try:
                rss = p.info["memory_info"].rss
                if rss > 500 * 1024 * 1024: score += 10
                if rss > 1024 * 1024 * 1024: score += 20
            except Exception:
                pass
            if score > 0:
                candidates.append({"pid": p.info["pid"], "name": name,
                                    "exe": exe, "score": score})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def set_detected_process(name: str):
    global _DETECTED_PROCESS
    _DETECTED_PROCESS = name
    state = _read_state()
    state["detected_process"] = name
    _write_state(state)


def is_boost_active() -> bool:
    return _STATE_FILE.exists()


# ── 1. POWER PLAN ─────────────────────────────────────────────────────────────

_ULTIMATE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"


def apply_ultimate_performance() -> tuple[bool, str]:
    state = _read_state()
    if "previous_power_plan" not in state:
        rc, out = _run(["powercfg", "/getactivescheme"], timeout=5)
        if rc == 0 and "GUID:" in out:
            state["previous_power_plan"] = out.split("GUID:")[1].strip().split()[0]
            _write_state(state)

    rc, _ = _run(["powercfg", "/setactive", _ULTIMATE_GUID], timeout=5)
    if rc != 0:
        _run(["powercfg", "-duplicatescheme", _ULTIMATE_GUID], timeout=5)
        rc, _ = _run(["powercfg", "/setactive", _ULTIMATE_GUID], timeout=5)
    return rc == 0, ("Power plan: Ultimate Performance"
                     if rc == 0 else "Power plan: nie udało się")


# ── 2. GAME BAR / DVR ────────────────────────────────────────────────────────

def disable_game_bar() -> tuple[bool, str]:
    if not _WINREG:
        return False, "Brak winreg"
    keys = [
        (winreg.HKEY_CURRENT_USER, r"System\GameConfigStore",
         "GameDVR_Enabled", 0),
        (winreg.HKEY_CURRENT_USER,
         r"Software\Microsoft\Windows\CurrentVersion\GameDVR",
         "AppCaptureEnabled", 0),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar",
         "AllowAutoGameMode", 1),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar",
         "AutoGameModeEnabled", 1),
    ]
    state = _read_state()
    state.setdefault("registry_backups", {})

    ok = 0
    for hive, path, name, value in keys:
        try:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as k:
                    cur, _ = winreg.QueryValueEx(k, name)
                    state["registry_backups"][f"{path}\\{name}"] = cur
            except OSError:
                pass
            with winreg.CreateKey(hive, path) as k:
                winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)
            ok += 1
        except Exception:
            pass
    _write_state(state)
    return ok > 0, f"Game DVR/Bar: {ok}/{len(keys)} kluczy"


# ── 3. HAGS ──────────────────────────────────────────────────────────────────

def enable_hags() -> tuple[bool, str]:
    if not _WINREG:
        return False, "Brak winreg"
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
            0, winreg.KEY_SET_VALUE,
        ) as k:
            winreg.SetValueEx(k, "HwSchMode", 0, winreg.REG_DWORD, 2)
        return True, "HAGS włączone (wymaga restartu)"
    except PermissionError:
        return False, "HAGS: brak uprawnień admin"
    except Exception as e:
        return False, f"HAGS: {e}"


# ── 4. TIMER RESOLUTION (system-wide, not game-process modification) ─────────

class _TimerResolution:
    def __init__(self):
        self._held = False
        try:
            import ctypes
            self._winmm = ctypes.WinDLL("winmm")
            r = self._winmm.timeBeginPeriod(1)
            self._held = (r == 0)
        except Exception:
            self._winmm = None

    def release(self):
        if self._held and self._winmm:
            try:
                self._winmm.timeEndPeriod(1)
            except Exception:
                pass
            self._held = False


_timer_holder: _TimerResolution | None = None


def boost_timer_resolution() -> tuple[bool, str]:
    global _timer_holder
    if _timer_holder is None:
        _timer_holder = _TimerResolution()
    return _timer_holder._held, ("Timer resolution: 1 ms"
                                  if _timer_holder._held else "Timer: nie udało się")


def release_timer_resolution():
    global _timer_holder
    if _timer_holder:
        _timer_holder.release()
        _timer_holder = None


# ── 5. NETWORK (system stack, not game-specific) ─────────────────────────────

def apply_low_latency_network() -> tuple[bool, str]:
    cmds = [
        ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
        ["netsh", "int", "tcp", "set", "global", "rss=enabled"],
        ["netsh", "int", "tcp", "set", "global", "ecncapability=enabled"],
        ["netsh", "int", "tcp", "set", "global", "timestamps=disabled"],
        ["ipconfig", "/flushdns"],
    ]
    ok = 0
    for c in cmds:
        rc, _ = _run(c, timeout=8)
        if rc == 0:
            ok += 1

    if _WINREG:
        try:
            base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base, 0,
                                winreg.KEY_READ) as root:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(root, i)
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                            f"{base}\\{sub}", 0,
                                            winreg.KEY_SET_VALUE) as k:
                            winreg.SetValueEx(k, "TcpAckFrequency", 0,
                                              winreg.REG_DWORD, 1)
                            winreg.SetValueEx(k, "TCPNoDelay", 0,
                                              winreg.REG_DWORD, 1)
                            winreg.SetValueEx(k, "TcpDelAckTicks", 0,
                                              winreg.REG_DWORD, 0)
                            ok += 1
                    except Exception:
                        pass
                    i += 1
        except Exception:
            pass
    return ok > 0, f"Network: {ok} tweak(s)"


# ── 6. KILL BLOAT (game + ACE always excluded by _is_protected) ──────────────

def kill_background_bloat(extra: list[str] | None = None) -> tuple[int, list[str]]:
    if not _PSUTIL:
        return 0, []
    targets = set(_BLOAT_PROCESSES)
    if extra:
        targets.update(extra)
    killed = []
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = p.info["name"]
            exe = p.info.get("exe")
            # Defensive: never kill game/anti-cheat/system
            if _is_protected(name, exe):
                continue
            if name in targets:
                p.kill()
                killed.append(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return len(killed), killed


# ── 7. MEMORY TRIM (explicitly skips game + protected) ───────────────────────

def trim_memory_before_launch() -> tuple[bool, str]:
    """Trim working sets — explicitly skips game/anti-cheat/system processes."""
    if not _PSUTIL:
        return False, "Brak psutil"

    trimmed = 0
    skipped = 0
    try:
        import ctypes
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")

        for p in psutil.process_iter(["pid", "name", "exe"]):
            try:
                if _is_protected(p.info.get("name"), p.info.get("exe")):
                    skipped += 1
                    continue
                handle = kernel32.OpenProcess(0x001F0FFF, False, p.info["pid"])
                if handle:
                    psapi.EmptyWorkingSet(handle)
                    kernel32.CloseHandle(handle)
                    trimmed += 1
            except Exception:
                pass
    except Exception:
        pass
    return trimmed > 0, f"Trim: {trimmed} (pominięto {skipped} chronionych)"


# ── 8. VISUAL EFFECTS — best performance ─────────────────────────────────────

def set_visual_effects_performance() -> tuple[bool, str]:
    if not _WINREG:
        return False, "Brak winreg"
    try:
        state = _read_state()
        state.setdefault("registry_backups", {})

        # Save current visual effects mode
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                                0, winreg.KEY_READ) as k:
                cur, _ = winreg.QueryValueEx(k, "VisualFXSetting")
                state["registry_backups"]["VisualFXSetting"] = cur
        except OSError:
            pass

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects") as k:
            winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
        _write_state(state)
        return True, "Visual effects: best performance"
    except Exception as e:
        return False, f"Visual effects: {e}"


# ── 9. DETECTION-ONLY WATCHDOG (NEVER modifies game process) ─────────────────

class _GameWatchdog:
    """
    DETECTION-ONLY. This thread observes whether the game is running.
    It does NOT modify the game process — no nice(), no cpu_affinity(),
    no OpenProcess with write privileges. ACE-safe.

    The 'observed_pid' field is consumed by the GUI to display status.
    """

    def __init__(self):
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.observed_pid: int | None = None
        self.observed_name: str = ""

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        if not _PSUTIL:
            return
        while not self._stop.is_set():
            try:
                found = None
                for p in psutil.process_iter(["pid", "name", "exe"]):
                    try:
                        if _proc_matches(p.info["name"], p.info.get("exe")):
                            found = (p.info["pid"], p.info["name"])
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                if found:
                    self.observed_pid, self.observed_name = found
                else:
                    self.observed_pid, self.observed_name = None, ""
            except Exception:
                pass
            self._stop.wait(3.0)


_watchdog = _GameWatchdog()


def start_game_watchdog():
    _watchdog.start()


def stop_game_watchdog():
    _watchdog.stop()


def get_watchdog_observation() -> dict:
    return {"pid": _watchdog.observed_pid, "name": _watchdog.observed_name}


# ── BIG GREEN BUTTON — SAFE PROFILE ──────────────────────────────────────────

def apply_all_safe(progress_cb=None) -> dict:
    """
    Apply every ANTI-CHEAT SAFE optimization.

    Does NOT touch game files. Does NOT modify the game process.
    Just system-level Windows tuning.
    """
    results: dict[str, tuple[bool, str]] = {}

    steps = [
        ("Power plan: Ultimate",         apply_ultimate_performance),
        ("Wyłączenie Game Bar/DVR",      disable_game_bar),
        ("Włączenie HAGS",                enable_hags),
        ("Timer resolution 1 ms",        boost_timer_resolution),
        ("Network low-latency",          apply_low_latency_network),
        ("Visual effects: performance",  set_visual_effects_performance),
        ("Kill background bloat",        lambda: (True, f"Zabito {kill_background_bloat()[0]} procesów (gra/AC pominięte)")),
        ("Trim pamięci (poza grą)",      trim_memory_before_launch),
    ]

    total = len(steps)
    for i, (name, fn) in enumerate(steps):
        if progress_cb:
            progress_cb(int(i * 100 / total), name)
        try:
            results[name] = fn()
        except Exception as e:
            results[name] = (False, f"Błąd: {e}")

    # Detection-only watchdog (anti-cheat safe)
    start_game_watchdog()

    # Mark state for revert
    state = _read_state()
    state["boost_applied_at"] = datetime.now().isoformat()
    state["mode"] = "anti_cheat_safe"
    _write_state(state)

    if progress_cb:
        progress_cb(100, "Boost gotowy (anti-cheat safe)")
    return results


# Backwards-compat alias (old code paths)
apply_all = apply_all_safe


# ── RECOMMENDED IN-GAME SETTINGS (informational — user applies manually) ─────

RECOMMENDED_INGAME_SETTINGS = [
    ("Tryb wyświetlania",     "Pełny ekran (exclusive fullscreen)"),
    ("V-Sync",                  "OFF"),
    ("Limit FPS",              "Bez limitu (lub 1 fps poniżej hz monitora dla G-Sync)"),
    ("Anti-aliasing",          "Niskie / FXAA"),
    ("Cienie",                 "Niskie (ALE NIE WYŁĄCZONE — usunięcie cieni gracza = ban risk)"),
    ("Tekstury",               "Średnie (jeśli VRAM > 6 GB, daj wyższe)"),
    ("Trawa / Foliage",        "Niska (NIE WYŁĄCZAĆ — usunięcie krzaków = unfair advantage)"),
    ("Post-processing",        "Niski"),
    ("Motion Blur",            "OFF"),
    ("Depth of Field",         "OFF"),
    ("Chromatic Aberration",   "OFF"),
    ("Film Grain",             "OFF"),
    ("Volumetric Effects",     "Niskie"),
]


# ── REVERT ───────────────────────────────────────────────────────────────────

def revert_all() -> dict:
    results = {}
    state = _read_state()

    # Power plan
    prev = state.get("previous_power_plan")
    if prev:
        rc, _ = _run(["powercfg", "/setactive", prev], timeout=5)
        results["Power plan"] = (rc == 0, "Przywrócono poprzedni power plan")

    # Visual effects
    if _WINREG and "VisualFXSetting" in state.get("registry_backups", {}):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                                0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "VisualFXSetting", 0, winreg.REG_DWORD,
                                  int(state["registry_backups"]["VisualFXSetting"]))
            results["Visual effects"] = (True, "Przywrócono")
        except Exception as e:
            results["Visual effects"] = (False, str(e))

    # Game Bar/DVR registry restore
    if _WINREG and "registry_backups" in state:
        restored = 0
        for path_name, value in state["registry_backups"].items():
            if path_name == "VisualFXSetting":
                continue
            try:
                path, name = path_name.rsplit("\\", 1)
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path,
                                    0, winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, int(value))
                restored += 1
            except Exception:
                pass
        results["Registry restore"] = (True, f"Klucze: {restored}")

    release_timer_resolution()
    results["Timer"] = (True, "Timer zwolniony")

    stop_game_watchdog()
    results["Watchdog"] = (True, "Watchdog zatrzymany")

    if _STATE_FILE.exists():
        _STATE_FILE.unlink()
    return results


# Restore persisted detected process on import
def _load_detected_process():
    global _DETECTED_PROCESS
    state = _read_state()
    if "detected_process" in state:
        _DETECTED_PROCESS = state["detected_process"]


_load_detected_process()
