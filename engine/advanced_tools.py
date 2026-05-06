"""Advanced system tools — hosts file, env vars, event logs, thumbnail/font cache, context menu."""

import os
import subprocess
import winreg
import shutil
from pathlib import Path


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _rr(hkey, path, name, default=None):
    try:
        with winreg.OpenKey(hkey, path) as k:
            v, _ = winreg.QueryValueEx(k, name)
            return v
    except OSError:
        return default


def _fmt(b):
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"


# ── hosts file ────────────────────────────────────────────────────────────────

HOSTS = Path(r"C:\Windows\System32\drivers\etc\hosts")


def read_hosts() -> str:
    try:
        return HOSTS.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_hosts() -> list[dict]:
    entries = []
    for line in read_hosts().splitlines():
        stripped = line.strip()
        comment = stripped.startswith("#")
        if not stripped:
            continue
        if comment:
            entries.append({"ip": "", "host": "", "comment": stripped, "raw": line})
        else:
            parts = stripped.split()
            if len(parts) >= 2:
                entries.append({"ip": parts[0], "host": parts[1],
                                 "comment": "", "raw": line})
    return entries


def write_hosts(content: str) -> bool:
    try:
        HOSTS.write_text(content, encoding="utf-8")
        return True
    except PermissionError:
        # Try via elevated powershell
        r = subprocess.run(
            ["powershell", "-Command",
             f"Set-Content -Path '{HOSTS}' -Value @'\n{content}\n'@ -Encoding UTF8"],
            capture_output=True
        )
        return r.returncode == 0


def add_hosts_entry(ip: str, hostname: str) -> bool:
    content = read_hosts()
    if hostname in content:
        return False
    content = content.rstrip() + f"\n{ip}\t{hostname}\n"
    return write_hosts(content)


def remove_hosts_entry(hostname: str) -> bool:
    lines = read_hosts().splitlines(keepends=True)
    new_lines = [l for l in lines if hostname not in l]
    return write_hosts("".join(new_lines))


# ── environment variables ─────────────────────────────────────────────────────

_SYS_ENV_PATH  = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
_USER_ENV_PATH = "Environment"


def get_env_vars(system: bool = False) -> dict[str, str]:
    hkey = winreg.HKEY_LOCAL_MACHINE if system else winreg.HKEY_CURRENT_USER
    path = _SYS_ENV_PATH if system else _USER_ENV_PATH
    result = {}
    try:
        with winreg.OpenKey(hkey, path) as k:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(k, i)
                    result[name] = str(value)
                    i += 1
                except OSError:
                    break
    except OSError:
        pass
    return result


def set_env_var(name: str, value: str, system: bool = False) -> bool:
    hkey = winreg.HKEY_LOCAL_MACHINE if system else winreg.HKEY_CURRENT_USER
    path = _SYS_ENV_PATH if system else _USER_ENV_PATH
    try:
        with winreg.OpenKey(hkey, path, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ, value)
        # Notify Windows of change
        subprocess.run(
            ["powershell", "-Command",
             f'[System.Environment]::SetEnvironmentVariable("{name}","{value}",'
             f'"{"Machine" if system else "User"}")'],
            capture_output=True
        )
        return True
    except OSError:
        return False


def delete_env_var(name: str, system: bool = False) -> bool:
    hkey = winreg.HKEY_LOCAL_MACHINE if system else winreg.HKEY_CURRENT_USER
    path = _SYS_ENV_PATH if system else _USER_ENV_PATH
    try:
        with winreg.OpenKey(hkey, path, 0, winreg.KEY_WRITE) as k:
            winreg.DeleteValue(k, name)
        return True
    except OSError:
        return False


# ── event log cleaner ─────────────────────────────────────────────────────────

def get_event_log_sizes() -> list[dict]:
    r = _run(["powershell", "-NoProfile", "-Command",
               "Get-WinEvent -ListLog * -ErrorAction SilentlyContinue "
               "| Select-Object LogName,RecordCount,FileSize "
               "| ConvertTo-Csv -NoTypeInformation"])
    logs = []
    lines = r.stdout.strip().splitlines()
    if len(lines) < 2:
        return logs
    for line in lines[1:]:
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) >= 3:
            try:
                size = int(parts[2]) if parts[2] else 0
                count = int(parts[1]) if parts[1] else 0
                logs.append({"name": parts[0], "records": count,
                              "size": size, "size_str": _fmt(size)})
            except ValueError:
                pass
    return sorted(logs, key=lambda x: x["size"], reverse=True)


def clear_event_log(log_name: str) -> bool:
    r = subprocess.run(
        ["powershell", "-Command",
         f'Clear-EventLog -LogName "{log_name}" -ErrorAction SilentlyContinue'],
        capture_output=True
    )
    if r.returncode != 0:
        # wevtutil fallback
        r2 = subprocess.run(["wevtutil", "cl", log_name], capture_output=True)
        return r2.returncode == 0
    return True


def clear_all_event_logs(progress_cb=None) -> tuple[int, int]:
    logs = get_event_log_sizes()
    ok = fail = 0
    for log in logs:
        if progress_cb:
            progress_cb(log["name"])
        if clear_event_log(log["name"]):
            ok += 1
        else:
            fail += 1
    return ok, fail


# ── thumbnail cache ───────────────────────────────────────────────────────────

def get_thumbnail_cache_size() -> int:
    explorer_dir = Path.home() / "AppData/Local/Microsoft/Windows/Explorer"
    total = 0
    if explorer_dir.exists():
        for f in explorer_dir.glob("thumbcache_*.db"):
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def clear_thumbnail_cache(progress_cb=None) -> int:
    """Returns bytes freed."""
    explorer_dir = Path.home() / "AppData/Local/Microsoft/Windows/Explorer"
    freed = 0
    if progress_cb:
        progress_cb("Stopping Explorer...")
    # We don't kill Explorer — just delete what we can; locked files skip silently
    if explorer_dir.exists():
        for f in explorer_dir.glob("thumbcache_*.db"):
            try:
                sz = f.stat().st_size
                f.unlink()
                freed += sz
                if progress_cb:
                    progress_cb(f"Deleted {f.name}")
            except OSError:
                pass
    # Legacy thumbs.db files
    for root, _, files in os.walk(Path.home()):
        for fname in files:
            if fname.lower() == "thumbs.db":
                fp = Path(root) / fname
                try:
                    freed += fp.stat().st_size
                    fp.unlink()
                except OSError:
                    pass
    return freed


# ── font cache ────────────────────────────────────────────────────────────────

_FONT_CACHE_PATHS = [
    Path(r"C:\Windows\ServiceProfiles\LocalService\AppData\Local\FontCache"),
    Path.home() / "AppData/Local/FontCache",
]


def get_font_cache_size() -> int:
    total = 0
    for p in _FONT_CACHE_PATHS:
        if p.exists():
            for f in p.rglob("*"):
                try:
                    if f.is_file():
                        total += f.stat().st_size
                except OSError:
                    pass
    return total


def clear_font_cache(progress_cb=None) -> int:
    freed = 0
    subprocess.run(["net", "stop", "FontCache"], capture_output=True)
    subprocess.run(["net", "stop", "FontCache3.0.0.0"], capture_output=True)

    for p in _FONT_CACHE_PATHS:
        if p.exists():
            for f in p.rglob("*"):
                try:
                    if f.is_file():
                        sz = f.stat().st_size
                        f.unlink()
                        freed += sz
                        if progress_cb:
                            progress_cb(f"Deleted: {f.name}")
                except OSError:
                    pass

    subprocess.run(["net", "start", "FontCache"], capture_output=True)
    return freed


# ── context menu (right-click) cleaner ───────────────────────────────────────

_CONTEXT_ROOTS = [
    (winreg.HKEY_CLASSES_ROOT, r"*\shell",                    "File"),
    (winreg.HKEY_CLASSES_ROOT, r"*\shellex\ContextMenuHandlers", "File (handler)"),
    (winreg.HKEY_CLASSES_ROOT, r"Directory\shell",             "Folder"),
    (winreg.HKEY_CLASSES_ROOT, r"Directory\shellex\ContextMenuHandlers", "Folder (handler)"),
    (winreg.HKEY_CLASSES_ROOT, r"Directory\Background\shell", "Desktop"),
    (winreg.HKEY_CLASSES_ROOT, r"Drive\shell",                "Drive"),
]


def list_context_menu_items() -> list[dict]:
    items = []
    for hkey, path, category in _CONTEXT_ROOTS:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name = winreg.EnumKey(key, i)
                        # Get display label
                        label = name
                        try:
                            with winreg.OpenKey(key, name) as sk:
                                try:
                                    label, _ = winreg.QueryValueEx(sk, "")
                                except OSError:
                                    pass
                        except OSError:
                            pass
                        items.append({"name": name, "label": label or name,
                                      "category": category, "path": path,
                                      "hkey": hkey})
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
    return items


def hide_context_menu_item(hkey: int, path: str, name: str) -> bool:
    """Add 'LegacyDisable' value — hides from context menu without deleting."""
    try:
        with winreg.OpenKey(hkey, f"{path}\\{name}", 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, "LegacyDisable", 0, winreg.REG_SZ, "")
        return True
    except OSError:
        return False


def show_context_menu_item(hkey: int, path: str, name: str) -> bool:
    try:
        with winreg.OpenKey(hkey, f"{path}\\{name}", 0, winreg.KEY_WRITE) as k:
            winreg.DeleteValue(k, "LegacyDisable")
        return True
    except OSError:
        return False


def is_context_item_hidden(hkey: int, path: str, name: str) -> bool:
    try:
        with winreg.OpenKey(hkey, f"{path}\\{name}") as k:
            winreg.QueryValueEx(k, "LegacyDisable")
            return True
    except OSError:
        return False
