"""
Smoke harness — proves the app still loads:
  1. every engine module imports cleanly
  2. every page class (from _NAV_CATEGORIES + _TOOLS_TABS) instantiates against a
     hidden Tk root without raising.

Run standalone:   python tests/test_smoke.py
Run under pytest: pytest tests/test_smoke.py

Only imports/instantiates — never calls destructive engine ops.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import sys
import traceback

# repo root on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import tkinter as tk  # noqa: E402


# ── enumeration ───────────────────────────────────────────────────────────────
def _enumerate_engine_modules() -> list[str]:
    import engine
    names = []
    for m in pkgutil.iter_modules(engine.__path__):
        if m.name.startswith("_"):
            continue
        names.append(f"engine.{m.name}")
    return sorted(names)


def _enumerate_page_classes() -> list[tuple[str, type]]:
    from gui.app import _NAV_CATEGORIES, _TOOLS_TABS
    out: list[tuple[str, type]] = []
    seen: set[type] = set()
    for cat in _NAV_CATEGORIES:
        for key, _icon, _label, PageClass in cat["items"]:
            if PageClass is not None and PageClass not in seen:
                out.append((key, PageClass))
                seen.add(PageClass)
    for label, TabClass in _TOOLS_TABS:
        if TabClass not in seen:
            out.append((f"tab:{label}", TabClass))
            seen.add(TabClass)
    return out


# ── fakes ───────────────────────────────────────────────────────────────────
class _FakeStatus:
    def set(self, *_a, **_k):
        pass


class _FakeApp:
    def __init__(self):
        self._pages = {}
        self._status = _FakeStatus()

    def activate_key(self, _k):
        pass

    def _switch_page(self, _k):
        pass


def _make_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    return root


def _instantiate(parent, PageClass, fake_app):
    # ToolsPage needs status_bar=
    try:
        return PageClass(parent, app_ref=fake_app, status_bar=_FakeStatus())
    except TypeError:
        pass
    try:
        return PageClass(parent, app_ref=fake_app)
    except TypeError:
        pass
    try:
        return PageClass(parent, fake_app)
    except TypeError:
        return PageClass(parent)


def _report(title: str, failures: list[tuple[str, str]], total: int) -> None:
    print(f"\n=== {title} — {total - len(failures)}/{total} passed ===")
    for name, tb in failures:
        first = tb.strip().splitlines()[-1] if tb.strip() else "?"
        print(f"  [FAIL] {name}: {first}")


# ── tests ───────────────────────────────────────────────────────────────────
def test_engine_imports():
    failures: list[tuple[str, str]] = []
    modules = _enumerate_engine_modules()
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception:
            failures.append((name, traceback.format_exc(limit=4)))
    _report("ENGINE IMPORTS", failures, len(modules))
    assert not failures, f"{len(failures)} engine module(s) failed to import"


def test_page_instantiation():
    root = _make_root()
    fake = _FakeApp()
    container = tk.Frame(root)
    failures: list[tuple[str, str]] = []
    pages = _enumerate_page_classes()
    for key, PageClass in pages:
        try:
            w = _instantiate(container, PageClass, fake)
            try:
                root.update_idletasks()  # drain pending after(0,…)
            except tk.TclError:
                pass
            w.destroy()
        except Exception:
            failures.append((f"{key}:{PageClass.__name__}", traceback.format_exc(limit=5)))
    try:
        root.update()
    except tk.TclError:
        pass
    try:
        root.destroy()
    except tk.TclError:
        pass
    _report("PAGE INSTANTIATION", failures, len(pages))
    assert not failures, f"{len(failures)} page(s) failed to instantiate"


if __name__ == "__main__":
    rc = 0
    for fn in (test_engine_imports, test_page_instantiation):
        try:
            fn()
        except AssertionError as e:
            print(f"\n!! {e}")
            rc = 1
        except Exception:
            print("\n!! harness error:\n" + traceback.format_exc())
            rc = 1
    print("\nDONE" if rc == 0 else "\nFAILURES PRESENT")
    sys.exit(rc)
