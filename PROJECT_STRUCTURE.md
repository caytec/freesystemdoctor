# FreeSystemDoctor — Project Structure

## Overview
**Total Files**: 44 Python modules  
**Architecture**: Modular GUI + Engine design with sidebar navigation  
**Dependencies**: tkinter (built-in), requests, winget (Windows 10+)

## Directory Structure

```
FreeSystemDoctor/
│
├── main.py                          # Entry point
│
├── gui/
│   ├── __init__.py
│   ├── app.py                       # Main app container (sidebar + pages)
│   ├── theme.py                     # Colors, fonts, utilities
│   ├── widgets.py                   # Custom widgets (buttons, toggles, etc.)
│   │
│   ├── page_care.py                 # CARE — Main scan hub
│   ├── page_speedup.py              # SPEED UP — RAM, power plans, startup
│   ├── page_protect.py              # PROTECT — Defender, firewall, browser
│   ├── page_software.py             # SOFTWARE — Update checker
│   ├── page_action_center.py        # ACTION CENTER — Quick actions
│   ├── page_ai_agent.py             # AI AGENT — LLM analysis (NEW)
│   │
│   ├── tab_cleaner.py               # TOOLS: Disk cleaner
│   ├── tab_startup.py               # TOOLS: Startup manager
│   ├── tab_duplicates.py            # TOOLS: Duplicate finder
│   ├── tab_large_files.py           # TOOLS: Large files finder
│   ├── tab_registry.py              # TOOLS: Registry cleaner
│   ├── tab_uninstaller.py           # TOOLS: Uninstaller
│   ├── tab_memory.py                # TOOLS: RAM & performance
│   ├── tab_network.py               # TOOLS: Network diagnostics
│   ├── tab_privacy.py               # TOOLS: Privacy cleaner
│   ├── tab_services.py              # TOOLS: Service manager
│   ├── tab_tasks.py                 # TOOLS: Task scheduler
│   ├── tab_shredder.py              # TOOLS: File shredder
│   └── tab_advanced.py              # TOOLS: Advanced settings
│
├── engine/
│   ├── __init__.py
│   │
│   ├── system_info.py               # System metrics (CPU, RAM, disk)
│   ├── memory_optimizer.py          # RAM optimization & power plans
│   ├── privacy_cleaner.py           # Privacy settings & telemetry
│   ├── protection.py                # Windows Defender & Firewall
│   ├── browser_protection.py        # Browser security & ad blocking
│   ├── software_updater.py          # Software detection & updates (ENHANCED)
│   ├── ai_agent.py                  # AI analysis with LLM chain (NEW)
│   ├── ram_daemon.py                # Background RAM optimizer
│   │
│   ├── disk_cleaner.py              # Junk file removal
│   ├── registry_cleaner.py          # Registry optimization
│   ├── duplicate_finder.py          # Duplicate file detection
│   ├── large_files.py               # Large files finder
│   ├── uninstaller.py               # Software uninstaller
│   ├── startup_manager.py           # Startup programs control
│   ├── network_tools.py             # Network utilities
│   ├── services_manager.py          # Windows services control
│   ├── task_scheduler.py            # Task scheduler editor
│   ├── file_shredder.py             # Secure file deletion
│   └── advanced_settings.py         # Advanced system tweaks
│
├── docs/
│   ├── IMPROVEMENTS_SUMMARY.md      # Detailed improvements guide
│   ├── QUICK_START.md               # Getting started guide
│   ├── RELEASE_NOTES_v2.1.md        # v2.1 release information
│   └── PROJECT_STRUCTURE.md         # This file
```

## Key Components

### GUI Framework (gui/)
- **app.py**: Main application window with sidebar navigation
  - 5 primary pages (Care, Speed Up, Protect, Software, Action Center)
  - 1 AI Agent page (new)
  - 13 tool pages in nested notebook
  - Status bar and progress tracking

- **theme.py**: Design system
  - Dark navy/coral color scheme
  - Font definitions
  - Color interpolation utilities
  - Theme constants

- **widgets.py**: Reusable components
  - SidebarButton (with hover effects)
  - CircleScanButton (animated circular button)
  - ToggleSwitch (canvas-based toggle)
  - StatusBadge (colored status pill)
  - RAMGauge (arc gauge with colors)
  - ProgressBar
  - StatusBar

### Primary Pages (New Architecture)

**page_care.py**
- CircleScanButton (animated 200x200px scan button)
- 11 scan module checkboxes
- Results treeview with category/issue/status
- FIX ALL button

**page_speedup.py**
- RAMGauge showing % usage
- ToggleSwitch for auto-clean daemon
- Power Plan radio buttons (3 options)
- Visual Effects mode selector
- Startup entries manager

**page_protect.py**
- Windows Defender status + real-time toggle
- Firewall 3-profile management
- Browser detection with safe browsing toggle
- Ad blocking toggle with domain count
- Privacy badges (telemetry, location, ad-ID)

**page_software.py**
- Software list with Installed/Latest/Status columns
- Filter and "Outdated only" checkbox
- Check for Updates (background scan)
- Update All or individual updates
- winget + known DB fallback

**page_action_center.py**
- Health score ring gauge
- Quick action grid (6 buttons)
- Disk usage treeview

**page_ai_agent.py** (NEW)
- Analysis Status card with API indicator
- Health Score display
- Critical Issues list
- Recommendations (numbered 1-5)
- Full analysis text (scrollable)
- Shows which API was used

### Engine Modules (engine/)

**Core Services**
- system_info.py: CPU%, RAM%, disk usage, health score
- memory_optimizer.py: RAM trimming, power plans, visual effects
- privacy_cleaner.py: Telemetry, location, ad-ID controls
- protection.py: Defender status, firewall management
- browser_protection.py: Safe browsing, ad blocking via hosts file

**New Modules**
- software_updater.py: Registry scan + winget integration (ENHANCED)
- ai_agent.py: LLM API chain (Cerebras→Groq→OpenRouter) (NEW)
- ram_daemon.py: Background memory optimization thread

**Tool Modules**
- disk_cleaner.py: Temporary files, cache cleanup
- registry_cleaner.py: Invalid shortcuts, old entries
- duplicate_finder.py: MD5-based duplicate detection
- large_files.py: Finds files >100MB
- uninstaller.py: Uninstall via registry + WMI
- startup_manager.py: HKLM/HKCU startup entries
- network_tools.py: DNS flush, IP config
- services_manager.py: Windows services on/off
- task_scheduler.py: Scheduled tasks editor
- file_shredder.py: DoD 5220.22-M overwrite
- advanced_settings.py: Registry tweaks

## Data Flow

### Software Update Check
```
User clicks "Check for Updates"
  ↓
spawn background thread (daemon=True)
  ↓
get_installed_software() — scan HKLM+HKCU registry
  ↓
check_winget() — verify winget available
  ↓
get_winget_upgrades() — run "winget upgrade --include-unknown"
  ↓
match against known_apps database (40+ apps)
  ↓
return list of SoftwareEntry objects
  ↓
UI shows results with filter/sort
  ↓
User clicks "Update Selected" → launch_update() → winget upgrade --silent
```

### AI Agent Analysis
```
User clicks "Analyze Now"
  ↓
spawn background thread (daemon=True)
  ↓
collect_system_data() — gather health metrics
  ↓
Try Cerebras API with 30s timeout
  ↓ (if fails)
Try Groq API with 30s timeout
  ↓ (if fails)
Try OpenRouter API with 30s timeout
  ↓ (if all fail)
Show error with config help
  ↓
Parse response → extract issues + recommendations
  ↓
UI displays with "via [API Name]" badge
```

## Threading Model

All background operations use daemon threads:
- Software scan: `threading.Thread(target=_do_check, daemon=True)`
- AI analysis: `threading.Thread(target=_do_analysis, daemon=True)`
- RAM daemon: Singleton thread with threading.Event.wait(timeout)

Thread-safe UI updates via `self.after(0, callback, args)`

## Error Handling Strategy

1. **Per-Operation Try-Catch**: Each function wrapped in try-catch
2. **Graceful Fallbacks**: If API fails, try next in chain
3. **Error Isolation**: One bad entry doesn't crash scan
4. **Logging**: All errors logged to `%TEMP%\FreeSystemDoctor\*.log`
5. **UI Protection**: TclError catching for destroyed widgets
6. **Progress Safety**: Callbacks protected against widget destruction

## Configuration

### Environment Variables (Optional)
```
CEREBRAS_API_KEY, CEREBRAS_MODEL
GROQ_API_KEY, GROQ_MODEL
OPENROUTER_API_KEY, OPENROUTER_MODEL
```

### Registry Paths Used
```
HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall
HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall
HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall
(and 30+ other paths for settings, policies, etc.)
```

## Dependencies

### Built-in
- tkinter (GUI)
- threading (background tasks)
- subprocess (system commands)
- winreg (registry access)
- json, re, os, pathlib, etc.

### External (Install)
- requests (HTTP for LLM APIs)

### System Requirements
- Python 3.10+
- Windows 10/11
- Administrator privileges (some features)
- Internet (for AI Agent)
- winget (optional, for software updates)

## Performance Profile

- Full system scan: 2-5 minutes
- Software update check: 1-3 minutes
- AI analysis: 10-40 seconds (API dependent)
- Memory: ~200-400 MB during normal operation
- CPU: Minimal except during scans

## Future Expansion Points

1. **More LLM Providers**: Add Claude, Cohere, HuggingFace
2. **Custom Modules**: Template system for user extensions
3. **Analysis History**: Database of past reports
4. **Scheduled Tasks**: Auto-run scans on timer
5. **Remote Support**: HTTP API for external control
6. **Mobile App**: Companion app for monitoring

## Version History

- **v2.1** (May 2, 2026): AI Agent + Enhanced Software Updater
- **v2.0** (Previous): Sidebar redesign, new UI framework
- **v1.x**: Original tab-based interface
