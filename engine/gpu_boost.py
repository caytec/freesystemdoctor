"""
gpu_boost.py — squeeze the full potential out of the GPU.

Persistent GPU-side tuning that complements game_booster (which is per-session)
and turbo_mode (which reverts on exit):

  • Live GPU telemetry — clocks, utilisation, temperature, power draw
    (nvidia-smi when available, WMI fallback) so the user sees proof.
  • HAGS (hardware-accelerated GPU scheduling) — lower scheduling latency.
  • PCIe link power management OFF — the GPU's bus link never drops to a
    low-power state mid-game (a stutter source no mainstream tool touches).
  • MPO disable — fixes VRR flicker/stutter on affected driver+monitor combos.
  • "Optimizations for windowed games" — modern flip model for windowed/
    borderless titles (lower latency, unlocks Auto-HDR there).
  • Game Mode ON + Game DVR/background capture OFF (persistent).
  • NVIDIA maximum performance state (PowerMizer/PerfLevelSrc registry).

Every tweak: backed up before first change, individually revertible,
honest impact + risk labels. Nothing applies automatically.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import winreg
from typing import Optional

_NO_WINDOW = 0x08000000
_LOG_DIR = os.path.join(tempfile.gettempdir(), "FreeSystemDoctor")
os.makedirs(_LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "gpu_boost.log"),
                              encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.DEBUG)

_STATE_FILE = os.path.join(os.path.expanduser("~"), ".fsd", "gpu_boost.json")

_GFX_KEY = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
_DWM_KEY = r"SOFTWARE\Microsoft\Windows\Dwm"
_GAMEBAR_KEY = r"Software\Microsoft\GameBar"
_GAMECONFIG_KEY = r"System\GameConfigStore"
_GAMEDVR_KEY = r"Software\Microsoft\Windows\CurrentVersion\GameDVR"
_DVR_POLICY_KEY = r"SOFTWARE\Policies\Microsoft\Windows\GameDVR"
_DX_PREF_KEY = r"Software\Microsoft\DirectX\UserGpuPreferences"
_NV_CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class" \
                r"\{4d36e968-e325-11ce-bfc1-08002be10318}"


# ── state / helpers ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        if os.path.exists(_STATE_FILE):
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_state(state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as exc:
        logger.warning("_save_state: %s", exc)


def _backup(key: str, value) -> None:
    state = _load_state()
    state.setdefault("backups", {})
    if key not in state["backups"]:
        state["backups"][key] = value
        _save_state(state)


def _restore_value(key):
    return (_load_state().get("backups") or {}).get(key)


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, creationflags=_NO_WINDOW)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as exc:
        return 1, str(exc)


def _reg_get(hive, path, name, default=None):
    try:
        with winreg.OpenKey(hive, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return default


def _reg_set(hive, path, name, value, vtype=winreg.REG_DWORD) -> bool:
    try:
        with winreg.CreateKey(hive, path) as k:
            winreg.SetValueEx(k, name, 0, vtype, value)
        return True
    except Exception as exc:
        logger.debug("_reg_set %s\\%s: %s", path, name, exc)
        return False


def _reg_delete(hive, path, name) -> bool:
    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, name)
        return True
    except OSError:
        return False


# ── live GPU snapshot ────────────────────────────────────────────────────────

def get_gpu_snapshot() -> dict:
    """Real GPU telemetry: nvidia-smi when present, WMI fallback.

    Returns {ok, name, vendor, vram_mb, util_pct, temp_c, clock_mhz,
             clock_max_mhz, power_w, power_limit_w, source}
    """
    snap = {"ok": False, "name": "", "vendor": "unknown", "vram_mb": 0,
            "util_pct": None, "temp_c": None, "clock_mhz": None,
            "clock_max_mhz": None, "power_w": None, "power_limit_w": None,
            "source": ""}

    rc, out = _run(["nvidia-smi",
                    "--query-gpu=name,memory.total,utilization.gpu,"
                    "temperature.gpu,clocks.gr,clocks.max.gr,"
                    "power.draw,power.limit",
                    "--format=csv,noheader,nounits"], timeout=15)
    if rc == 0 and "," in out:
        parts = [p.strip() for p in out.strip().splitlines()[0].split(",")]
        if len(parts) >= 8:
            def num(s, cast=float):
                try:
                    return cast(s)
                except (ValueError, TypeError):
                    return None
            snap.update({
                "ok": True, "vendor": "nvidia", "source": "nvidia-smi",
                "name": parts[0],
                "vram_mb": num(parts[1], int) or 0,
                "util_pct": num(parts[2], int),
                "temp_c": num(parts[3], int),
                "clock_mhz": num(parts[4], int),
                "clock_max_mhz": num(parts[5], int),
                "power_w": num(parts[6]),
                "power_limit_w": num(parts[7]),
            })
            return snap

    # WMI fallback (AMD/Intel or missing nvidia-smi)
    script = ("$g = Get-CimInstance Win32_VideoController | "
              "Where-Object { $_.AdapterRAM -gt 0 } | "
              "Sort-Object AdapterRAM -Descending | Select-Object -First 1; "
              "if ($g) { Write-Output ('NAME=' + $g.Name); "
              "Write-Output ('RAM=' + [math]::Round($g.AdapterRAM/1MB)) }")
    rc, out = _run(["powershell", "-NoProfile", "-Command", script], timeout=30)
    for line in out.splitlines():
        k, _, v = line.strip().partition("=")
        if k == "NAME":
            snap["name"] = v.strip()
            snap["ok"] = True
            snap["source"] = "wmi"
        elif k == "RAM":
            try:
                snap["vram_mb"] = int(v)
            except ValueError:
                pass
    n = snap["name"].lower()
    if "nvidia" in n or "geforce" in n:
        snap["vendor"] = "nvidia"
    elif "amd" in n or "radeon" in n:
        snap["vendor"] = "amd"
    elif "intel" in n or "arc" in n:
        snap["vendor"] = "intel"
    return snap


# ── individual tweaks ────────────────────────────────────────────────────────

def get_hags_status() -> Optional[bool]:
    val = _reg_get(winreg.HKEY_LOCAL_MACHINE, _GFX_KEY, "HwSchMode")
    return None if val is None else val == 2


def apply_hags() -> tuple[bool, str]:
    old = _reg_get(winreg.HKEY_LOCAL_MACHINE, _GFX_KEY, "HwSchMode")
    _backup("HwSchMode", old if old is None else int(old))
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _GFX_KEY, "HwSchMode", 2):
        return True, "GPU hardware scheduling ON (reboot to apply)"
    return False, "Access denied — run as administrator"


def revert_hags() -> tuple[bool, str]:
    old = _restore_value("HwSchMode")
    if old is None:
        _reg_delete(winreg.HKEY_LOCAL_MACHINE, _GFX_KEY, "HwSchMode")
        return True, "GPU scheduling back to driver default (reboot)"
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _GFX_KEY, "HwSchMode", int(old)):
        return True, f"HwSchMode restored to {old} (reboot)"
    return False, "Access denied"


def get_pcie_aspm_status() -> Optional[bool]:
    """True when link power management is OFF (index 0)."""
    rc, out = _run(["powercfg", "/qh", "SCHEME_CURRENT",
                    "SUB_PCIEXPRESS", "ASPM"], timeout=20)
    if rc != 0:
        return None
    for line in out.splitlines():
        if "ac power setting index" in line.lower():
            try:
                return int(line.split(":")[-1].strip(), 16) == 0
            except ValueError:
                return None
    return None


def apply_pcie_aspm_off() -> tuple[bool, str]:
    rc, out = _run(["powercfg", "/qh", "SCHEME_CURRENT",
                    "SUB_PCIEXPRESS", "ASPM"], timeout=20)
    ac = dc = None
    for line in out.splitlines():
        low = line.lower()
        try:
            if "ac power setting index" in low:
                ac = int(line.split(":")[-1].strip(), 16)
            elif "dc power setting index" in low:
                dc = int(line.split(":")[-1].strip(), 16)
        except ValueError:
            pass
    _backup("ASPM", [ac, dc])
    rc1, _ = _run(["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                   "SUB_PCIEXPRESS", "ASPM", "0"], timeout=20)
    _run(["powercfg", "/setdcvalueindex", "SCHEME_CURRENT",
          "SUB_PCIEXPRESS", "ASPM", "0"], timeout=20)
    _run(["powercfg", "/setactive", "SCHEME_CURRENT"], timeout=20)
    if rc1 == 0:
        return True, "PCIe link never drops to low-power mid-game"
    return False, "powercfg refused (run as administrator)"


def revert_pcie_aspm() -> tuple[bool, str]:
    saved = _restore_value("ASPM")
    ac = saved[0] if saved and saved[0] is not None else 2  # moderate savings
    dc = saved[1] if saved and saved[1] is not None else ac
    _run(["powercfg", "/setacvalueindex", "SCHEME_CURRENT",
          "SUB_PCIEXPRESS", "ASPM", str(ac)], timeout=20)
    _run(["powercfg", "/setdcvalueindex", "SCHEME_CURRENT",
          "SUB_PCIEXPRESS", "ASPM", str(dc)], timeout=20)
    _run(["powercfg", "/setactive", "SCHEME_CURRENT"], timeout=20)
    return True, f"PCIe link power management restored (AC={ac}, DC={dc})"


def get_mpo_status() -> bool:
    """True when MPO is disabled (OverlayTestMode == 5)."""
    return _reg_get(winreg.HKEY_LOCAL_MACHINE, _DWM_KEY,
                    "OverlayTestMode", 0) == 5


def apply_disable_mpo() -> tuple[bool, str]:
    old = _reg_get(winreg.HKEY_LOCAL_MACHINE, _DWM_KEY, "OverlayTestMode")
    _backup("OverlayTestMode", old if old is None else int(old))
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _DWM_KEY, "OverlayTestMode", 5):
        return True, "MPO disabled (reboot to apply)"
    return False, "Access denied — run as administrator"


def revert_mpo() -> tuple[bool, str]:
    old = _restore_value("OverlayTestMode")
    if old is None:
        _reg_delete(winreg.HKEY_LOCAL_MACHINE, _DWM_KEY, "OverlayTestMode")
        return True, "MPO back to Windows default (reboot)"
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _DWM_KEY, "OverlayTestMode",
                int(old)):
        return True, f"OverlayTestMode restored to {old} (reboot)"
    return False, "Access denied"


def get_windowed_optim_status() -> bool:
    val = _reg_get(winreg.HKEY_CURRENT_USER, _DX_PREF_KEY,
                   "DirectXUserGlobalSettings", "")
    return "SwapEffectUpgradeEnable=1" in str(val)


def apply_windowed_optim() -> tuple[bool, str]:
    old = _reg_get(winreg.HKEY_CURRENT_USER, _DX_PREF_KEY,
                   "DirectXUserGlobalSettings")
    _backup("DirectXUserGlobalSettings", old)
    cur = str(old or "")
    if "SwapEffectUpgradeEnable" in cur:
        cur = cur.replace("SwapEffectUpgradeEnable=0",
                          "SwapEffectUpgradeEnable=1")
    else:
        cur = (cur + ";" if cur and not cur.endswith(";") else cur) \
              + "SwapEffectUpgradeEnable=1;"
    if _reg_set(winreg.HKEY_CURRENT_USER, _DX_PREF_KEY,
                "DirectXUserGlobalSettings", cur, winreg.REG_SZ):
        return True, "Windowed games now use the modern low-latency flip model"
    return False, "Could not write setting"


def revert_windowed_optim() -> tuple[bool, str]:
    old = _restore_value("DirectXUserGlobalSettings")
    if old is None:
        _reg_delete(winreg.HKEY_CURRENT_USER, _DX_PREF_KEY,
                    "DirectXUserGlobalSettings")
        return True, "Windowed-games optimisation removed"
    if _reg_set(winreg.HKEY_CURRENT_USER, _DX_PREF_KEY,
                "DirectXUserGlobalSettings", str(old), winreg.REG_SZ):
        return True, "Setting restored"
    return False, "Could not write setting"


def get_game_capture_status() -> bool:
    """True when Game Mode is ON and DVR background capture is OFF."""
    mode = _reg_get(winreg.HKEY_CURRENT_USER, _GAMEBAR_KEY,
                    "AutoGameModeEnabled", 1)  # default ON in Win11
    dvr = _reg_get(winreg.HKEY_CURRENT_USER, _GAMECONFIG_KEY,
                   "GameDVR_Enabled", 1)
    cap = _reg_get(winreg.HKEY_CURRENT_USER, _GAMEDVR_KEY,
                   "AppCaptureEnabled", 1)
    return mode == 1 and dvr == 0 and cap == 0


def apply_game_capture_tuning() -> tuple[bool, str]:
    for hive, path, name in ((winreg.HKEY_CURRENT_USER, _GAMEBAR_KEY,
                              "AutoGameModeEnabled"),
                             (winreg.HKEY_CURRENT_USER, _GAMECONFIG_KEY,
                              "GameDVR_Enabled"),
                             (winreg.HKEY_CURRENT_USER, _GAMEDVR_KEY,
                              "AppCaptureEnabled")):
        _backup(f"cap::{name}", _reg_get(hive, path, name))
    ok = _reg_set(winreg.HKEY_CURRENT_USER, _GAMEBAR_KEY,
                  "AutoGameModeEnabled", 1)
    ok &= _reg_set(winreg.HKEY_CURRENT_USER, _GAMECONFIG_KEY,
                   "GameDVR_Enabled", 0)
    ok &= _reg_set(winreg.HKEY_CURRENT_USER, _GAMEDVR_KEY,
                   "AppCaptureEnabled", 0)
    if ok:
        return True, "Game Mode ON, background recording OFF"
    return False, "Could not write settings"


def revert_game_capture_tuning() -> tuple[bool, str]:
    for hive, path, name, default in (
            (winreg.HKEY_CURRENT_USER, _GAMEBAR_KEY,
             "AutoGameModeEnabled", 1),
            (winreg.HKEY_CURRENT_USER, _GAMECONFIG_KEY,
             "GameDVR_Enabled", 1),
            (winreg.HKEY_CURRENT_USER, _GAMEDVR_KEY,
             "AppCaptureEnabled", 1)):
        old = _restore_value(f"cap::{name}")
        if old is None:
            _reg_delete(hive, path, name)
        else:
            _reg_set(hive, path, name, int(old))
    return True, "Game Mode / capture settings restored"


# ── NVIDIA maximum performance state ─────────────────────────────────────────

def _find_nvidia_class_subkey() -> Optional[str]:
    """Find the display-class subkey (0000, 0001…) belonging to NVIDIA."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _NV_CLASS_KEY) as k:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(k, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():
                    continue
                desc = _reg_get(winreg.HKEY_LOCAL_MACHINE,
                                f"{_NV_CLASS_KEY}\\{sub}", "DriverDesc", "")
                prov = _reg_get(winreg.HKEY_LOCAL_MACHINE,
                                f"{_NV_CLASS_KEY}\\{sub}", "ProviderName", "")
                if "nvidia" in (str(desc) + str(prov)).lower():
                    return sub
    except OSError:
        pass
    return None


def get_nv_max_perf_status() -> Optional[bool]:
    """None when no NVIDIA adapter is present."""
    sub = _find_nvidia_class_subkey()
    if sub is None:
        return None
    val = _reg_get(winreg.HKEY_LOCAL_MACHINE, f"{_NV_CLASS_KEY}\\{sub}",
                   "PerfLevelSrc")
    return val == 0x2222


def apply_nv_max_perf() -> tuple[bool, str]:
    sub = _find_nvidia_class_subkey()
    if sub is None:
        return False, "No NVIDIA adapter found"
    path = f"{_NV_CLASS_KEY}\\{sub}"
    for name in ("PerfLevelSrc", "PowerMizerEnable", "PowerMizerLevel",
                 "PowerMizerLevelAC"):
        _backup(f"nv::{name}", _reg_get(winreg.HKEY_LOCAL_MACHINE, path, name))
    ok = _reg_set(winreg.HKEY_LOCAL_MACHINE, path, "PerfLevelSrc", 0x2222)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, path, "PowerMizerEnable", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, path, "PowerMizerLevel", 1)
    _reg_set(winreg.HKEY_LOCAL_MACHINE, path, "PowerMizerLevelAC", 1)
    if ok:
        return True, "NVIDIA forced to maximum performance state (reboot)"
    return False, "Access denied — run as administrator"


def revert_nv_max_perf() -> tuple[bool, str]:
    sub = _find_nvidia_class_subkey()
    if sub is None:
        return False, "No NVIDIA adapter found"
    path = f"{_NV_CLASS_KEY}\\{sub}"
    for name in ("PerfLevelSrc", "PowerMizerEnable", "PowerMizerLevel",
                 "PowerMizerLevelAC"):
        old = _restore_value(f"nv::{name}")
        if old is None:
            _reg_delete(winreg.HKEY_LOCAL_MACHINE, path, name)
        else:
            _reg_set(winreg.HKEY_LOCAL_MACHINE, path, name, int(old))
    return True, "NVIDIA power management restored (reboot)"


# ── tweak catalogue (drives the UI) ──────────────────────────────────────────

def get_tweaks() -> list[dict]:
    tweaks: list[dict] = []

    hags = get_hags_status()
    tweaks.append({
        "id": "hags",
        "name": "Hardware-accelerated GPU scheduling (HAGS)",
        "desc": "The GPU manages its own work queue instead of waiting for "
                "the CPU — lower scheduling latency and better 1%-low FPS "
                "in modern titles. Needs a Turing/RDNA-or-newer driver.",
        "impact": "Lower render latency, steadier frametimes",
        "risk": "low", "reboot": True,
        "optimized": bool(hags),
    })

    aspm = get_pcie_aspm_status()
    tweaks.append({
        "id": "pcie_aspm",
        "name": "PCIe link power management OFF",
        "desc": "Windows lets the PCIe link to your GPU drop into low-power "
                "states; waking it mid-frame causes latency spikes. This "
                "keeps the link at full speed. No mainstream tool touches it.",
        "impact": "No PCIe wake-up stalls mid-game",
        "risk": "low", "reboot": False,
        "optimized": bool(aspm),
    })

    tweaks.append({
        "id": "windowed_optim",
        "name": "Optimizations for windowed games",
        "desc": "Runs windowed/borderless DX10-11 games through the modern "
                "flip presentation model — the same low-latency path "
                "fullscreen games use.",
        "impact": "Lower latency in windowed/borderless",
        "risk": "low", "reboot": False,
        "optimized": get_windowed_optim_status(),
    })

    tweaks.append({
        "id": "game_capture",
        "name": "Game Mode ON + background recording OFF",
        "desc": "Game Mode gives your game scheduling priority; Game DVR "
                "quietly records gameplay in the background and costs FPS. "
                "This sets both the right way, permanently.",
        "impact": "Recovers the FPS background capture steals",
        "risk": "low", "reboot": False,
        "optimized": get_game_capture_status(),
    })

    tweaks.append({
        "id": "mpo",
        "name": "Disable multiplane overlay (MPO)",
        "desc": "MPO causes flicker, black flashes and VRR stutter on some "
                "driver+monitor combos. Apply only if you see those "
                "symptoms — otherwise leave it on.",
        "impact": "Fixes VRR flicker/stutter (when affected)",
        "risk": "medium", "reboot": True,
        "optimized": get_mpo_status(),
    })

    nv = get_nv_max_perf_status()
    if nv is not None:
        tweaks.append({
            "id": "nv_max_perf",
            "name": "NVIDIA maximum performance state",
            "desc": "Stops the driver dropping to low power states "
                    "(PowerMizer) — clocks stay high instead of ramping up "
                    "after the frame needed them. Higher idle power draw.",
            "impact": "GPU clocks always ready, no ramp-up lag",
            "risk": "medium", "reboot": True,
            "optimized": bool(nv),
        })

    return tweaks


_APPLY = {
    "hags": apply_hags,
    "pcie_aspm": apply_pcie_aspm_off,
    "windowed_optim": apply_windowed_optim,
    "game_capture": apply_game_capture_tuning,
    "mpo": apply_disable_mpo,
    "nv_max_perf": apply_nv_max_perf,
}

_REVERT = {
    "hags": revert_hags,
    "pcie_aspm": revert_pcie_aspm,
    "windowed_optim": revert_windowed_optim,
    "game_capture": revert_game_capture_tuning,
    "mpo": revert_mpo,
    "nv_max_perf": revert_nv_max_perf,
}


def apply_tweak(tweak_id: str) -> tuple[bool, str]:
    fn = _APPLY.get(tweak_id)
    if not fn:
        return False, "Unknown tweak"
    try:
        return fn()
    except Exception as exc:
        logger.exception("apply_tweak(%s)", tweak_id)
        return False, str(exc)


def revert_tweak(tweak_id: str) -> tuple[bool, str]:
    fn = _REVERT.get(tweak_id)
    if not fn:
        return False, "Unknown tweak"
    try:
        return fn()
    except Exception as exc:
        logger.exception("revert_tweak(%s)", tweak_id)
        return False, str(exc)
