## Approach
- Read existing files before writing. Don't re-read unless changed.
- Thorough in reasoning, concise in output.
- Skip files over 100KB unless required.
- No sycophantic openers or closing fluff.
- No emojis or em-dashes.
- Do not guess APIs, versions, flags, commit SHAs, or package names. Verify by reading code or docs before asserting.

## FreeSystemDoctor-Specific Rules (Token Optimization)

### Engine Module Patterns
- All engine modules follow: imports with try/except guard → `_MODULE_AVAILABLE` flag → public functions with guard check → return [] or False on unavailability
- Always catch (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) in process_iter loops
- Never raise exceptions from engine — always return safe defaults ([], False, 0)
- Use `if not _PSUTIL: return []` at start of functions, not repeated checks

### GUI Page Patterns
- Standard structure: `__init__` → `_build_ui()` → header bar (T.ACCENT, 48px) → body frame (T.BG, padx=16, pady=12) → cards
- Threading: spawn daemon thread for engine calls → use `self.after(0, callback)` for UI updates (never block main thread)
- Treeview: always call `apply_treeview_style()` after creation; use `iid=str(identifier)` for row IDs; sort before insert
- `on_activate()` method triggers data load only if empty (avoid redundant reload)
- Color tags: use T.SUCCESS (green), T.WARNING (amber), T.DANGER (red), T.FG2 (muted), T.FG (primary text)

### File Structure
- Engine: ~80-150 lines (simple functions, no classes)
- GUI pages: ~200-300 lines (layout + threading callbacks)
- Always: validate with `python -m py_compile` before commit

### Common Imports (Don't re-verify)
- `import threading`, `import tkinter as tk`, `from tkinter import messagebox, ttk`
- `from . import theme as T`, `from .widgets import Card, SectionLabel, ActionButton, ProgressBar, apply_treeview_style`
- `try: import psutil` with `_PSUTIL` guard pattern
- `import subprocess, winreg, os, json` (stdlib, always available)

### app.py Integration
- Imports go after line 27 (after `FileRecoveryPage` import)
- `_SIDEBAR_TOOLBOX` entries: (key, icon, label, PageClass) — auto-wired by existing loops
- No changes to `_SIDEBAR_PRIMARY`, `_build_pages()`, or `_build_sidebar()` — existing code handles new pages

### Testing Shortcut
- Skip manual testing of individual functions; compile check only: `python -m py_compile engine/module.py gui/page.py`
- Syntax errors caught by compiler; logic errors assume won't occur if pattern matches existing code
- No need to test in IDE unless user explicitly requests it
