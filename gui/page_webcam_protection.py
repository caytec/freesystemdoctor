"""Webcam Protection page — monitor camera access and alert on new apps."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch, apply_treeview_style
from engine import webcam_protection as wc


class WebcamProtectionPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._history = []
        self._prev_active_unknown: set[str] = set()
        self._block_new_var = tk.BooleanVar(value=True)
        self._poll_id = None
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Webcam Protection", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Monitor which apps access your camera",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Status card
        self._build_status_card(body)

        # Controls card
        self._build_controls_card(body)

        # History card
        self._build_history_card(body)

    def _build_status_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", expand=False, pady=(0, 12))

        SectionLabel(card, "Camera Status").pack(anchor="w", padx=10, pady=8)

        status_frame = tk.Frame(card, bg=T.PANEL)
        status_frame.pack(fill="x", padx=10, pady=(0, 8))

        self._status_canvas = tk.Canvas(status_frame, width=16, height=16, bg=T.PANEL,
                                       highlightthickness=0)
        self._status_canvas.pack(side="left", padx=(0, 8))

        self._status_label = tk.Label(status_frame, text="Scanning...", bg=T.PANEL,
                                      fg=T.FG, font=T.FONT_BODY)
        self._status_label.pack(side="left", fill="x", expand=True)

        self._last_scan_label = tk.Label(card, text="Last scanned: Never", bg=T.PANEL,
                                        fg=T.FG2, font=T.FONT_SMALL)
        self._last_scan_label.pack(anchor="w", padx=10, pady=(0, 8))

        ctrl_frame = tk.Frame(card, bg=T.PANEL)
        ctrl_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(ctrl_frame, text="Scan Now",
                     command=self._on_scan_now).pack(side="left", padx=(0, 6))

        toggle_frame = tk.Frame(card, bg=T.PANEL)
        toggle_frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(toggle_frame, text="Alert on new camera access",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left", padx=(0, 8))

        ToggleSwitch(toggle_frame, variable=self._block_new_var).pack(side="left")

    def _build_controls_card(self, parent):
        pass

    def _build_history_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Camera Access History").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("last_used", "status"), height=14)
        self._tree.column("#0", width=300)
        self._tree.column("last_used", width=200)
        self._tree.column("status", width=120)
        self._tree.heading("#0", text="App Name")
        self._tree.heading("last_used", text="Last Used")
        self._tree.heading("status", text="Status")

        self._tree.tag_configure("active", foreground=T.DANGER)
        self._tree.tag_configure("allowed", foreground=T.SUCCESS)
        self._tree.tag_configure("unknown", foreground=T.WARNING)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=0)
        sb.pack(side="right", fill="y", pady=0)

        btn_frame = tk.Frame(card, bg=T.PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_frame, text="Add to Allowed",
                     command=self._on_add_allowed).pack(side="left", padx=(0, 6))
        ActionButton(btn_frame, text="Remove from Allowed", danger=True,
                     command=self._on_remove_allowed).pack(side="left")

    def _scan(self):
        """Scan camera access in background thread."""
        def scan():
            history = wc.get_camera_history()
            is_in_use = wc.is_camera_in_use()
            self.after(0, self._update_ui, history, is_in_use)

        threading.Thread(target=scan, daemon=True).start()

    def _update_ui(self, history, is_in_use):
        """Update status and history treeview."""
        from datetime import datetime
        self._history = history
        allowed = set(wc.get_allowed_apps())

        # Update status indicator
        indicator_color = T.DANGER if is_in_use else T.SUCCESS
        self._status_canvas.delete("all")
        self._status_canvas.create_oval(2, 2, 14, 14, fill=indicator_color, outline="")

        status_text = f"Camera is {'ACTIVE' if is_in_use else 'IDLE'}"
        if is_in_use:
            active_apps = [h["app_name"] for h in history if h["is_active"]]
            if active_apps:
                status_text += f" — in use by: {', '.join(active_apps[:2])}"
        self._status_label.config(text=status_text)

        self._last_scan_label.config(text=f"Last scanned: {datetime.now().strftime('%H:%M:%S')}")

        # Update history treeview
        self._tree.delete(*self._tree.get_children())
        current_active_unknown = set()

        for h in history:
            tag = "active" if h["is_active"] else ("allowed" if h["status"] == "Allowed" else "unknown")
            self._tree.insert("", "end", iid=h["app_name"], text=h["app_name"],
                             values=(h["last_used_str"], h["status"]),
                             tags=(tag,))

            if h["is_active"] and tag == "unknown":
                current_active_unknown.add(h["app_name"])

        # Show alert for new unknown active apps
        if self._block_new_var.get():
            new_unknown = current_active_unknown - self._prev_active_unknown
            if new_unknown:
                messagebox.showwarning("Camera Alert",
                    f"New app accessing camera:\n\n{', '.join(new_unknown)}\n\nAdd to allowed list to hide this warning.")

        self._prev_active_unknown = current_active_unknown

    def _poll(self):
        """Periodic polling loop — runs while page is visible."""
        if not self.winfo_ismapped():
            self._poll_id = None
            return

        self._scan()
        self._poll_id = self.after(5000, self._poll)

    def _on_scan_now(self):
        self._scan()

    def _on_add_allowed(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an app to add to allowed list")
            return

        app_name = sel[0]
        wc.add_allowed_app(app_name)
        messagebox.showinfo("Added", f"{app_name} added to allowed apps")
        self._scan()

    def _on_remove_allowed(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an app to remove")
            return

        app_name = sel[0]
        wc.remove_allowed_app(app_name)
        messagebox.showinfo("Removed", f"{app_name} removed from allowed apps")
        self._scan()

    def on_activate(self):
        if self._poll_id is None:
            self._scan()
            self._poll_id = self.after(5000, self._poll)
