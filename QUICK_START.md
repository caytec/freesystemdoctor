# FreeSystemDoctor Quick Start Guide

## Installation
```bash
cd C:\Users\Kajetan\Documents\Projekty\FreeSystemDoctor
pip install requests  # For AI Agent and Software Updater
python main.py
```

## AI Agent Setup (Optional but Recommended)

Set one or more API keys in PowerShell before running the app:

### Option 1: Cerebras (Fastest - Recommended)
```powershell
$env:CEREBRAS_API_KEY="YOUR_CEREBRAS_API_KEY_HERE"
$env:CEREBRAS_MODEL="qwen-3-235b-a22b-instruct-2507"
```

### Option 2: Groq (Fast Alternative)
```powershell
$env:GROQ_API_KEY="YOUR_GROQ_API_KEY_HERE"
$env:GROQ_MODEL="llama-3.3-70b-versatile"
```

### Option 3: OpenRouter (Lightweight Fallback)
```powershell
$env:OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY_HERE"
$env:OPENROUTER_MODEL="meta-llama/llama-3.2-3b-instruct:free"
```

Then run:
```powershell
python main.py
```

## Core Features

### 🛡️ Care Tab
- System scan with 11+ optimization modules
- Health score and issue detection
- One-click "Fix All" for detected problems

### ⚡ Speed Up Tab
- RAM optimizer with real-time cleanup daemon
- Power plan manager
- Visual effects tuning
- Startup program manager

### 🔐 Protect Tab
- Windows Defender status and quick scan
- Firewall profile management
- Browser safe browsing controls
- Ad blocking via hosts file
- Privacy settings (telemetry, location, ad ID)

### ⬇️ Software Tab
- Scan for installed programs
- Detect outdated software
- Update via winget or browser
- Filter and sort updates

### 🤖 AI Agent Tab
- Click "Analyze Now"
- AI analyzes system with 3-API fallback chain
- Get health score + critical issues + top 5 recommendations
- Shows which API was used

### ⚙️ All Tools Tab
- 13 advanced tool tabs:
  - Disk Cleaner
  - Startup Manager
  - Duplicate Finder
  - Large Files
  - Registry Cleaner
  - Uninstaller
  - RAM & Performance
  - Network Tools
  - Privacy Cleaner
  - Services Manager
  - Task Scheduler
  - File Shredder
  - Advanced Settings

## Troubleshooting

### Software Updater Not Working
1. Check if winget is installed: `winget --version`
2. If not available, updater falls back to known versions database
3. Check logs: `%TEMP%\FreeSystemDoctor\software_updater.log`

### AI Agent Returns Error
1. Ensure `requests` library is installed: `pip install requests`
2. Check if you set API keys correctly in environment
3. Verify internet connection
4. Check logs: `%TEMP%\FreeSystemDoctor\ai_agent.log`
5. If one API fails, it automatically tries the next

### UI Freezes During Scan
- All operations run in background threads
- If UI still freezes, check for console errors
- Restart the app

### Administrator Access Needed
Some features require admin:
- Disabling telemetry
- Modifying firewall
- Changing power plans
- Visual effects
- Some registry operations

Right-click → Run as Administrator

## Log Locations
- Software Updater: `%TEMP%\FreeSystemDoctor\software_updater.log`
- AI Agent: `%TEMP%\FreeSystemDoctor\ai_agent.log`

Expand `%TEMP%` to: `C:\Users\<YourUsername>\AppData\Local\Temp\`

## Tips & Tricks

### For Best Results
1. Run as Administrator (some features require it)
2. Close web browsers before running browser privacy cleaner
3. Don't use AI Agent with slow internet (timeouts at 30s per API)
4. Check logs if something fails—gives exact error details

### Performance
- Full system scan: 2-5 minutes
- Software update check: 1-3 minutes  
- AI analysis: 10-40 seconds (depends on API)
- RAM cleanup: 5-30 seconds

### Privacy
- All operations are local (Windows only)
- AI Agent sends anonymized system metrics to LLM APIs
- No personal data collected or stored
- Check logs to see exactly what's sent

## Keyboard Shortcuts
None yet—all features accessible via buttons and menus

## Uninstall
Simply delete the folder:
```powershell
Remove-Item -Recurse -Force "C:\Users\Kajetan\Documents\Projekty\FreeSystemDoctor"
```

Logs are kept in temp and auto-cleanup by Windows.

## Support
Check the included `IMPROVEMENTS_SUMMARY.md` for detailed feature information.
