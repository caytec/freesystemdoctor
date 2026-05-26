"""Main application window — premium sidebar navigation with glassmorphism design."""

import webbrowser
import tkinter as tk
from tkinter import ttk
import threading
import time

from . import theme as T
from .widgets import StatusBar, SidebarButton, apply_treeview_style, Toast

KOFI_URL = "https://ko-fi.com/F1F51O3A4A"

# ── Page imports ───────────────────────────────────────────────────────────────
from .page_care             import CarePage
from .page_speedup          import SpeedUpPage
from .page_protect          import ProtectPage
from .page_software         import SoftwarePage
from .page_action_center    import ActionCenterPage
from .page_ai_agent         import AIAgentPage
from .page_disk_optimizer   import DiskOptimizerPage
from .page_internet_booster import InternetBoosterPage
from .page_turbo_mode       import TurboModePage
from .page_cpu_optimizer    import CpuOptimizerPage
from .page_space_hogs       import SpaceHogsPage
from .page_driver_updater   import DriverUpdaterPage
from .page_system_restore   import SystemRestorePage
from .page_empty_folder_finder import EmptyFolderFinderPage
from .page_benchmark        import BenchmarkPage
from .page_scheduled_cleaner import ScheduledCleanerPage
from .page_health_check     import HealthCheckPage
from .page_disk_analyzer    import DiskAnalyzerPage
from .page_cloud_cleaner    import CloudCleanerPage
from .page_file_recovery    import FileRecoveryPage
from .page_app_prioritizer  import AppPrioritizerPage
from .page_app_freezer      import AppFreezerPage
from .page_webcam_protection import WebcamProtectionPage
from .page_smart_notifications import SmartNotificationsPage
from .page_browser_plugins  import BrowserPluginsPage
from .page_drive_wipe       import DriveWipePage
from .page_browser_history  import BrowserHistoryPage
from .page_bandwidth_monitor import BandwidthMonitorPage
from .page_registry_backup  import RegistryBackupPage
from .page_speedup_wizard   import SpeedupWizardPage
from .page_settings         import SettingsPage
from .page_hardware_monitor import HardwareMonitorPage
from .page_network_security import NetworkSecurityPage
from .page_idle_maintenance import IdleMaintenancePage
from .page_performance_profiles import PerformanceProfilesPage
from .page_smart_defrag     import SmartDefragPage
from .page_system_backup    import SystemBackupPage
from .page_startup_insights import StartupInsightsPage
from .page_resource_monitor import ResourceMonitorPage
from .page_onedrive_cleaner import OneDriveCleanerPage
from .page_system_repair    import SystemRepairPage
from .page_browser_profile_manager import BrowserProfileManagerPage
from .page_email_security   import EmailSecurityPage
from .page_advanced_scheduler import AdvancedSchedulerPage
from .page_theme_manager    import ThemeManagerPage
from .page_game_booster     import GameBoosterPage
from .page_deep_clean       import DeepCleanPage
from .first_run_dialog      import maybe_show_first_run_dialog
from .page_realtime_dashboard import RealtimeDashboardPage
from .page_cron_builder     import CronBuilderPage
from .page_home             import HomePage
from .page_dns_protector    import DnsProtectorPage
from .page_service_optimizer import ServiceOptimizerPage
from .page_auto_shutdown    import AutoShutdownPage
from .page_icon_saver       import IconSaverPage
from .page_browser_autoclean import BrowserAutoCleanPage
from .page_publisher        import PublisherPage
from .system_hud            import SystemHud

# Legacy tool tabs
from .tab_cleaner      import CleanerTab
from .tab_startup      import StartupTab
from .tab_duplicates   import DuplicatesTab
from .tab_large_files  import LargeFilesTab
from .tab_registry     import RegistryTab
from .tab_uninstaller  import UninstallerTab
from .tab_memory       import MemoryTab
from .tab_network      import NetworkTab
from .tab_privacy      import PrivacyTab
from .tab_services     import ServicesTab
from .tab_tasks        import TasksTab
from .tab_shredder     import ShredderTab
from .tab_advanced     import AdvancedTab


# ── Navigation structure ───────────────────────────────────────────────────────
# Each entry: (key, icon, label, PageClass)
# Categories shown as separators in sidebar

_NAV_CATEGORIES = [
    # ── Dashboard & Monitoring ────────────────────────────────────────────────
    {
        "id":    "dashboard",
        "label": "PULPIT",       # Dashboard
        "color": T.HIGHLIGHT,
        "items": [
            ("home",       "🏠", "Home",           HomePage),
            ("health",     "❤",  "Health Check",   HealthCheckPage),
            ("dashboard",  "📊", "Live Monitor",   RealtimeDashboardPage),
            ("monitor",    "📈", "Resource Mon.",  ResourceMonitorPage),
            ("hardware",   "🌡",  "HW Monitor",     HardwareMonitorPage),
            ("bandwidth",  "📶", "Bandwidth",      BandwidthMonitorPage),
        ],
    },
    # ── AI & Automation ───────────────────────────────────────────────────────
    {
        "id":    "ai",
        "label": "AI / AUTO",
        "color": T.PURPLE,
        "items": [
            ("ai",         "🤖", "AI Agent",        AIAgentPage),
            ("wizard",     "⭐", "Speedup Wizard",  SpeedupWizardPage),
            ("idle",       "💤", "Idle Maintain.",  IdleMaintenancePage),
            ("auto",       "⚙",  "Scheduled Clean", ScheduledCleanerPage),
            ("adv_sched",  "📅", "Adv. Scheduler",  AdvancedSchedulerPage),
            ("cron",       "⏰", "Cron Builder",    CronBuilderPage),
            ("notifications","🔔","Smart Alerts",   SmartNotificationsPage),
        ],
    },
    # ── Performance & Speed ───────────────────────────────────────────────────
    {
        "id":    "performance",
        "label": "WYDAJNOŚĆ",     # Performance
        "color": T.SUCCESS,
        "items": [
            ("care",       "♥",  "System Care",     CarePage),
            ("speedup",    "⚡", "Speed Up",         SpeedUpPage),
            ("turbo",      "🔥", "Turbo Mode",      TurboModePage),
            ("cpu_max",    "⚡", "CPU Max Perf.",   CpuOptimizerPage),
            ("profiles",   "🎯", "Perf. Profiles",  PerformanceProfilesPage),
            ("memory",     "🧠", "RAM & Perf.",     None),
            ("svc_opt",    "⚙",  "Service Optim.",  ServiceOptimizerPage),
            ("startup",    "🚀", "Startup Insights",StartupInsightsPage),
        ],
    },
    # ── Gaming ────────────────────────────────────────────────────────────────
    {
        "id":    "gaming",
        "label": "GAMING",
        "color": "#ff5252",
        "items": [
            ("game",       "🎮", "Game Booster",   GameBoosterPage),
            ("deep_clean", "💾", "Deep Clean",     DeepCleanPage),
            ("app_prio",   "⚡", "App Priority",   AppPrioritizerPage),
            ("app_freeze", "❄",  "App Freezer",    AppFreezerPage),
            ("bench",      "📈", "Benchmark",      BenchmarkPage),
        ],
    },
    # ── Cleaning ──────────────────────────────────────────────────────────────
    {
        "id":    "clean",
        "label": "CZYSZCZENIE",   # Cleaning
        "color": T.WARNING,
        "items": [
            ("clean_tools","🧹", "All Cleaners",    None),
            ("disk_analyzer","📁","Disk Analyzer",  DiskAnalyzerPage),
            ("space_hogs",  "🗂","Space Hogs",      SpaceHogsPage),
            ("empty",      "📂", "Empty Folders",   EmptyFolderFinderPage),
            ("browser_hist","🌐","Browser History", BrowserHistoryPage),
            ("browser_auto","🔄","Browser Auto-Clean", BrowserAutoCleanPage),
            ("cloud",      "☁",  "Cloud Cleaner",   CloudCleanerPage),
            ("onedrive",   "🔵", "OneDrive",        OneDriveCleanerPage),
            ("drive_wipe", "💿", "Drive Wipe",      DriveWipePage),
        ],
    },
    # ── Disk & Storage ────────────────────────────────────────────────────────
    {
        "id":    "disk",
        "label": "DYSK",         # Disk
        "color": "#40c4ff",
        "items": [
            ("disk_opt",   "💿", "Disk Optimizer",  DiskOptimizerPage),
            ("defrag",     "🔄", "Smart Defrag",    SmartDefragPage),
            ("recovery",   "🔍", "File Recovery",   FileRecoveryPage),
        ],
    },
    # ── Network ───────────────────────────────────────────────────────────────
    {
        "id":    "network",
        "label": "SIEĆ",         # Network
        "color": "#7b61ff",
        "items": [
            ("internet",   "🌐", "Net Booster",     InternetBoosterPage),
            ("dns_lock",   "🔐", "DNS Protector",   DnsProtectorPage),
            ("network",    "🔒", "Network Sec.",    NetworkSecurityPage),
        ],
    },
    # ── Protection & Privacy ──────────────────────────────────────────────────
    {
        "id":    "protect",
        "label": "OCHRONA",      # Protection
        "color": T.DANGER,
        "items": [
            ("protect",    "🛡",  "Protection",      ProtectPage),
            ("webcam",     "📷", "Webcam Guard",    WebcamProtectionPage),
            ("email",      "📧", "Email Security",  EmailSecurityPage),
            ("plugins",    "🧩", "Browser Plugins", BrowserPluginsPage),
            ("browser_mgr","🌐", "Browser Mgr.",    BrowserProfileManagerPage),
        ],
    },
    # ── Repair & Backup ───────────────────────────────────────────────────────
    {
        "id":    "repair",
        "label": "NAPRAWA",      # Repair
        "color": "#ffab40",
        "items": [
            ("repair",     "🔨", "System Repair",   SystemRepairPage),
            ("restore",    "⏮",  "Sys. Restore",    SystemRestorePage),
            ("backup",     "📦", "System Backup",   SystemBackupPage),
            ("reg_backup", "💾", "Reg. Backup",     RegistryBackupPage),
            ("drivers",    "🔧", "Drivers",         DriverUpdaterPage),
        ],
    },
    # ── Apps & Software ───────────────────────────────────────────────────────
    {
        "id":    "apps",
        "label": "APLIKACJE",    # Apps
        "color": "#00e676",
        "items": [
            ("software",   "⬇",  "Software",        SoftwarePage),
            ("action",     "⚠",  "Action Center",   ActionCenterPage),
            ("auto_off",   "⏻",  "Auto-Shutdown",   AutoShutdownPage),
        ],
    },
    # ── Customize & Settings ──────────────────────────────────────────────────
    {
        "id":    "personal",
        "label": "WYGLĄD",       # Look & Feel
        "color": T.FG2,
        "items": [
            ("themes",     "🎨", "Themes",          ThemeManagerPage),
            ("icons",      "🖥", "Icon Saver",      IconSaverPage),
            ("publisher",  "🌍", "Publisher",       PublisherPage),
            ("settings",   "⚙",  "Settings",        SettingsPage),
            ("toolbox",    "🔧", "All Tools",       None),
        ],
    },
]

_TOOLS_TABS = [
    ("Disk Cleaner",      CleanerTab),
    ("Startup",           StartupTab),
    ("Duplicates",        DuplicatesTab),
    ("Large Files",       LargeFilesTab),
    ("Registry",          RegistryTab),
    ("Uninstaller",       UninstallerTab),
    ("RAM & Performance", MemoryTab),
    ("Network",           NetworkTab),
    ("Privacy",           PrivacyTab),
    ("Services",          ServicesTab),
    ("Sched. Tasks",      TasksTab),
    ("File Shredder",     ShredderTab),
    ("Advanced",          AdvancedTab),
]


class ToolsPage(tk.Frame):
    """Wrapper that hosts all legacy tabs in an inner notebook."""
    def __init__(self, parent, app_ref, status_bar):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref

        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔧", bg=T.ACCENT, fg=T.HIGHLIGHT,
                 font=(T.FONT_FAMILY, 16)).pack(side="left", padx=(16, 8))
        tk.Label(hdr, text="All Tools", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left")
        tk.Label(hdr, text="  Full maintenance toolkit",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        for label, TabClass in _TOOLS_TABS:
            frame = TabClass(nb, status_bar)
            nb.add(frame, text=f"  {label}  ")

    def on_activate(self):
        pass


# ── Tooltip ────────────────────────────────────────────────────────────────────

class _Tooltip(tk.Toplevel):
    def __init__(self, parent, text: str, color: str = T.HIGHLIGHT):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=T.ACCENT)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        # Left color accent
        tk.Frame(self, bg=color, width=3).pack(side="left", fill="y")
        tk.Label(self, text=text, bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_BODY, padx=10, pady=6).pack()

        # Position right of parent widget
        parent.update_idletasks()
        x = parent.winfo_rootx() + parent.winfo_width() + 4
        y = parent.winfo_rooty() + parent.winfo_height() // 2 - 14
        self.geometry(f"+{x}+{y}")


# ── Sidebar panel ──────────────────────────────────────────────────────────────

class _SidebarPanel(tk.Frame):
    """
    Two-column sidebar:
      col 0 (72px): icon-only quick nav (pinned categories)
      col 1 (180px, sliding): full label list for active category
    """
    ICON_W = 72
    EXPAND_W = 180

    def __init__(self, parent, switch_cb, **kw):
        kw.setdefault("bg", T.SIDEBAR)
        super().__init__(parent, **kw)
        self._switch = switch_cb
        self._active_key = ""
        self._active_cat = ""
        self._expanded = False
        self._expand_w = 0
        self._tooltip_win: _Tooltip = None

        self._btns: dict[str, SidebarButton] = {}      # key → SidebarButton
        self._cat_btns: dict[str, tk.Canvas] = {}      # cat_id → category button

        self._build()

    def _build(self):
        # Icon column (always visible)
        self._icon_col = tk.Frame(self, bg=T.SIDEBAR, width=self.ICON_W)
        self._icon_col.pack(side="left", fill="y")
        self._icon_col.pack_propagate(False)

        # Logo mark
        logo = tk.Canvas(self._icon_col, width=self.ICON_W, height=56,
                         bg=T.SIDEBAR, highlightthickness=0)
        logo.pack()
        self._draw_logo(logo)
        self._animate_logo(logo)

        # Category icon buttons
        for cat in _NAV_CATEGORIES:
            first_icon = cat["items"][0][1] if cat["items"] else "●"
            self._add_cat_btn(cat["id"], cat["label"], first_icon, cat["color"])

        # Separator + version
        tk.Frame(self._icon_col, bg=T.BORDER, height=1).pack(fill="x", padx=6, pady=4)
        tk.Label(self._icon_col, text="v2.2", bg=T.SIDEBAR,
                 fg=T.lerp_color(T.FG2, T.SIDEBAR, 0.5),
                 font=T.FONT_MICRO).pack(side="bottom", pady=4)
        donate = tk.Label(self._icon_col, text="☕", bg=T.SIDEBAR,
                          fg=T.lerp_color(T.HIGHLIGHT, T.FG2, 0.3),
                          font=(T.FONT_FAMILY, 14), cursor="hand2")
        donate.pack(side="bottom", pady=2)
        donate.bind("<Button-1>", lambda e: webbrowser.open(KOFI_URL))
        donate.bind("<Enter>", lambda e: donate.config(fg=T.HIGHLIGHT))
        donate.bind("<Leave>",
                    lambda e: donate.config(fg=T.lerp_color(T.HIGHLIGHT, T.FG2, 0.3)))

        # Expand panel (slides in/out)
        self._expand_frame = tk.Frame(self, bg=T.lerp_color(T.SIDEBAR, T.ACCENT, 0.3),
                                      width=0)
        self._expand_frame.pack(side="left", fill="y")
        self._expand_frame.pack_propagate(False)

        # Divider between expand panel and content
        self._divider = tk.Frame(self, bg=T.BORDER, width=1)
        self._divider.pack(side="left", fill="y")

        # Scrollable inner for expand panel
        self._expand_canvas = tk.Canvas(self._expand_frame, bg=T.lerp_color(T.SIDEBAR, T.ACCENT, 0.3),
                                        highlightthickness=0, bd=0)
        self._expand_canvas.pack(fill="both", expand=True)
        self._expand_inner = tk.Frame(self._expand_canvas,
                                      bg=T.lerp_color(T.SIDEBAR, T.ACCENT, 0.3))
        self._expand_win = self._expand_canvas.create_window(0, 0, window=self._expand_inner,
                                                              anchor="nw")
        self._expand_inner.bind("<Configure>", self._on_expand_configure)
        self._expand_canvas.bind("<Configure>", self._on_expand_canvas_configure)

        sb = ttk.Scrollbar(self._expand_frame, orient="vertical",
                            command=self._expand_canvas.yview)
        sb.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self._expand_canvas.configure(yscrollcommand=sb.set)
        self._expand_canvas.bind("<MouseWheel>",
                                  lambda e: self._expand_canvas.yview_scroll(
                                      int(-1*(e.delta/120)), "units"))

        # Click-away closes expand panel
        # (handled via global binding in App)

    def _on_expand_configure(self, e):
        self._expand_canvas.configure(scrollregion=self._expand_canvas.bbox("all"))

    def _on_expand_canvas_configure(self, e):
        self._expand_canvas.itemconfig(self._expand_win, width=e.width)

    def _draw_logo(self, canvas):
        w, h = self.ICON_W, 56
        canvas.delete("all")
        cx, cy = w//2, h//2
        canvas.create_oval(cx-18, cy-18, cx+18, cy+18,
                           fill=T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, 0.15),
                           outline=T.lerp_color(T.BORDER, T.HIGHLIGHT, 0.4))
        canvas.create_text(cx, cy, text="FSD",
                           fill=T.HIGHLIGHT, font=(T.FONT_FAMILY, 9, "bold"))

    def _animate_logo(self, canvas, phase: int = 0):
        t = (1 + import_math_sin(phase * 0.05)) / 2
        col = T.lerp_color(T.lerp_color(T.BORDER, T.HIGHLIGHT, 0.4),
                           T.HIGHLIGHT, t * 0.6)
        canvas.delete("all")
        cx, cy = self.ICON_W//2, 28
        canvas.create_oval(cx-18, cy-18, cx+18, cy+18,
                           fill=T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, 0.08 + t*0.1),
                           outline=col)
        canvas.create_text(cx, cy, text="FSD",
                           fill=T.lerp_color(T.HIGHLIGHT, "#ffffff", t*0.2),
                           font=(T.FONT_FAMILY, 9, "bold"))
        canvas.after(50, lambda: self._animate_logo(canvas, phase + 1))

    def _add_cat_btn(self, cat_id: str, label: str, icon: str, color: str):
        """Add a category tab on the icon column."""
        c = tk.Canvas(self._icon_col, width=self.ICON_W, height=52,
                      bg=T.SIDEBAR, highlightthickness=0, cursor="hand2")
        c.pack()
        self._cat_btns[cat_id] = c

        def draw(active=False, hover=False):
            c.delete("all")
            if active:
                bg = T.lerp_color(T.SIDEBAR, color, 0.15)
                c.create_rectangle(0, 0, self.ICON_W, 52, fill=bg, outline="")
                c.create_rectangle(0, 4, 3, 48, fill=color, outline="")
                # glow
                glow = T.lerp_color(color, T.SIDEBAR, 0.55)
                c.create_rectangle(3, 4, 12, 48, fill=glow, outline="")
                icon_c = color
                lbl_c  = T.FG
            elif hover:
                bg = T.lerp_color(T.SIDEBAR, T.ACCENT, 0.8)
                c.create_rectangle(0, 0, self.ICON_W, 52, fill=bg, outline="")
                icon_c = T.lerp_color(T.FG2, color, 0.5)
                lbl_c  = T.lerp_color(T.FG2, T.FG, 0.5)
            else:
                c.create_rectangle(0, 0, self.ICON_W, 52, fill=T.SIDEBAR, outline="")
                icon_c = T.FG2
                lbl_c  = T.FG2

            c.create_text(self.ICON_W//2, 20, text=icon, fill=icon_c,
                          font=(T.FONT_FAMILY, 16))
            c.create_text(self.ICON_W//2, 40, text=label[:6],
                          fill=lbl_c, font=T.FONT_MICRO)

        draw()
        c._draw = draw
        c._active = False

        def on_enter(e):
            if not c._active:
                draw(hover=True)
                self._show_tooltip(c, label, color)
        def on_leave(e):
            if not c._active:
                draw()
            self._hide_tooltip()

        def on_click(e):
            self._toggle_category(cat_id)

        c.bind("<Enter>", on_enter)
        c.bind("<Leave>", on_leave)
        c.bind("<Button-1>", on_click)

    def _show_tooltip(self, widget, text: str, color: str):
        self._hide_tooltip()
        try:
            self._tooltip_win = _Tooltip(widget, text, color)
        except Exception:
            pass

    def _hide_tooltip(self):
        if self._tooltip_win:
            try:
                self._tooltip_win.destroy()
            except Exception:
                pass
            self._tooltip_win = None

    def _toggle_category(self, cat_id: str):
        if self._active_cat == cat_id and self._expanded:
            self._collapse()
        else:
            self._active_cat = cat_id
            self._show_category(cat_id)

    def _show_category(self, cat_id: str):
        # Update category button states
        for cid, c in self._cat_btns.items():
            active = cid == cat_id
            c._active = active
            cat = next((x for x in _NAV_CATEGORIES if x["id"] == cid), None)
            if cat:
                c._draw(active=active)

        # Rebuild expand panel content
        for w in self._expand_inner.winfo_children():
            w.destroy()

        cat = next((x for x in _NAV_CATEGORIES if x["id"] == cat_id), None)
        if not cat:
            return

        bg = T.lerp_color(T.SIDEBAR, T.ACCENT, 0.3)

        # Category header
        hdr = tk.Frame(self._expand_inner, bg=T.lerp_color(bg, cat["color"], 0.08))
        hdr.pack(fill="x")
        tk.Label(hdr, text=cat["label"], bg=T.lerp_color(bg, cat["color"], 0.08),
                 fg=cat["color"], font=(T.FONT_FAMILY, 8, "bold"),
                 padx=12, pady=8).pack(side="left")

        for key, icon, label, PageClass in cat["items"]:
            if PageClass is None:
                self._add_expand_item(key, icon, label, cat["color"], special=True)
            else:
                self._add_expand_item(key, icon, label, cat["color"])

        # Slide in
        if not self._expanded:
            self._expand(self.EXPAND_W)

    def _add_expand_item(self, key: str, icon: str, label: str,
                          color: str, special: bool = False):
        bg = T.lerp_color(T.SIDEBAR, T.ACCENT, 0.3)
        is_active = key == self._active_key

        row = tk.Frame(self._expand_inner, bg=bg, cursor="hand2")
        row.pack(fill="x")

        # Left accent bar
        bar = tk.Frame(row, bg=color if is_active else bg, width=3)
        bar.pack(side="left", fill="y")

        icon_lbl = tk.Label(row, text=icon, bg=bg,
                             fg=color if is_active else T.FG2,
                             font=(T.FONT_FAMILY, 12), padx=8, pady=10)
        icon_lbl.pack(side="left")

        text_lbl = tk.Label(row, text=label, bg=bg,
                             fg=T.FG if is_active else T.FG2,
                             font=T.FONT_SMALL if not special else T.FONT_SMALL,
                             anchor="w", pady=10)
        text_lbl.pack(side="left", fill="x", expand=True)

        if is_active:
            row.config(bg=T.lerp_color(bg, color, 0.12))
            icon_lbl.config(bg=T.lerp_color(bg, color, 0.12))
            text_lbl.config(bg=T.lerp_color(bg, color, 0.12))

        def on_enter(e):
            if key != self._active_key:
                hbg = T.lerp_color(bg, color, 0.08)
                row.config(bg=hbg)
                icon_lbl.config(bg=hbg, fg=T.lerp_color(T.FG2, color, 0.6))
                text_lbl.config(bg=hbg, fg=T.lerp_color(T.FG2, T.FG, 0.7))
                bar.config(bg=T.lerp_color(bg, color, 0.4))

        def on_leave(e):
            if key != self._active_key:
                row.config(bg=bg)
                icon_lbl.config(bg=bg, fg=T.FG2)
                text_lbl.config(bg=bg, fg=T.FG2)
                bar.config(bg=bg)

        def on_click(e):
            if special:
                if key in ("memory", "clean_tools"):
                    self._switch("tools")
                elif key == "toolbox":
                    self._switch("tools")
                else:
                    self._switch(key)
            else:
                self._switch(key)

        for w in (row, icon_lbl, text_lbl, bar):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    def _expand(self, target_w: int):
        self._expanded = True
        self._animate_width(self._expand_w, target_w)

    def _collapse(self):
        self._expanded = False
        self._active_cat = ""
        for cid, c in self._cat_btns.items():
            c._active = False
            cat = next((x for x in _NAV_CATEGORIES if x["id"] == cid), None)
            if cat:
                c._draw(active=False)
        self._animate_width(self._expand_w, 0)

    def _animate_width(self, start: int, end: int, step: int = 0, steps: int = 10):
        t = step / steps
        t_ease = 1 - (1 - t) ** 3  # ease-out cubic
        w = int(start + (end - start) * t_ease)
        self._expand_w = w
        self._expand_frame.config(width=w)
        if step < steps:
            self.after(12, lambda: self._animate_width(start, end, step + 1, steps))

    def set_active(self, key: str):
        self._active_key = key
        # Rebuild expand panel to update highlight state
        if self._expanded and self._active_cat:
            self._show_category(self._active_cat)

    def get_all_buttons(self) -> dict:
        return self._btns


def import_math_sin(x):
    import math
    return math.sin(x)


# ── Animated titlebar particles ────────────────────────────────────────────────

class _TitleParticles(tk.Canvas):
    """Subtle floating particle effect in the titlebar."""
    N = 18

    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.SIDEBAR)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        import random, math
        self._particles = [
            {
                "x": random.uniform(0, 1200),
                "y": random.uniform(0, 46),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.1, 0.1),
                "r": random.uniform(1, 3),
                "alpha": random.uniform(0.2, 0.7),
            }
            for _ in range(self.N)
        ]
        self._animate()

    def _animate(self):
        import random
        self.delete("all")
        w = max(self.winfo_width(), 1200)
        h = max(self.winfo_height(), 46)

        for p in self._particles:
            p["x"] = (p["x"] + p["vx"]) % w
            p["y"] = max(0, min(h, p["y"] + p["vy"]))
            if p["y"] <= 0 or p["y"] >= h:
                p["vy"] *= -1

            alpha = p["alpha"]
            color = T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, alpha * 0.5)
            r = p["r"]
            self.create_oval(p["x"]-r, p["y"]-r, p["x"]+r, p["y"]+r,
                             fill=color, outline="")

        self.after(40, self._animate)


# ── Live stats strip ───────────────────────────────────────────────────────────

class _LiveStatsStrip(tk.Frame):
    """Small CPU/RAM/Disk indicator in titlebar right side."""
    def __init__(self, parent, **kw):
        kw.setdefault("bg", T.SIDEBAR)
        super().__init__(parent, **kw)
        self._labels = {}
        for metric, icon, color in [
            ("cpu",  "CPU", T.HIGHLIGHT),
            ("ram",  "RAM", T.SUCCESS),
            ("disk", "DSK", T.WARNING),
        ]:
            f = tk.Frame(self, bg=T.SIDEBAR, padx=8)
            f.pack(side="left")
            tk.Label(f, text=icon, bg=T.SIDEBAR, fg=T.FG2,
                     font=T.FONT_MICRO).pack()
            lbl = tk.Label(f, text="–%", bg=T.SIDEBAR, fg=color,
                           font=(T.FONT_FAMILY, 8, "bold"))
            lbl.pack()
            self._labels[metric] = lbl

        self._update()

    def _update(self):
        def fetch():
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage("C:\\").percent
                self.after(0, lambda: self._set(cpu, ram, disk))
            except Exception:
                pass

        threading.Thread(target=fetch, daemon=True).start()
        self.after(2000, self._update)

    def _set(self, cpu: float, ram: float, disk: float):
        def color_for(pct):
            if pct > 85:
                return T.DANGER
            if pct > 60:
                return T.WARNING
            return T.SUCCESS

        self._labels["cpu"].config(text=f"{cpu:.0f}%", fg=color_for(cpu))
        self._labels["ram"].config(text=f"{ram:.0f}%", fg=color_for(ram))
        self._labels["disk"].config(text=f"{disk:.0f}%", fg=color_for(disk))


# ── App ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FreeSystemDoctor — Advanced Windows Optimizer")
        self.geometry("1280x780")
        self.minsize(960, 640)
        self.configure(bg=T.BG)
        self._pages: dict[str, tk.Frame] = {}
        self._active_page: str = ""
        self._fade_alpha = 1.0
        self._setup_styles()
        self._build_ui()
        self._switch_page("home")
        self._hud = SystemHud(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # Opt-in prompt for LibreHardwareMonitor (only first run, dismissible)
        maybe_show_first_run_dialog(self)

    # ── styles ─────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",
                        background=T.BG,
                        borderwidth=0,
                        tabmargins=[0, 0, 0, 0])
        style.configure("TNotebook.Tab",
                        background=T.ACCENT,
                        foreground=T.FG2,
                        font=T.FONT_SMALL,
                        padding=[12, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.25))],
                  foreground=[("selected", T.HIGHLIGHT)])
        style.configure("TProgressbar",
                        troughcolor=T.BORDER,
                        background=T.HIGHLIGHT,
                        borderwidth=0,
                        thickness=6)
        style.configure("TScrollbar",
                        troughcolor=T.PANEL,
                        background=T.ACCENT,
                        borderwidth=0,
                        arrowsize=10)
        style.map("TScrollbar",
                  background=[("active", T.lerp_color(T.ACCENT, T.HIGHLIGHT, 0.3))])
        apply_treeview_style()

    # ── layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Titlebar ───────────────────────────────────────────────────────────
        titlebar = tk.Frame(self, bg=T.SIDEBAR, height=48)
        titlebar.pack(fill="x", side="top")
        titlebar.pack_propagate(False)

        # Particle canvas behind everything
        particles = _TitleParticles(titlebar, bg=T.SIDEBAR)
        particles.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Logo section
        logo_frame = tk.Frame(titlebar, bg=T.SIDEBAR)
        logo_frame.place(x=0, y=0, relheight=1)

        logo_dot = tk.Canvas(logo_frame, width=32, height=32,
                             bg=T.SIDEBAR, highlightthickness=0)
        logo_dot.pack(side="left", padx=(16, 4), pady=8)
        logo_dot.create_oval(4, 4, 28, 28,
                             fill=T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, 0.2),
                             outline=T.HIGHLIGHT)
        logo_dot.create_text(16, 16, text="F", fill=T.HIGHLIGHT,
                             font=(T.FONT_FAMILY, 11, "bold"))

        tk.Label(logo_frame, text="FreeSystemDoctor",
                 bg=T.SIDEBAR, fg=T.FG,
                 font=(T.FONT_FAMILY, 13, "bold")).pack(side="left")
        tk.Label(logo_frame, text=" — Advanced Windows Optimizer",
                 bg=T.SIDEBAR, fg=T.FG2,
                 font=T.FONT_SMALL).pack(side="left")

        # Live stats on the right
        stats = _LiveStatsStrip(titlebar)
        stats.place(relx=1.0, rely=0, relheight=1, anchor="ne", x=-16)

        # Thin bottom border
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x", side="top")

        # ── Status bar ─────────────────────────────────────────────────────────
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x", side="bottom")

        # ── Body ───────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = _SidebarPanel(body, switch_cb=self._switch_page)
        self._sidebar.pack(side="left", fill="y")

        # Content area (fade container)
        self._content_wrapper = tk.Frame(body, bg=T.BG)
        self._content_wrapper.pack(side="left", fill="both", expand=True)

        # Translucent overlay for fade effect
        self._fade_overlay = tk.Canvas(self._content_wrapper, bg=T.BG,
                                       highlightthickness=0, bd=0)
        # (placed over content during transitions)

        self._content = tk.Frame(self._content_wrapper, bg=T.BG)
        self._content.pack(fill="both", expand=True)

        # Close expand panel on click in content area
        self._content_wrapper.bind("<Button-1>",
                                   lambda e: self._sidebar._collapse())
        self._content.bind("<Button-1>",
                           lambda e: self._sidebar._collapse())

        self._build_pages()

    def _build_pages(self):
        def make(PageClass):
            try:
                return PageClass(self._content, app_ref=self)
            except TypeError:
                return PageClass(self._content)

        built: set[str] = set()
        for cat in _NAV_CATEGORIES:
            for key, icon, label, PageClass in cat["items"]:
                if key in built or PageClass is None:
                    continue
                self._pages[key] = make(PageClass)
                built.add(key)

        # Tools page
        self._pages["tools"] = ToolsPage(self._content, app_ref=self,
                                          status_bar=self._status)
        self._pages["toolbox"] = self._pages["tools"]

        # Map alias keys
        for alias, target in [("memory", "tools"), ("clean_tools", "tools")]:
            if alias not in self._pages and target in self._pages:
                self._pages[alias] = self._pages[target]

    # ── navigation ─────────────────────────────────────────────────────────────

    def _switch_page(self, name: str):
        if name == self._active_page:
            return
        # Hide current
        if self._active_page and self._active_page in self._pages:
            self._pages[self._active_page].pack_forget()
        # Show new (with brief fade)
        if name in self._pages:
            page = self._pages[name]
            page.pack(fill="both", expand=True)
            self._active_page = name
            self._sidebar.set_active(name)
            if hasattr(page, "on_activate"):
                page.on_activate()
            self._status.set(f"Navigated to: {name.replace('_', ' ').title()}")

    # ── run ────────────────────────────────────────────────────────────────────

    def _on_close(self):
        try:
            self._hud.destroy()
        except Exception:
            pass
        self.destroy()

    @classmethod
    def run(cls):
        app = cls()
        app.mainloop()
