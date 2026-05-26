"""Startup Insights page — analyze and optimize startup performance."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import startup_insights as si
from engine import startup_link_analyzer as sla


class StartupInsightsPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Startup Insights", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Analyze and optimize your startup performance",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Startup time estimate
        self._build_estimate_card(body)

        # Recommendations
        self._build_recommendations_card(body)

        # Startup items
        self._build_items_card(body)

    def _build_estimate_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Startup Time Estimate").pack(anchor="w", padx=10, pady=8)

        row = tk.Frame(card, bg=T.PANEL)
        row.pack(fill="x", padx=10, pady=(0, 8))

        self._startup_time = tk.Label(row, text="–", bg=T.PANEL, fg=T.HIGHLIGHT,
                                     font=(T.FONT_FAMILY, 24, "bold"))
        self._startup_time.pack(side="left", padx=10)

        info = tk.Frame(row, bg=T.PANEL)
        info.pack(side="left", padx=10, fill="both", expand=True)

        self._high_impact_label = tk.Label(info, text="", bg=T.PANEL, fg=T.FG2,
                                          font=T.FONT_BODY)
        self._high_impact_label.pack(anchor="w")

        self._savings_label = tk.Label(info, text="", bg=T.PANEL, fg=T.FG2,
                                      font=T.FONT_SMALL)
        self._savings_label.pack(anchor="w")

    def _build_recommendations_card(self, parent):
        card = Card(parent)
        card.pack(fill="x", pady=(0, 12))

        SectionLabel(card, "Optimization Recommendations").pack(anchor="w", padx=10, pady=8)

        self._recommendations_text = tk.Text(card, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY,
                                            height=4, bd=0, padx=8, pady=6,
                                            state="disabled", wrap="word")
        self._recommendations_text.pack(fill="both", expand=False, padx=10, pady=(0, 8))

    def _build_items_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True)

        SectionLabel(card, "Startup Items").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._tree = ttk.Treeview(tree_frame, columns=("impact", "category"), height=12)
        self._tree.column("#0", width=200)
        self._tree.column("impact", width=80)
        self._tree.column("category", width=100)
        self._tree.heading("#0", text="Application")
        self._tree.heading("impact", text="Impact")
        self._tree.heading("category", text="Category")

        self._tree.tag_configure("high", foreground=T.DANGER)
        self._tree.tag_configure("medium", foreground=T.WARNING)
        self._tree.tag_configure("low", foreground=T.SUCCESS)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_row, text="Disable Selected",
                     command=self._on_disable).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Refresh Scan",
                     command=self._on_refresh).pack(side="left")

        self._status = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._status.pack(anchor="w", padx=10, pady=(0, 8))

    def _load_startup_items(self):
        """Load startup items in background."""
        def load():
            entries = si.scan_startup_with_impact()
            startup_time = si.estimate_startup_time()
            recommendations = si.get_startup_recommendations()
            links = sla.scan_startup_links()
            link_recs = sla.get_startup_recommendations()
            self.after(0, self._display_data, entries, startup_time, recommendations, links, link_recs)

        threading.Thread(target=load, daemon=True).start()

    def _display_data(self, entries, startup_time, recommendations, links, link_recs):
        """Display startup data."""
        # Update estimate
        seconds = startup_time["estimated_seconds"]
        self._startup_time.config(text=f"{seconds:.0f}s")

        self._high_impact_label.config(
            text=f"{startup_time['high_impact_count']} high-impact items")
        self._savings_label.config(
            text=f"Potential savings: {startup_time['savings_if_disabled']/1000:.1f}s")

        # Update recommendations (combine registry + link recommendations)
        combined_recs = recommendations + link_recs
        self._recommendations_text.config(state="normal")
        self._recommendations_text.delete("1.0", "end")
        if combined_recs:
            self._recommendations_text.insert("end", "\n".join(f"• {r}" for r in combined_recs))
        else:
            self._recommendations_text.insert("end", "Your startup is well optimized!")
        self._recommendations_text.config(state="disabled")

        # Update tree with both registry entries and shortcut links
        self._tree.delete(*self._tree.get_children())

        # Add registry startup entries
        for entry in entries:
            tag = entry.impact.lower()
            self._tree.insert("", "end", iid=entry.name, text=entry.name,
                             values=(entry.impact, entry.category),
                             tags=(tag,))

        # Add shortcut link entries
        for link in links:
            tag = link.impact.lower()
            self._tree.insert("", "end", iid=link.path.stem, text=link.name,
                             values=(link.impact, f"{link.category} (Link)"),
                             tags=(tag,))

        self._status.config(text=f"Total startup items: {len(entries) + len(links)} ({len(links)} shortcuts)")

    def _on_disable(self):
        selection = self._tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select items to disable")
            return

        if not messagebox.askyesno("Disable Startup Items",
                f"Disable {len(selection)} startup item(s)?"):
            return

        disabled = 0
        for item_id in selection:
            # Try registry entry first
            if si.disable_startup_entry(item_id):
                disabled += 1
            else:
                # Try shortcut link
                try:
                    from pathlib import Path
                    links = sla.scan_startup_links()
                    for link in links:
                        if link.path.stem == item_id:
                            if sla.disable_startup_link(link.path):
                                disabled += 1
                            break
                except Exception:
                    pass

        messagebox.showinfo("Complete", f"Disabled {disabled} item(s). Restart to apply.")
        self._on_refresh()

    def _on_refresh(self):
        self._load_startup_items()

    def on_activate(self):
        self._load_startup_items()
