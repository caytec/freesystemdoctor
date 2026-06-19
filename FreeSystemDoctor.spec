# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hidden = [
    # core deps
    'psutil', 'psutil._pswindows',
    'winreg', 'ctypes', 'ctypes.wintypes',
    # hardware monitoring (optional)
    'wmi', 'win32com', 'win32com.client', 'pythoncom', 'pywintypes',
    # google APIs (optional — imported lazily)
    'google.auth', 'google.auth.transport', 'google.oauth2',
    'google.oauth2.credentials', 'google.auth.transport.requests',
    'googleapiclient', 'googleapiclient.discovery',
    # requests (used by ai_agent + cloud cleaners)
    'requests', 'requests.adapters', 'urllib3',
    # anthropic SDK (optional)
    'anthropic',
    # stdlib modules that PyInstaller sometimes misses
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
    'tkinter.colorchooser', 'tkinter.filedialog',
    'json', 'threading', 'subprocess', 'pathlib',
    'collections', 'datetime', 'struct', 'uuid',
    'platform', 're', 'shutil', 'logging',
    # engine submodules
    'engine.ai_agent', 'engine.system_info', 'engine.disk_cleaner',
    'engine.registry_cleaner', 'engine.startup_manager',
    'engine.memory_optimizer', 'engine.privacy_cleaner',
    'engine.protection', 'engine.network_optimizer',
    'engine.software_updater', 'engine.disk_optimizer',
    'engine.internet_booster', 'engine.turbo_mode',
    'engine.driver_updater', 'engine.system_restore',
    'engine.empty_folder_finder', 'engine.benchmark',
    'engine.scheduled_cleaner', 'engine.health_check',
    'engine.disk_analyzer', 'engine.cloud_drive_cleaner',
    'engine.file_recovery', 'engine.app_prioritizer',
    'engine.app_freezer', 'engine.webcam_protection',
    'engine.smart_notifications', 'engine.browser_plugin_manager',
    'engine.drive_wipe', 'engine.browser_history',
    'engine.bandwidth_monitor', 'engine.registry_backup',
    'engine.hardware_monitor', 'engine.idle_maintenance',
    'engine.network_security', 'engine.performance_profiles',
    'engine.smart_defrag', 'engine.system_backup',
    'engine.startup_insights', 'engine.resource_monitor',
    'engine.windows_update_manager',
    'engine.onedrive_cleaner', 'engine.startup_link_analyzer',
    'engine.system_repair', 'engine.browser_profile_manager',
    'engine.network_diagnostics', 'engine.email_security',
    'engine.batch_uninstaller', 'engine.advanced_scheduler',
    'engine.theme_manager', 'engine.report_exporter',
    'engine.realtime_monitor', 'engine.cron_builder',
    'engine.game_booster', 'engine.cpu_optimizer', 'engine.space_hogs',
    'engine.dns_protector', 'engine.service_optimizer',
    'engine.auto_shutdown', 'engine.icon_saver',
    'engine.browser_autoclean', 'engine.turbo_clean',
    'engine._perf',
    # Monetization (Option D)
    'engine.affiliate', 'engine.ad_network',
    'engine.sponsored_notifications', 'engine.email_capture',
    'engine.dependency_installer',
    # Publisher subsystem
    'publisher', 'publisher.config', 'publisher.directory',
    'publisher.release_builder', 'publisher.orchestrator',
    'publisher.manual_submitter', 'publisher.cli',
    'publisher.api_publishers',
    'publisher.api_publishers.github', 'publisher.api_publishers.winget',
    'publisher.api_publishers.chocolatey', 'publisher.api_publishers.scoop',
    'publisher.api_publishers.sourceforge',
    'gui.page_publisher',
    # GUI pages
    'gui.page_home',
    'gui.page_dns_protector', 'gui.page_service_optimizer',
    'gui.page_auto_shutdown', 'gui.page_icon_saver',
    'gui.page_browser_autoclean',
    'gui.page_cpu_optimizer',
    'gui.page_space_hogs',
    # Monetization GUI surfaces
    'gui.affiliate_banner', 'gui.native_ad_widgets',
    'gui.pro_upsell_smart', 'gui.first_run_dialog',
    'gui.system_hud',
    # New features: command palette, auto-pilot, health timeline, ask-your-PC
    'gui.nav_registry', 'gui.command_palette', 'gui._pro_gate',
    'gui.page_autopilot', 'gui.page_health_timeline', 'gui.page_ai_ask',
    'engine.health_timeline', 'engine.ai_ask',
    'engine.license_manager', 'engine.stripe_checkout',
    'engine.app_settings',
    'gui.page_performance_guardian', 'engine.performance_guardian',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'PIL',
              'PyQt5', 'wx', 'gi'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FreeSystemDoctor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui/icon.ico' if os.path.exists('gui/icon.ico') else None,
    uac_admin=True,
    uac_uiaccess=False,
)
