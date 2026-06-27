"""Settings page — theme, language, report export, tray icon."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import webbrowser

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ToggleSwitch
from engine import i18n
from engine import report_exporter


class SettingsPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._tray_var = tk.BooleanVar(value=False)
        self._lang_var = tk.StringVar(value=i18n.get_language())
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Settings", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Application preferences and configuration",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_appearance_card(body)
        self._build_autorun_card(body)
        self._build_tray_card(body)
        self._build_language_card(body)
        self._build_report_card(body)
        self._build_hud_card(body)
        self._build_support_card(body)
        self._build_privacy_card(body)
        self._build_license_card(body)
        self._build_about_card(body)

    def _build_privacy_card(self, parent):
        from engine import affiliate, ad_network, email_capture, sponsored_notifications
        from .native_ad_widgets import PartnerGrid
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "✦ Monetization & support").pack(anchor="w", padx=10, pady=8)

        tk.Label(card,
            text=("FreeSystemDoctor is free. We help keep it that way through a few "
                  "hand-picked partner recommendations (affiliate links). "
                  "No third-party ad networks, no trackers, no impression "
                  "pixels — a partner is contacted only when you deliberately click a CTA. "
                  "You can turn off everything below with one click."),
            bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
            justify="left", anchor="w", wraplength=560).pack(
            anchor="w", padx=10, pady=(0, 8))

        # Master toggle ---------------------------------------------------
        self._aff_var = tk.BooleanVar(value=affiliate.is_enabled())
        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=(0, 4))
        tk.Checkbutton(
            row1,
            text="Show partner recommendations (banners + tip of the day)",
            variable=self._aff_var,
            bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
            activebackground=T.PANEL, font=T.FONT_BODY,
            command=lambda: affiliate.set_enabled(self._aff_var.get()),
        ).pack(side="left")

        # Optional ad-network toggle (off by default) ---------------------
        self._adnet_var = tk.BooleanVar(value=ad_network.is_enabled())
        row2 = tk.Frame(card, bg=T.PANEL)
        row2.pack(fill="x", padx=10, pady=(0, 4))
        tk.Checkbutton(
            row2,
            text=("Support development with subtle native ads "
                  "(optional, our own server, 1 fetch / 24 h)"),
            variable=self._adnet_var,
            bg=T.PANEL, fg=T.FG, selectcolor=T.ACCENT,
            activebackground=T.PANEL, font=T.FONT_BODY,
            command=lambda: ad_network.set_enabled(self._adnet_var.get()),
        ).pack(side="left")

        # Newsletter reset ------------------------------------------------
        row3 = tk.Frame(card, bg=T.PANEL)
        row3.pack(fill="x", padx=10, pady=(2, 6))
        sub_state = "✓ subscribed" if email_capture.is_subscribed() else "—"
        tk.Label(row3,
                 text=f"Newsletter: {sub_state}",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
        ActionButton(row3, text="Reset tips",
                     command=sponsored_notifications.reset).pack(side="right")
        if email_capture.is_subscribed():
            ActionButton(row3, text="Unsubscribe",
                         command=email_capture.unsubscribe).pack(side="right", padx=(0, 6))

        # Local stats line (transparency) ---------------------------------
        stats = affiliate.get_local_stats()
        tk.Label(card,
            text=(f"Local stats (never sent anywhere): "
                  f"{stats['total_impressions']} impressions · "
                  f"{stats['total_clicks']} clicks"),
            bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(
            anchor="w", padx=10, pady=(0, 6))

        # Partner grid (per-category opt-out) -----------------------------
        try:
            PartnerGrid(card).pack(fill="x", padx=2, pady=(0, 10))
        except Exception:
            pass

    def _build_hud_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "📊 System HUD").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 10))

        ActionButton(row, text="Show HUD",
                     command=self._hud_show).pack(side="left", padx=(0, 6))
        ActionButton(row, text="Hide HUD",
                     command=self._hud_hide).pack(side="left", padx=(0, 6))
        ActionButton(row, text="Move to corner ↘",
                     command=self._hud_corner).pack(side="left")

        tk.Label(row,
                 text="  Always-on-top mini CPU/RAM/GPU overlay",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=8)

    def _hud_show(self):
        try:
            self._app._hud.show()
        except Exception:
            pass

    def _hud_hide(self):
        try:
            self._app._hud.hide()
        except Exception:
            pass

    def _hud_corner(self):
        try:
            self._app._hud._place_bottom_right()
        except Exception:
            pass

    def _build_license_card(self, parent):
        """License status and activation card"""
        from engine import license_manager as lm

        mgr  = lm.get_manager()
        tier = mgr.get_tier()

        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "📋 License & Pro Features").pack(anchor="w", padx=10, pady=8)

        # ── Tier badge ─────────────────────────────────────────
        tier_text  = {"free": "Free Edition", "pro": "Pro Edition",
                      "lifetime": "Lifetime Pro"}
        tier_color = T.DANGER if tier == "free" else T.SUCCESS

        badge_row = tk.Frame(card, bg=T.PANEL)
        badge_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(badge_row, text="Current tier:",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY).pack(side="left")
        tk.Label(badge_row, text=f"  {tier_text.get(tier, tier)}",
                 bg=T.PANEL, fg=tier_color, font=T.FONT_BOLD).pack(side="left")

        if tier != "free":
            # ── Pro info row ───────────────────────────────────
            info_row = tk.Frame(card, bg=T.PANEL)
            info_row.pack(fill="x", padx=10, pady=(0, 4))
            tk.Label(info_row, text=f"Email:   {mgr.get_email() or '—'}",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")
            exp = (mgr.get_expires() or "")[:10]
            tk.Label(info_row, text=f"Expires: {exp}",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")
            cd = mgr.get_cd_key() or ""
            tk.Label(info_row, text=f"CD-Key:  {cd}",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")

            bf = tk.Frame(card, bg=T.PANEL)
            bf.pack(fill="x", padx=10, pady=(6, 10))
            ActionButton(bf, text="Sync license", width=120,
                         command=self._on_license_sync).pack(side="left")
            ActionButton(bf, text="Deactivate", width=100,
                         command=self._on_deactivate).pack(side="left", padx=(8, 0))

        else:
            # ── Free tier — buy + activate ─────────────────────
            form = tk.Frame(card, bg=T.PANEL)
            form.pack(fill="x", padx=10, pady=(4, 10))

            # Feature list
            feats = [
                "Advanced Scheduler   (unlimited tasks)",
                "AI Agent             (unlimited API requests)",
                "Idle Maintenance     (continuous auto-care)",
                "Deep Clean           (ML junk predictor)",
                "Turbo Mode           (persistent profiles)",
                "Performance Profiles (unlimited)",
                "System Backup        (incremental + scheduled)",
                "Disk Analyzer        (real-time monitoring)",
            ]
            tk.Label(form, text="Pro Edition — $9.99/year (auto-renews) — unlocks:",
                     bg=T.PANEL, fg=T.HIGHLIGHT, font=T.FONT_BOLD).pack(anchor="w", pady=(0, 4))
            for f in feats:
                tk.Label(form, text=f"  • {f}",
                         bg=T.PANEL, fg=T.FG, font=T.FONT_SMALL).pack(anchor="w")

            tk.Frame(form, bg=T.PANEL, height=10).pack()

            # ─ BUY with Stripe ─
            tk.Label(form, text="Buy with Stripe (secure card payment):",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", pady=(0, 4))

            email_row = tk.Frame(form, bg=T.PANEL)
            email_row.pack(fill="x", pady=(0, 6))
            tk.Label(email_row, text="Email:", width=8,
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
            self._stripe_email = tk.Entry(email_row, font=T.FONT_BODY, width=36)
            self._stripe_email.pack(side="left", padx=(0, 8))

            buy_row = tk.Frame(form, bg=T.PANEL)
            buy_row.pack(fill="x", pady=(0, 12))
            ActionButton(buy_row, text="Buy Pro — $9.99", width=150,
                         command=self._on_buy_stripe).pack(side="left")
            tk.Label(buy_row, text="  Opens Stripe checkout in browser",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left")

            # ─ Activate CD-key ─
            tk.Label(form, text="─" * 56,
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w")
            tk.Label(form, text="Already have a CD-key? Enter it below:",
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(anchor="w", pady=(6, 4))

            key_row = tk.Frame(form, bg=T.PANEL)
            key_row.pack(fill="x", pady=(0, 6))
            tk.Label(key_row, text="CD-Key:", width=8,
                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left")
            self._cd_key_entry = tk.Entry(key_row, font=T.FONT_BODY, width=24)
            self._cd_key_entry.insert(0, "FSD-XXXX-XXXX-XXXX-XXXX")
            self._cd_key_entry.pack(side="left", padx=(0, 8))

            act_row = tk.Frame(form, bg=T.PANEL)
            act_row.pack(fill="x")
            ActionButton(act_row, text="Activate CD-Key", width=140,
                         command=self._on_activate_cd).pack(side="left")

    # ── License handlers ────────────────────────────────────────

    def _on_buy_stripe(self):
        from engine import license_manager as lm, stripe_checkout
        email = self._stripe_email.get().strip()
        if not email or "@" not in email:
            messagebox.showwarning("Email needed", "Enter a valid email address first.")
            return

        device_id = lm.get_manager()._device_id()

        def success(cd_key, email_):
            # Activate locally
            ok, msg = lm.get_manager().activate(cd_key)
            # Show result on main thread
            self.after(0, lambda: messagebox.showinfo(
                "Pro Activated!",
                f"Payment successful!\n\n"
                f"Your CD-Key:\n{cd_key}\n\n"
                f"{msg}\n\n"
                f"Restart the app to enable all Pro features."
            ))

        def error(msg):
            self.after(0, lambda: messagebox.showerror("Payment error", msg))

        ok = stripe_checkout.begin_checkout(
            email=email, device_id=device_id,
            on_success=success, on_error=error,
        )
        if ok:
            messagebox.showinfo(
                "Browser opened",
                "Complete your payment in the browser.\n"
                "Your CD-key will appear automatically once payment is confirmed.\n\n"
                "Test card: 4242 4242 4242 4242  Exp: 12/26  CVC: 123"
            )

    def _on_activate_cd(self):
        from engine import license_manager as lm
        cd = self._cd_key_entry.get().strip()
        if not cd or cd == "FSD-XXXX-XXXX-XXXX-XXXX":
            messagebox.showwarning("CD-Key", "Enter your CD-key first.")
            return
        ok, msg = lm.get_manager().activate(cd)
        if ok:
            messagebox.showinfo("Activated!", f"{msg}\n\nRestart the app to unlock Pro features.")
            self._cd_key_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Activation failed", msg)

    def _on_license_sync(self):
        from engine import license_manager as lm
        mgr = lm.get_manager()
        if not mgr.get_cd_key():
            messagebox.showinfo("No license", "No Pro license found.")
            return
        cd = mgr.get_cd_key()
        ok, msg = mgr.activate(cd)
        if ok:
            messagebox.showinfo("Synced", msg)
        else:
            messagebox.showerror("Sync failed", msg)

    def _on_deactivate(self):
        from engine import license_manager as lm
        if messagebox.askyesno("Deactivate", "Remove local Pro license?\n(You can re-activate anytime with your CD-key)"):
            lm.get_manager().deactivate()
            messagebox.showinfo("Deactivated", "License removed. Restart the app.")

    def _build_support_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "☕ Support the Project").pack(anchor="w", padx=10, pady=8)

        msg = tk.Label(
            card,
            text="FreeSystemDoctor is and always will be free.\n"
                 "If it helped you optimize your PC, consider buying me a coffee.",
            bg=T.PANEL, fg=T.FG, font=T.FONT_BODY, justify="left", anchor="w",
        )
        msg.pack(anchor="w", padx=10, pady=(0, 8))

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 10))
        ActionButton(
            row, text="☕ Donate on Ko-fi",
            command=lambda: webbrowser.open("https://ko-fi.com/F1F51O3A4A"),
        ).pack(side="left")

        tk.Label(row, text="Opens ko-fi.com/F1F51O3A4A in your browser",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=12)

    def _build_appearance_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Appearance").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(row, text="Theme:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")

        theme_frame = tk.Frame(row, bg=T.PANEL)
        theme_frame.pack(side="left")
        ActionButton(theme_frame, text="Dark (current)",
                     command=lambda: self._set_theme("dark")).pack(side="left", padx=(0, 6))
        ActionButton(theme_frame, text="Light",
                     command=lambda: self._set_theme("light")).pack(side="left")

        self._theme_note = tk.Label(card,
            text="Theme change requires application restart to fully apply.",
            bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._theme_note.pack(anchor="w", padx=10, pady=(0, 8))

        # Animations toggle — independent of Windows performance settings
        anim_row = tk.Frame(card, bg=T.PANEL)
        anim_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(anim_row, text="Smooth animations:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")
        from engine import app_settings as _aset
        self._anim_var = tk.BooleanVar(value=_aset.get("animations_enabled", True))
        ToggleSwitch(anim_row, variable=self._anim_var,
                     command=self._on_anim_toggle).pack(side="left", padx=12)
        tk.Label(card,
                 text="Keeps the app smooth & animated even when Windows is set "
                      "to 'Best performance'. On by default.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 wraplength=560, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        # Simple mode — show only essential tools (beginner-friendly)
        simple_row = tk.Frame(card, bg=T.PANEL)
        simple_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(simple_row, text="Simple mode:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")
        from engine import app_settings as _aset2
        self._simple_var = tk.BooleanVar(
            value=_aset2.get("ui_mode", "advanced") == "simple")
        ToggleSwitch(simple_row, variable=self._simple_var,
                     command=self._on_simple_toggle).pack(side="left", padx=12)
        tk.Label(card,
                 text="Shows only the essential, everyday tools in the menu. "
                      "Turn off to see every advanced tool.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 wraplength=560, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        # Replay the interactive first-run tour
        tour_row = tk.Frame(card, bg=T.PANEL)
        tour_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(tour_row, text="Guided tour:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY, width=20, anchor="w").pack(side="left")
        ActionButton(tour_row, text="Take a tour", command=self._on_take_tour,
                     width=120).pack(side="left", padx=12)
        tk.Label(card,
                 text="Replay the interactive walkthrough that highlights the "
                      "main parts of the app.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                 wraplength=560, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

    def _on_take_tour(self):
        try:
            from .tutorial import start_tutorial
            start_tutorial(self._app)
        except Exception:
            pass

    def _on_anim_toggle(self):
        from engine import app_settings as _aset
        on = self._anim_var.get()
        T.set_animations_enabled(on)
        _aset.set_and_save("animations_enabled", on)

    def _on_simple_toggle(self):
        from engine import app_settings as _aset
        mode = "simple" if self._simple_var.get() else "advanced"
        _aset.set_and_save("ui_mode", mode)
        # Apply immediately so the sidebar updates without a restart.
        try:
            self._app._sidebar.refresh_mode()
            from .widgets import Toast
            Toast.show(self.winfo_toplevel(),
                       "Simple mode on — showing essential tools" if mode == "simple"
                       else "Showing all tools", "info")
        except Exception:
            pass

    def _build_autorun_card(self, parent):
        from engine import startup_manager
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "🚀 Start with Windows").pack(anchor="w", padx=10, pady=8)

        tk.Label(card,
            text=(
                "Launches FreeSystemDoctor automatically every time you sign in.\n"
                "Uses Windows Task Scheduler with administrator rights "
                "— no UAC prompt at startup."
            ),
            bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
            justify="left", anchor="w", wraplength=560,
        ).pack(anchor="w", padx=10, pady=(0, 8))

        self._autorun_var = tk.BooleanVar(value=startup_manager.is_autorun_enabled())
        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(row, text="Start at sign-in:",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        ToggleSwitch(row, variable=self._autorun_var,
                     command=self._on_autorun_toggle).pack(side="left", padx=12)

        self._autorun_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._autorun_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _on_autorun_toggle(self):
        from engine import startup_manager
        enabled = self._autorun_var.get()
        if enabled:
            ok = startup_manager.register_autorun()
            if ok:
                self._autorun_status.config(
                    text="✓ Scheduled task created — autostart is active", fg=T.SUCCESS)
            else:
                self._autorun_var.set(False)
                self._autorun_status.config(
                    text="✗ Could not create the task — run as administrator", fg=T.DANGER)
        else:
            ok = startup_manager.unregister_autorun()
            if ok:
                self._autorun_status.config(text="Autostart disabled", fg=T.FG2)
            else:
                self._autorun_status.config(
                    text="✗ Could not remove the task", fg=T.DANGER)

    def _build_tray_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "System Tray").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(row, text="Show tray icon with live CPU/RAM",
                 bg=T.PANEL, fg=T.FG, font=T.FONT_BODY).pack(side="left")
        ToggleSwitch(row, variable=self._tray_var,
                     command=self._on_tray_toggle).pack(side="left", padx=12)

        self._tray_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._tray_status.pack(anchor="w", padx=10, pady=(0, 8))

        note = tk.Label(card,
            text="Requires: pip install pystray pillow",
            bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        note.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_language_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Language").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(row, text="Interface language:", bg=T.PANEL, fg=T.FG,
                 font=T.FONT_BODY).pack(side="left")

        langs = i18n.available_languages()
        lang_display = [name for _, name in langs]
        lang_codes = [code for code, _ in langs]

        current_name = next((n for c, n in langs if c == self._lang_var.get()), "English")
        self._lang_display_var = tk.StringVar(value=current_name)

        cb = ttk.Combobox(row, textvariable=self._lang_display_var,
                          values=lang_display, state="readonly", width=15)
        cb.pack(side="left", padx=8)

        def on_lang_change(event=None):
            name = self._lang_display_var.get()
            code = next((c for c, n in langs if n == name), "en")
            i18n.set_language(code)
            messagebox.showinfo("Language", "Language saved. Restart the application to apply.")

        cb.bind("<<ComboboxSelected>>", on_lang_change)
        ActionButton(row, text="Apply", command=on_lang_change).pack(side="left")

    def _build_report_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "Reports").pack(anchor="w", padx=10, pady=8)

        tk.Label(card, text="Generate a detailed HTML report of your system status and scan results.",
                 bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL, wraplength=550, justify="left"
                 ).pack(anchor="w", padx=10, pady=(0, 8))

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))
        ActionButton(btn_row, text="Generate Report (Desktop)",
                     command=self._on_generate_report).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Choose Save Location",
                     command=self._on_generate_report_custom).pack(side="left")

        self._report_status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._report_status.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_about_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))
        SectionLabel(card, "About FreeSystemDoctor").pack(anchor="w", padx=10, pady=8)

        info = [
            ("Version", "2.2.0"),
            ("Python", "3.12+"),
            ("Platform", "Windows 10/11"),
            ("License", "Free & Open Source (MIT)"),
        ]
        for label, value in info:
            row = tk.Frame(card, bg=T.PANEL)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=label + ":", bg=T.PANEL, fg=T.FG2,
                     font=T.FONT_SMALL, width=12, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=T.PANEL, fg=T.FG,
                     font=T.FONT_BODY).pack(side="left")

        tk.Frame(card, bg=T.PANEL, height=8).pack()

    def _set_theme(self, theme: str):
        import json, os
        from pathlib import Path
        cfg_dir = Path(os.environ.get("TEMP", "C:\\Temp")) / "FreeSystemDoctor"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        with open(cfg_dir / "theme.json", "w") as f:
            json.dump({"theme": theme}, f)
        messagebox.showinfo("Theme", f"{theme.capitalize()} theme saved. Restart to apply.")

    def _on_tray_toggle(self):
        enabled = self._tray_var.get()
        if enabled:
            try:
                from engine import system_tray
                ok = system_tray.start_tray(self._app)
                if ok:
                    self._tray_status.config(text="Tray icon active", fg=T.SUCCESS)
                else:
                    self._tray_var.set(False)
                    self._tray_status.config(
                        text="Failed — install pystray and pillow: pip install pystray pillow",
                        fg=T.DANGER)
            except Exception as e:
                self._tray_var.set(False)
                self._tray_status.config(text=f"Error: {e}", fg=T.DANGER)
        else:
            try:
                from engine import system_tray
                system_tray.stop_tray()
                self._tray_status.config(text="Tray icon stopped", fg=T.FG2)
            except Exception:
                pass

    def _on_generate_report(self):
        self._report_status.config(text="Generating report...", fg=T.FG2)

        def gen():
            try:
                path = report_exporter.generate_quick_report()
                self.after(0, lambda: self._report_status.config(
                    text=f"Saved to: {path}", fg=T.SUCCESS))
                webbrowser.open(path)
            except Exception as e:
                self.after(0, lambda: self._report_status.config(
                    text=f"Error: {e}", fg=T.DANGER))

        threading.Thread(target=gen, daemon=True).start()

    def _on_generate_report_custom(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML Report", "*.html"), ("All Files", "*.*")],
            title="Save Report"
        )
        if not path:
            return
        self._report_status.config(text="Generating report...", fg=T.FG2)

        def gen():
            try:
                out = report_exporter.generate_quick_report(path)
                self.after(0, lambda: self._report_status.config(
                    text=f"Saved: {out}", fg=T.SUCCESS))
                webbrowser.open(out)
            except Exception as e:
                self.after(0, lambda: self._report_status.config(
                    text=f"Error: {e}", fg=T.DANGER))

        threading.Thread(target=gen, daemon=True).start()

    def on_activate(self):
        try:
            from engine import system_tray
            self._tray_var.set(system_tray.is_running())
        except Exception:
            pass
