"""
Searchable navigation registry — a thin, tk-free accessor over `_NAV_CATEGORIES`.

Used by the Command Palette (Ctrl+K) and the AI "Ask your PC" tool-mapping so they
can search/launch any page without duplicating the menu definition.

IMPORTANT: never import `gui.app` at module top — that would create a circular import
(app.py imports every page). `get_registry()` imports it lazily at call time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavEntry:
    key: str             # passed to App.activate_key / _switch_page
    icon: str            # emoji
    label: str           # human label e.g. "Health Check"
    category_id: str     # e.g. "dashboard"
    category_label: str  # e.g. "PULPIT"
    color: str           # category accent color
    has_page: bool       # True if a real PageClass is wired (None ⇒ alias/placeholder)


def build_registry(nav_categories) -> list[NavEntry]:
    """Flatten _NAV_CATEGORIES into a searchable list. Pure — no tkinter."""
    out: list[NavEntry] = []
    for cat in nav_categories:
        for key, icon, label, PageClass in cat["items"]:
            out.append(NavEntry(
                key=key,
                icon=icon,
                label=label,
                category_id=cat["id"],
                category_label=cat["label"],
                color=cat["color"],
                has_page=PageClass is not None,
            ))
    return out


def get_registry() -> list[NavEntry]:
    """Live registry pulled from gui.app (lazy import to avoid circular dependency)."""
    from .app import _NAV_CATEGORIES
    return build_registry(_NAV_CATEGORIES)


def _is_subsequence(query: str, text: str) -> tuple[bool, int]:
    """Return (matched, gaps) where matched=True if every query char appears in
    order within text; gaps = number of non-contiguous jumps (lower is better)."""
    qi = 0
    gaps = 0
    last_hit = -2
    for i, ch in enumerate(text):
        if qi < len(query) and ch == query[qi]:
            if i != last_hit + 1 and qi > 0:
                gaps += 1
            last_hit = i
            qi += 1
    return (qi == len(query), gaps)


def fuzzy_score(query: str, entry: NavEntry) -> int | None:
    """Score an entry against a query.

    Returns an int score (higher = better) or None if it doesn't match.
    Empty query ⇒ score 0 for everything (show all, original order).
    """
    q = (query or "").strip().lower()
    if not q:
        return 0

    label = entry.label.lower()
    hay = f"{label} {entry.category_label.lower()}"

    matched, gaps = _is_subsequence(q, hay)
    if not matched:
        return None

    score = 50
    if label.startswith(q):
        score += 60
    elif q in label:
        score += 35
    # reward whole-word boundary starts
    if any(word.startswith(q) for word in label.split()):
        score += 20
    # shorter labels rank a touch higher for the same match
    score -= max(0, len(label) - len(q)) // 4
    # penalize fragmentation
    score -= gaps * 3
    # category-only matches rank below label matches
    if q not in hay.split(" ", 1)[0] and q not in label:
        score -= 15
    return score


def search(query: str, registry: list[NavEntry] | None = None,
           include_aliases: bool = False) -> list[NavEntry]:
    """Return entries matching `query`, best first. Skips placeholder/alias rows
    (has_page False) unless include_aliases=True."""
    reg = registry if registry is not None else get_registry()
    scored: list[tuple[int, int, NavEntry]] = []
    for idx, e in enumerate(reg):
        if not include_aliases and not e.has_page:
            continue
        s = fuzzy_score(query, e)
        if s is not None:
            scored.append((s, idx, e))
    # sort by score desc, then original order for stability
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [e for _, _, e in scored]
