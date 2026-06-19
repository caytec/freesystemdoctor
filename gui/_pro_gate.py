"""
FreeSystemDoctor — Pro Feature Gate Widget
Drop-in upsell overlay for Pro-only pages.
Usage:
    from gui._pro_gate import gate_or_build  # noqa: F401

    class MyPage(tk.Frame):
        def _build_ui(self):
            if gate_or_build(self, "feature_id", "Feature Name", [...]):
                return
            # ... rest of normal UI
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from . import theme as T
from .widgets import Card, ActionButton


PRO_DESCRIPTIONS: dict[str, tuple[str, list[str]]] = {
    "advanced_scheduler": (
        "Schedule unlimited maintenance tasks with cron-like expressions.",
        ["Unlimited scheduled tasks", "Cron expressions (daily/weekly/monthly)",
         "Task persistence across reboots", "Email notifications"],
    ),
    "ai_agent": (
        "Unlimited AI-powered system analysis with multi-LLM fallback.",
        ["Unlimited API requests", "Pre-configured API keys included",
         "Cerebras → Groq → OpenRouter fallback", "Priority model access"],
    ),
    "idle_maintenance": (
        "Continuous background maintenance — fires whenever your PC is idle.",
        ["Continuous (not just weekly)", "Smart idle detection",
         "Background cleanup without interruption", "Custom idle thresholds"],
    ),
    "deep_clean": (
        "ML-powered junk predictor with parallel multi-drive processing.",
        ["ML junk file predictor", "Parallel multi-drive scan",
         "Custom exclusion rules", "Duplicate file detection"],
    ),
    "turbo_mode": (
        "Save and switch Turbo profiles per game/app — instantly.",
        ["Unlimited saved profiles", "Per-app auto-switching",
         "Profile import/export", "Hardware-specific tuning"],
    ),
    "performance_profiles": (
        "Unlimited performance profiles with advanced per-app settings.",
        ["Unlimited profiles (Free: 3)", "Per-app auto-apply",
         "Schedule by time-of-day", "Profile cloud backup"],
    ),
    "system_backup": (
        "Incremental + scheduled system backups with instant restore.",
        ["Incremental backups (changed files only)", "Scheduled auto-backup",
         "One-click restore", "Cloud upload support"],
    ),
    "disk_analyzer": (
        "Real-time disk usage monitoring with trend analysis.",
        ["Real-time monitoring", "7/30/90-day growth trends",
         "Auto-alert on low space", "Largest-folder drill-down"],
    ),
}


def gate_or_build(page: tk.Frame, feature_id: str, title: str,
                  subtitle: str = "") -> bool:
    """
    Check if feature_id is available.
    If NOT → build upsell overlay in `page` and return True (caller should return).
    If YES → return False (caller continues building normal UI).
    """
    from engine import license_manager as lm
    if lm.is_feature_available(feature_id):
        page._pro_gated = False
        return False        # caller builds normal UI

    # Mark the page as gated so post-build hooks (on_activate, _load_*, _refresh_*)
    # can early-return instead of touching widgets that were never created.
    page._pro_gated = True

    desc, feats = PRO_DESCRIPTIONS.get(feature_id, (
        "This feature is available in the Pro Edition.",
        ["Advanced functionality", "Priority support", "No limits"],
    ))
    _build_upsell(page, title, desc, feats)
    return True             # caller stops here


def _build_upsell(page: tk.Frame, title: str, desc: str, feats: list[str]):
    # Header bar (matches normal page style)
    hdr = tk.Frame(page, bg=T.ACCENT, height=48)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text=title, bg=T.ACCENT, fg=T.FG,
             font=T.FONT_TITLE).pack(side="left", padx=16)
    tk.Label(hdr, text="Pro feature", bg=T.ACCENT,
             fg=T.HIGHLIGHT, font=T.FONT_SMALL).pack(side="left", padx=4)

    body = tk.Frame(page, bg=T.BG)
    body.pack(fill="both", expand=True, padx=16, pady=16)

    card = Card(body)
    card.pack(fill="x")

    # Lock icon + headline
    tk.Label(card, text="🔒  Pro Edition Required",
             bg=T.PANEL, fg=T.HIGHLIGHT,
             font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=16, pady=(14, 4))

    tk.Label(card, text=desc,
             bg=T.PANEL, fg=T.FG, font=T.FONT_BODY,
             wraplength=560, justify="left").pack(anchor="w", padx=16, pady=(0, 10))

    # Feature bullets
    for feat in feats:
        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=16, pady=1)
        tk.Label(row, text="✓", bg=T.PANEL, fg=T.SUCCESS,
                 font=T.FONT_SMALL, width=3).pack(side="left")
        tk.Label(row, text=feat, bg=T.PANEL, fg=T.FG,
                 font=T.FONT_SMALL).pack(side="left")

    tk.Frame(card, bg=T.PANEL, height=12).pack()

    # CTA buttons
    btn_row = tk.Frame(card, bg=T.PANEL)
    btn_row.pack(fill="x", padx=16, pady=(0, 16))

    ActionButton(btn_row, text="Buy Pro — $9.99/year", width=180,
                 command=_open_settings_license).pack(side="left")
    ActionButton(btn_row, text="Enter CD-Key", width=120,
                 command=_open_settings_license).pack(side="left", padx=(8, 0))

    tk.Label(btn_row, text="  Already purchased? Go to Settings → License",
             bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=12)


def _open_settings_license():
    """Navigate to Settings page (best-effort)."""
    import tkinter as _tk
    # Walk up widget tree to find the App instance
    try:
        root = _tk._default_root                  # type: ignore
        if hasattr(root, "_app"):
            root._app._switch_page("settings")
    except Exception:
        pass


# ── Inline limit banner (for LIMITED Pro features) ─────────────────────────────

def limit_banner(parent: tk.Frame, feature_id: str,
                 used: int = None, total: int = None) -> tk.Frame | None:
    """Build a slim 'Free tier limit — Upgrade to Pro' banner inside *parent*.

    Returns the banner Frame (so callers can pack/destroy it), or None for Pro
    users / non-limited features (no banner needed). Use on LIMITED pages that
    build their normal UI but enforce a Free quota.
    """
    from engine import license_manager as lm
    if lm.feature_mode(feature_id) != "limited":
        return None

    label = lm.limit_label(feature_id)
    if used is not None and total is not None:
        label = f"{label}  ({used}/{total} used)"

    bar = tk.Frame(parent, bg=T.lerp_color(T.PANEL, T.HIGHLIGHT, 0.10))
    accent = tk.Frame(bar, bg=T.HIGHLIGHT, width=3)
    accent.pack(side="left", fill="y")

    tk.Label(bar, text="🔓", bg=bar.cget("bg"), fg=T.HIGHLIGHT,
             font=(T.FONT_FAMILY, 12)).pack(side="left", padx=(8, 4), pady=6)
    tk.Label(bar, text=label, bg=bar.cget("bg"), fg=T.FG,
             font=T.FONT_SMALL).pack(side="left", padx=(0, 8))

    ActionButton(bar, text="Upgrade to Pro", width=130,
                 command=_open_settings_license).pack(side="right", padx=8, pady=5)
    return bar


def at_limit_dialog(feature_id: str):
    """Show a messagebox explaining the Free limit was reached + offer upgrade."""
    from tkinter import messagebox
    from engine import license_manager as lm
    name = feature_id.replace("_", " ").title()
    if messagebox.askyesno(
        f"{name} — Free limit reached",
        f"{lm.limit_label(feature_id)}.\n\n"
        f"Upgrade to Pro for unlimited access.\n\nOpen Settings → License now?"):
        _open_settings_license()
