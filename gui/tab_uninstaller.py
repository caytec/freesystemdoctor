"""Uninstaller tab — list installed programs and launch their uninstallers."""

import threading
import winreg
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style


def _get_installed() -> list[dict]:
    programs = []
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    seen: set[str] = set()
    for hkey, path in keys:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub) as sk:
                            def qv(name):
                                try:
                                    v, _ = winreg.QueryValueEx(sk, name)
                                    return str(v).strip()
                                except OSError:
                                    return ""
                            name = qv("DisplayName")
                            if not name or name in seen:
                                i += 1
                                continue
                            seen.add(name)
                            programs.append({
                                "name":      name,
                                "version":   qv("DisplayVersion") or "—",
                                "publisher": qv("Publisher") or "—",
                                "install_date": qv("InstallDate") or "—",
                                "size":      qv("EstimatedSize") or "—",
                                "uninstall": qv("UninstallString"),
                            })
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
    return sorted(programs, key=lambda x: x["name"].lower())


class UninstallerTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._all: list[dict] = []
        self._build_ui()
        self.after(300, self._load)

    def _build_ui(self):
        hdr = Card(self)
        hdr.pack(fill="x", padx=16, pady=(16, 4))
        SectionLabel(hdr, "Installed Programs").pack(side="left", padx=8, pady=8)

        search_row = tk.Frame(self, bg=T.BG)
        search_row.pack(fill="x", padx=16, pady=4)
        tk.Label(search_row, text="Filter:", bg=T.BG, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        tk.Entry(search_row, textvariable=self._filter_var, width=30,
                 bg=T.PANEL, fg=T.FG, insertbackground=T.FG,
                 font=T.FONT_BODY).pack(side="left", padx=6)
        ActionButton(search_row, "Refresh", command=self._load).pack(side="left", padx=4)

        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        self._uninst_btn = ActionButton(btn_row, "Uninstall Selected",
                                        command=self._uninstall, danger=True)
        self._uninst_btn.pack(side="left", padx=(0, 6))
        self._uninst_btn.config(state="disabled")

        ActionButton(btn_row, "Batch Uninstall Selected",
                     command=self._batch_uninstall, danger=True).pack(side="left")

        card = Card(self)
        card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        cols = ("Version", "Publisher", "Installed", "Size (KB)")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",         text="Program Name", anchor="w")
        self._tv.heading("Version",    text="Version",      anchor="w")
        self._tv.heading("Publisher",  text="Publisher",    anchor="w")
        self._tv.heading("Installed",  text="Installed",    anchor="w")
        self._tv.heading("Size (KB)",  text="Size (KB)",    anchor="w")
        self._tv.column("#0",        width=260)
        self._tv.column("Version",   width=100)
        self._tv.column("Publisher", width=160)
        self._tv.column("Installed", width=90)
        self._tv.column("Size (KB)", width=80)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._tv.bind("<<TreeviewSelect>>", lambda _: self._uninst_btn.config(state="normal"))

        self._count_lbl = tk.Label(self, text="", bg=T.BG, fg=T.FG2, font=T.FONT_SMALL)
        self._count_lbl.pack(anchor="w", padx=16, pady=4)

    def _load(self):
        self._status.set("Loading installed programs...")
        self._uninst_btn.config(state="disabled")
        threading.Thread(target=lambda: self.after(0, self._show, _get_installed()),
                         daemon=True).start()

    def _show(self, programs):
        self._all = programs
        self._apply_filter()
        self._status.set(f"Found {len(programs)} installed programs.")

    def _apply_filter(self):
        q = self._filter_var.get().lower()
        filtered = [p for p in self._all if q in p["name"].lower() or q in p["publisher"].lower()]
        for item in self._tv.get_children():
            self._tv.delete(item)
        for p in filtered:
            self._tv.insert("", "end", text=p["name"],
                            values=(p["version"], p["publisher"],
                                    p["install_date"], p["size"]))
        self._count_lbl.config(text=f"Showing {len(filtered)} of {len(self._all)} programs")

    def _uninstall(self):
        sel = self._tv.selection()
        if not sel:
            return
        name = self._tv.item(sel[0], "text")
        prog = next((p for p in self._all if p["name"] == name), None)
        if not prog:
            return
        if not prog["uninstall"]:
            messagebox.showerror("No uninstaller",
                                 f"No uninstall string found for '{name}'.")
            return
        if not messagebox.askyesno("Uninstall",
                                   f"Run the uninstaller for:\n{name}\n\nContinue?"):
            return
        try:
            subprocess.Popen(prog["uninstall"], shell=True)
            self._status.set(f"Uninstaller launched for: {name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _batch_uninstall(self):
        sel = self._tv.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select programs to uninstall")
            return

        names = [self._tv.item(item, "text") for item in sel]
        progs = [p for p in self._all if p["name"] in names]
        uninstallable = [p for p in progs if p["uninstall"]]

        if not uninstallable:
            messagebox.showerror("Error", "No uninstall strings found for selected programs")
            return

        msg = f"Uninstall {len(uninstallable)} program(s)?\n\n"
        msg += "\n".join(f"• {p['name']}" for p in uninstallable[:10])
        if len(uninstallable) > 10:
            msg += f"\n• ... and {len(uninstallable) - 10} more"
        msg += "\n\nContinue?"

        if not messagebox.askyesno("Batch Uninstall", msg):
            return

        def batch():
            success = 0
            for prog in uninstallable:
                try:
                    subprocess.run(prog["uninstall"], shell=True, timeout=30)
                    success += 1
                except Exception:
                    pass

            self.after(0, lambda: messagebox.showinfo("Complete",
                f"Uninstalled {success} of {len(uninstallable)} programs\nPlease restart your computer"))
            self._status.set(f"Batch uninstall completed: {success}/{len(uninstallable)}")

        threading.Thread(target=batch, daemon=True).start()
