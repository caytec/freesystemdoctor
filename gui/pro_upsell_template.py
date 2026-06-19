"""
Reusable Pro feature upsell card template
Use this in Pro-only pages to show upsell when user is on Free tier
"""

import tkinter as tk
from tkinter import messagebox
from . import theme as T
from .widgets import Card, ActionButton


def build_upsell_card(parent, feature_name: str, description: str, features_list: list[str]) -> None:
    """
    Build and pack a Pro upsell card.

    Args:
        parent: Parent frame/widget
        feature_name: Pro feature name (e.g., "Advanced Scheduler")
        description: Feature description
        features_list: List of features (strings)
    """
    card = Card(parent)
    card.pack(fill="both", expand=True, padx=16, pady=12)

    # Title
    tk.Label(
        card,
        text=f"🔒 {feature_name} is a Pro-only feature",
        bg=T.PANEL, fg=T.HIGHLIGHT, font=T.FONT_BOLD
    ).pack(anchor="w", padx=12, pady=(12, 4))

    # Description
    tk.Label(
        card,
        text=description,
        bg=T.PANEL, fg=T.FG, font=T.FONT_BODY,
        justify="left", anchor="w", wraplength=560
    ).pack(anchor="w", padx=12, pady=(0, 12))

    # Features list
    for feat in features_list:
        tk.Label(
            card, text=feat,
            bg=T.PANEL, fg=T.SUCCESS, font=T.FONT_SMALL
        ).pack(anchor="w", padx=12, pady=2)

    tk.Label(card, text="", bg=T.PANEL).pack(pady=6)

    # CTA Button
    btn_frame = tk.Frame(card, bg=T.PANEL)
    btn_frame.pack(fill="x", padx=12, pady=(0, 12))

    ActionButton(
        btn_frame, text="Upgrade to Pro", width=140,
        command=lambda: messagebox.showinfo(
            "Pro Edition",
            "Paste your license key in Settings > License & Pro Features\n\n"
            "Only $9.99/year • Unlimited Pro features"
        )
    ).pack(side="left")

    tk.Label(
        btn_frame, text="Only $9.99/year",
        bg=T.PANEL, fg=T.HIGHLIGHT, font=T.FONT_BOLD
    ).pack(side="left", padx=12)


def build_header(parent, feature_name: str, pro_label: str = None) -> None:
    """
    Build page header with Pro badge.

    Args:
        parent: Parent frame
        feature_name: Page title
        pro_label: Optional pro label (default: "💎 Pro Feature")
    """
    if pro_label is None:
        pro_label = "💎 Pro Feature"

    hdr = tk.Frame(parent, bg=T.ACCENT, height=48)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)

    tk.Label(
        hdr, text=feature_name, bg=T.ACCENT, fg=T.FG,
        font=T.FONT_TITLE
    ).pack(side="left", padx=16)

    tk.Label(
        hdr, text=pro_label,
        bg=T.ACCENT, fg=T.HIGHLIGHT, font=T.FONT_SMALL
    ).pack(side="left", padx=4)
