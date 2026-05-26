"""Desktop Icon Saver — snapshot/restore desktop icon positions.

Inspired by Ashampoo WinOptimizer Icon Saver.
Stores .lnk/.url filenames + (x, y) grid positions. Restores by sending
LVM_SETITEMPOSITION messages to the desktop ListView.
"""

import os
import json
import ctypes
import ctypes.wintypes as wt
from pathlib import Path
from datetime import datetime

_CFG_DIR = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", "."))) / "FreeSystemDoctor"
_LAYOUT_DIR = _CFG_DIR / "desktop_layouts"

# Desktop ListView messages
LVM_FIRST              = 0x1000
LVM_GETITEMCOUNT       = LVM_FIRST + 4
LVM_GETITEMW           = LVM_FIRST + 75
LVM_SETITEMPOSITION    = LVM_FIRST + 15
LVM_GETITEMPOSITION    = LVM_FIRST + 16
LVM_GETITEMTEXTW       = LVM_FIRST + 115
LVM_REDRAWITEMS        = LVM_FIRST + 21
LVIF_TEXT              = 0x00000001
PROCESS_VM_READ        = 0x0010
PROCESS_VM_WRITE       = 0x0020
PROCESS_VM_OPERATION   = 0x0008
PROCESS_QUERY_INFO     = 0x0400
MEM_COMMIT             = 0x1000
MEM_RESERVE            = 0x2000
MEM_RELEASE            = 0x8000
PAGE_READWRITE         = 0x04


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class LVITEM(ctypes.Structure):
    _fields_ = [
        ("mask", ctypes.c_uint),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
        ("state", ctypes.c_uint),
        ("stateMask", ctypes.c_uint),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", ctypes.c_long),
        ("iIndent", ctypes.c_int),
    ]


def _get_desktop_listview():
    user32 = ctypes.windll.user32
    progman = user32.FindWindowW("Progman", None)
    if not progman:
        return 0
    # Try the regular path
    shell = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
    if not shell:
        # Wallpaper-engine variant: hidden in WorkerW
        worker = 0
        for _ in range(40):
            worker = user32.FindWindowExW(0, worker, "WorkerW", None)
            if not worker:
                break
            shell = user32.FindWindowExW(worker, 0, "SHELLDLL_DefView", None)
            if shell:
                break
    if not shell:
        return 0
    sysview = user32.FindWindowExW(shell, 0, "SysListView32", None)
    return sysview


def _get_pid_from_hwnd(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    pid = wt.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def list_icons() -> list[dict]:
    """Return [{name, x, y}, ...] for every icon on the desktop."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = _get_desktop_listview()
    if not hwnd:
        return []

    count = user32.SendMessageW(hwnd, LVM_GETITEMCOUNT, 0, 0)
    if count <= 0:
        return []

    pid = _get_pid_from_hwnd(hwnd)
    h_proc = kernel32.OpenProcess(
        PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFO,
        False, pid)
    if not h_proc:
        return []

    items = []
    try:
        # Allocate remote buffers
        remote_buf = kernel32.VirtualAllocEx(h_proc, 0, 1024,
                                             MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        remote_lvi = kernel32.VirtualAllocEx(h_proc, 0, ctypes.sizeof(LVITEM),
                                             MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        remote_pt = kernel32.VirtualAllocEx(h_proc, 0, ctypes.sizeof(POINT),
                                            MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
        if not remote_buf or not remote_lvi or not remote_pt:
            return []

        for i in range(count):
            # ── Get text ──
            lvi = LVITEM()
            lvi.mask = LVIF_TEXT
            lvi.iItem = i
            lvi.iSubItem = 0
            lvi.pszText = remote_buf
            lvi.cchTextMax = 512
            kernel32.WriteProcessMemory(h_proc, remote_lvi, ctypes.byref(lvi),
                                         ctypes.sizeof(LVITEM), None)
            user32.SendMessageW(hwnd, LVM_GETITEMTEXTW, i, remote_lvi)

            text_buf = ctypes.create_unicode_buffer(256)
            kernel32.ReadProcessMemory(h_proc, remote_buf, text_buf, 512, None)
            name = text_buf.value

            # ── Get position ──
            user32.SendMessageW(hwnd, LVM_GETITEMPOSITION, i, remote_pt)
            pt = POINT()
            kernel32.ReadProcessMemory(h_proc, remote_pt, ctypes.byref(pt),
                                        ctypes.sizeof(POINT), None)

            if name:
                items.append({"name": name, "x": pt.x, "y": pt.y})

        kernel32.VirtualFreeEx(h_proc, remote_buf, 0, MEM_RELEASE)
        kernel32.VirtualFreeEx(h_proc, remote_lvi, 0, MEM_RELEASE)
        kernel32.VirtualFreeEx(h_proc, remote_pt, 0, MEM_RELEASE)
    finally:
        kernel32.CloseHandle(h_proc)

    return items


def save_layout(name: str = None) -> str:
    """Save current desktop layout under a name. Returns saved path."""
    _LAYOUT_DIR.mkdir(parents=True, exist_ok=True)
    if not name:
        name = datetime.now().strftime("layout_%Y-%m-%d_%H-%M-%S")
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    path = _LAYOUT_DIR / f"{safe}.json"

    items = list_icons()
    payload = {
        "name": name,
        "saved": datetime.now().isoformat(),
        "icons": items,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def list_saved_layouts() -> list[dict]:
    if not _LAYOUT_DIR.exists():
        return []
    out = []
    for p in sorted(_LAYOUT_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "file":  str(p),
                "name":  data.get("name", p.stem),
                "saved": data.get("saved", ""),
                "count": len(data.get("icons", [])),
            })
        except Exception:
            pass
    return out


def restore_layout(path: str) -> tuple[bool, str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return (False, str(e))

    user32 = ctypes.windll.user32
    hwnd = _get_desktop_listview()
    if not hwnd:
        return (False, "Desktop ListView not found")

    # Build name → (x, y) lookup
    target = {it["name"]: (it["x"], it["y"]) for it in data.get("icons", [])}

    # Get current items so we can map index → name
    current = list_icons()

    moved = 0
    for i, item in enumerate(current):
        if item["name"] in target:
            x, y = target[item["name"]]
            # LPARAM with packed (x, y)
            lparam = (y << 16) | (x & 0xFFFF)
            user32.SendMessageW(hwnd, LVM_SETITEMPOSITION, i, lparam)
            moved += 1

    # Force refresh
    user32.SendMessageW(hwnd, LVM_REDRAWITEMS, 0, len(current) - 1)
    user32.UpdateWindow(hwnd)
    return (True, f"Restored {moved} icons")


def delete_layout(path: str) -> bool:
    try:
        Path(path).unlink()
        return True
    except Exception:
        return False
