"""
system_hud.py — mini always-on-top overlay showing CPU / RAM / GPU usage,
plus a Turbo Clean button and a launcher button to bring the main window
to the foreground.

Features:
- Frameless, semi-transparent, always on top
- No taskbar entry
- Draggable by left-click-drag (anywhere except buttons)
- Right-click → context menu (hide / move / exit)
- Updates every 1 second via tkinter .after()
- GPU: tries nvidia-smi → WMI → "N/A"
- "FSD" logo button → restores/raises main window
- "TURBO" button → runs engine.turbo_clean (RAM, temp, recycle, DNS)
"""

import threading
import tkinter as tk
from tkinter import font as tkfont
import subprocess
import sys

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    from engine import turbo_clean
except Exception:
    turbo_clean = None


# ── GPU helpers ───────────────────────────────────────────────────────────────

def _gpu_via_nvidiasmi() -> float | None:
    try:
        flags = 0x08000000 if sys.platform == "win32" else 0
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
            creationflags=flags,
        )
        if r.returncode == 0:
            return float(r.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return None


def _gpu_via_wmi() -> float | None:
    try:
        import wmi  # type: ignore
        c = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        for sensor in c.Sensor():
            if sensor.SensorType == "Load" and "GPU" in sensor.Name:
                return float(sensor.Value)
    except Exception:
        pass
    return None


class GpuMonitor:
    def __init__(self):
        self._value: float | None = None
        self._lock = threading.Lock()
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def _loop(self):
        import time
        while True:
            val = _gpu_via_nvidiasmi()
            if val is None:
                val = _gpu_via_wmi()
            with self._lock:
                self._value = val
            time.sleep(2)

    def get(self) -> float | None:
        with self._lock:
            return self._value


# ── HUD window ────────────────────────────────────────────────────────────────

class SystemHud:
    """
    Small always-on-top overlay.

    Usage:
        hud = SystemHud(root_tk_window)
        # hud.show() / hud.hide() / hud.destroy()
    """

    BG        = "#0a0e1a"
    PANEL     = "#161b27"
    FG        = "#e8edf5"
    FG2       = "#6b7a99"
    CLR_CPU   = "#00d4ff"
    CLR_RAM   = "#00e676"
    CLR_GPU   = "#ffab40"
    BAR_BG    = "#1c2438"
    BORDER    = "#1e2d45"
    HIGHLIGHT = "#00d4ff"
    PURPLE    = "#7b61ff"
    DANGER    = "#ff5252"
    SUCCESS   = "#00e676"
    ALPHA     = 0.92
    WIDTH     = 240
    ROW_H     = 18
    PAD_X     = 10
    PAD_Y     = 8
    BTN_H     = 32

    def __init__(self, master: tk.Misc):
        self._master = master
        self._gpu = GpuMonitor()
        self._drag_x = 0
        self._drag_y = 0
        self._visible = True
        self._after_id = None
        self._turbo_running = False
        self._turbo_pct = 0
        self._turbo_step = ""
        self._turbo_status_until = 0
        self._turbo_result_text = ""

        self._build()
        self._place_bottom_right()
        self._update()

    # ── build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        rows = 3  # CPU / RAM / GPU
        # height = padding + 3 rows + spacing + button row + padding
        height = (self.PAD_Y * 2 + rows * self.ROW_H + (rows - 1) * 4
                  + 8 + self.BTN_H + 4 + 14)  # +14 for status line

        self._win = tk.Toplevel(self._master)
        self._win.overrideredirect(True)
        self._win.wm_attributes("-topmost", True)
        self._win.wm_attributes("-alpha", self.ALPHA)
        if sys.platform == "win32":
            self._win.wm_attributes("-toolwindow", True)

        self._win.configure(bg=self.BG)
        self._win.resizable(False, False)

        self._canvas = tk.Canvas(
            self._win,
            width=self.WIDTH,
            height=height,
            bg=self.BG,
            highlightthickness=0,
        )
        self._canvas.pack()

        # Drag bindings (only the metrics area triggers dragging)
        self._canvas.bind("<ButtonPress-1>",   self._on_canvas_click)
        self._canvas.bind("<B1-Motion>",        self._on_drag_move)
        self._canvas.bind("<ButtonRelease-1>",  self._on_canvas_release)
        self._canvas.bind("<Button-3>",         self._on_right_click)
        self._canvas.bind("<Motion>",           self._on_motion)

        self._height = height
        self._rows: list[dict] = []
        self._draw_static()
        self._draw_rows()

    def _draw_static(self):
        """Background panel + border."""
        c = self._canvas
        c.delete("static")
        # Subtle border glow
        c.create_rectangle(0, 0, self.WIDTH, self._height,
                            fill=self.PANEL, outline=self.BORDER,
                            tags="static")
        # Top accent strip
        c.create_rectangle(0, 0, self.WIDTH, 2,
                            fill=self.HIGHLIGHT, outline="", tags="static")

    def _draw_rows(self):
        """Draw CPU / RAM / GPU rows + bottom button bar."""
        specs = [
            ("CPU", self.CLR_CPU),
            ("RAM", self.CLR_RAM),
            ("GPU", self.CLR_GPU),
        ]
        bar_w = self.WIDTH - self.PAD_X * 2
        bar_h = 5

        # Clear non-static / non-button items
        self._canvas.delete("rows")
        self._rows = []

        for i, (label, color) in enumerate(specs):
            y = self.PAD_Y + i * (self.ROW_H + 4)

            self._canvas.create_text(
                self.PAD_X, y + self.ROW_H // 2,
                text=label, anchor="w", fill=self.FG2,
                font=("Segoe UI", 8, "bold"), tags="rows",
            )

            pct_id = self._canvas.create_text(
                self.WIDTH - self.PAD_X, y + self.ROW_H // 2,
                text="–", anchor="e", fill=self.FG,
                font=("Segoe UI", 9, "bold"), tags="rows",
            )

            bar_x = self.PAD_X + 30
            bar_y = y + (self.ROW_H - bar_h) // 2
            bar_max = bar_w - 30 - 36
            self._canvas.create_rectangle(
                bar_x, bar_y,
                bar_x + bar_max, bar_y + bar_h,
                fill=self.BAR_BG, outline="", tags="rows",
            )

            bar_fill = self._canvas.create_rectangle(
                bar_x, bar_y,
                bar_x, bar_y + bar_h,
                fill=color, outline="", tags="rows",
            )

            self._rows.append({
                "pct_id":   pct_id,
                "bar_fill": bar_fill,
                "bar_x":    bar_x,
                "bar_y":    bar_y,
                "bar_max":  bar_max,
                "bar_h":    bar_h,
                "color":    color,
            })

        # ── Buttons row ───────────────────────────────────────────────────────
        rows_block_h = self.PAD_Y + 3 * self.ROW_H + 2 * 4
        btn_y = rows_block_h + 8
        btn_h = self.BTN_H

        # Logo / launcher button (left, square)
        logo_w = btn_h
        self._logo_rect = (self.PAD_X, btn_y,
                            self.PAD_X + logo_w, btn_y + btn_h)
        self._draw_logo_btn(hover=False)

        # Turbo button (right, fills remaining)
        turbo_x = self.PAD_X + logo_w + 6
        turbo_w = self.WIDTH - turbo_x - self.PAD_X
        self._turbo_rect = (turbo_x, btn_y, turbo_x + turbo_w, btn_y + btn_h)
        self._draw_turbo_btn(hover=False)

        # Status line below buttons
        self._status_y = btn_y + btn_h + 2
        self._status_id = self._canvas.create_text(
            self.WIDTH // 2, self._status_y + 6,
            text="", anchor="center", fill=self.FG2,
            font=("Segoe UI", 7), tags="rows",
        )

    def _draw_logo_btn(self, hover: bool):
        c = self._canvas
        c.delete("logo_btn")
        x0, y0, x1, y1 = self._logo_rect
        bg = self._lerp(self.PANEL, self.HIGHLIGHT, 0.25 if hover else 0.10)
        c.create_rectangle(x0, y0, x1, y1, fill=bg,
                            outline=self._lerp(self.BORDER, self.HIGHLIGHT,
                                                0.6 if hover else 0.3),
                            tags="logo_btn")
        # FSD letter mark
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        c.create_text(cx, cy, text="FSD",
                       fill=self.HIGHLIGHT,
                       font=("Segoe UI", 9, "bold"),
                       tags="logo_btn")

    def _draw_turbo_btn(self, hover: bool):
        c = self._canvas
        c.delete("turbo_btn")
        x0, y0, x1, y1 = self._turbo_rect
        w = x1 - x0

        if self._turbo_running:
            # Progress bar fill
            base_c = self._lerp(self.PURPLE, self.HIGHLIGHT, 0.4)
            c.create_rectangle(x0, y0, x1, y1, fill=self.BAR_BG,
                                outline=self.BORDER, tags="turbo_btn")
            fill_w = int(w * self._turbo_pct / 100)
            if fill_w > 0:
                c.create_rectangle(x0, y0, x0 + fill_w, y1,
                                    fill=base_c, outline="", tags="turbo_btn")
            # Step text
            step_short = (self._turbo_step or "Working…")[:24]
            c.create_text((x0 + x1) // 2, (y0 + y1) // 2,
                           text=f"⚡ {step_short}",
                           fill="#ffffff",
                           font=("Segoe UI", 8, "bold"),
                           tags="turbo_btn")
        else:
            # Gradient background
            c1 = self.PURPLE if not hover else self._lerp(self.PURPLE, "#ffffff", 0.1)
            c2 = self.HIGHLIGHT if not hover else self._lerp(self.HIGHLIGHT, "#ffffff", 0.1)
            steps = 18
            for i in range(steps):
                t = i / steps
                col = self._lerp(c1, c2, t)
                xa = x0 + int(w * t)
                xb = x0 + int(w * (i + 1) / steps) + 1
                c.create_rectangle(xa, y0, xb, y1, fill=col, outline="",
                                    tags="turbo_btn")
            # Border
            c.create_rectangle(x0, y0, x1, y1, fill="",
                                outline=self._lerp(self.HIGHLIGHT, "#ffffff",
                                                    0.5 if hover else 0.0),
                                tags="turbo_btn")
            # Top shine
            shine = self._lerp(c2, "#ffffff", 0.2)
            c.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y0 + (y1 - y0) // 2,
                                fill=shine, outline="", tags="turbo_btn")
            # Label
            c.create_text((x0 + x1) // 2, (y0 + y1) // 2,
                           text="⚡  TURBO CLEAN",
                           fill="#ffffff",
                           font=("Segoe UI", 9, "bold"),
                           tags="turbo_btn")

    def _set_row(self, idx: int, pct: float | None):
        row = self._rows[idx]
        if pct is None:
            self._canvas.itemconfigure(row["pct_id"], text="N/A", fill=self.FG2)
            self._canvas.coords(
                row["bar_fill"],
                row["bar_x"], row["bar_y"],
                row["bar_x"], row["bar_y"] + row["bar_h"],
            )
            return

        pct = max(0.0, min(100.0, pct))
        fill_w = int(row["bar_max"] * pct / 100)

        if pct < 60:
            bar_color = row["color"]
        elif pct < 80:
            bar_color = "#ffab40"
        else:
            bar_color = self.DANGER

        self._canvas.itemconfigure(
            row["pct_id"],
            text=f"{pct:.0f}%",
            fill=self.FG,
        )
        self._canvas.itemconfigure(row["bar_fill"], fill=bar_color)
        self._canvas.coords(
            row["bar_fill"],
            row["bar_x"], row["bar_y"],
            row["bar_x"] + fill_w, row["bar_y"] + row["bar_h"],
        )

    def _lerp(self, c1: str, c2: str, t: float) -> str:
        t = max(0.0, min(1.0, t))
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

    # ── position ──────────────────────────────────────────────────────────────

    def _place_bottom_right(self):
        self._win.update_idletasks()
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        x = sw - self.WIDTH - 12
        y = sh - self._height - 48
        self._win.geometry(f"{self.WIDTH}x{self._height}+{x}+{y}")

    # ── update loop ───────────────────────────────────────────────────────────

    def _update(self):
        if not self._visible:
            self._after_id = self._win.after(1000, self._update)
            return

        if _PSUTIL:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
        else:
            cpu, ram = None, None

        gpu = self._gpu.get()

        self._set_row(0, cpu)
        self._set_row(1, ram)
        self._set_row(2, gpu)

        # Status text auto-clear
        import time
        if self._turbo_status_until and time.time() > self._turbo_status_until:
            self._turbo_result_text = ""
            self._turbo_status_until = 0

        self._canvas.itemconfigure(self._status_id,
                                     text=self._turbo_result_text)

        # Refresh turbo button if running
        if self._turbo_running:
            self._draw_turbo_btn(hover=False)

        self._after_id = self._win.after(1000, self._update)

    # ── click / drag dispatch ─────────────────────────────────────────────────

    def _hit(self, x: int, y: int, rect: tuple) -> bool:
        return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]

    def _on_canvas_click(self, event):
        # Check if hit a button first
        if self._hit(event.x, event.y, self._logo_rect):
            self._mode = "logo"
            return
        if self._hit(event.x, event.y, self._turbo_rect):
            self._mode = "turbo"
            return
        # Otherwise: start drag
        self._mode = "drag"
        self._drag_x = event.x_root - self._win.winfo_x()
        self._drag_y = event.y_root - self._win.winfo_y()

    def _on_drag_move(self, event):
        if getattr(self, "_mode", None) == "drag":
            x = event.x_root - self._drag_x
            y = event.y_root - self._drag_y
            self._win.geometry(f"+{x}+{y}")

    def _on_canvas_release(self, event):
        mode = getattr(self, "_mode", None)
        if mode == "logo" and self._hit(event.x, event.y, self._logo_rect):
            self._raise_main_window()
        elif mode == "turbo" and self._hit(event.x, event.y, self._turbo_rect):
            self._start_turbo()
        self._mode = None

    def _on_motion(self, event):
        # Hover effects
        on_logo = self._hit(event.x, event.y, self._logo_rect)
        on_turbo = self._hit(event.x, event.y, self._turbo_rect)

        if on_logo or on_turbo:
            self._canvas.config(cursor="hand2")
        else:
            self._canvas.config(cursor="")

        if getattr(self, "_logo_hover", False) != on_logo:
            self._logo_hover = on_logo
            self._draw_logo_btn(hover=on_logo)
        if getattr(self, "_turbo_hover", False) != on_turbo and not self._turbo_running:
            self._turbo_hover = on_turbo
            self._draw_turbo_btn(hover=on_turbo)

    # ── actions ───────────────────────────────────────────────────────────────

    def _raise_main_window(self):
        try:
            self._master.deiconify()
            self._master.lift()
            self._master.focus_force()
            self._master.attributes("-topmost", True)
            self._master.after(150, lambda: self._master.attributes("-topmost", False))
        except Exception:
            pass

    def _start_turbo(self):
        if self._turbo_running or turbo_clean is None:
            return
        self._turbo_running = True
        self._turbo_pct = 0
        self._turbo_step = "Starting…"
        self._draw_turbo_btn(hover=False)

        def on_progress(step, pct):
            self._turbo_step = step
            self._turbo_pct = pct
            try:
                self._win.after(0, lambda: self._draw_turbo_btn(hover=False))
            except Exception:
                pass

        def on_done(stats):
            import time
            self._turbo_running = False
            self._turbo_pct = 0
            self._turbo_step = ""
            ram = stats.get("ram_freed_mb", 0)
            disk = stats.get("disk_freed_mb", 0)
            self._turbo_result_text = f"✓ {ram:.0f} MB RAM, {disk:.0f} MB disk freed"
            self._turbo_status_until = time.time() + 8
            try:
                self._win.after(0, lambda: self._draw_turbo_btn(hover=False))
            except Exception:
                pass

        turbo_clean.run_async(progress_cb=on_progress, done_cb=on_done)

    # ── right-click menu ──────────────────────────────────────────────────────

    def _on_right_click(self, event):
        menu = tk.Menu(self._win, tearoff=0,
                       bg=self.PANEL, fg=self.FG,
                       activebackground=self.HIGHLIGHT,
                       activeforeground="#000000",
                       font=("Segoe UI", 9))
        menu.add_command(label="Otwórz aplikację", command=self._raise_main_window)
        if not self._turbo_running:
            menu.add_command(label="⚡  Turbo Clean", command=self._start_turbo)
        menu.add_separator()
        if self._visible:
            menu.add_command(label="Ukryj HUD", command=self.hide)
        else:
            menu.add_command(label="Pokaż HUD", command=self.show)
        menu.add_command(label="Przenieś do rogu ↘", command=self._place_bottom_right)
        menu.add_separator()
        menu.add_command(label="Zamknij HUD", command=self.destroy)
        menu.tk_popup(event.x_root, event.y_root)

    # ── public API ────────────────────────────────────────────────────────────

    def show(self):
        self._visible = True
        self._win.deiconify()

    def hide(self):
        self._visible = False
        self._win.withdraw()

    def destroy(self):
        if self._after_id:
            try:
                self._win.after_cancel(self._after_id)
            except Exception:
                pass
        try:
            self._win.destroy()
        except Exception:
            pass
