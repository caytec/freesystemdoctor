"""
ram_master.py — ISLC-class RAM engine with measured, per-stage proof.

Mainstream optimizers "free RAM" by trimming working sets and calling it a day.
The tools that actually work (Mem Reduct, ISLC) drive the Windows native memory
list API. This module does all of it, and measures each stage separately so the
numbers we show are real:

  • MemoryEmptyWorkingSets     — trim every process's working set (kernel-side)
  • MemoryFlushModifiedList    — write dirty pages out, freeing the modified list
  • MemoryPurgeStandbyList     — drop the cached (standby) list
  • MemoryPurgeLowPriorityStandbyList — drop only low-priority cache (gentler)
  • SetSystemFileCacheSize     — flush the system file cache

Plus the memory knobs nobody exposes: live memory composition, memory
compression (MMAgent), page combining, and a pagefile advisor.

Honest by design: every stage reports the MB it actually freed. A stage that
frees nothing says so instead of padding the total.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import re
import winreg
from ctypes import wintypes
from pathlib import Path
from typing import Callable, Optional

from . import _perf

logger = logging.getLogger(__name__)

_STATE_FILE = Path(os.path.expanduser("~")) / ".fsd" / "ram_master.json"

# SystemMemoryListInformation command codes
MEMORY_EMPTY_WORKING_SETS = 2
MEMORY_FLUSH_MODIFIED_LIST = 3
MEMORY_PURGE_STANDBY_LIST = 4
MEMORY_PURGE_LOW_PRIORITY_STANDBY = 5

_SYSTEM_MEMORY_LIST_INFORMATION = 80

_MM_KEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"

ProgressCb = Optional[Callable[[str, int], None]]


# ── state ────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, _STATE_FILE)
    except Exception as exc:
        logger.warning("ram_master._save_state: %s", exc)


def _backup(key: str, value) -> None:
    state = _load_state()
    state.setdefault("backups", {})
    if key not in state["backups"]:
        state["backups"][key] = value
        _save_state(state)


def _restore_value(key):
    return (_load_state().get("backups") or {}).get(key)


# ── privilege handling (shared by every native call below) ───────────────────

class _LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class _LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", _LUID), ("Attributes", wintypes.DWORD)]


class _TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD),
                ("Privileges", _LUID_AND_ATTRIBUTES * 1)]


_SE_PRIVILEGE_ENABLED = 0x00000002
_TOKEN_ADJUST_PRIVILEGES = 0x0020
_TOKEN_QUERY = 0x0008


def _enable_privilege(name: str) -> bool:
    """Enable a privilege on the current process token. Requires admin for the
    memory-list privileges; returns False rather than raising when denied."""
    try:
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        token = wintypes.HANDLE()
        if not adv.OpenProcessToken(ctypes.windll.kernel32.GetCurrentProcess(),
                                    _TOKEN_ADJUST_PRIVILEGES | _TOKEN_QUERY,
                                    ctypes.byref(token)):
            return False
        luid = _LUID()
        if not adv.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            return False
        tp = _TOKEN_PRIVILEGES(1, (_LUID_AND_ATTRIBUTES * 1)(
            _LUID_AND_ATTRIBUTES(luid, _SE_PRIVILEGE_ENABLED)))
        adv.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None)
        # AdjustTokenPrivileges reports success even when the privilege was not
        # assigned — GetLastError is the real verdict.
        return ctypes.get_last_error() == 0
    except Exception as exc:
        logger.debug("_enable_privilege(%s): %s", name, exc)
        return False


def _set_memory_list(command: int) -> tuple[bool, str]:
    """Drive NtSetSystemInformation(SystemMemoryListInformation, command).

    This is the same API Mem Reduct and ISLC use. Requires administrator.
    """
    try:
        if not _enable_privilege("SeProfileSingleProcessPrivilege"):
            return False, "Requires administrator privileges"
        cmd = ctypes.c_int(command)
        status = ctypes.windll.ntdll.NtSetSystemInformation(
            _SYSTEM_MEMORY_LIST_INFORMATION, ctypes.byref(cmd),
            ctypes.sizeof(cmd))
        if status == 0:
            return True, "OK"
        # STATUS_PRIVILEGE_NOT_HELD / STATUS_INVALID_INFO_CLASS are the usual ones
        return False, f"Windows refused the request (status 0x{status & 0xFFFFFFFF:08X})"
    except Exception as exc:
        return False, str(exc)


def flush_system_file_cache() -> tuple[bool, str]:
    """Flush the Windows system file cache (SetSystemFileCacheSize(-1,-1)).

    This is the "system cache" clean Mem Reduct performs; it is separate from
    the standby list and often frees a few hundred MB on long-running systems.
    """
    try:
        if not _enable_privilege("SeIncreaseQuotaPrivilege"):
            return False, "Requires administrator privileges"
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.SetSystemFileCacheSize.argtypes = [ctypes.c_size_t,
                                                    ctypes.c_size_t,
                                                    wintypes.DWORD]
        kernel32.SetSystemFileCacheSize.restype = wintypes.BOOL
        minus_one = ctypes.c_size_t(-1).value
        if kernel32.SetSystemFileCacheSize(minus_one, minus_one, 0):
            return True, "OK"
        return False, "Requires administrator privileges"
    except Exception as exc:
        return False, str(exc)


# ── live memory composition ──────────────────────────────────────────────────

def _available_mb() -> int:
    psutil = _perf.get_psutil()
    if not psutil:
        return 0
    try:
        return int(psutil.virtual_memory().available / (1024 * 1024))
    except Exception:
        return 0


def get_memory_composition() -> dict:
    """Live memory breakdown — the view Task Manager shows but no optimizer does.

    Returns {ok, total_mb, in_use_mb, modified_mb, standby_mb, free_mb,
             compressed_mb, cached_mb, percent}. Standby/modified come from
            performance counters; falls back to psutil-only numbers if the
            counters are unavailable (then standby/modified are None).
    """
    psutil = _perf.get_psutil()
    comp = {"ok": False, "total_mb": 0, "in_use_mb": 0, "modified_mb": None,
            "standby_mb": None, "free_mb": 0, "compressed_mb": None,
            "cached_mb": 0, "percent": 0.0}
    if not psutil:
        return comp
    try:
        vm = psutil.virtual_memory()
        mb = 1024 * 1024
        comp.update({"ok": True,
                     "total_mb": int(vm.total / mb),
                     "in_use_mb": int((vm.total - vm.available) / mb),
                     "free_mb": int(vm.available / mb),
                     "percent": round(vm.percent, 1)})
    except Exception:
        return comp

    script = (
        "$c = Get-Counter "
        "'\\Memory\\Standby Cache Reserve Bytes',"
        "'\\Memory\\Standby Cache Normal Priority Bytes',"
        "'\\Memory\\Standby Cache Core Bytes',"
        "'\\Memory\\Modified Page List Bytes',"
        "'\\Memory\\Free & Zero Page List Bytes' "
        "-ErrorAction Stop; "
        "foreach ($s in $c.CounterSamples) "
        "{ Write-Output ($s.Path + '=' + [math]::Round($s.CookedValue)) }"
    )
    r = _perf.run_powershell(script, timeout=30)
    if r.returncode != 0 or not r.stdout:
        return comp

    vals: dict[str, float] = {}
    for line in r.stdout.splitlines():
        path, _, raw = line.strip().rpartition("=")
        try:
            vals[path.strip().lower()] = float(raw)
        except ValueError:
            continue

    def pick(fragment: str) -> float:
        for k, v in vals.items():
            if fragment in k:
                return v
        return 0.0

    mb = 1024 * 1024
    standby = (pick("standby cache reserve")
               + pick("standby cache normal")
               + pick("standby cache core"))
    modified = pick("modified page list")
    free_zero = pick("free & zero page list")
    if standby or modified:
        comp["standby_mb"] = int(standby / mb)
        comp["modified_mb"] = int(modified / mb)
        comp["cached_mb"] = int((standby + modified) / mb)
        # "free" from the counters excludes standby; psutil's available includes it
        comp["free_mb"] = int(free_zero / mb) or comp["free_mb"]
        comp["in_use_mb"] = max(
            0, comp["total_mb"] - comp["free_mb"]
            - comp["standby_mb"] - comp["modified_mb"])
    return comp


# ── the staged deep clean ────────────────────────────────────────────────────

_LEVELS = {
    # level      → stages run, in order
    "quick":  ("working_sets", "standby_low"),
    "normal": ("working_sets", "modified", "standby_low", "standby"),
    "deep":   ("working_sets", "modified", "standby_low", "standby",
               "file_cache"),
}

_STAGE_LABELS = {
    "working_sets": "Trimming process working sets",
    "modified":     "Flushing modified page list",
    "standby_low":  "Purging low-priority cache",
    "standby":      "Purging standby cache",
    "file_cache":   "Flushing system file cache",
}


def _run_stage(stage: str) -> tuple[bool, str]:
    if stage == "working_sets":
        # Prefer the protected-process-aware trim already proven in game_booster
        try:
            from . import game_booster
            return game_booster.trim_memory_before_launch()
        except Exception:
            return _set_memory_list(MEMORY_EMPTY_WORKING_SETS)
    if stage == "modified":
        return _set_memory_list(MEMORY_FLUSH_MODIFIED_LIST)
    if stage == "standby_low":
        return _set_memory_list(MEMORY_PURGE_LOW_PRIORITY_STANDBY)
    if stage == "standby":
        return _set_memory_list(MEMORY_PURGE_STANDBY_LIST)
    if stage == "file_cache":
        return flush_system_file_cache()
    return False, "Unknown stage"


def deep_clean(level: str = "normal",
               progress_cb: ProgressCb = None) -> dict:
    """Run the RAM cleaning stages for `level`, measuring each one separately.

    Returns {ok, level, stages: [{stage, label, ok, msg, freed_mb}],
             before_mb, after_mb, total_freed_mb}

    Each stage's freed_mb is measured independently, so the report shows which
    technique actually did the work — not one padded total.
    """
    stages = _LEVELS.get(level, _LEVELS["normal"])
    before = _available_mb()
    results: list[dict] = []
    prev = before

    for i, stage in enumerate(stages):
        label = _STAGE_LABELS.get(stage, stage)
        if progress_cb:
            try:
                progress_cb(label + "…",
                            int(5 + (i / max(1, len(stages))) * 90))
            except Exception:
                pass
        ok, msg = _run_stage(stage)
        now = _available_mb()
        freed = max(0, now - prev)
        prev = now
        results.append({"stage": stage, "label": label, "ok": bool(ok),
                        "msg": msg, "freed_mb": freed})

    after = _available_mb()
    if progress_cb:
        try:
            progress_cb("Done", 100)
        except Exception:
            pass
    return {"ok": any(s["ok"] for s in results), "level": level,
            "stages": results, "before_mb": before, "after_mb": after,
            "total_freed_mb": max(0, after - before)}


# ── memory compression (MMAgent) ─────────────────────────────────────────────

def get_compression_status() -> dict:
    """Read MMAgent state: memory compression and page combining.

    Get-MMAgent needs administrator rights — without them it fails with
    "Access is denied", which we surface as needs_admin so the UI can say so
    instead of silently hiding the feature. Note the -ErrorAction Stop is
    load-bearing: without it PowerShell returns exit code 0 even when the
    cmdlet was denied.
    """
    r = _perf.run_powershell(
        "$m = Get-MMAgent -ErrorAction Stop; "
        "Write-Output ('MC=' + $m.MemoryCompression); "
        "Write-Output ('PC=' + $m.PageCombining)", timeout=30)
    out = {"ok": False, "compression": None, "page_combining": None,
           "needs_admin": False}
    if r.returncode != 0 or not r.stdout:
        if "denied" in (r.stderr or "").lower():
            out["needs_admin"] = True
        return out
    for line in r.stdout.splitlines():
        k, _, v = line.strip().partition("=")
        val = v.strip().lower() in ("true", "1")
        if k == "MC":
            out["compression"] = val
            out["ok"] = True
        elif k == "PC":
            out["page_combining"] = val
    return out


def set_compression(enable: bool) -> tuple[bool, str]:
    """Enable/disable memory compression.

    Trade-off is real in both directions: compression saves RAM but costs CPU
    to compress/decompress. On 16 GB+ gaming rigs turning it off removes CPU
    spikes; on 8 GB or less it should stay on or the system will page to disk.
    """
    cur = get_compression_status()
    if cur["ok"] and cur["compression"] is not None:
        _backup("MemoryCompression", bool(cur["compression"]))
    verb = "Enable-MMAgent -mc" if enable else "Disable-MMAgent -mc"
    r = _perf.run_powershell(verb, timeout=45)
    if r.returncode == 0:
        return True, ("Memory compression enabled" if enable
                      else "Memory compression disabled (reboot to apply)")
    return False, "Requires administrator privileges"


def set_page_combining(enable: bool) -> tuple[bool, str]:
    cur = get_compression_status()
    if cur["ok"] and cur["page_combining"] is not None:
        _backup("PageCombining", bool(cur["page_combining"]))
    verb = "Enable-MMAgent -pc" if enable else "Disable-MMAgent -pc"
    r = _perf.run_powershell(verb, timeout=45)
    if r.returncode == 0:
        return True, ("Page combining enabled" if enable
                      else "Page combining disabled (reboot to apply)")
    return False, "Requires administrator privileges"


# ── pagefile advisor ─────────────────────────────────────────────────────────

def analyze_pagefile() -> dict:
    """Read the current pagefile config and recommend a setting.

    Returns {ok, system_managed, entries: [{path, initial_mb, maximum_mb}],
             ram_mb, recommended_initial_mb, recommended_maximum_mb, advice}
    """
    psutil = _perf.get_psutil()
    ram_mb = 0
    if psutil:
        try:
            ram_mb = int(psutil.virtual_memory().total / (1024 * 1024))
        except Exception:
            pass

    raw = _reg_get_multi(_MM_KEY, "PagingFiles")
    entries = []
    for line in raw or []:
        # Format: "C:\pagefile.sys 4096 8192"  (empty sizes = system managed)
        parts = str(line).split()
        if not parts:
            continue
        path = parts[0]
        try:
            initial = int(parts[1]) if len(parts) > 1 else 0
            maximum = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            initial = maximum = 0
        entries.append({"path": path, "initial_mb": initial,
                        "maximum_mb": maximum})

    system_managed = all(e["initial_mb"] == 0 for e in entries) if entries else True
    rec_init = min(ram_mb, 32768) if ram_mb else 4096
    rec_max = min(int(ram_mb * 1.5), 32768) if ram_mb else 8192

    if system_managed:
        advice = ("Windows manages the pagefile. A fixed size stops it growing "
                  "and shrinking, which avoids fragmentation and the stalls "
                  "that come with resizing under load.")
    else:
        advice = ("A fixed pagefile is already configured. Leave it unless you "
                  "changed drives or RAM.")
    return {"ok": bool(entries) or ram_mb > 0, "system_managed": system_managed,
            "entries": entries, "ram_mb": ram_mb,
            "recommended_initial_mb": rec_init,
            "recommended_maximum_mb": rec_max, "advice": advice}


def _reg_get_multi(path: str, name: str):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as k:
            val, _ = winreg.QueryValueEx(k, name)
            if isinstance(val, str):
                return [val]
            return list(val or [])
    except OSError:
        return []


def apply_pagefile(initial_mb: int, maximum_mb: int,
                   drive: str = "C:") -> tuple[bool, str]:
    """Set a fixed pagefile size. Takes effect after a reboot."""
    old = _reg_get_multi(_MM_KEY, "PagingFiles")
    _backup("PagingFiles", old)
    value = [f"{drive}\\pagefile.sys {int(initial_mb)} {int(maximum_mb)}"]
    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, _MM_KEY) as k:
            winreg.SetValueEx(k, "PagingFiles", 0, winreg.REG_MULTI_SZ, value)
        return True, (f"Pagefile fixed at {initial_mb}–{maximum_mb} MB "
                      f"on {drive} (reboot to apply)")
    except Exception:
        return False, "Access denied — run as administrator"


def revert_pagefile() -> tuple[bool, str]:
    old = _restore_value("PagingFiles")
    try:
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, _MM_KEY) as k:
            winreg.SetValueEx(k, "PagingFiles", 0, winreg.REG_MULTI_SZ,
                              list(old) if old else
                              ["?:\\pagefile.sys 0 0"])
        return True, "Pagefile configuration restored (reboot to apply)"
    except Exception:
        return False, "Access denied — run as administrator"


# ── tweak catalogue (drives the UI) ──────────────────────────────────────────

def get_tweaks() -> list[dict]:
    """Declarative catalogue, same contract as deep_optimize/gpu_boost."""
    tweaks: list[dict] = []
    psutil = _perf.get_psutil()
    ram_gb = 0
    if psutil:
        try:
            ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        except Exception:
            pass

    comp = get_compression_status()
    if not comp["ok"] and comp.get("needs_admin"):
        tweaks.append({
            "id": "mem_compression",
            "name": "Memory compression",
            "desc": "Reading this setting needs administrator rights. "
                    "Restart FreeSystemDoctor as administrator to see and "
                    "change it.",
            "impact": "Unavailable without elevation",
            "risk": "low", "reboot": True,
            "optimized": None, "_locked": True,
        })
    elif comp["ok"]:
        big_ram = ram_gb >= 15.5
        tweaks.append({
            "id": "mem_compression",
            "name": "Memory compression",
            "desc": ("Windows compresses idle pages to fit more in RAM, paying "
                     "CPU time to do it. With " f"{ram_gb:.0f} GB installed, "
                     + ("turning it off removes those CPU spikes and you still "
                        "have headroom." if big_ram else
                        "you should keep it ON — without it this system would "
                        "page to disk instead.")),
            "impact": ("Fewer CPU spikes" if big_ram
                       else "Keep enabled — protects against paging"),
            "risk": "low" if big_ram else "medium", "reboot": True,
            # "optimized" means: in the state we recommend for this machine
            "optimized": (not comp["compression"]) if big_ram
            else bool(comp["compression"]),
            "_target": (not big_ram),
        })

    pf = analyze_pagefile()
    if pf["ok"]:
        tweaks.append({
            "id": "pagefile",
            "name": "Fixed pagefile size",
            "desc": (f"{pf['advice']} Recommended for your "
                     f"{pf['ram_mb'] // 1024} GB: "
                     f"{pf['recommended_initial_mb']}–"
                     f"{pf['recommended_maximum_mb']} MB."),
            "impact": "No resize stalls under memory pressure",
            "risk": "medium", "reboot": True,
            "optimized": not pf["system_managed"],
        })

    return tweaks


def apply_tweak(tweak_id: str) -> tuple[bool, str]:
    ok, msg = _apply_tweak_inner(tweak_id)
    try:
        from . import change_ledger
        name = next((t["name"] for t in get_tweaks()
                     if t["id"] == tweak_id), tweak_id)
        change_ledger.record("ram_master", tweak_id, name, ok, msg)
    except Exception:
        pass
    return ok, msg


def _apply_tweak_inner(tweak_id: str) -> tuple[bool, str]:
    try:
        if tweak_id == "mem_compression":
            for t in get_tweaks():
                if t["id"] == "mem_compression":
                    return set_compression(bool(t.get("_target", True)))
            return False, "Unavailable on this system"
        if tweak_id == "pagefile":
            pf = analyze_pagefile()
            return apply_pagefile(pf["recommended_initial_mb"],
                                  pf["recommended_maximum_mb"])
        return False, "Unknown tweak"
    except Exception as exc:
        logger.exception("apply_tweak(%s)", tweak_id)
        return False, str(exc)


def revert_tweak(tweak_id: str) -> tuple[bool, str]:
    try:
        if tweak_id == "mem_compression":
            old = _restore_value("MemoryCompression")
            return set_compression(bool(old) if old is not None else True)
        if tweak_id == "pagefile":
            return revert_pagefile()
        return False, "Unknown tweak"
    except Exception as exc:
        logger.exception("revert_tweak(%s)", tweak_id)
        return False, str(exc)
