"""Static audit: verify GUI pages/tabs call engine functions that ACTUALLY exist
with a plausible argument count.

Catches the biggest real-world bug class (missing engine functions, arity
mismatches, renamed APIs) without running any destructive system operation.

For every file in gui/, we:
  1. resolve `from engine import X as alias` / `from engine import X`
  2. find calls `alias.func(...)` / `X.func(...)`
  3. check that `func` exists on the engine module
  4. if it's a plain `def` (not *args/**kwargs), check the positional arg count
     against the number of required params.

Run:  python tests/audit_calls.py
"""

import ast
import importlib
import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

GUI_DIR = os.path.join(ROOT, "gui")


def _engine_aliases(tree):
    """Map local alias -> engine module name for `from engine import x [as y]`."""
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("engine"):
            for n in node.names:
                aliases[n.asname or n.name] = node.module + "." + n.name \
                    if node.module != "engine" else "engine." + n.name
    return aliases


def _load(modname):
    try:
        return importlib.import_module(modname)
    except Exception:
        return None


def _check_call(fn, n_pos, passed_kw):
    """Return an error string if the call is definitely wrong, else None.

    n_pos      : number of positional args passed
    passed_kw  : set of keyword-arg names passed
    A required param is satisfied if given positionally OR by keyword name.
    """
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return None
    params = [p for p in sig.parameters.values() if p.name != "self"]
    if any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params):
        # *args/**kwargs — can't reliably bound; only flag missing required kw
        pass
    pos_params = [p for p in params
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    has_varargs = any(p.kind == p.VAR_POSITIONAL for p in params)
    # too many positionals?
    if not has_varargs and n_pos > len(pos_params):
        return f"{n_pos} positional args — accepts <= {len(pos_params)}"
    # unsatisfied required params
    for i, p in enumerate(params):
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if p.default is not p.empty:
            continue
        given_pos = (p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                     and i < n_pos)
        given_kw = p.name in passed_kw
        if not (given_pos or given_kw):
            return f"required param '{p.name}' not provided"
    return None


def audit_file(path):
    findings = []
    src = open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"SYNTAX ERROR: {e}"]
    aliases = _engine_aliases(tree)
    if not aliases:
        return findings
    mods = {a: _load(m) for a, m in aliases.items()}

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        val = node.func.value
        if not isinstance(val, ast.Name):
            continue
        alias = val.id
        if alias not in mods:
            continue
        mod = mods[alias]
        if mod is None:
            continue
        fname = node.func.attr
        if fname.startswith("_"):
            continue   # private/internal — skip
        if not hasattr(mod, fname):
            findings.append(
                f"L{node.lineno}: {alias}.{fname}(...) — MISSING in {aliases[alias]}")
            continue
        fn = getattr(mod, fname)
        if not callable(fn):
            continue
        # positional args (skip if *unpacking used — can't count reliably)
        if any(isinstance(a, ast.Starred) for a in node.args):
            continue
        if any(kw.arg is None for kw in node.keywords):   # **kwargs unpack
            continue
        n_pos = len(node.args)
        passed_kw = {kw.arg for kw in node.keywords}
        err = _check_call(fn, n_pos, passed_kw)
        if err:
            findings.append(f"L{node.lineno}: {alias}.{fname}(...) — {err}")
    return findings


def main():
    total = 0
    files_with = 0
    for label, d in (("gui", GUI_DIR), ("engine", os.path.join(ROOT, "engine"))):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(d, fn)
            found = audit_file(path)
            if found:
                files_with += 1
                print(f"\n{label}/{fn}")
                for f in found:
                    print("   ", f)
                total += len(found)
    print("\n" + "=" * 60)
    print(f"AUDIT: {total} suspicious call(s) across {files_with} file(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
