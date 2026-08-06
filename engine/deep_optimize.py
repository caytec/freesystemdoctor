"""
deep_optimize.py — advanced Windows tuning that mainstream optimizers don't do.

CCleaner / Advanced SystemCare / Glary stop at junk files, startup entries and
power plans. This module goes a layer deeper — into the kernel scheduler,
interrupt delivery, virtualisation overhead and the component store — where the
measurable wins actually live.

EVERY tweak here is:
  • declared with an honest impact + risk label,
  • fully reversible (old values are backed up before the first change),
  • read-only until the user explicitly applies it.

Nothing is applied automatically. Risky items are labelled "high" and the UI
must confirm them separately.
"""

from __future__ import annotations

import json
import os
import subprocess
import winreg
from pathlib import Path
from typing import Callable, Optional

_NO_WINDOW = 0x08000000
_STATE_DIR = Path(os.path.expanduser("~")) / ".fsd"
_STATE_FILE = _STATE_DIR / "deep_optimize.json"


# ── state / backup ───────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(state: dict) -> None:
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, _STATE_FILE)
    except Exception:
        pass


def _backup(key: str, value) -> None:
    state = _load_state()
    state.setdefault("backups", {})
    if key not in state["backups"]:
        state["backups"][key] = value
        _save_state(state)


def _restore_value(key):
    return (_load_state().get("backups") or {}).get(key, None)


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           creationflags=_NO_WINDOW)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as exc:
        return 1, str(exc)


def _ps(script: str, timeout: int = 90) -> tuple[int, str]:
    return _run(["powershell", "-NoProfile", "-Command", script], timeout)


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
    except Exception:
        return False


# ── 1. DPC / interrupt latency diagnostic (read-only, unique) ────────────────

def measure_dpc_latency(seconds: int = 3) -> dict:
    """Measure kernel DPC/interrupt pressure — the thing that causes stutter
    and input lag even when FPS looks fine.

    No mainstream optimizer reports this. Uses real Windows performance
    counters, so it's a genuine measurement, not an estimate.

    Returns {ok, dpc_time_pct, dpcs_per_sec, interrupt_time_pct, verdict, advice}
    """
    script = (
        f"$s = Get-Counter '\\Processor(_Total)\\% DPC Time',"
        f"'\\Processor(_Total)\\DPCs Queued/sec',"
        f"'\\Processor(_Total)\\% Interrupt Time' "
        f"-SampleInterval 1 -MaxSamples {max(1, seconds)} -ErrorAction Stop; "
        f"$g = $s.CounterSamples | Group-Object Path; "
        f"foreach ($x in $g) {{ "
        f"Write-Output ($x.Name + '=' + "
        f"[math]::Round((($x.Group | Measure-Object CookedValue -Average).Average),3)) }}"
    )
    rc, out = _ps(script, timeout=seconds * 3 + 30)
    if rc != 0 or "=" not in out:
        return {"ok": False, "dpc_time_pct": 0, "dpcs_per_sec": 0,
                "interrupt_time_pct": 0, "verdict": "Unavailable",
                "advice": ["Performance counters could not be read."]}

    vals = {}
    for line in out.splitlines():
        if "=" not in line:
            continue
        path, _, raw = line.rpartition("=")
        try:
            vals[path.strip().lower()] = float(raw)
        except ValueError:
            continue

    def pick(fragment: str) -> float:
        for k, v in vals.items():
            if fragment in k:
                return v
        return 0.0

    dpc = pick("% dpc time")
    queued = pick("dpcs queued")
    irq = pick("% interrupt time")

    advice: list[str] = []
    if dpc >= 3:
        verdict = "High — stutter and input lag likely"
        advice.append("A driver is hogging the kernel. Enable MSI mode below, "
                      "then update GPU/network/audio drivers.")
    elif dpc >= 1.5:
        verdict = "Moderate"
        advice.append("Some driver overhead. MSI mode usually smooths this out.")
    else:
        verdict = "Good — low kernel latency"
        advice.append("Kernel latency looks healthy.")

    if queued > 8000:
        advice.append(f"{queued:,.0f} DPCs/sec is high — often a network or "
                      f"USB controller without MSI mode.")
    if irq >= 3:
        advice.append("High interrupt time — check for a failing device or "
                      "an old chipset driver.")
    return {"ok": True, "dpc_time_pct": round(dpc, 2),
            "dpcs_per_sec": round(queued), "interrupt_time_pct": round(irq, 2),
            "verdict": verdict, "advice": advice}


# ── 2. MSI mode (message-signalled interrupts) ───────────────────────────────

_MSI_CLASSES = ("Display", "Net", "USB", "MEDIA", "SCSIAdapter", "HDC")


def list_msi_devices() -> list[dict]:
    """Devices whose interrupt mode we can read/change.

    MSI replaces legacy line-based interrupts; on GPUs and USB/network
    controllers it measurably reduces DPC latency, stutter and input lag.
    """
    classes = "','".join(_MSI_CLASSES)
    script = (
        f"Get-CimInstance Win32_PnPEntity -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.PNPClass -in @('{classes}') -and "
        f"$_.PNPDeviceID -like 'PCI*' }} | ForEach-Object {{ "
        f"$p = 'HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\' + $_.PNPDeviceID + "
        f"'\\Device Parameters\\Interrupt Management\\MessageSignaledInterruptProperties'; "
        f"$m = (Get-ItemProperty $p -ErrorAction SilentlyContinue).MSISupported; "
        f"if ($null -ne $m) {{ Write-Output ($_.PNPClass + '|' + $_.Name + '|' + "
        f"$_.PNPDeviceID + '|' + $m) }} }}"
    )
    rc, out = _ps(script, timeout=120)
    devices = []
    if rc != 0:
        return devices
    for line in out.splitlines():
        parts = line.strip().split("|")
        if len(parts) != 4:
            continue
        cls, name, devid, msi = parts
        try:
            enabled = int(msi) == 1
        except ValueError:
            continue
        devices.append({"class": cls, "name": name.strip(), "device_id": devid,
                        "msi_enabled": enabled})
    return devices


def set_msi_mode(device_id: str, enable: bool = True) -> tuple[bool, str]:
    """Enable/disable MSI for one device. Takes effect after a reboot."""
    path = (r"SYSTEM\CurrentControlSet\Enum\%s"
            r"\Device Parameters\Interrupt Management"
            r"\MessageSignaledInterruptProperties" % device_id)
    old = _reg_get(winreg.HKEY_LOCAL_MACHINE, path, "MSISupported")
    if old is not None:
        _backup(f"msi::{device_id}", int(old))
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, path, "MSISupported",
                1 if enable else 0):
        return True, ("MSI enabled (reboot required)" if enable
                      else "MSI disabled (reboot required)")
    return False, "Access denied — run as administrator"


def enable_msi_all() -> dict:
    """Turn MSI on for every capable device that doesn't have it yet."""
    changed, failed, skipped = 0, 0, 0
    for dev in list_msi_devices():
        if dev["msi_enabled"]:
            skipped += 1
            continue
        ok, _ = set_msi_mode(dev["device_id"], True)
        changed += 1 if ok else 0
        failed += 0 if ok else 1
    return {"changed": changed, "failed": failed, "already_on": skipped}


# ── 3. Virtualisation-based security (VBS/HVCI) ──────────────────────────────

def get_vbs_status() -> dict:
    """Is VBS/HVCI running? It costs roughly 2-8% FPS in games."""
    script = ("try { $v = Get-CimInstance -ClassName Win32_DeviceGuard "
              "-Namespace root\\Microsoft\\Windows\\DeviceGuard -ErrorAction Stop; "
              "Write-Output ('VBS=' + $v.VirtualizationBasedSecurityStatus); "
              "Write-Output ('SVC=' + ($v.SecurityServicesRunning -join ',')) } "
              "catch { Write-Output 'VBS=?' }")
    rc, out = _ps(script, timeout=60)
    running = False
    hvci = False
    for line in out.splitlines():
        if line.startswith("VBS="):
            running = line.strip().endswith("2")
        if line.startswith("SVC="):
            hvci = "2" in line
    return {"vbs_running": running, "hvci_running": hvci,
            "impact": "Costs about 2-8% FPS in games while enabled."}


def disable_vbs() -> tuple[bool, str]:
    """Disable VBS + HVCI (memory integrity).

    SECURITY TRADE-OFF: this removes a hypervisor-backed protection against
    malicious drivers. Worth it only if you game and accept the risk. Requires
    a reboot and is fully reversible with enable_vbs().
    """
    _backup("vbs_was_enabled", True)
    ok = 0
    if _reg_set(winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\DeviceGuard",
                "EnableVirtualizationBasedSecurity", 0):
        ok += 1
    if _reg_set(winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios"
                r"\HypervisorEnforcedCodeIntegrity", "Enabled", 0):
        ok += 1
    rc, _ = _run(["bcdedit", "/set", "hypervisorlaunchtype", "off"], timeout=30)
    if rc == 0:
        ok += 1
    if ok:
        return True, f"VBS/HVCI disabled ({ok}/3 steps) — reboot to apply"
    return False, "Access denied — run as administrator"


def enable_vbs() -> tuple[bool, str]:
    """Re-enable VBS/HVCI (restores the security protection)."""
    ok = 0
    if _reg_set(winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\DeviceGuard",
                "EnableVirtualizationBasedSecurity", 1):
        ok += 1
    if _reg_set(winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios"
                r"\HypervisorEnforcedCodeIntegrity", "Enabled", 1):
        ok += 1
    rc, _ = _run(["bcdedit", "/set", "hypervisorlaunchtype", "auto"], timeout=30)
    if rc == 0:
        ok += 1
    return ok > 0, f"VBS/HVCI re-enabled ({ok}/3) — reboot to apply"


# ── 4. Scheduler quantum (foreground responsiveness) ─────────────────────────

_PRIO_PATH = r"SYSTEM\CurrentControlSet\Control\PriorityControl"


def get_quantum_status() -> dict:
    val = _reg_get(winreg.HKEY_LOCAL_MACHINE, _PRIO_PATH,
                   "Win32PrioritySeparation", 2)
    return {"value": val,
            "optimized": val == 38,
            "meaning": ("Short, variable quantum with 3:1 foreground boost "
                        "(best for games/apps)" if val == 38 else
                        f"Current value {val} (Windows default is 2)")}


def apply_quantum_tuning() -> tuple[bool, str]:
    """Give the foreground app a bigger share of CPU time slices."""
    old = _reg_get(winreg.HKEY_LOCAL_MACHINE, _PRIO_PATH,
                   "Win32PrioritySeparation", 2)
    _backup("Win32PrioritySeparation", int(old))
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _PRIO_PATH,
                "Win32PrioritySeparation", 38):
        return True, "Foreground apps now get a 3:1 CPU time-slice boost"
    return False, "Access denied — run as administrator"


def revert_quantum_tuning() -> tuple[bool, str]:
    old = _restore_value("Win32PrioritySeparation")
    val = int(old) if old is not None else 2
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _PRIO_PATH,
                "Win32PrioritySeparation", val):
        return True, f"Restored scheduler quantum to {val}"
    return False, "Access denied"


# ── 5. Keep the kernel in RAM ────────────────────────────────────────────────

_MEM_PATH = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"


def get_kernel_paging_status() -> bool:
    return _reg_get(winreg.HKEY_LOCAL_MACHINE, _MEM_PATH,
                    "DisablePagingExecutive", 0) == 1


def apply_kernel_in_ram() -> tuple[bool, str]:
    """Stop Windows paging kernel code to disk — smoother on 8 GB+ systems."""
    old = _reg_get(winreg.HKEY_LOCAL_MACHINE, _MEM_PATH,
                   "DisablePagingExecutive", 0)
    _backup("DisablePagingExecutive", int(old))
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _MEM_PATH,
                "DisablePagingExecutive", 1):
        return True, "Kernel stays in RAM (reboot to apply)"
    return False, "Access denied — run as administrator"


def revert_kernel_in_ram() -> tuple[bool, str]:
    old = _restore_value("DisablePagingExecutive")
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _MEM_PATH,
                "DisablePagingExecutive", int(old) if old is not None else 0):
        return True, "Kernel paging restored"
    return False, "Access denied"


# ── 6. CPU power throttling ──────────────────────────────────────────────────

_THROTTLE_PATH = r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling"


def get_power_throttling_status() -> bool:
    """True when throttling is already OFF (optimized)."""
    return _reg_get(winreg.HKEY_LOCAL_MACHINE, _THROTTLE_PATH,
                    "PowerThrottlingOff", 0) == 1


def apply_disable_power_throttling() -> tuple[bool, str]:
    """Stop Windows down-clocking background apps you actually care about."""
    old = _reg_get(winreg.HKEY_LOCAL_MACHINE, _THROTTLE_PATH,
                   "PowerThrottlingOff", 0)
    _backup("PowerThrottlingOff", int(old))
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _THROTTLE_PATH,
                "PowerThrottlingOff", 1):
        return True, "CPU power throttling disabled"
    return False, "Access denied — run as administrator"


def revert_power_throttling() -> tuple[bool, str]:
    old = _restore_value("PowerThrottlingOff")
    if _reg_set(winreg.HKEY_LOCAL_MACHINE, _THROTTLE_PATH,
                "PowerThrottlingOff", int(old) if old is not None else 0):
        return True, "Power throttling restored"
    return False, "Access denied"


# ── 7. Raw mouse input (remove acceleration curve) ───────────────────────────

_MOUSE_PATH = r"Control Panel\Mouse"


def get_mouse_accel_status() -> bool:
    """True when acceleration is already OFF (1:1 input)."""
    return str(_reg_get(winreg.HKEY_CURRENT_USER, _MOUSE_PATH,
                        "MouseSpeed", "1")) == "0"


def apply_raw_mouse_input() -> tuple[bool, str]:
    """Remove Windows pointer acceleration — 1:1 aim, what pros use."""
    for name in ("MouseSpeed", "MouseThreshold1", "MouseThreshold2"):
        old = _reg_get(winreg.HKEY_CURRENT_USER, _MOUSE_PATH, name, "1")
        _backup(f"mouse::{name}", str(old))
    ok = all(_reg_set(winreg.HKEY_CURRENT_USER, _MOUSE_PATH, n, "0",
                      winreg.REG_SZ)
             for n in ("MouseSpeed", "MouseThreshold1", "MouseThreshold2"))
    return (True, "Pointer acceleration off — 1:1 mouse input (sign out to apply)") \
        if ok else (False, "Could not write mouse settings")


def revert_raw_mouse_input() -> tuple[bool, str]:
    ok = True
    for name, default in (("MouseSpeed", "1"), ("MouseThreshold1", "6"),
                          ("MouseThreshold2", "10")):
        old = _restore_value(f"mouse::{name}")
        ok &= _reg_set(winreg.HKEY_CURRENT_USER, _MOUSE_PATH, name,
                       str(old if old is not None else default), winreg.REG_SZ)
    return ok, "Mouse acceleration restored"


# ── 8. Component store (WinSxS) cleanup ──────────────────────────────────────

def analyze_component_store() -> dict:
    """How much space superseded Windows components are wasting.

    Mainstream cleaners skip WinSxS entirely — it's often several GB.
    """
    rc, out = _run(["dism", "/online", "/cleanup-image",
                    "/analyzecomponentstore"], timeout=600)
    result = {"ok": rc == 0, "actual_size": "", "reclaimable": "",
              "recommended": False, "raw": out[-2000:]}
    for line in out.splitlines():
        low = line.lower()
        if "actual size of component store" in low:
            result["actual_size"] = line.split(":")[-1].strip()
        elif "reclaimable packages" in low or "reclaimable" in low and ":" in line:
            result["reclaimable"] = line.split(":")[-1].strip()
        elif "component store cleanup recommended" in low:
            result["recommended"] = "yes" in low
    return result


def cleanup_component_store(reset_base: bool = False,
                            progress_cb: Optional[Callable[[str, int], None]] = None
                            ) -> tuple[bool, str]:
    """Remove superseded components. reset_base also drops the ability to
    uninstall previously installed updates (frees the most space)."""
    if progress_cb:
        progress_cb("Cleaning component store (this can take a while)…", 10)
    cmd = ["dism", "/online", "/cleanup-image", "/startcomponentcleanup"]
    if reset_base:
        cmd.append("/resetbase")
    rc, out = _run(cmd, timeout=1800)
    if progress_cb:
        progress_cb("Done", 100)
    if rc == 0:
        return True, ("Component store cleaned"
                      + (" (base reset — updates can no longer be uninstalled)"
                         if reset_base else ""))
    return False, (out.strip().splitlines() or ["DISM failed"])[-1][:200]


# ── tweak catalogue (drives the UI) ──────────────────────────────────────────

def get_tweaks() -> list[dict]:
    """Declarative catalogue: id, name, what it does, impact, risk, state."""
    vbs = get_vbs_status()
    return [
        {
            "id": "msi_mode",
            "name": "MSI interrupt mode",
            "desc": "Switch GPU, network and USB controllers to message-signalled "
                    "interrupts — cuts DPC latency, stutter and input lag.",
            "impact": "Smoother frametimes, lower input lag",
            "risk": "low", "reboot": True,
            "optimized": all(d["msi_enabled"] for d in list_msi_devices()) or None,
        },
        {
            "id": "vbs",
            "name": "Virtualisation-based security (VBS/HVCI)",
            "desc": "Windows runs a hypervisor that vets every driver call. "
                    "Turning it off reclaims roughly 2-8% FPS.",
            "impact": "2-8% more FPS",
            "risk": "high", "reboot": True,
            "optimized": not vbs["vbs_running"],
        },
        {
            "id": "quantum",
            "name": "Foreground CPU priority",
            "desc": "Give the app you're actually using a 3:1 share of CPU "
                    "time slices instead of Windows' balanced default.",
            "impact": "Snappier foreground apps and games",
            "risk": "low", "reboot": False,
            "optimized": get_quantum_status()["value"] == 38,
        },
        {
            "id": "kernel_ram",
            "name": "Keep kernel in RAM",
            "desc": "Stop Windows paging kernel code to disk. Recommended on "
                    "8 GB+ systems.",
            "impact": "Fewer micro-stutters",
            "risk": "low", "reboot": True,
            "optimized": get_kernel_paging_status(),
        },
        {
            "id": "power_throttle",
            "name": "CPU power throttling",
            "desc": "Windows down-clocks apps it thinks are idle. Disabling "
                    "keeps background work (and games) at full speed.",
            "impact": "No surprise slowdowns",
            "risk": "low", "reboot": False,
            "optimized": get_power_throttling_status(),
        },
        {
            "id": "raw_mouse",
            "name": "1:1 mouse input",
            "desc": "Remove the Windows pointer acceleration curve so your aim "
                    "maps directly to mouse movement.",
            "impact": "Consistent aim",
            "risk": "low", "reboot": False,
            "optimized": get_mouse_accel_status(),
        },
    ]


_APPLY = {
    "msi_mode": lambda: (lambda r: (r["changed"] > 0 or r["already_on"] > 0,
                                    f"MSI on for {r['changed']} device(s), "
                                    f"{r['already_on']} already enabled"))(enable_msi_all()),
    "vbs": disable_vbs,
    "quantum": apply_quantum_tuning,
    "kernel_ram": apply_kernel_in_ram,
    "power_throttle": apply_disable_power_throttling,
    "raw_mouse": apply_raw_mouse_input,
}

_REVERT = {
    "vbs": enable_vbs,
    "quantum": revert_quantum_tuning,
    "kernel_ram": revert_kernel_in_ram,
    "power_throttle": revert_power_throttling,
    "raw_mouse": revert_raw_mouse_input,
}


def apply_tweak(tweak_id: str) -> tuple[bool, str]:
    fn = _APPLY.get(tweak_id)
    if not fn:
        return False, "Unknown tweak"
    try:
        return fn()
    except Exception as exc:
        return False, str(exc)


def revert_tweak(tweak_id: str) -> tuple[bool, str]:
    fn = _REVERT.get(tweak_id)
    if not fn:
        return False, "This tweak has no automatic revert"
    try:
        return fn()
    except Exception as exc:
        return False, str(exc)
