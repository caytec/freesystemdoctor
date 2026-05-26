"""Publisher — standalone GUI tool to push any software to 30+ download portals.

Self-contained launcher. Works for FreeSystemDoctor or any other Windows EXE.
Run with:  python publisher_app.py
"""

import json
import os
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

# Ensure the publisher package is importable
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from publisher.directory import SUBMISSION_TARGETS
from publisher.config import RELEASE_CONFIG, ROOT as PUB_ROOT


# ── Theme ──────────────────────────────────────────────────────────────────────
BG       = "#0d1117"
PANEL    = "#161b27"
ACCENT   = "#1c2438"
SIDEBAR  = "#0a0e1a"
HIGHLIGHT= "#00d4ff"
HL_END   = "#0099cc"
PURPLE   = "#7b61ff"
SUCCESS  = "#00e676"
WARNING  = "#ffab40"
DANGER   = "#ff5252"
FG       = "#e8edf5"
FG2      = "#6b7a99"
BORDER   = "#1e2d45"
FONT     = ("Segoe UI", 10)
FONT_B   = ("Segoe UI", 10, "bold")
FONT_SM  = ("Segoe UI", 9)
FONT_T   = ("Segoe UI", 14, "bold")
FONT_H   = ("Segoe UI", 11, "bold")


PROFILE_FILE = ROOT / ".publisher_profile.json"


def load_profile() -> dict:
    if PROFILE_FILE.exists():
        try:
            return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Defaults from RELEASE_CONFIG
    return {
        "name":         RELEASE_CONFIG["name"],
        "display_name": RELEASE_CONFIG["display_name"],
        "version":      RELEASE_CONFIG["version"],
        "publisher":    RELEASE_CONFIG["publisher"],
        "homepage":     RELEASE_CONFIG["homepage"],
        "license":      RELEASE_CONFIG["license"],
        "summary":      RELEASE_CONFIG["summary"],
        "description":  RELEASE_CONFIG["description"],
        "tags":         ", ".join(RELEASE_CONFIG.get("tags", [])),
        "exe_path":     str(ROOT / "dist" / RELEASE_CONFIG["exe_name"]),
        "github_owner": RELEASE_CONFIG["github_owner"],
        "github_repo":  RELEASE_CONFIG["github_repo"],
    }


def save_profile(data: dict):
    PROFILE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Custom widgets ─────────────────────────────────────────────────────────────

class GradButton(tk.Canvas):
    """Gradient button with hover."""
    def __init__(self, parent, text, command=None, width=160, height=34,
                 c1=HL_END, c2=HIGHLIGHT, **kw):
        try:
            parent_bg = parent.cget("bg") if hasattr(parent, "cget") else PANEL
            if not parent_bg or not str(parent_bg).startswith("#"):
                parent_bg = PANEL
        except Exception:
            parent_bg = PANEL

        super().__init__(parent, bg=parent_bg, highlightthickness=0,
                          width=width, height=height, bd=0)
        self._W, self._H = width, height   # avoid clobbering Tk's _w
        self._text = text
        self._cmd = command
        self._c1, self._c2 = c1, c2
        self._hover = False
        self._draw()
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self._click())
        self.config(cursor="hand2")

    def _set_hover(self, h):
        self._hover = h
        self._draw()

    def _click(self):
        if self._cmd:
            self._cmd()

    def _lerp(self, a, b, t):
        ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
        br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
        return f"#{int(ar+(br-ar)*t):02x}{int(ag+(bg-ag)*t):02x}{int(ab+(bb-ab)*t):02x}"

    def _draw(self):
        self.delete("all")
        c1 = self._lerp(self._c1, "#ffffff", 0.1) if self._hover else self._c1
        c2 = self._lerp(self._c2, "#ffffff", 0.1) if self._hover else self._c2
        steps = 16
        for i in range(steps):
            t = i / steps
            col = self._lerp(c1, c2, t)
            x = int(self._W * t)
            xn = int(self._W * (i + 1) / steps) + 1
            self.create_rectangle(x, 0, xn, self._H, fill=col, outline="")
        # Border
        self.create_rectangle(0, 0, self._W-1, self._H-1, outline=self._lerp(c2, "#ffffff", 0.3 if self._hover else 0))
        # Top shine
        self.create_rectangle(1, 1, self._W-1, self._H//2, fill=self._lerp(c2, "#ffffff", 0.15), outline="")
        self.create_text(self._W//2, self._H//2, text=self._text,
                          fill="#ffffff", font=FONT_B)


def open_url_safe(url: str) -> bool:
    """Open URL in default browser via subprocess (prevents tab flooding)."""
    try:
        import subprocess
        subprocess.Popen(["start", "", url], shell=True,
                        creationflags=0x08000000)  # No console
        return True
    except Exception:
        return False


class InternalBrowserPanel(tk.Toplevel):
    """Queue-based manual submission panel."""
    def __init__(self, parent, manifest):
        super().__init__(parent)
        self.title("Manual Site Submission Queue")
        self.geometry("1000x700")
        self.configure(bg=BG)

        from publisher.manual_submitter import ManualSubmissionQueue
        self.queue = ManualSubmissionQueue(manifest, region=None)
        self.manifest = manifest
        self._opening_browser = False

        self._build()
        self._update_display()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=ACCENT, height=50)
        hdr.pack(fill="x", padx=0, pady=0)
        hdr.pack_propagate(False)

        prog_text, total = self.queue.get_progress()
        tk.Label(hdr, text=f"Manual Submission Queue: {prog_text} of {total}",
                bg=ACCENT, fg=HIGHLIGHT, font=FONT_H).pack(side="left", padx=14, pady=12)

        # Main container (sidebar + content)
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=0, pady=0)

        # Left sidebar: target list
        left = tk.Frame(main, bg=PANEL, width=200)
        left.pack(side="left", fill="both", padx=0, pady=0)
        left.pack_propagate(False)

        tk.Label(left, text="Sites to Submit", bg=PANEL, fg=HIGHLIGHT,
                font=FONT_B).pack(pady=8, padx=6)

        self._target_listbox = tk.Listbox(left, bg=ACCENT, fg=FG,
                                          font=FONT_SM, highlightthickness=0, bd=0)
        self._target_listbox.pack(fill="both", expand=True, padx=6, pady=6)

        for i, t in enumerate(self.queue.targets):
            self._target_listbox.insert(i, t["label"])

        # Right sidebar: submission text
        right = tk.Frame(main, bg=PANEL, width=250)
        right.pack(side="right", fill="both", padx=0, pady=0)
        right.pack_propagate(False)

        tk.Label(right, text="Submission Text", bg=PANEL, fg=HIGHLIGHT,
                font=FONT_B).pack(pady=8, padx=6)

        text_frame = tk.Frame(right, bg=ACCENT)
        text_frame.pack(fill="both", expand=True, padx=6, pady=6)

        self._text_widget = tk.Text(text_frame, bg=ACCENT, fg=FG, font=FONT_SM,
                                     wrap="word", state="disabled")
        self._text_widget.pack(fill="both", expand=True)

        # Center: main content
        center = tk.Frame(main, bg=BG)
        center.pack(side="left", fill="both", expand=True, padx=12, pady=12)

        tk.Label(center, text="Current Site", bg=BG, fg=HIGHLIGHT,
                font=FONT_B).pack(pady=8)

        self._url_label = tk.Label(center, text="", bg=ACCENT, fg="#00d4ff",
                                   font=FONT_SM, wraplength=500, justify="left")
        self._url_label.pack(fill="x", padx=8, pady=4)

        inst_text = ("Open the submission form in your browser using the button below.\n"
                    "Fill out the form and submit. Then return here and click\n"
                    "'Mark Done & Next Site' to move to the next submission.")
        tk.Label(center, text=inst_text, bg=BG, fg=FG2, font=FONT_SM,
                justify="left").pack(pady=12, padx=8)

        # Buttons
        btn_frame = tk.Frame(center, bg=BG)
        btn_frame.pack(fill="x", pady=20)

        GradButton(btn_frame, "Open in Browser",
                  command=self._open_current, width=140, height=36).pack(side="left", padx=4)
        GradButton(btn_frame, "Skip This Site",
                  command=self._skip_current, width=140, height=36,
                  c1="#ff7a5c", c2="#ff9c6e").pack(side="left", padx=4)
        GradButton(btn_frame, "Mark Done & Next",
                  command=self._mark_done, width=140, height=36,
                  c1="#45b393", c2="#5ec9a0").pack(side="left", padx=4)
        GradButton(btn_frame, "Cancel All",
                  command=self._cancel, width=140, height=36,
                  c1="#666666", c2="#888888").pack(side="left", padx=4)

        # Status bar
        self._status_label = tk.Label(self, text="", bg=ACCENT, fg=FG2, font=FONT_SM)
        self._status_label.pack(fill="x", padx=12, pady=8)

    def _update_display(self):
        """Update UI to show current target."""
        if self.queue.is_done():
            self._status_label.config(text="✓ All sites processed!")
            return

        target = self.queue.get_current_target()
        url = self.queue.get_current_url()
        prog_text, total = self.queue.get_progress()

        # Update header
        self.title(f"Manual Submission: {prog_text} of {total}")

        # Update listbox highlight
        self._target_listbox.selection_clear(0, "end")
        self._target_listbox.selection_set(self.queue.current_index)
        self._target_listbox.see(self.queue.current_index)

        # Update URL
        self._url_label.config(text=f"URL: {url}")

        # Update submission text
        self._text_widget.config(state="normal")
        self._text_widget.delete("1.0", "end")
        self._text_widget.insert("1.0", self.queue.submission_text)
        self._text_widget.config(state="disabled")

        # Update status
        submitted = self.queue.submitted_count
        skipped = self.queue.skipped_count
        self._status_label.config(
            text=f"Progress: {prog_text}/{total} | Submitted: {submitted} | Skipped: {skipped}"
        )

    def _open_current(self):
        """Open current URL in browser."""
        if self._opening_browser:
            messagebox.showinfo("Wait", "URL is already opening...")
            return

        url = self.queue.get_current_url()
        if not url:
            messagebox.showerror("Error", "No URL available")
            return

        self._opening_browser = True
        try:
            if open_url_safe(url):
                messagebox.showinfo("Browser opened",
                                  f"Opening {self.queue.get_current_label()} in your browser.\n\n"
                                  f"Fill out the form and submit, then return here.")
            else:
                messagebox.showerror("Error", "Failed to open browser")
        finally:
            self._opening_browser = False

    def _skip_current(self):
        """Skip current site and move to next."""
        has_more = self.queue.skip()
        if has_more:
            self._update_display()
        else:
            messagebox.showinfo("Done", f"Skipped all remaining sites.\n"
                              f"Submitted: {self.queue.submitted_count}, "
                              f"Skipped: {self.queue.skipped_count}")
            self.destroy()

    def _mark_done(self):
        """Mark current as done and move to next."""
        has_more = self.queue.advance()
        if has_more:
            self._update_display()
        else:
            messagebox.showinfo("Complete!", f"✓ All sites processed!\n"
                              f"Submitted: {self.queue.submitted_count}, "
                              f"Skipped: {self.queue.skipped_count}")
            self.destroy()

    def _cancel(self):
        """Cancel submission queue."""
        if messagebox.askyesno("Cancel", "Cancel all remaining submissions?"):
            self.destroy()


# ── Main App ───────────────────────────────────────────────────────────────────

class PublisherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Publisher — Multi-Channel Software Distribution")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(bg=BG)

        self._profile = load_profile()
        self._target_vars = {}
        self._publishing = False

        self._setup_styles()
        self._build()

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TScrollbar", background=ACCENT, troughcolor=PANEL,
                         borderwidth=0, arrowsize=10)
        style.configure("TCombobox", fieldbackground=ACCENT, background=ACCENT,
                         foreground=FG, borderwidth=0)

    def _build(self):
        # ── Titlebar ───────────────────────────────────────────────────────────
        titlebar = tk.Frame(self, bg=SIDEBAR, height=56)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)

        logo = tk.Canvas(titlebar, width=44, height=44, bg=SIDEBAR,
                          highlightthickness=0)
        logo.pack(side="left", padx=(16, 8), pady=6)
        logo.create_oval(2, 2, 42, 42,
                          fill=self._lerp(SIDEBAR, HIGHLIGHT, 0.25),
                          outline=HIGHLIGHT, width=2)
        logo.create_text(22, 22, text="📤", fill=HIGHLIGHT,
                          font=("Segoe UI", 16))

        text_frame = tk.Frame(titlebar, bg=SIDEBAR)
        text_frame.pack(side="left", pady=4)
        tk.Label(text_frame, text="Publisher",
                 bg=SIDEBAR, fg=FG, font=("Segoe UI", 16, "bold"),
                 anchor="w").pack(anchor="w")
        tk.Label(text_frame, text="Push your software to 30+ download portals worldwide",
                 bg=SIDEBAR, fg=FG2, font=FONT_SM, anchor="w").pack(anchor="w")

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Body: 2 columns (form left, targets right) ─────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # Left: metadata form (380 px)
        left = tk.Frame(body, bg=BG, width=400)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_form(left)

        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # Right: targets + status
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_targets(right)

        # ── Bottom action bar ──────────────────────────────────────────────────
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        bottom = tk.Frame(self, bg=SIDEBAR, height=72)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)
        self._build_actions(bottom)

    # ── Form ───────────────────────────────────────────────────────────────────

    def _build_form(self, parent):
        tk.Label(parent, text="📦  Project Metadata",
                 bg=BG, fg=HIGHLIGHT, font=FONT_T,
                 anchor="w").pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(parent, text="Edit and save once — reused for every release.",
                 bg=BG, fg=FG2, font=FONT_SM,
                 anchor="w").pack(anchor="w", padx=14, pady=(0, 8))

        # Scrollable form
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True, padx=(8, 0))
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window(0, 0, window=inner, anchor="nw")
        inner.bind("<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                     lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind("<MouseWheel>",
                     lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._form_entries = {}
        fields = [
            ("name",         "Name (no spaces)",      "entry"),
            ("display_name", "Display Name",          "entry"),
            ("version",      "Version",               "entry"),
            ("publisher",    "Publisher",             "entry"),
            ("homepage",     "Homepage URL",          "entry"),
            ("github_owner", "GitHub Owner",          "entry"),
            ("github_repo",  "GitHub Repo",           "entry"),
            ("license",      "License",               "entry"),
            ("tags",         "Tags (comma-separated)","entry"),
            ("summary",      "Short Summary",         "entry"),
            ("description",  "Full Description",      "text"),
            ("exe_path",     "EXE File Path",         "file"),
        ]

        for key, label, kind in fields:
            row = tk.Frame(inner, bg=BG)
            row.pack(fill="x", padx=14, pady=4)
            tk.Label(row, text=label, bg=BG, fg=FG2, font=FONT_SM,
                     anchor="w").pack(anchor="w")

            if kind == "text":
                widget = tk.Text(row, bg=ACCENT, fg=FG, insertbackground=FG,
                                  font=FONT_SM, height=5, wrap="word",
                                  borderwidth=0, padx=8, pady=6)
                widget.pack(fill="x")
                widget.insert("1.0", str(self._profile.get(key, "")))
            elif kind == "file":
                fr = tk.Frame(row, bg=BG)
                fr.pack(fill="x")
                widget = tk.Entry(fr, bg=ACCENT, fg=FG, insertbackground=FG,
                                   font=FONT_SM, borderwidth=0)
                widget.pack(side="left", fill="x", expand=True, ipady=4)
                widget.insert(0, str(self._profile.get(key, "")))
                btn = tk.Button(fr, text="…", command=lambda w=widget: self._browse_exe(w),
                                bg=ACCENT, fg=FG, font=FONT_B, relief="flat",
                                padx=10, cursor="hand2")
                btn.pack(side="left", padx=(4, 0))
            else:
                widget = tk.Entry(row, bg=ACCENT, fg=FG, insertbackground=FG,
                                   font=FONT_SM, borderwidth=0)
                widget.pack(fill="x", ipady=4)
                widget.insert(0, str(self._profile.get(key, "")))

            self._form_entries[key] = widget

        # Save button
        save_row = tk.Frame(inner, bg=BG)
        save_row.pack(fill="x", padx=14, pady=10)
        GradButton(save_row, "💾  Save Profile",
                    command=self._save_profile, width=200, height=32).pack()

    def _browse_exe(self, entry_widget):
        path = filedialog.askopenfilename(
            title="Select EXE",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def _save_profile(self):
        for key, widget in self._form_entries.items():
            if isinstance(widget, tk.Text):
                self._profile[key] = widget.get("1.0", "end").strip()
            else:
                self._profile[key] = widget.get().strip()
        save_profile(self._profile)
        self._set_status("✓ Profile saved", SUCCESS)

    # ── Targets ────────────────────────────────────────────────────────────────

    def _build_targets(self, parent):
        # Header row
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill="x", padx=14, pady=(14, 4))
        tk.Label(hdr, text="🌍  Distribution Targets",
                 bg=BG, fg=HIGHLIGHT, font=FONT_T,
                 anchor="w").pack(side="left")

        api_count = sum(1 for t in SUBMISSION_TARGETS if t["type"] == "api")
        manual_count = sum(1 for t in SUBMISSION_TARGETS if t["type"] == "manual")
        tk.Label(hdr,
                 text=f"  {api_count} API • {manual_count} Manual • "
                       f"{len(SUBMISSION_TARGETS)} Total",
                 bg=BG, fg=FG2, font=FONT_SM).pack(side="left", padx=8)

        # Filter row
        filter_row = tk.Frame(parent, bg=BG)
        filter_row.pack(fill="x", padx=14, pady=(4, 8))

        self._filter_var = tk.StringVar(value="all")
        for label, val in [("All", "all"), ("API only", "api"),
                            ("🌍 Global", "global"), ("🇵🇱 Polska", "poland")]:
            tk.Radiobutton(filter_row, text=label, value=val,
                            variable=self._filter_var,
                            bg=BG, fg=FG, selectcolor=ACCENT,
                            activebackground=BG, activeforeground=HIGHLIGHT,
                            font=FONT_SM,
                            command=self._refresh_targets).pack(side="left", padx=(0, 8))

        tk.Label(filter_row, text="  Quick:", bg=BG, fg=FG2,
                 font=FONT_SM).pack(side="left", padx=(16, 4))
        for label, fn in [("✓ All", self._sel_all),
                           ("✓ API only", self._sel_api),
                           ("○ None", self._sel_none)]:
            tk.Button(filter_row, text=label, command=fn,
                       bg=ACCENT, fg=FG, font=FONT_SM, relief="flat",
                       padx=8, cursor="hand2").pack(side="left", padx=2)

        # Scrollable target list
        list_frame = tk.Frame(parent, bg=PANEL)
        list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        self._list_canvas = tk.Canvas(list_frame, bg=PANEL, highlightthickness=0)
        self._list_canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=self._list_canvas.yview)
        sb.pack(side="right", fill="y")
        self._list_canvas.configure(yscrollcommand=sb.set)

        self._list_inner = tk.Frame(self._list_canvas, bg=PANEL)
        self._list_win = self._list_canvas.create_window(
            0, 0, window=self._list_inner, anchor="nw")
        self._list_inner.bind("<Configure>",
                                lambda e: self._list_canvas.configure(
                                    scrollregion=self._list_canvas.bbox("all")))
        self._list_canvas.bind("<Configure>",
                                 lambda e: self._list_canvas.itemconfig(
                                     self._list_win, width=e.width))
        self._list_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._list_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"))

        # Init checkboxes
        for t in SUBMISSION_TARGETS:
            self._target_vars[t["id"]] = tk.BooleanVar(
                value=t["type"] == "api")

        self._refresh_targets()

    def _refresh_targets(self):
        for w in self._list_inner.winfo_children():
            w.destroy()

        flt = self._filter_var.get()
        groups = {"global": [], "poland": []}
        for t in SUBMISSION_TARGETS:
            if flt == "api" and t["type"] != "api":
                continue
            if flt in ("global", "poland") and t["region"] != flt:
                continue
            groups[t["region"]].append(t)

        for region, label, color in [
            ("global", "🌍  Global", HIGHLIGHT),
            ("poland", "🇵🇱  Polska", SUCCESS),
        ]:
            if not groups[region]:
                continue
            sec = tk.Frame(self._list_inner, bg=PANEL)
            sec.pack(fill="x", pady=(8, 4))
            tk.Label(sec, text=label, bg=PANEL, fg=color,
                     font=FONT_H, anchor="w",
                     padx=12).pack(fill="x")

            for t in groups[region]:
                self._add_target_row(t)

    def _add_target_row(self, target):
        row = tk.Frame(self._list_inner,
                        bg=self._lerp(PANEL, ACCENT, 0.4),
                        padx=12, pady=8)
        row.pack(fill="x", padx=8, pady=2)

        cb = tk.Checkbutton(row, variable=self._target_vars[target["id"]],
                             bg=row.cget("bg"), fg=FG,
                             selectcolor=ACCENT,
                             activebackground=row.cget("bg"))
        cb.pack(side="left")

        type_color = HIGHLIGHT if target["type"] == "api" else FG2
        type_label = "API " if target["type"] == "api" else "MAN"
        tk.Label(row, text=type_label, bg=row.cget("bg"),
                 fg=type_color, font=FONT_SM,
                 width=4).pack(side="left", padx=4)

        info_frame = tk.Frame(row, bg=row.cget("bg"))
        info_frame.pack(side="left", fill="x", expand=True)

        tk.Label(info_frame, text=target["label"], bg=row.cget("bg"),
                 fg=FG, font=FONT_B, anchor="w").pack(anchor="w")
        tk.Label(info_frame, text=target.get("notes", ""),
                 bg=row.cget("bg"), fg=FG2, font=FONT_SM,
                 anchor="w", wraplength=520, justify="left").pack(anchor="w")

        tk.Button(row, text="↗", command=lambda t=target: self._open_one(t),
                   bg=ACCENT, fg=HIGHLIGHT, font=FONT_B, relief="flat",
                   padx=10, cursor="hand2",
                   width=3).pack(side="right")

    def _sel_all(self):
        for v in self._target_vars.values():
            v.set(True)

    def _sel_api(self):
        for t in SUBMISSION_TARGETS:
            self._target_vars[t["id"]].set(t["type"] == "api")

    def _sel_none(self):
        for v in self._target_vars.values():
            v.set(False)

    # ── Bottom action bar ─────────────────────────────────────────────────────

    def _build_actions(self, parent):
        # Status text on left
        self._status_lbl = tk.Label(parent,
                                      text="Ready. Configure metadata, select targets, then publish.",
                                      bg=SIDEBAR, fg=FG2, font=FONT_SM,
                                      anchor="w")
        self._status_lbl.pack(side="left", padx=16, fill="x", expand=True)

        # Buttons on right
        btn_frame = tk.Frame(parent, bg=SIDEBAR)
        btn_frame.pack(side="right", padx=16)

        GradButton(btn_frame, "🔨  Build", command=self._build_only,
                    width=110, c1="#33aa33", c2="#55cc55").pack(side="left", padx=4)
        GradButton(btn_frame, "📊  Dashboard", command=self._open_dashboard,
                    width=130, c1="#7b61ff", c2="#9580ff").pack(side="left", padx=4)
        GradButton(btn_frame, "🚀  Publish to Selected",
                    command=self._publish, width=200,
                    c1=HL_END, c2=HIGHLIGHT).pack(side="left", padx=4)

    # ── Actions ────────────────────────────────────────────────────────────────

    def _set_status(self, msg, color=FG2):
        self._status_lbl.config(text=msg, fg=color)
        self.update_idletasks()

    def _build_manifest(self) -> dict:
        """Build a release manifest from current form values."""
        # Sync form to profile
        for key, widget in self._form_entries.items():
            if isinstance(widget, tk.Text):
                self._profile[key] = widget.get("1.0", "end").strip()
            else:
                self._profile[key] = widget.get().strip()

        return self._profile

    def _do_build(self):
        """Run the release builder using current form values."""
        manifest_form = self._build_manifest()

        # Validate
        if not manifest_form.get("version"):
            self._set_status("✗ Version is required", DANGER)
            return None

        exe_path = Path(manifest_form["exe_path"])
        if not exe_path.exists():
            self._set_status(f"✗ EXE not found: {exe_path}", DANGER)
            messagebox.showerror("EXE missing",
                                  f"File not found:\n{exe_path}\n\n"
                                  f"Build it first or pick another file.")
            return None

        # Override RELEASE_CONFIG with form values temporarily
        import publisher.config as cfg_mod
        cfg_mod.RELEASE_CONFIG.update({
            "name":         manifest_form["name"],
            "display_name": manifest_form["display_name"],
            "version":      manifest_form["version"],
            "publisher":    manifest_form["publisher"],
            "homepage":     manifest_form["homepage"],
            "license":      manifest_form["license"],
            "summary":      manifest_form["summary"],
            "description":  manifest_form["description"],
            "tags":         [t.strip() for t in manifest_form["tags"].split(",") if t.strip()],
            "github_owner": manifest_form["github_owner"],
            "github_repo":  manifest_form["github_repo"],
            "exe_name":     exe_path.name,
        })

        # Save version.json
        cfg_mod.save_version(manifest_form["version"])

        from publisher.release_builder import build_release_artifacts, DIST
        # If user picked an EXE outside dist/, copy it
        target_exe = DIST / exe_path.name
        if exe_path.parent != DIST:
            DIST.mkdir(exist_ok=True)
            import shutil
            shutil.copy2(exe_path, target_exe)

        manifest = build_release_artifacts(
            version=manifest_form["version"], skip_build=True)
        return manifest

    def _build_only(self):
        if self._publishing:
            return
        self._publishing = True

        def work():
            try:
                self.after(0, lambda: self._set_status(
                    "🔨 Building release artifacts…", HIGHLIGHT))
                manifest = self._do_build()
                if manifest:
                    msg = (f"✓ Built {len(manifest['artifacts'])} artifacts in "
                            f"{manifest['release_dir']}")
                    self.after(0, lambda: self._set_status(msg, SUCCESS))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._set_status(f"✗ Build failed: {err}", DANGER))
            finally:
                self._publishing = False

        threading.Thread(target=work, daemon=True).start()

    def _publish(self):
        if self._publishing:
            return
        selected = [t for t in SUBMISSION_TARGETS
                     if self._target_vars[t["id"]].get()]
        if not selected:
            messagebox.showwarning("No targets selected",
                                     "Select at least one distribution target.")
            return

        api_count = sum(1 for t in selected if t["type"] == "api")
        manual_count = sum(1 for t in selected if t["type"] == "manual")

        if not messagebox.askyesno(
                "Confirm publish",
                f"Publish to {len(selected)} target(s)?\n\n"
                f"  • {api_count} API targets (will publish automatically)\n"
                f"  • {manual_count} manual targets (will open in browser)"):
            return

        self._publishing = True

        def work():
            try:
                self.after(0, lambda: self._set_status(
                    "🔨 Building release…", HIGHLIGHT))
                manifest = self._do_build()
                if not manifest:
                    return

                from publisher.orchestrator import publish_to
                results = []

                # APIs first
                for i, target in enumerate([t for t in selected if t["type"] == "api"]):
                    self.after(0, lambda lbl=target["label"]:
                                self._set_status(f"🚀 Publishing to {lbl}…", HIGHLIGHT))
                    r = publish_to(target["id"], manifest, open_browser=False)
                    results.append((target, r))

                # Manual: open internal browser panel
                manual_targets = [t for t in selected if t["type"] == "manual"]
                if manual_targets:
                    self.after(0, lambda: self._set_status(
                        f"🌐 Opening manual submission queue…", HIGHLIGHT))
                    self.after(0, lambda m=manifest: InternalBrowserPanel(self, m))

                ok = sum(1 for _, r in results if r.get("ok"))
                msg = f"✓ {ok}/{len(results)} targets published"
                self.after(0, lambda m=msg: self._set_status(m, SUCCESS if ok == len(results) else WARNING))
                self.after(0, lambda r=results: self._show_results(r))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._set_status(f"✗ Publish failed: {err}", DANGER))
            finally:
                self._publishing = False

        threading.Thread(target=work, daemon=True).start()

    def _show_results(self, results):
        # Build results window
        win = tk.Toplevel(self)
        win.title("Publish Results")
        win.geometry("700x500")
        win.configure(bg=BG)

        tk.Label(win, text=f"Published to {len(results)} targets",
                 bg=BG, fg=HIGHLIGHT, font=FONT_T).pack(pady=10)

        tv_frame = tk.Frame(win, bg=BG)
        tv_frame.pack(fill="both", expand=True, padx=14, pady=8)

        cols = ("status", "target", "msg", "url")
        tv = ttk.Treeview(tv_frame, columns=cols, show="headings", height=18)
        for col, label, width in [("status", "✓", 40), ("target", "Target", 180),
                                    ("msg", "Message", 280), ("url", "URL", 180)]:
            tv.heading(col, text=label)
            tv.column(col, width=width)
        tv.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(tv_frame, orient="vertical", command=tv.yview)
        sb.pack(side="right", fill="y")
        tv.configure(yscrollcommand=sb.set)

        for target, r in results:
            icon = "✓" if r.get("ok") else "✗"
            tv.insert("", "end", values=(
                icon, target["label"], (r.get("msg", "") or "")[:80],
                (r.get("url", "") or "")[:60]
            ))

        # Open URL on double-click
        def on_dbl(event):
            sel = tv.selection()
            if sel:
                vals = tv.item(sel[0])["values"]
                if len(vals) >= 4 and vals[3]:
                    url = str(vals[3])
                    if url.startswith("http"):
                        webbrowser.open(url)
        tv.bind("<Double-1>", on_dbl)

        tk.Label(win, text="Double-click a row to open the URL.",
                 bg=BG, fg=FG2, font=FONT_SM).pack(pady=4)

    def _open_one(self, target):
        if self._publishing:
            return
        self._publishing = True

        def work():
            try:
                self.after(0, lambda: self._set_status(
                    f"Opening {target['label']}…", HIGHLIGHT))
                manifest = self._do_build()
                if not manifest:
                    return
                from publisher.orchestrator import publish_to
                r = publish_to(target["id"], manifest, open_browser=True)
                msg = f"{target['label']}: {(r.get('msg', '') or '')[:80]}"
                self.after(0, lambda m=msg: self._set_status(m, SUCCESS if r.get("ok") else DANGER))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._set_status(f"✗ Failed: {err}", DANGER))
            finally:
                self._publishing = False

        threading.Thread(target=work, daemon=True).start()

    def _open_dashboard(self):
        try:
            self._build_manifest()
            from publisher.orchestrator import open_dashboard_url
            path = open_dashboard_url(self._profile.get("version", "0.0.0"))
            webbrowser.open(f"file:///{path}")
            self._set_status(f"📊 Dashboard opened: {path}", SUCCESS)
        except Exception as e:
            self._set_status(f"✗ Dashboard error: {e}", DANGER)

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _lerp(a, b, t):
        ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
        br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
        return f"#{int(ar+(br-ar)*t):02x}{int(ag+(bg-ag)*t):02x}{int(ab+(bb-ab)*t):02x}"


def main():
    app = PublisherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
