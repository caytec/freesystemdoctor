"""Care page — main scan hub with circular scan button and all-module scan."""

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, CircleScanButton, ActionButton, IssueBadge, ProgressBar, apply_treeview_style
from engine import disk_cleaner, registry_cleaner, startup_manager
from engine import system_info, memory_optimizer, network_optimizer
from engine import privacy_cleaner, protection


# ── scan module definitions ───────────────────────────────────────────────────

SCAN_MODULES = [
    ("Privacy Sweep",       "privacy"),
    ("Junk File Clean",     "junk"),
    ("Registry Clean",      "registry"),
    ("Shortcut Fix",        "shortcut"),
    ("System Optimization", "sysopt"),
    ("Internet Boost",      "internet"),
    ("Firewall Check",      "firewall"),
    ("Antivirus",           "antivirus"),
    ("Hardware Health",     "hardware"),
    ("Software Health",     "software"),
    ("Disk Check",          "disk"),
]


class CarePage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._scanning = False
        self._scan_vars: dict[str, tk.BooleanVar] = {}
        self._issue_badges: dict[str, IssueBadge] = {}
        self._scan_results: dict[str, int] = {}
        self._build_ui()

    def on_activate(self):
        pass

    def _build_ui(self):
        # ── header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="System Care", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Scan and fix all system issues in one click",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        # ── body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left column: scan button + checkboxes
        left = tk.Frame(body, bg=T.BG)
        left.pack(side="left", fill="y", padx=(0, 12))
        self._build_scan_column(left)

        # Right column: results panel
        right = tk.Frame(body, bg=T.BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_results_panel(right)

    def _build_scan_column(self, parent):
        # Circular scan button
        btn_frame = tk.Frame(parent, bg=T.BG)
        btn_frame.pack(pady=(8, 8))
        self._scan_btn = CircleScanButton(btn_frame, command=self._start_scan, bg=T.BG)
        self._scan_btn.pack()

        self._scan_status_lbl = tk.Label(parent, text="Select modules and press SCAN",
                                         bg=T.BG, fg=T.FG2, font=T.FONT_SMALL)
        self._scan_status_lbl.pack(pady=(0, 8))

        # "Select All" toggle
        self._select_all_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="Select All", variable=self._select_all_var,
                       bg=T.BG, fg=T.FG, selectcolor=T.ACCENT,
                       activebackground=T.BG, font=T.FONT_BOLD,
                       command=self._toggle_all).pack(anchor="w", padx=8, pady=(0, 4))

        # Checkbox grid
        grid = tk.Frame(parent, bg=T.BG)
        grid.pack(fill="x", padx=8)
        for idx, (label, key) in enumerate(SCAN_MODULES):
            var = tk.BooleanVar(value=True)
            self._scan_vars[key] = var
            col = idx % 2
            row = idx // 2
            cb = tk.Checkbutton(grid, text=label, variable=var,
                                bg=T.BG, fg=T.FG, selectcolor=T.ACCENT,
                                activebackground=T.BG, font=T.FONT_BODY)
            cb.grid(row=row, column=col, sticky="w", padx=4, pady=2)

        # Fix All button (hidden until scan done)
        self._fix_btn = ActionButton(parent, "⚡ FIX ALL ISSUES",
                                     command=self._fix_all)
        self._fix_btn.config(state="disabled", font=T.FONT_BOLD, pady=10)
        self._fix_btn.pack(fill="x", padx=8, pady=(12, 0))

        # Progress bar (hidden until fix runs)
        self._fix_progress_frame = tk.Frame(parent, bg=T.BG)
        self._fix_progress_lbl = tk.Label(self._fix_progress_frame, text="",
                                          bg=T.BG, fg=T.HIGHLIGHT,
                                          font=T.FONT_SMALL, anchor="w")
        self._fix_progress_lbl.pack(fill="x", padx=8, pady=(8, 2))
        self._fix_progress = ProgressBar(self._fix_progress_frame)
        self._fix_progress.pack(fill="x", padx=8, pady=(0, 4))

        # Result panel (summary card after fix)
        self._fix_result_frame = tk.Frame(parent, bg=T.PANEL,
                                          highlightthickness=1,
                                          highlightbackground=T.SUCCESS)
        self._fix_result_title = tk.Label(self._fix_result_frame,
                                          text="✓ All Fixes Applied",
                                          bg=T.PANEL, fg=T.SUCCESS,
                                          font=T.FONT_H2, anchor="w")
        self._fix_result_title.pack(fill="x", padx=10, pady=(8, 4))
        self._fix_result_stats = tk.Label(self._fix_result_frame, text="",
                                          bg=T.PANEL, fg=T.FG,
                                          font=T.FONT_BOLD, anchor="w",
                                          justify="left")
        self._fix_result_stats.pack(fill="x", padx=10, pady=(0, 4))
        self._fix_result_details = tk.Label(self._fix_result_frame, text="",
                                            bg=T.PANEL, fg=T.FG2,
                                            font=T.FONT_SMALL, anchor="w",
                                            justify="left", wraplength=260)
        self._fix_result_details.pack(fill="x", padx=10, pady=(0, 8))

    def _build_results_panel(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        hdr = tk.Frame(card, bg=T.PANEL)
        hdr.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(hdr, text="Scan Results", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_H2).pack(side="left")
        self._total_lbl = tk.Label(hdr, text="", bg=T.PANEL, fg=T.HIGHLIGHT,
                                   font=T.FONT_BOLD)
        self._total_lbl.pack(side="right")

        cols = ("Issues", "Status")
        self._tv = ttk.Treeview(card, columns=cols, show="tree headings", height=14)
        apply_treeview_style(self._tv)
        self._tv.heading("#0",      text="Category",  anchor="w")
        self._tv.heading("Issues",  text="Issues",    anchor="w")
        self._tv.heading("Status",  text="Status",    anchor="w")
        self._tv.column("#0",      width=200)
        self._tv.column("Issues",  width=80)
        self._tv.column("Status",  width=160)
        self._tv.tag_configure("ok",       foreground=T.SUCCESS)
        self._tv.tag_configure("issue",    foreground=T.WARNING)
        self._tv.tag_configure("scanning", foreground=T.INFO)
        self._tv.tag_configure("pending",  foreground=T.FG2)
        sb = ttk.Scrollbar(card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

        # Populate initial rows
        for label, key in SCAN_MODULES:
            self._tv.insert("", "end", iid=key, text=label,
                            values=("–", "Pending"), tags=("pending",))

    # ── actions ───────────────────────────────────────────────────────────────

    def _toggle_all(self):
        val = self._select_all_var.get()
        for var in self._scan_vars.values():
            var.set(val)

    def _set_row(self, key: str, issues: int, status: str, tag: str):
        try:
            issue_str = str(issues) if issues > 0 else "0" if issues == 0 else "–"
            self._tv.item(key, values=(issue_str, status), tags=(tag,))
        except tk.TclError:
            pass

    def _start_scan(self):
        if self._scanning:
            return
        enabled = [key for label, key in SCAN_MODULES if self._scan_vars.get(key, tk.BooleanVar()).get()]
        if not enabled:
            messagebox.showinfo("Nothing selected", "Select at least one scan module.")
            return

        self._scanning = True
        self._scan_results = {}
        self._fix_btn.config(state="disabled")
        self._fix_result.config(text="")
        self._total_lbl.config(text="")
        self._scan_status_lbl.config(text="Scanning...")
        self._scan_btn.set_scanning(True)

        # Reset all rows
        for label, key in SCAN_MODULES:
            if key in enabled:
                self._set_row(key, -1, "Scanning...", "scanning")
            else:
                self._set_row(key, -1, "Skipped", "pending")

        threading.Thread(target=self._run_scan, args=(enabled,), daemon=True).start()

    def _run_scan(self, enabled: list[str]):
        results = {}

        def update(key, count, status, tag):
            self.after(0, self._set_row, key, count, status, tag)
            results[key] = count

        for key in enabled:
            try:
                if key == "privacy":
                    items = privacy_cleaner.scan_browser_privacy()
                    n = sum(1 for i in items if i["size"] > 0)
                    update(key, n, f"{n} privacy items" if n else "Clean", "issue" if n else "ok")

                elif key == "junk":
                    items = disk_cleaner.scan_junk()
                    total = sum(r.size for r in items)
                    n = len(items)
                    sz = disk_cleaner._format_size(total)
                    update(key, n, f"{sz} junk" if n else "Clean", "issue" if n else "ok")

                elif key == "registry":
                    issues = registry_cleaner.scan_registry()
                    n = len(issues)
                    update(key, n, f"{n} registry issues" if n else "Clean", "issue" if n else "ok")

                elif key == "shortcut":
                    # Check startup items for broken paths
                    entries = startup_manager.get_startup_entries()
                    broken = sum(1 for e in entries if not e.enabled)
                    update(key, broken, f"{broken} disabled items" if broken else "Clean",
                           "issue" if broken else "ok")

                elif key == "sysopt":
                    detail = memory_optimizer.get_memory_detail()
                    pct = detail.get("ram_pct", 0)
                    n = 1 if pct > 80 else 0
                    update(key, n, f"RAM {pct:.0f}% used" if n else f"RAM {pct:.0f}% OK",
                           "issue" if n else "ok")

                elif key == "internet":
                    tcp = network_optimizer.get_tcp_global()
                    n = 1 if "autotuninglevel" not in tcp.lower() else 0
                    update(key, n, "TCP not optimized" if n else "TCP optimized",
                           "issue" if n else "ok")

                elif key == "firewall":
                    fw = protection.get_firewall_status()
                    off = [p for p, s in fw.items() if not s.get("enabled", False)]
                    n = len(off)
                    update(key, n, f"{', '.join(off)} disabled" if off else "All profiles on",
                           "issue" if n else "ok")

                elif key == "antivirus":
                    df = protection.get_defender_status()
                    n = 0 if (df.get("enabled") and df.get("realtime")) else 1
                    update(key, n, "Defender active" if not n else "Defender issue",
                           "ok" if not n else "issue")

                elif key == "hardware":
                    disks = system_info.get_disk_info()
                    n = sum(1 for d in disks if d.get("used_pct", 0) > 85)
                    update(key, n, f"{n} disk(s) near full" if n else "Disk space OK",
                           "issue" if n else "ok")

                elif key == "software":
                    # Quick check: just count known outdated from DB without winget
                    from engine.software_updater import get_installed_software, match_known, version_lt
                    installed = get_installed_software()
                    outdated = 0
                    for prog in installed[:50]:  # limit for speed
                        known = match_known(prog["name"])
                        if known and version_lt(prog["version"], known["latest"]):
                            outdated += 1
                    update(key, outdated, f"{outdated} outdated apps" if outdated else "Apps OK",
                           "issue" if outdated else "ok")

                elif key == "disk":
                    rb = disk_cleaner.get_recycle_bin_size()
                    n = 1 if rb > 0 else 0
                    sz = disk_cleaner._format_size(rb)
                    update(key, n, f"Recycle Bin: {sz}" if n else "Recycle bin empty",
                           "issue" if n else "ok")

            except Exception as ex:
                update(key, 0, f"Error: {str(ex)[:30]}", "pending")

        self.after(0, self._scan_done, results)

    def _scan_done(self, results: dict):
        self._scanning = False
        self._scan_results = results
        self._scan_btn.set_scanning(False)
        total_issues = sum(v for v in results.values() if isinstance(v, int) and v > 0)
        self._total_lbl.config(text=f"{total_issues} total issue(s) found")
        self._scan_status_lbl.config(
            text=f"Scan complete — {total_issues} issue(s) found" if total_issues
                 else "Scan complete — System is clean!")
        if total_issues > 0:
            self._fix_btn.config(state="normal")

        # Update action center
        if hasattr(self._app, "_pages") and "action" in self._app._pages:
            self._app._pages["action"].update_from_scan(results)

    def _fix_all(self):
        if self._scanning:
            return
        if not messagebox.askyesno("Fix All Issues",
                                   "Apply automatic fixes for all detected issues?\n\n"
                                   "This will clean junk, registry, privacy traces,\n"
                                   "empty Recycle Bin, optimize RAM and network."):
            return
        self._fix_btn.config(state="disabled")
        self._fix_result_frame.pack_forget()
        self._fix_progress_frame.pack(fill="x", padx=0, pady=(8, 0))
        self._fix_progress.set(0)
        self._fix_progress_lbl.config(text="Preparing…")
        self._scan_status_lbl.config(text="Applying fixes…")
        threading.Thread(target=self._run_fixes, daemon=True).start()

    # ── fix orchestration ─────────────────────────────────────────────────────

    def _fix_set_status(self, key: str, status: str, tag: str):
        try:
            cur = self._tv.item(key, "values")
            issue_str = cur[0] if cur else "–"
            self._tv.item(key, values=(issue_str, status), tags=(tag,))
        except tk.TclError:
            pass

    def _fix_progress_update(self, pct: float, label: str):
        self._fix_progress.set(pct)
        self._fix_progress_lbl.config(text=label)

    def _run_fixes(self):
        # Build task list from scan results — only categories with issues
        tasks = []
        if self._scan_results.get("junk", 0) > 0:
            tasks.append(("junk", "Cleaning junk files"))
        if self._scan_results.get("disk", 0) > 0:
            tasks.append(("disk", "Emptying Recycle Bin"))
        if self._scan_results.get("privacy", 0) > 0:
            tasks.append(("privacy", "Wiping privacy traces"))
        if self._scan_results.get("registry", 0) > 0:
            tasks.append(("registry", "Repairing registry"))
        if self._scan_results.get("sysopt", 0) > 0:
            tasks.append(("sysopt", "Optimizing RAM"))
        if self._scan_results.get("internet", 0) > 0:
            tasks.append(("internet", "Tuning network"))
        if self._scan_results.get("firewall", 0) > 0:
            tasks.append(("firewall", "Enabling firewall"))

        total = max(len(tasks), 1)
        stats = {
            "fixed_count": 0,
            "failed_count": 0,
            "bytes_freed": 0,
            "items_removed": 0,
            "fixed_labels": [],
            "failed_labels": [],
        }
        t0 = time.time()

        def step(idx, key, label):
            pct = (idx / total) * 100
            self.after(0, self._fix_progress_update, pct, f"{label}…")
            self.after(0, self._fix_set_status, key, "Fixing…", "scanning")

        for idx, (key, label) in enumerate(tasks):
            step(idx, key, label)
            try:
                if key == "junk":
                    items = disk_cleaner.scan_junk()
                    freed_total = 0
                    removed_total = 0
                    for r in items:
                        freed, removed = disk_cleaner.clean_folder(r.path)
                        freed_total += freed
                        removed_total += removed
                    stats["bytes_freed"] += freed_total
                    stats["items_removed"] += removed_total
                    detail = f"Cleaned {disk_cleaner._format_size(freed_total)}"
                    self._mark_fixed(key, detail, stats, label)

                elif key == "disk":
                    rb_size = disk_cleaner.get_recycle_bin_size()
                    if disk_cleaner.empty_recycle_bin():
                        stats["bytes_freed"] += rb_size
                        detail = f"Freed {disk_cleaner._format_size(rb_size)}"
                        self._mark_fixed(key, detail, stats, label)
                    else:
                        self._mark_failed(key, stats, label)

                elif key == "privacy":
                    items = privacy_cleaner.scan_browser_privacy()
                    selected = [{**i, "selected": True} for i in items if i.get("size", 0) > 0]
                    freed, count = privacy_cleaner.clean_browser_privacy(selected)
                    stats["bytes_freed"] += freed
                    stats["items_removed"] += count
                    detail = f"Cleared {count} traces ({disk_cleaner._format_size(freed)})"
                    self._mark_fixed(key, detail, stats, label)

                elif key == "registry":
                    issues = registry_cleaner.scan_registry()
                    removed = 0
                    for issue in issues:
                        if registry_cleaner.remove_issue(issue):
                            removed += 1
                    stats["items_removed"] += removed
                    detail = f"Removed {removed} entries"
                    self._mark_fixed(key, detail, stats, label)

                elif key == "sysopt":
                    trimmed, _ = memory_optimizer.trim_working_sets()
                    detail = f"Trimmed {trimmed} processes"
                    self._mark_fixed(key, detail, stats, label)

                elif key == "internet":
                    network_optimizer.apply_tcp_tweaks()
                    network_optimizer.flush_dns()
                    self._mark_fixed(key, "TCP tuned, DNS flushed", stats, label)

                elif key == "firewall":
                    if protection.set_all_firewall_profiles(True):
                        self._mark_fixed(key, "All profiles enabled", stats, label)
                    else:
                        self._mark_failed(key, stats, label)

            except Exception as ex:
                stats["failed_labels"].append(f"{label}: {str(ex)[:40]}")
                stats["failed_count"] += 1
                self.after(0, self._fix_set_status, key, "Failed", "issue")

            time.sleep(0.15)  # small delay so user can see live progress

        self.after(0, self._fix_progress_update, 100, "Done")
        elapsed = time.time() - t0
        self.after(0, self._fix_done, stats, elapsed)

    def _mark_fixed(self, key: str, detail: str, stats: dict, label: str):
        stats["fixed_count"] += 1
        stats["fixed_labels"].append(f"{label}: {detail}")
        self.after(0, self._fix_set_status, key, f"✓ {detail}", "ok")

    def _mark_failed(self, key: str, stats: dict, label: str):
        stats["failed_count"] += 1
        stats["failed_labels"].append(label)
        self.after(0, self._fix_set_status, key, "Failed", "issue")

    def _fix_done(self, stats: dict, elapsed: float):
        self._fix_progress_frame.pack_forget()

        # Recalculate remaining issues for the header counter
        remaining = sum(1 for v in self._scan_results.values()
                        if isinstance(v, int) and v > 0) - stats["fixed_count"]
        remaining = max(remaining, 0)
        self._total_lbl.config(
            text=f"{remaining} issue(s) remaining" if remaining else "All clean ✓",
            fg=T.WARNING if remaining else T.SUCCESS,
        )

        # Build stats summary
        freed_str = disk_cleaner._format_size(stats["bytes_freed"]) if stats["bytes_freed"] else "0 B"
        summary_lines = [
            f"Fixed: {stats['fixed_count']}   Failed: {stats['failed_count']}",
            f"Freed: {freed_str}   Removed: {stats['items_removed']} items",
            f"Time: {elapsed:.1f}s",
        ]
        details = "\n".join(stats["fixed_labels"][:6])
        if stats["failed_labels"]:
            details += "\n\nFailed:\n" + "\n".join(stats["failed_labels"][:3])

        # Color border by outcome
        border_color = T.SUCCESS if stats["failed_count"] == 0 else T.WARNING
        title = "✓ All Fixes Applied" if stats["failed_count"] == 0 else "⚠ Fixes Applied with Warnings"
        self._fix_result_frame.config(highlightbackground=border_color)
        self._fix_result_title.config(text=title, fg=border_color)
        self._fix_result_stats.config(text="\n".join(summary_lines))
        self._fix_result_details.config(text=details)
        self._fix_result_frame.pack(fill="x", padx=8, pady=(8, 0))

        self._scan_status_lbl.config(
            text=f"Done — {stats['fixed_count']} fix(es) applied in {elapsed:.1f}s")
        self._fix_btn.config(state="disabled")  # keep disabled until next scan

        # Clear in-memory results so a re-scan is required for further fixes
        self._scan_results = {k: 0 for k in self._scan_results}

        # Update action center
        if hasattr(self._app, "_pages") and "action" in self._app._pages:
            try:
                self._app._pages["action"].update_from_scan(self._scan_results)
            except Exception:
                pass
