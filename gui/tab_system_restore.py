"""System Restore tab — manage restore points, storage, and SR status."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import theme as T
from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style
from engine import system_restore


class SystemRestoreTab(tk.Frame):
    def __init__(self, parent, status_bar):
        super().__init__(parent, bg=T.BG)
        self._status = status_bar
        self._restore_points: list[dict] = []
        self._build_ui()
        self.after(400, self._refresh)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top: SR status + storage ──────────────────────────────────────────
        top = tk.Frame(self, bg=T.BG)
        top.pack(fill="x", padx=16, pady=(16, 4))

        # SR status card
        st_card = Card(top)
        st_card.pack(side="left", fill="y", padx=(0, 8))
        SectionLabel(st_card, "System Restore Status").pack(anchor="w", padx=8, pady=(6, 2))

        self._sr_status_lbl = tk.Label(st_card, text="Checking…",
                                       bg=T.PANEL, fg=T.FG2, font=T.FONT_BOLD)
        self._sr_status_lbl.pack(padx=12, pady=(4, 2), anchor="w")

        self._sr_points_lbl = tk.Label(st_card, text="",
                                       bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL)
        self._sr_points_lbl.pack(padx=12, pady=2, anchor="w")

        self._enable_toggle_btn = ActionButton(st_card, "Enable System Restore",
                                               command=self._toggle_sr)
        self._enable_toggle_btn.pack(padx=8, pady=(6, 8), anchor="w")

        # Storage card
        stor_card = Card(top)
        stor_card.pack(side="left", fill="y", padx=(0, 8))
        SectionLabel(stor_card, "Shadow Storage").pack(anchor="w", padx=8, pady=(6, 2))

        self._storage_lbl = tk.Label(stor_card, text="Checking…",
                                     bg=T.PANEL, fg=T.FG2, font=T.FONT_SMALL,
                                     justify="left")
        self._storage_lbl.pack(padx=12, pady=(4, 8), anchor="w")

        # Warning card
        warn_card = Card(top)
        warn_card.pack(side="left", fill="both", expand=True)
        SectionLabel(warn_card, "Notes").pack(anchor="w", padx=8, pady=(6, 2))
        tk.Label(warn_card,
                 text="Creating or deleting restore points requires\n"
                      "administrator rights.\n\n"
                      "Do not turn off your PC during operations.\n\n"
                      "Restore points are stored on the system drive.",
                 bg=T.PANEL, fg=T.WARNING, font=T.FONT_SMALL,
                 justify="left").pack(padx=12, pady=(4, 8), anchor="w")

        # ── Create restore point row ──────────────────────────────────────────
        create_card = Card(self)
        create_card.pack(fill="x", padx=16, pady=4)
        create_row = tk.Frame(create_card, bg=T.PANEL)
        create_row.pack(fill="x", padx=8, pady=8)

        SectionLabel(create_row, "Create Restore Point").pack(side="left", padx=(0, 8))
        self._rp_name_entry = tk.Entry(create_row, width=30, bg=T.ACCENT,
                                       fg=T.FG, insertbackground=T.FG,
                                       font=T.FONT_BODY, relief="flat")
        self._rp_name_entry.insert(0, "FreeSystemDoctor Checkpoint")
        self._rp_name_entry.pack(side="left", padx=4)
        ActionButton(create_row, "Create",
                     command=self._create_rp).pack(side="left", padx=6)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=T.BG)
        btn_row.pack(fill="x", padx=16, pady=4)
        ActionButton(btn_row, "Refresh",
                     command=self._refresh).pack(side="left", padx=(0, 8))
        ActionButton(btn_row, "Delete Selected",
                     command=self._delete_selected, danger=True).pack(side="left", padx=(0, 8))

        # ── Progress ──────────────────────────────────────────────────────────
        self._progress = ProgressBar(self, bg=T.BG)
        self._progress.pack(fill="x", padx=16, pady=4)

        # ── Restore points treeview ───────────────────────────────────────────
        tv_card = Card(self)
        tv_card.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        SectionLabel(tv_card, "Restore Points").pack(anchor="w", padx=8, pady=(6, 2))

        cols = ("Description", "Date", "Type")
        self._tv = ttk.Treeview(tv_card, columns=cols, show="tree headings")
        apply_treeview_style(self._tv)
        self._tv.heading("#0",         text="Seq #",       anchor="w")
        self._tv.heading("Description",text="Description", anchor="w")
        self._tv.heading("Date",       text="Date",        anchor="w")
        self._tv.heading("Type",       text="Type",        anchor="w")
        self._tv.column("#0",         width=60,  minwidth=45)
        self._tv.column("Description",width=280, minwidth=160)
        self._tv.column("Date",       width=155, minwidth=100)
        self._tv.column("Type",       width=160, minwidth=90)

        sb = ttk.Scrollbar(tv_card, orient="vertical", command=self._tv.yview)
        self._tv.configure(yscrollcommand=sb.set)
        self._tv.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        sb.pack(side="right", fill="y", pady=(0, 8), padx=(0, 8))

    # ── refresh ───────────────────────────────────────────────────────────────

    def _refresh(self):
        self._progress.indeterminate(True)
        self._status.set("Loading restore points…")
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        try:
            points  = system_restore.get_restore_points()
            sr_stat = system_restore.get_restore_status()
            storage = system_restore.get_shadow_storage()
            self.after(0, self._apply_refresh, points, sr_stat, storage)
        except Exception as exc:
            self.after(0, self._status.set, f"Refresh error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _apply_refresh(self, points: list[dict], sr_stat: dict, storage: dict):
        self._progress.indeterminate(False)
        self._restore_points = points

        # SR status label
        enabled = sr_stat.get("enabled", False)
        if enabled:
            self._sr_status_lbl.config(text="ENABLED", fg=T.SUCCESS)
            self._enable_toggle_btn.config(text="Re-enable System Restore")
        else:
            self._sr_status_lbl.config(text="DISABLED", fg=T.DANGER)
            self._enable_toggle_btn.config(text="Enable System Restore")

        count = sr_stat.get("point_count", len(points))
        self._sr_points_lbl.config(text=f"{count} restore point(s)")

        # Storage label
        used_gb  = storage.get("used_gb", 0.0)
        alloc_gb = storage.get("allocated_gb", 0.0)
        max_gb   = storage.get("max_gb", 0.0)
        drive    = storage.get("drive", "C:")
        self._storage_lbl.config(
            text=f"Drive:     {drive}\n"
                 f"Used:      {used_gb:.2f} GB\n"
                 f"Allocated: {alloc_gb:.2f} GB\n"
                 f"Maximum:   {max_gb:.2f} GB"
        )

        # Populate treeview
        for item in self._tv.get_children():
            self._tv.delete(item)
        for p in sorted(points, key=lambda x: x.get("sequence_number", 0), reverse=True):
            self._tv.insert("", "end",
                            text=str(p.get("sequence_number", "")),
                            values=(p.get("description", ""),
                                    p.get("creation_time", ""),
                                    p.get("type_str", "")))

        self._status.set(
            f"Found {len(points)} restore point(s). "
            f"System Restore is {'enabled' if enabled else 'disabled'}."
        )

    # ── toggle SR enabled ─────────────────────────────────────────────────────

    def _toggle_sr(self):
        if not messagebox.askyesno(
            "Enable System Restore",
            "Enable System Restore on drive C:?\n\n"
            "This requires administrator rights."
        ):
            return
        self._progress.indeterminate(True)
        self._status.set("Enabling System Restore…")
        threading.Thread(target=self._do_toggle_sr, daemon=True).start()

    def _do_toggle_sr(self):
        try:
            ok = system_restore.enable_system_restore("C:")
            self.after(0, self._toggle_sr_done, ok)
        except Exception as exc:
            self.after(0, self._status.set, f"Error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _toggle_sr_done(self, ok: bool):
        self._progress.indeterminate(False)
        if ok:
            self._status.set("System Restore enabled.")
            messagebox.showinfo("System Restore", "System Restore has been enabled on C:.")
            self._refresh()
        else:
            messagebox.showerror("Error",
                                 "Could not enable System Restore.\n"
                                 "(Requires administrator rights)")

    # ── create restore point ──────────────────────────────────────────────────

    def _create_rp(self):
        name = self._rp_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Empty name", "Enter a name for the restore point.")
            return
        if not messagebox.askyesno(
            "Create Restore Point",
            f"Create restore point:\n'{name}'?\n\n"
            "Requires administrator rights."
        ):
            return
        self._progress.indeterminate(True)
        self._status.set(f"Creating restore point '{name}'…")
        threading.Thread(target=self._do_create, args=(name,), daemon=True).start()

    def _do_create(self, name: str):
        try:
            ok = system_restore.create_restore_point(name)
            self.after(0, self._create_done, name, ok)
        except Exception as exc:
            self.after(0, self._status.set, f"Create error: {exc}")
            self.after(0, self._progress.indeterminate, False)

    def _create_done(self, name: str, ok: bool):
        self._progress.indeterminate(False)
        if ok:
            self._status.set(f"Restore point '{name}' created.")
            messagebox.showinfo("Created",
                                f"Restore point created successfully:\n'{name}'")
            self._refresh()
        else:
            messagebox.showerror("Error",
                                 "Could not create restore point.\n"
                                 "(Requires administrator rights or SR is disabled)")

    # ── delete restore point ──────────────────────────────────────────────────

    def _delete_selected(self):
        sel = self._tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a restore point to delete.")
            return
        # Collect sequence numbers
        seq_nums: list[int] = []
        descs: list[str] = []
        for iid in sel:
            seq_str = self._tv.item(iid, "text")
            try:
                seq_nums.append(int(seq_str))
            except ValueError:
                pass
            vals = self._tv.item(iid, "values")
            descs.append(vals[0] if vals else seq_str)

        if not seq_nums:
            return
        if not messagebox.askyesno(
            "Delete Restore Points",
            f"Permanently delete {len(seq_nums)} restore point(s)?\n\n"
            + "\n".join(descs[:5]) +
            ("\n…" if len(descs) > 5 else "") +
            "\n\nThis cannot be undone."
        ):
            return
        self._progress.indeterminate(True)
        self._status.set(f"Deleting {len(seq_nums)} restore point(s)…")
        threading.Thread(target=self._do_delete,
                         args=(seq_nums,), daemon=True).start()

    def _do_delete(self, seq_nums: list[int]):
        ok_count = 0
        fail_count = 0
        for seq in seq_nums:
            self.after(0, self._status.set, f"Deleting sequence #{seq}…")
            try:
                ok = system_restore.delete_restore_point(seq)
                if ok:
                    ok_count += 1
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1
        self.after(0, self._delete_done, ok_count, fail_count)

    def _delete_done(self, ok: int, fail: int):
        self._progress.indeterminate(False)
        self._status.set(f"Deleted {ok} restore point(s). {fail} failed.")
        if fail:
            messagebox.showwarning("Partial failure",
                                   f"Deleted: {ok}\nFailed: {fail}\n\n"
                                   "(Some deletions may require administrator rights)")
        self._refresh()
