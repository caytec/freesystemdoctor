"""Release Publisher page — one-click upload to download portals worldwide."""

import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar


def _get_internal_browser_panel():
    """Lazy import to avoid circular dependencies."""
    try:
        from publisher_app import InternalBrowserPanel
        return InternalBrowserPanel
    except ImportError:
        return None


class PublisherPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._publishing = False
        self._target_vars: dict[str, tk.BooleanVar] = {}
        self._build_ui()
        self._load_targets()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🌍  Publisher", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Upload releases to download portals worldwide",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Top control card ─────────────────────────────────────────────────
        ctrl = Card(body)
        ctrl.pack(fill="x", pady=(0, 8))
        SectionLabel(ctrl, "Release Configuration").pack(
            anchor="w", padx=12, pady=8)

        row1 = tk.Frame(ctrl, bg=T.PANEL)
        row1.pack(fill="x", padx=12, pady=4)

        tk.Label(row1, text="Version:", bg=T.PANEL, fg=T.FG2,
                 width=10, anchor="w", font=T.FONT_BODY).pack(side="left")
        self._version_entry = tk.Entry(row1, bg=T.ACCENT, fg=T.FG,
                                         font=T.FONT_BODY, width=14,
                                         insertbackground=T.FG)
        self._version_entry.pack(side="left", padx=8)

        try:
            from publisher.config import get_version
            self._version_entry.insert(0, get_version())
        except Exception:
            self._version_entry.insert(0, "2.2.0")

        ActionButton(row1, text="🔨 Build Artifacts",
                      command=self._on_build, width=160).pack(
            side="left", padx=(8, 4))
        ActionButton(row1, text="🚀 Publish to APIs",
                      command=self._on_publish_apis, width=160).pack(
            side="left", padx=4)
        ActionButton(row1, text="🌐 Open Manual Sites",
                      command=self._on_publish_manual, width=160,
                      secondary=True).pack(side="left", padx=4)
        ActionButton(row1, text="📊 Dashboard",
                      command=self._on_dashboard, width=120,
                      secondary=True).pack(side="left", padx=4)

        self._progress = ProgressBar(ctrl)
        self._progress.pack(fill="x", padx=12, pady=(8, 4))

        self._status_lbl = tk.Label(ctrl, text="Ready to release.",
                                      bg=T.PANEL, fg=T.FG2,
                                      font=T.FONT_SMALL, anchor="w")
        self._status_lbl.pack(fill="x", padx=12, pady=(0, 12))

        # ── Targets list ─────────────────────────────────────────────────────
        targets_card = Card(body)
        targets_card.pack(fill="both", expand=True)
        SectionLabel(targets_card, "Submission Targets").pack(
            anchor="w", padx=12, pady=8)

        # Filter row
        filter_row = tk.Frame(targets_card, bg=T.PANEL)
        filter_row.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(filter_row, text="Filter:", bg=T.PANEL, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left", padx=(0, 4))

        self._filter_var = tk.StringVar(value="all")
        for label, val in [("All", "all"), ("API only", "api"),
                            ("Global", "global"), ("Polska", "poland")]:
            tk.Radiobutton(filter_row, text=label, value=val,
                            variable=self._filter_var,
                            bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
                            activebackground=T.PANEL,
                            font=T.FONT_SMALL,
                            command=self._refresh_target_list).pack(
                side="left", padx=(0, 8))

        ActionButton(filter_row, text="✓ All", command=self._select_all,
                      width=70, secondary=True).pack(side="right", padx=2)
        ActionButton(filter_row, text="○ None", command=self._select_none,
                      width=70, secondary=True).pack(side="right", padx=2)

        # Scrollable targets area
        scroll_frame = tk.Frame(targets_card, bg=T.PANEL)
        scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        canvas = tk.Canvas(scroll_frame, bg=T.PANEL, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(scroll_frame, orient="vertical",
                            command=canvas.yview)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)

        self._inner = tk.Frame(canvas, bg=T.PANEL)
        self._inner_id = canvas.create_window(0, 0, window=self._inner, anchor="nw")
        self._canvas = canvas
        self._inner.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                     lambda e: canvas.itemconfig(self._inner_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                         lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _load_targets(self):
        try:
            from publisher.directory import SUBMISSION_TARGETS
            self._targets = SUBMISSION_TARGETS
        except Exception as e:
            self._targets = []
            self._status_lbl.config(text=f"Failed to load targets: {e}",
                                      fg=T.DANGER)
            return

        for t in self._targets:
            self._target_vars[t["id"]] = tk.BooleanVar(
                value=t["type"] == "api")  # APIs default-on, manual default-off

        self._refresh_target_list()

    def _refresh_target_list(self):
        for w in self._inner.winfo_children():
            w.destroy()

        flt = self._filter_var.get()

        # Group by region
        groups = {"global": [], "poland": []}
        for t in self._targets:
            if flt == "api" and t["type"] != "api":
                continue
            if flt in ("global", "poland") and t["region"] != flt:
                continue
            groups.setdefault(t["region"], []).append(t)

        for region, label, color in [
            ("global", "🌍 Global", T.HIGHLIGHT),
            ("poland", "🇵🇱 Polska", T.SUCCESS),
        ]:
            if not groups.get(region):
                continue
            section = tk.Frame(self._inner, bg=T.PANEL)
            section.pack(fill="x", pady=(8, 4))
            tk.Label(section, text=label, bg=T.PANEL, fg=color,
                     font=T.FONT_H3, anchor="w").pack(fill="x")

            for t in groups[region]:
                self._add_target_row(t)

    def _add_target_row(self, target):
        row = tk.Frame(self._inner, bg=T.lerp_color(T.PANEL, T.ACCENT, 0.2),
                        padx=10, pady=4)
        row.pack(fill="x", pady=1)

        tk.Checkbutton(row, variable=self._target_vars[target["id"]],
                        bg=row.cget("bg"), fg=T.FG,
                        selectcolor=T.ACCENT,
                        activebackground=row.cget("bg")).pack(side="left")

        type_color = T.HIGHLIGHT if target["type"] == "api" else T.FG2
        type_label = "[ API ]" if target["type"] == "api" else "[MANUAL]"
        tk.Label(row, text=type_label, bg=row.cget("bg"), fg=type_color,
                 font=T.FONT_MICRO, width=8).pack(side="left", padx=4)

        tk.Label(row, text=target["label"], bg=row.cget("bg"), fg=T.FG,
                 font=T.FONT_BOLD, width=30, anchor="w").pack(side="left")

        tk.Label(row, text=target.get("notes", ""),
                 bg=row.cget("bg"), fg=T.FG2, font=T.FONT_MICRO,
                 anchor="w").pack(side="left", fill="x", expand=True)

        ActionButton(row, text="↗ Open",
                      command=lambda t=target: self._open_one(t),
                      width=70, secondary=True).pack(side="right")

    def _select_all(self):
        for v in self._target_vars.values():
            v.set(True)

    def _select_none(self):
        for v in self._target_vars.values():
            v.set(False)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_build(self):
        if self._publishing:
            return
        self._publishing = True
        version = self._version_entry.get().strip()
        self._status_lbl.config(text=f"Building v{version}…", fg=T.FG2)
        self._progress.indeterminate(True)

        def work():
            try:
                from publisher.config import save_version
                from publisher.release_builder import build_release_artifacts
                save_version(version)
                manifest = build_release_artifacts(version=version)
                self.after(0, lambda: self._after_build(manifest, None))
            except Exception as e:
                self.after(0, lambda: self._after_build(None, str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _after_build(self, manifest, error):
        self._progress.indeterminate(False)
        self._publishing = False
        if error:
            self._status_lbl.config(text=f"Build failed: {error}", fg=T.DANGER)
            messagebox.showerror("Build error", error)
            return
        self._status_lbl.config(
            text=f"✓ Built {len(manifest['artifacts'])} artifacts in {manifest['release_dir']}",
            fg=T.SUCCESS)

    def _on_publish_apis(self):
        if self._publishing:
            return
        version = self._version_entry.get().strip()
        selected_apis = [t for t in self._targets
                          if t["type"] == "api"
                          and self._target_vars[t["id"]].get()]
        if not selected_apis:
            messagebox.showinfo("No targets", "No API targets selected.")
            return

        self._publishing = True
        self._status_lbl.config(text="Building artifacts…", fg=T.FG2)
        self._progress.set(0)

        def work():
            try:
                from publisher.release_builder import build_release_artifacts
                from publisher.orchestrator import publish_to
                manifest = build_release_artifacts(
                    version=version, skip_build=False)
                self.after(0, lambda: self._status_lbl.config(
                    text="Publishing to API targets…", fg=T.FG2))

                results = []
                for i, target in enumerate(selected_apis):
                    self.after(0, lambda v=(i / len(selected_apis) * 100):
                                self._progress.set(v))
                    self.after(0, lambda lbl=target["label"]:
                                self._status_lbl.config(
                                    text=f"Publishing to {lbl}…",
                                    fg=T.FG2))
                    r = publish_to(target["id"], manifest, open_browser=False)
                    results.append((target, r))

                self.after(0, lambda: self._after_publish(results, None))
            except Exception as e:
                self.after(0, lambda: self._after_publish([], str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _after_publish(self, results, error):
        self._progress.set(100)
        self._publishing = False

        if error:
            self._status_lbl.config(text=f"Publish failed: {error}", fg=T.DANGER)
            messagebox.showerror("Publish error", error)
            return

        ok = sum(1 for _, r in results if r.get("ok"))
        total = len(results)
        self._status_lbl.config(
            text=f"✓ {ok}/{total} targets published successfully",
            fg=T.SUCCESS if ok == total else T.WARNING)

        # Show results dialog
        msg_lines = []
        for target, r in results:
            icon = "✓" if r.get("ok") else "✗"
            msg_lines.append(f"{icon} {target['label']}")
            if r.get("msg"):
                msg_lines.append(f"   {r['msg'][:80]}")
            if r.get("url"):
                msg_lines.append(f"   {r['url']}")
        messagebox.showinfo("Publish results", "\n".join(msg_lines))

    def _on_publish_manual(self):
        version = self._version_entry.get().strip()
        selected = [t for t in self._targets
                     if t["type"] == "manual"
                     and self._target_vars[t["id"]].get()]
        if not selected:
            messagebox.showinfo("No targets",
                                  "Select at least one manual site.")
            return

        if not messagebox.askyesno(
                "Manual Submission Queue",
                f"Open submission queue for {len(selected)} manual sites?\n\n"
                f"You'll submit to each site one at a time with submission text "
                f"pre-filled in your clipboard."):
            return

        def work():
            try:
                from publisher.release_builder import build_release_artifacts
                from publisher.manual_submitter import ManualSubmissionQueue
                from publisher.config import get_version
                manifest = build_release_artifacts(
                    version=version, skip_build=True)

                # Create queue and open in dialog
                queue = ManualSubmissionQueue(manifest, region=None)
                self.after(0, lambda q=queue: self._show_queue_dialog(q))

                self.after(0, lambda: self._status_lbl.config(
                    text="Opening manual submission queue...",
                    fg=T.HIGHLIGHT))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._status_lbl.config(
                    text=f"Failed: {err}", fg=T.DANGER))

        threading.Thread(target=work, daemon=True).start()

    def _show_queue_dialog(self, queue):
        """Show manual submission queue dialog (simplified version)."""
        try:
            # Try to import and use the InternalBrowserPanel from publisher_app
            from publisher_app import InternalBrowserPanel
            # Create a dummy toplevel parent
            parent = self.winfo_toplevel()
            InternalBrowserPanel(parent, queue.manifest)
        except Exception:
            # Fallback: simple message with next site
            self._status_lbl.config(
                text="Manual submission queue opened (check system windows)",
                fg=T.SUCCESS)

    def _open_one(self, target):
        version = self._version_entry.get().strip()

        def work():
            try:
                from publisher.release_builder import build_release_artifacts
                from publisher.orchestrator import publish_to
                manifest = build_release_artifacts(
                    version=version, skip_build=True)
                r = publish_to(target["id"], manifest, open_browser=True)
                self.after(0, lambda: self._status_lbl.config(
                    text=f"{target['label']}: {r.get('msg', '')[:80]}",
                    fg=T.SUCCESS if r.get("ok") else T.DANGER))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._status_lbl.config(
                    text=f"Failed: {err}", fg=T.DANGER))

        threading.Thread(target=work, daemon=True).start()

    def _on_dashboard(self):
        version = self._version_entry.get().strip()
        try:
            from publisher.orchestrator import open_dashboard_url
            path = open_dashboard_url(version)
            webbrowser.open(f"file:///{path}")
        except Exception as e:
            messagebox.showerror("Dashboard", str(e))

    def on_activate(self):
        pass
