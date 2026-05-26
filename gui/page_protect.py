"""System Protection + Browser Protection page."""

import threading
import tkinter as tk
from tkinter import messagebox

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch, StatusBadge
from engine import protection as prot
from engine import browser_protection as bp


class ProtectPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._fw_toggles: dict[str, tuple[tk.BooleanVar, ToggleSwitch]] = {}
        self._browser_rows: dict[str, dict] = {}
        self._build_ui()

    def on_activate(self):
        self.after(300, self._refresh_all)

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Protect", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="System, browser and privacy protection status",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)
        ActionButton(hdr, "Refresh All", command=self._refresh_all,
                     ).pack(side="right", padx=12)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left: System protection
        left = tk.Frame(body, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._build_system_protection(left)

        # Right: Browser protection
        right = tk.Frame(body, bg=T.BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_browser_protection(right)

    # ── System protection ─────────────────────────────────────────────────────

    def _build_system_protection(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 8))

        icon_row = tk.Frame(card, bg=T.PANEL)
        icon_row.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(icon_row, text="🛡", bg=T.PANEL, fg=T.FG, font=("Segoe UI", 20)).pack(side="left")
        SectionLabel(icon_row, "  System Protection").pack(side="left")
        self._sys_badge = StatusBadge(icon_row)
        self._sys_badge.pack(side="right")

        # Defender section
        def_card = tk.Frame(card, bg=T.ACCENT, bd=0)
        def_card.pack(fill="x", padx=10, pady=4)
        self._build_defender_rows(def_card)

        # Firewall section
        fw_lbl = tk.Frame(card, bg=T.PANEL)
        fw_lbl.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(fw_lbl, text="Windows Firewall", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_H3).pack(side="left")
        for profile in ("Domain", "Private", "Public"):
            self._build_firewall_row(card, profile)

        # Action buttons
        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(8, 10))
        ActionButton(btn_row, "Quick Scan", command=lambda: self._run_defender_scan(False)
                     ).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Full Scan", command=lambda: self._run_defender_scan(True)
                     ).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, "Update Definitions", command=self._update_definitions
                     ).pack(side="left")

    def _build_defender_rows(self, parent):
        def_row = tk.Frame(parent, bg=T.ACCENT)
        def_row.pack(fill="x", padx=6, pady=6)
        tk.Label(def_row, text="Windows Defender", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left", padx=6)
        self._def_badge = StatusBadge(def_row)
        self._def_badge.pack(side="right", padx=6)

        self._def_rt_var = tk.BooleanVar(value=True)
        rt_row = tk.Frame(parent, bg=T.ACCENT)
        rt_row.pack(fill="x", padx=6, pady=2)
        tk.Label(rt_row, text="Real-time Protection", bg=T.ACCENT, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left", padx=6)
        self._def_toggle = ToggleSwitch(rt_row, variable=self._def_rt_var,
                                         command=self._toggle_defender, bg=T.ACCENT)
        self._def_toggle.pack(side="right", padx=6)

        self._def_info = tk.Label(parent, bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL,
                                   text="Last scan: –  |  Definitions: –", anchor="w")
        self._def_info.pack(fill="x", padx=12, pady=(0, 6))

    def _build_firewall_row(self, parent, profile: str):
        row = tk.Frame(parent, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=2)
        tk.Label(row, text=f"{profile} Profile", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=14, anchor="w").pack(side="left")
        badge = StatusBadge(row)
        badge.pack(side="right", padx=4)
        var = tk.BooleanVar(value=False)
        toggle = ToggleSwitch(row, variable=var, bg=T.PANEL,
                              command=lambda p=profile, v=var: self._toggle_fw(p, v.get()))
        toggle.pack(side="right", padx=4)
        self._fw_toggles[profile] = (var, badge)

    # ── Browser protection ────────────────────────────────────────────────────

    def _build_browser_protection(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 8))
        icon_row = tk.Frame(card, bg=T.PANEL)
        icon_row.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(icon_row, text="🌐", bg=T.PANEL, fg=T.FG, font=("Segoe UI", 20)).pack(side="left")
        SectionLabel(icon_row, "  Browser Protection").pack(side="left")

        tk.Label(card, text="Secure your browsing and block malicious content",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", padx=10)

        # Browser rows (populated after detection)
        self._browser_frame = tk.Frame(card, bg=T.PANEL)
        self._browser_frame.pack(fill="x", padx=10, pady=4)

        # Ad blocking
        ad_sep = tk.Frame(card, bg=T.ACCENT, height=1)
        ad_sep.pack(fill="x", padx=10, pady=4)
        ad_row = tk.Frame(card, bg=T.PANEL)
        ad_row.pack(fill="x", padx=10, pady=4)
        tk.Label(ad_row, text="Ads Removal (hosts-based)", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")
        self._ad_count_lbl = tk.Label(ad_row, text="", bg=T.PANEL, fg=T.FG2,
                                       font=T.FONT_SMALL)
        self._ad_count_lbl.pack(side="left", padx=6)
        self._ad_var = tk.BooleanVar(value=bp.get_ad_blocking_status())
        ToggleSwitch(ad_row, variable=self._ad_var, bg=T.PANEL,
                     command=self._toggle_ad_blocking).pack(side="right")
        self._update_ad_label()

        # Privacy protection card
        priv_card = Card(parent)
        priv_card.pack(fill="x", pady=(0, 8))
        icon_row2 = tk.Frame(priv_card, bg=T.PANEL)
        icon_row2.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(icon_row2, text="🔒", bg=T.PANEL, fg=T.FG, font=("Segoe UI", 20)).pack(side="left")
        SectionLabel(icon_row2, "  Privacy Protection").pack(side="left")
        self._build_privacy_toggles(priv_card)

    def _build_privacy_toggles(self, card):
        from engine import privacy_cleaner as pc

        items = [
            ("Telemetry Disabled", pc.get_telemetry_status, "telemetry_level"),
            ("Location Tracking", pc.get_location_status, None),
            ("Advertising ID",    pc.get_advertising_id_status, None),
        ]
        self._priv_badges: dict[str, StatusBadge] = {}

        for label, _, _ in items:
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=3)
            tk.Label(row, text=label, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BODY).pack(side="left")
            badge = StatusBadge(row)
            badge.pack(side="right")
            self._priv_badges[label] = badge

        ActionButton(card, "Disable All Tracking",
                     command=self._disable_all_tracking).pack(anchor="w", padx=10, pady=(6, 10))

    # ── refresh data ──────────────────────────────────────────────────────────

    def _refresh_all(self):
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        def_status = prot.get_defender_status()
        fw_status  = prot.get_firewall_status()
        browsers   = bp.detect_browsers()
        self.after(0, self._apply_defender, def_status)
        self.after(0, self._apply_firewall, fw_status)
        self.after(0, self._apply_browsers, browsers)
        self.after(0, self._refresh_privacy)

    def _apply_defender(self, status: dict):
        enabled = status.get("enabled", False)
        realtime = status.get("realtime", False)
        if not status.get("available"):
            self._def_badge.set_warning("Not Available")
            self._sys_badge.set_warning("Unknown")
        elif enabled and realtime:
            self._def_badge.set_ok("Protected")
            self._sys_badge.set_ok("Protected")
        else:
            self._def_badge.set_error("At Risk")
            self._sys_badge.set_error("At Risk")
        self._def_rt_var.set(realtime)
        self._def_info.config(
            text=f"Last scan: {status.get('last_scan','–')}  |  "
                 f"Definitions: {status.get('definition_date','–')}"
        )

    def _apply_firewall(self, status: dict):
        for profile, (var, badge) in self._fw_toggles.items():
            enabled = status.get(profile, {}).get("enabled", False)
            var.set(enabled)
            if enabled:
                badge.set_ok("ON")
            else:
                badge.set_error("OFF")

    def _apply_browsers(self, browsers: list[dict]):
        for w in self._browser_frame.winfo_children():
            w.destroy()
        self._browser_rows = {}
        for browser in browsers:
            name = browser["name"]
            row = tk.Frame(self._browser_frame, bg=T.PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=name, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BODY, width=10, anchor="w").pack(side="left")
            tk.Label(row, text=f"v{browser['version']}", bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL).pack(side="left", padx=4)
            status_str = bp.get_safe_browsing_status(name)
            badge = StatusBadge(row)
            if status_str in ("enabled", "default"):
                badge.set_ok("Safe Browsing ON")
            else:
                badge.set_error("Safe Browsing OFF")
            badge.pack(side="right")
            var = tk.BooleanVar(value=status_str != "disabled")
            ToggleSwitch(row, variable=var, bg=T.PANEL,
                         command=lambda n=name, v=var: bp.set_safe_browsing(n, v.get())
                         ).pack(side="right", padx=4)
            self._browser_rows[name] = {"var": var, "badge": badge}

    def _refresh_privacy(self):
        from engine import privacy_cleaner as pc
        status = pc.get_telemetry_status()
        level = status.get("telemetry_level", "1")
        badge = self._priv_badges.get("Telemetry Disabled")
        if badge:
            if level == 0 or level == "0":
                badge.set_ok("Disabled")
            else:
                badge.set_error("Enabled")

        loc = pc.get_location_status()
        lb = self._priv_badges.get("Location Tracking")
        if lb:
            if loc.lower() == "deny":
                lb.set_ok("Blocked")
            else:
                lb.set_error("Allowed")

        adid = pc.get_advertising_id_status()
        ab = self._priv_badges.get("Advertising ID")
        if ab:
            if adid == 0:
                ab.set_ok("Disabled")
            else:
                ab.set_error("Enabled")

    # ── toggles ───────────────────────────────────────────────────────────────

    def _toggle_defender(self):
        enabled = self._def_rt_var.get()
        if not enabled:
            if not messagebox.askyesno("Disable Defender",
                                       "Disable real-time protection?\n"
                                       "This reduces your system's security."):
                self._def_rt_var.set(True)
                return
        ok = prot.set_defender_realtime(enabled)
        if not ok:
            messagebox.showerror("Error",
                                 "Could not change Defender settings.\n(Requires administrator)")
            self._def_rt_var.set(not enabled)

    def _toggle_fw(self, profile: str, enabled: bool):
        ok = prot.set_firewall_profile(profile, enabled)
        var, badge = self._fw_toggles.get(profile, (None, None))
        if ok and badge:
            badge.set_ok("ON") if enabled else badge.set_error("OFF")
        elif not ok:
            messagebox.showerror("Error", f"Could not change {profile} firewall.\n(Requires administrator)")
            if var:
                var.set(not enabled)

    def _toggle_ad_blocking(self):
        enabled = self._ad_var.get()
        if enabled:
            ok = bp.enable_ad_blocking()
        else:
            ok = bp.disable_ad_blocking()
        if not ok:
            messagebox.showerror("Error", "Could not modify hosts file.\n(Requires administrator)")
            self._ad_var.set(not enabled)
        else:
            self._update_ad_label()

    def _update_ad_label(self):
        n = bp.get_blocked_count()
        self._ad_count_lbl.config(text=f"({n} domains blocked)" if n else "")

    def _run_defender_scan(self, full: bool):
        prot.start_defender_scan(full=full)
        scan_type = "full" if full else "quick"
        messagebox.showinfo("Scan Launched", f"Windows Defender {scan_type} scan started.")

    def _update_definitions(self):
        def run():
            ok = prot.update_defender_definitions()
            msg = "Definitions updated successfully." if ok else "Update failed. Check internet connection."
            self.after(0, messagebox.showinfo, "Definitions", msg)
        threading.Thread(target=run, daemon=True).start()

    def _disable_all_tracking(self):
        from engine import privacy_cleaner as pc
        pc.disable_telemetry()
        pc.disable_location()
        pc.disable_advertising_id()
        self._refresh_privacy()
        messagebox.showinfo("Privacy", "Telemetry, location and advertising ID disabled.")
