"""PC Speedup Wizard — guided one-click optimization."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar


_STEPS = [
    ("disk",     "Disk Cleaner",       "Scan and remove junk files"),
    ("registry", "Registry Cleaner",   "Fix registry errors"),
    ("startup",  "Startup Optimizer",  "Analyze startup impact"),
    ("memory",   "Memory Optimizer",   "Optimize RAM usage"),
    ("privacy",  "Privacy Cleaner",    "Remove tracking data"),
]


class SpeedupWizardPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._running = False
        self._results: dict[str, dict] = {}
        self._step_labels: dict[str, tk.Label] = {}
        self._step_status: dict[str, tk.Label] = {}
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="PC Speedup Wizard", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="One-click guided system optimization",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        intro_card = Card(body)
        intro_card.pack(fill="x", pady=(0, 12))
        SectionLabel(intro_card, "Welcome to the PC Speedup Wizard").pack(anchor="w", padx=10, pady=8)
        tk.Label(intro_card,
                 text="The wizard will run a series of optimizations automatically.\n"
                      "Review the results and apply the recommended fixes with one click.",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY, justify="left"
                 ).pack(anchor="w", padx=10, pady=(0, 8))

        steps_card = Card(body)
        steps_card.pack(fill="x", pady=(0, 12))
        SectionLabel(steps_card, "Optimization Steps").pack(anchor="w", padx=10, pady=8)

        for key, title, desc in _STEPS:
            row = tk.Frame(steps_card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=3)

            tk.Label(row, text=title, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BOLD, width=20, anchor="w").pack(side="left")
            tk.Label(row, text=desc, bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, anchor="w").pack(side="left", expand=True, fill="x")

            status = tk.Label(row, text="Waiting", bg=T.PANEL, fg=T.FG2,
                              font=T.FONT_SMALL, width=12, anchor="e")
            status.pack(side="right")
            self._step_status[key] = status

        tk.Frame(steps_card, bg=T.PANEL, height=8).pack()

        progress_card = Card(body)
        progress_card.pack(fill="x", pady=(0, 12))
        SectionLabel(progress_card, "Progress").pack(anchor="w", padx=10, pady=8)
        self._progress = ProgressBar(progress_card)
        self._progress.pack(fill="x", padx=10, pady=(0, 4))
        self._progress_label = tk.Label(progress_card, text="Ready",
                                        bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._progress_label.pack(anchor="w", padx=10, pady=(0, 8))

        results_card = Card(body)
        results_card.pack(fill="both", expand=True)
        SectionLabel(results_card, "Results").pack(anchor="w", padx=10, pady=8)

        self._results_text = tk.Text(results_card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                     height=6, bd=0, padx=8, pady=6,
                                     state="disabled", wrap="word")
        self._results_text.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        btn_row = tk.Frame(results_card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        self._start_btn = ActionButton(btn_row, text="Start Optimization Wizard",
                                       command=self._on_start)
        self._start_btn.pack(side="left", padx=(0, 6))
        self._apply_btn = ActionButton(btn_row, text="Apply All Fixes",
                                       command=self._on_apply)
        self._apply_btn.pack(side="left")
        self._apply_btn.config(state="disabled")

    def _set_step_status(self, key: str, text: str, color: str):
        self.after(0, lambda: self._step_status[key].config(text=text, fg=color))

    def _on_start(self):
        if self._running:
            return
        self._running = True
        self._results = {}
        self._start_btn.config(state="disabled")
        self._apply_btn.config(state="disabled")
        for key, _, _ in _STEPS:
            self._step_status[key].config(text="Waiting", fg=T.FG2)

        def run():
            total = len(_STEPS)
            for i, (key, title, _) in enumerate(_STEPS):
                self._set_step_status(key, "Scanning...", T.WARNING)
                pct = int(i / total * 100)
                self.after(0, lambda p=pct, t=title: (
                    self._progress.set_value(p),
                    self._progress_label.config(text=f"Running: {t}...")
                ))

                try:
                    result = self._run_step(key)
                    self._results[key] = result
                    issues = result.get("issues", 0)
                    size = result.get("size_str", "")
                    if issues > 0 or size:
                        label = f"{issues} issues" if issues else size
                        self._set_step_status(key, label, T.WARNING)
                    else:
                        self._set_step_status(key, "OK", T.SUCCESS)
                except Exception as e:
                    self._results[key] = {"error": str(e)}
                    self._set_step_status(key, "Error", T.DANGER)

            self.after(0, self._show_results)
            self._running = False

        threading.Thread(target=run, daemon=True).start()

    def _run_step(self, key: str) -> dict:
        if key == "disk":
            from engine import disk_cleaner
            items = disk_cleaner.scan_junk()
            total = sum(i.size for i in items)
            return {"issues": len(items), "size": total,
                    "size_str": _fmt_bytes(total), "items": items}

        if key == "registry":
            from engine import registry_cleaner
            issues = registry_cleaner.scan_registry()
            return {"issues": len(issues), "data": issues}

        if key == "startup":
            from engine import startup_manager
            entries = startup_manager.get_startup_entries_with_impact()
            high = [e for e in entries if e.impact == "High" and e.enabled]
            return {"issues": len(high), "entries": entries, "high": high}

        if key == "memory":
            try:
                import psutil
                mem = psutil.virtual_memory()
                return {"issues": 1 if mem.percent > 80 else 0,
                        "size_str": f"{mem.percent:.0f}% used"}
            except Exception:
                return {"issues": 0}

        if key == "privacy":
            from engine import privacy_cleaner
            items = privacy_cleaner.scan_browser_privacy()
            total = sum(i.get("size", 0) for i in items)
            return {"issues": len(items), "size": total,
                    "size_str": _fmt_bytes(total), "items": items}

        return {}

    def _show_results(self):
        self._progress.set_value(100)
        self._progress_label.config(text="Scan complete")

        lines = []
        total_issues = 0
        total_size = 0

        for key, title, _ in _STEPS:
            r = self._results.get(key, {})
            issues = r.get("issues", 0)
            size = r.get("size", 0)
            total_issues += issues
            total_size += size
            if issues:
                lines.append(f"  {title}: {issues} issue(s)" +
                             (f" — {r['size_str']}" if r.get("size_str") else ""))

        self._results_text.config(state="normal")
        self._results_text.delete("1.0", "end")
        if lines:
            self._results_text.insert("end", f"Found {total_issues} issues ({_fmt_bytes(total_size)} to free):\n\n")
            self._results_text.insert("end", "\n".join(lines))
        else:
            self._results_text.insert("end", "Your PC looks great! No issues found.")
        self._results_text.config(state="disabled")

        self._start_btn.config(state="normal")
        if total_issues > 0:
            self._apply_btn.config(state="normal")

    def _on_apply(self):
        if not messagebox.askyesno("Apply All Fixes",
                "Apply all recommended fixes?\n\nThis will clean junk files, fix registry, optimize startup and privacy."):
            return

        self._apply_btn.config(state="disabled")

        def apply():
            done = []
            for key, title, _ in _STEPS:
                r = self._results.get(key, {})
                try:
                    if key == "disk" and r.get("items"):
                        from engine import disk_cleaner
                        disk_cleaner.clean_items(r["items"])
                        done.append(f"Disk Cleaner: cleaned")
                    elif key == "registry" and r.get("data"):
                        from engine import registry_cleaner
                        registry_cleaner.fix_issues(r["data"])
                        done.append(f"Registry: fixed {len(r['data'])} issues")
                    elif key == "privacy" and r.get("items"):
                        from engine import privacy_cleaner
                        freed, _ = privacy_cleaner.clean_browser_privacy(r["items"])
                        done.append(f"Privacy: cleaned {_fmt_bytes(freed)}")
                    elif key == "memory":
                        from engine import memory_optimizer
                        memory_optimizer.free_ram()
                        done.append("Memory: optimized")
                except Exception as e:
                    done.append(f"{title}: error — {e}")

            self.after(0, lambda: messagebox.showinfo("Done",
                "Applied fixes:\n" + "\n".join(done)))
            self.after(0, self._on_start)  # re-scan after apply

        threading.Thread(target=apply, daemon=True).start()

    def on_activate(self):
        pass


def _fmt_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"
