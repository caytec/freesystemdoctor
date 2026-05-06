"""Main application window — sidebar navigation, Advanced SystemCare-style layout."""

import tkinter as tk
from tkinter import ttk

from . import theme as T
from .widgets import StatusBar, SidebarButton, apply_treeview_style

# New main pages
from .page_care            import CarePage
from .page_speedup         import SpeedUpPage
from .page_protect         import ProtectPage
from .page_software        import SoftwarePage
from .page_action_center   import ActionCenterPage
from .page_ai_agent        import AIAgentPage
from .page_disk_optimizer  import DiskOptimizerPage
from .page_internet_booster import InternetBoosterPage
from .page_turbo_mode      import TurboModePage
from .page_driver_updater  import DriverUpdaterPage
from .page_system_restore  import SystemRestorePage
from .page_empty_folder_finder import EmptyFolderFinderPage
from .page_benchmark       import BenchmarkPage
from .page_scheduled_cleaner import ScheduledCleanerPage
from .page_health_check import HealthCheckPage
from .page_disk_analyzer import DiskAnalyzerPage
from .page_cloud_cleaner import CloudCleanerPage
from .page_file_recovery import FileRecoveryPage
from .page_app_prioritizer import AppPrioritizerPage
from .page_app_freezer import AppFreezerPage
from .page_webcam_protection import WebcamProtectionPage
from .page_smart_notifications import SmartNotificationsPage
from .page_browser_plugins import BrowserPluginsPage
from .page_drive_wipe import DriveWipePage
from .page_browser_history import BrowserHistoryPage
from .page_bandwidth_monitor import BandwidthMonitorPage
from .page_registry_backup import RegistryBackupPage
from .page_speedup_wizard import SpeedupWizardPage
from .page_settings import SettingsPage
from .page_hardware_monitor import HardwareMonitorPage
from .page_network_security import NetworkSecurityPage
from .page_idle_maintenance import IdleMaintenancePage
from .page_performance_profiles import PerformanceProfilesPage
from .page_smart_defrag import SmartDefragPage
from .page_system_backup import SystemBackupPage
from .page_startup_insights import StartupInsightsPage
from .page_resource_monitor import ResourceMonitorPage
from .page_onedrive_cleaner import OneDriveCleanerPage
from .page_system_repair import SystemRepairPage
from .page_browser_profile_manager import BrowserProfileManagerPage
from .page_email_security import EmailSecurityPage
from .page_advanced_scheduler import AdvancedSchedulerPage
from .page_theme_manager import ThemeManagerPage
from .page_realtime_dashboard import RealtimeDashboardPage
from .page_cron_builder import CronBuilderPage

# Legacy tool tabs (wrapped as pages)
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


# Sidebar items: (key, icon, label, PageClass)
_SIDEBAR_PRIMARY = [
    ("health",   "❤",  "Health Check",    HealthCheckPage),
    ("dashboard","📊", "Real-time",       RealtimeDashboardPage),
    ("care",     "♥",  "Care",            CarePage),
    ("speedup",  "⚡",  "Speed Up",        SpeedUpPage),
    ("protect",  "⛔",  "Protect",         ProtectPage),
    ("software", "⬇",  "Software",        SoftwarePage),
    ("action",   "⚠",  "Action Center",   ActionCenterPage),
    ("ai",       "🤖",  "AI Agent",        AIAgentPage),
]

# Secondary toolbox items
_SIDEBAR_TOOLBOX = [
    ("disk_analyzer", "📊", "Disk Analyzer",     DiskAnalyzerPage),
    ("disk_opt",      "💿", "Disk Optimizer",    DiskOptimizerPage),
    ("internet",      "🌐", "Internet Booster",  InternetBoosterPage),
    ("turbo",         "🔥", "Turbo Mode",        TurboModePage),
    ("drivers",       "🔧", "Driver Updater",    DriverUpdaterPage),
    ("restore",       "⏮",  "System Restore",    SystemRestorePage),
    ("empty",         "📁", "Empty Folders",     EmptyFolderFinderPage),
    ("cloud",         "☁",  "Cloud Cleaner",     CloudCleanerPage),
    ("onedrive",      "☁",  "OneDrive Cleaner",  OneDriveCleanerPage),
    ("recovery",      "🔍", "File Recovery",     FileRecoveryPage),
    ("app_prio",      "⚡", "App Priority",      AppPrioritizerPage),
    ("app_freeze",    "❄",  "App Freezer",       AppFreezerPage),
    ("webcam",        "📷", "Webcam Guard",      WebcamProtectionPage),
    ("notifications", "🔔", "Smart Alerts",      SmartNotificationsPage),
    ("plugins",       "🧩", "Browser Plugins",   BrowserPluginsPage),
    ("browser_mgr",   "🌐", "Browser Manager",   BrowserProfileManagerPage),
    ("drive_wipe",    "🗑",  "Drive Wipe",        DriveWipePage),
    ("browser_hist",  "🌐", "Browser History",   BrowserHistoryPage),
    ("bandwidth",     "📶", "Bandwidth",          BandwidthMonitorPage),
    ("reg_backup",    "💾", "Reg Backup",         RegistryBackupPage),
    ("wizard",        "⭐", "Speedup Wizard",     SpeedupWizardPage),
    ("bench",         "📈", "Benchmark",         BenchmarkPage),
    ("auto",          "⚙",  "Scheduled Clean",   ScheduledCleanerPage),
    ("adv_sched",     "📅", "Advanced Scheduler", AdvancedSchedulerPage),
    ("cron",          "⏰", "Cron Builder",      CronBuilderPage),
    ("hardware",      "🌡",  "Hardware Monitor",  HardwareMonitorPage),
    ("network",       "🔒", "Network Security",  NetworkSecurityPage),
    ("email",         "📧", "Email Security",    EmailSecurityPage),
    ("idle",          "💤", "Idle Maintenance",  IdleMaintenancePage),
    ("profiles",      "⚡", "Performance",       PerformanceProfilesPage),
    ("defrag",        "💾", "Smart Defrag",      SmartDefragPage),
    ("backup",        "📦", "System Backup",     SystemBackupPage),
    ("startup",       "🚀", "Startup Insights",  StartupInsightsPage),
    ("monitor",       "📊", "Resource Monitor",  ResourceMonitorPage),
    ("repair",        "🔧", "System Repair",     SystemRepairPage),
    ("themes",        "🎨", "Theme Manager",     ThemeManagerPage),
    ("settings",      "⚙",  "Settings",          SettingsPage),
]

# Tools submenu — shown in a sub-notebook inside a "Tools" page
_TOOLS_TABS = [
    ("Disk Cleaner",     CleanerTab),
    ("Startup",          StartupTab),
    ("Duplicates",       DuplicatesTab),
    ("Large Files",      LargeFilesTab),
    ("Registry",         RegistryTab),
    ("Uninstaller",      UninstallerTab),
    ("RAM & Performance",MemoryTab),
    ("Network",          NetworkTab),
    ("Privacy",          PrivacyTab),
    ("Services",         ServicesTab),
    ("Sched. Tasks",     TasksTab),
    ("File Shredder",    ShredderTab),
    ("Advanced",         AdvancedTab),
]


class ToolsPage(tk.Frame):
    """Wrapper that hosts all legacy tabs in an inner notebook."""
    def __init__(self, parent, app_ref, status_bar):
        super().__init__(parent, bg=T.BG)
        self._app = app_ref

        hdr = tk.Frame(self, bg=T.ACCENT, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="All Tools", bg=T.ACCENT, fg=T.FG,
                 font=T.FONT_TITLE).pack(side="left", padx=16)
        tk.Label(hdr, text="Full toolkit — advanced system maintenance",
                 bg=T.ACCENT, fg=T.FG2, font=T.FONT_SMALL).pack(side="left", padx=4)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        for label, TabClass in _TOOLS_TABS:
            frame = TabClass(nb, status_bar)
            nb.add(frame, text=f"  {label}  ")

    def on_activate(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FreeSystemDoctor — Advanced Windows Optimizer")
        self.geometry("1200x740")
        self.minsize(900, 600)
        self.configure(bg=T.BG)
        self._pages: dict[str, tk.Frame] = {}
        self._active_page: str = ""
        self._sidebar_btns: dict[str, SidebarButton] = {}
        self._setup_styles()
        self._build_ui()
        self._switch_page("care")

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
                  background=[("selected", T.HIGHLIGHT)],
                  foreground=[("selected", "#ffffff")])
        style.configure("TProgressbar",
                        troughcolor=T.BORDER,
                        background=T.HIGHLIGHT,
                        borderwidth=0,
                        thickness=6)
        style.configure("TScrollbar",
                        troughcolor=T.PANEL,
                        background=T.ACCENT,
                        borderwidth=0,
                        arrowsize=12)
        style.map("TScrollbar",
                  background=[("active", T.HIGHLIGHT)])
        apply_treeview_style()

    # ── layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        titlebar = tk.Frame(self, bg=T.SIDEBAR, height=46)
        titlebar.pack(fill="x", side="top")
        titlebar.pack_propagate(False)

        # Left: logo dot + title
        left_tb = tk.Frame(titlebar, bg=T.SIDEBAR)
        left_tb.pack(side="left", padx=14, fill="y")
        tk.Label(left_tb, text="●", bg=T.SIDEBAR, fg=T.HIGHLIGHT,
                 font=(T.FONT_FAMILY, 10)).pack(side="left", padx=(0, 6))
        tk.Label(left_tb, text="FreeSystemDoctor",
                 bg=T.SIDEBAR, fg=T.FG, font=(T.FONT_FAMILY, 12, "bold")
                 ).pack(side="left")
        tk.Label(left_tb, text="  Advanced Windows Optimizer",
                 bg=T.SIDEBAR, fg=T.FG2, font=T.FONT_SMALL
                 ).pack(side="left")

        # Thin bottom border on titlebar
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x", side="top")

        # Status bar
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")
        # Thin top border on statusbar
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x", side="bottom")

        # Body: sidebar + content
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)

        self._content = tk.Frame(body, bg=T.BG)
        self._content.pack(side="left", fill="both", expand=True)

        self._build_pages()

    def _build_sidebar(self, body):
        # Sidebar container: fixed width, holds all nav elements
        sidebar = tk.Frame(body, bg=T.SIDEBAR, width=128)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Right border
        tk.Frame(body, bg=T.BORDER, width=1).pack(side="left", fill="y")

        # Logo
        logo_frame = tk.Frame(sidebar, bg=T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, 0.15), height=58)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        tk.Label(logo_frame, text="FSD", fg=T.HIGHLIGHT,
                 bg=T.lerp_color(T.SIDEBAR, T.HIGHLIGHT, 0.15),
                 font=(T.FONT_FAMILY, 15, "bold")).pack(expand=True)

        # Primary nav buttons (always visible, not scrollable)
        for key, icon, label, _ in _SIDEBAR_PRIMARY:
            btn = SidebarButton(sidebar, icon, label,
                                command=lambda k=key: self._switch_page(k))
            btn.pack(fill="x")
            self._sidebar_btns[key] = btn

        # Separator
        tk.Frame(sidebar, bg=T.BORDER, height=1).pack(fill="x", padx=10, pady=4)

        # Version pinned at bottom — must be packed before the scrollable area
        tk.Label(sidebar, text="v2.1", bg=T.SIDEBAR,
                 fg=T.lerp_color(T.FG2, T.SIDEBAR, 0.4),
                 font=T.FONT_SMALL).pack(side="bottom", pady=4)

        # Scrollable area: use grid so canvas + scrollbar share the space cleanly
        scroll_container = tk.Frame(sidebar, bg=T.SIDEBAR)
        scroll_container.pack(fill="both", expand=True)
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(1, weight=0)

        canvas = tk.Canvas(scroll_container, bg=T.SIDEBAR,
                           highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical",
                                  command=canvas.yview)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        inner_frame = tk.Frame(canvas, bg=T.SIDEBAR)
        win_id = canvas.create_window(0, 0, window=inner_frame, anchor="nw")

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            # Make inner_frame fill canvas width minus scrollbar
            canvas.itemconfig(win_id, width=event.width)

        inner_frame.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_scroll_recursive(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_scroll_recursive(child)

        canvas.bind("<MouseWheel>", _on_mousewheel)
        inner_frame.bind("<MouseWheel>", _on_mousewheel)

        # Toolbox buttons
        for key, icon, label, _ in _SIDEBAR_TOOLBOX:
            btn = SidebarButton(inner_frame, icon, label,
                                command=lambda k=key: self._switch_page(k))
            btn.pack(fill="x")
            _bind_scroll_recursive(btn)
            self._sidebar_btns[key] = btn

        # All Tools button
        btn = SidebarButton(inner_frame, "🔧", "All Tools",
                            command=lambda: self._switch_page("tools"))
        btn.pack(fill="x")
        _bind_scroll_recursive(btn)
        self._sidebar_btns["tools"] = btn

    def _build_pages(self):
        # Primary pages
        for key, icon, label, PageClass in _SIDEBAR_PRIMARY:
            frame = PageClass(self._content, app_ref=self)
            self._pages[key] = frame

        # Toolbox pages
        for key, icon, label, PageClass in _SIDEBAR_TOOLBOX:
            frame = PageClass(self._content, app_ref=self)
            self._pages[key] = frame

        # Tools page
        tools_page = ToolsPage(self._content, app_ref=self, status_bar=self._status)
        self._pages["tools"] = tools_page

    # ── navigation ────────────────────────────────────────────────────────────

    def _switch_page(self, name: str):
        if name == self._active_page:
            return
        # Hide current
        if self._active_page and self._active_page in self._pages:
            self._pages[self._active_page].pack_forget()
        # Show new
        if name in self._pages:
            self._pages[name].pack(fill="both", expand=True)
            # Update sidebar active state
            for key, btn in self._sidebar_btns.items():
                btn.set_active(key == name)
            self._active_page = name
            # Call on_activate if the page supports it
            page = self._pages[name]
            if hasattr(page, "on_activate"):
                page.on_activate()

    # ── run ───────────────────────────────────────────────────────────────────

    @classmethod
    def run(cls):
        app = cls()
        app.mainloop()
