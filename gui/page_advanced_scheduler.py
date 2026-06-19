"""Advanced Scheduler page — cron-like scheduling for maintenance tasks."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, apply_treeview_style
from engine import advanced_scheduler as asched
from engine import license_manager as lm
from ._pro_gate import limit_banner, at_limit_dialog


class AdvancedSchedulerPage(tk.Frame):
    def __init__(self, parent, app_ref):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref
        self._build_ui()

    def _build_ui(self):
        self._build_scheduler_ui()

    def _build_scheduler_ui(self):
        """Scheduler UI — Free capped at 3 tasks (FREE_LIMITS), Pro unlimited."""
        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Advanced Scheduler", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Cron-like maintenance scheduling",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        banner = limit_banner(body, "advanced_scheduler")
        if banner:
            banner.pack(fill="x", pady=(0, 10))

        self._build_tasks_card(body)
        self._build_create_task_card(body)

    def _build_tasks_card(self, parent):
        card = Card(parent)
        card.pack(fill="both", expand=True, pady=(0, 12))

        SectionLabel(card, "Scheduled Tasks").pack(anchor="w", padx=10, pady=8)

        tree_frame = tk.Frame(card, bg=T.PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        apply_treeview_style()
        self._task_tree = ttk.Treeview(tree_frame, columns=("action", "schedule", "enabled"), height=10)
        self._task_tree.column("#0", width=200)
        self._task_tree.column("action", width=150)
        self._task_tree.column("schedule", width=150)
        self._task_tree.column("enabled", width=80)
        self._task_tree.heading("#0", text="Task Name")
        self._task_tree.heading("action", text="Action")
        self._task_tree.heading("schedule", text="Schedule")
        self._task_tree.heading("enabled", text="Enabled")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._task_tree.yview)
        self._task_tree.configure(yscrollcommand=sb.set)
        self._task_tree.pack(side="left", fill="both", expand=True, padx=(0, 6))
        sb.pack(side="right", fill="y")

        btn_row = tk.Frame(card, bg=T.PANEL)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        ActionButton(btn_row, text="Edit Selected",
                     command=self._on_edit).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Delete Selected",
                     command=self._on_delete).pack(side="left", padx=(0, 6))
        ActionButton(btn_row, text="Toggle Enabled",
                     command=self._on_toggle).pack(side="left")

    def _build_create_task_card(self, parent):
        card = Card(parent)
        card.pack(fill="x")

        SectionLabel(card, "Create New Task").pack(anchor="w", padx=10, pady=8)

        # Task name
        row1 = tk.Frame(card, bg=T.PANEL)
        row1.pack(fill="x", padx=10, pady=4)
        tk.Label(row1, text="Name:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._task_name = tk.Entry(row1, bg=T.ACCENT, fg=T.FG, font=T.FONT_BODY)
        self._task_name.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Action dropdown
        row2 = tk.Frame(card, bg=T.PANEL)
        row2.pack(fill="x", padx=10, pady=4)
        tk.Label(row2, text="Action:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._action_var = tk.StringVar()
        action_combo = ttk.Combobox(row2, textvariable=self._action_var, state="readonly", width=30)
        action_combo["values"] = list(asched.get_available_actions().values())
        action_combo.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Schedule preset dropdown
        row3 = tk.Frame(card, bg=T.PANEL)
        row3.pack(fill="x", padx=10, pady=4)
        tk.Label(row3, text="Preset:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._preset_var = tk.StringVar()
        preset_combo = ttk.Combobox(row3, textvariable=self._preset_var, state="readonly", width=30)
        preset_combo["values"] = list(asched.get_predefined_schedules().keys())
        preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)
        preset_combo.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Custom cron expression
        row4 = tk.Frame(card, bg=T.PANEL)
        row4.pack(fill="x", padx=10, pady=4)
        tk.Label(row4, text="Cron:", bg=T.PANEL, fg=T.FG2, font=T.FONT_BODY, width=12).pack(side="left")
        self._cron_entry = tk.Entry(row4, bg=T.ACCENT, fg=T.FG, font=T.FONT_SMALL)
        self._cron_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        tk.Label(row4, text="(min hour day month dow)", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=10)

        # Description
        self._desc_label = tk.Label(card, text="", bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._desc_label.pack(anchor="w", padx=10, pady=4)

        # Create button
        ActionButton(card, text="Create Task",
                     command=self._on_create).pack(anchor="w", padx=10, pady=(4, 8))

    def _on_preset_changed(self, event=None):
        preset = self._preset_var.get()
        if preset:
            cron = asched.get_predefined_schedules()[preset]
            self._cron_entry.delete(0, tk.END)
            self._cron_entry.insert(0, cron)
            self._update_description()

    def _update_description(self):
        cron = self._cron_entry.get()
        desc = asched.get_task_schedule_description(cron)
        self._desc_label.config(text=desc)

    def _on_create(self):
        name = self._task_name.get().strip()
        action = self._action_var.get().strip()
        cron = self._cron_entry.get().strip()

        if not name or not action or not cron:
            messagebox.showwarning("Missing Fields", "Fill in all fields")
            return

        # Free-tier quota: max 3 scheduled tasks
        existing = asched.load_scheduled_tasks()
        if not lm.is_within_limit("advanced_scheduler", len(existing)):
            at_limit_dialog("advanced_scheduler")
            return

        # Find action key
        action_key = None
        for key, val in asched.get_available_actions().items():
            if val == action:
                action_key = key
                break

        if not action_key:
            messagebox.showerror("Error", "Invalid action selected")
            return

        try:
            asched.create_scheduled_task(name, action_key, cron)
            messagebox.showinfo("Success", f"Created task '{name}'")
            self._task_name.delete(0, tk.END)
            self._action_var.set("")
            self._cron_entry.delete(0, tk.END)
            self._load_tasks()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_edit(self):
        selection = self._task_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select a task to edit")
            return

        messagebox.showinfo("Edit Task", "Edit functionality coming soon")

    def _on_delete(self):
        selection = self._task_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select a task to delete")
            return

        task_id = selection[0]
        if messagebox.askyesno("Delete Task", "Delete this task?"):
            asched.delete_scheduled_task(task_id)
            self._load_tasks()

    def _on_toggle(self):
        selection = self._task_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select a task to toggle")
            return

        task_id = selection[0]
        tasks = asched.load_scheduled_tasks()
        for task in tasks:
            if task.task_id == task_id:
                task.enabled = not task.enabled
                asched.update_scheduled_task(task_id, enabled=task.enabled)
                break

        self._load_tasks()

    def _load_tasks(self):
        def load():
            tasks = asched.load_scheduled_tasks()
            self.after(0, self._display_tasks, tasks)

        threading.Thread(target=load, daemon=True).start()

    def _display_tasks(self, tasks):
        self._task_tree.delete(*self._task_tree.get_children())

        for task in tasks:
            action_name = asched.get_available_actions().get(task.action, task.action)
            enabled_text = "Yes" if task.enabled else "No"
            enabled_color = T.SUCCESS if task.enabled else T.FG2

            self._task_tree.insert("", "end", iid=task.task_id, text=task.name,
                                  values=(action_name, task.schedule, enabled_text),
                                  tags=("enabled" if task.enabled else "disabled",))

        self._task_tree.tag_configure("enabled", foreground=T.SUCCESS)
        self._task_tree.tag_configure("disabled", foreground=T.FG2)

    def on_activate(self):
        self._load_tasks()
