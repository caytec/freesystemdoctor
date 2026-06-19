"""
Ask-your-PC — natural-language helper.

Takes a user question, adds compact system context, asks the LLM (via ai_agent.ask,
Ollama-first ⇒ offline), and returns a plain-language answer plus an optional
suggested tool key the GUI can turn into an "Open <tool>" button.

Engine-only: does NOT import gui. The tool catalog here mirrors nav keys; the GUI
validates the suggested key against the live registry before showing the button.
"""

from __future__ import annotations

import re

from . import ai_agent

# Curated catalog: nav key → short purpose (kept in sync with gui _NAV_CATEGORIES keys)
TOOL_CATALOG: dict[str, str] = {
    "autopilot":    "one-click clean + optimize + re-score",
    "health":       "full system health scan (4 scores)",
    "timeline":     "health score trend over time",
    "care":         "general system care & cleanup",
    "speedup":      "speed up a slow PC",
    "turbo":        "turbo/gaming performance mode",
    "cpu_max":      "force maximum CPU performance",
    "profiles":     "performance profiles (work/gaming/battery)",
    "deep_clean":   "aggressive deep disk cleanup",
    "disk_analyzer":"see what's using disk space",
    "space_hogs":   "find the largest files & folders",
    "empty":        "find & remove empty folders",
    "recovery":     "recover deleted files",
    "defrag":       "defragment / TRIM drives",
    "disk_opt":     "optimize disk health",
    "internet":     "boost internet / TCP tuning",
    "dns_lock":     "lock & protect DNS settings",
    "network":      "network security & firewall",
    "protect":      "antivirus / Defender & privacy protection",
    "webcam":       "block unauthorized webcam access",
    "game":         "game booster (anti-cheat safe)",
    "startup":      "analyze & trim startup programs",
    "svc_opt":      "optimize Windows services",
    "drivers":      "check & update drivers",
    "backup":       "create a system restore point / backup",
    "restore":      "restore the system to an earlier point",
    "repair":       "detect & fix common Windows issues",
    "bench":        "benchmark CPU / RAM / disk",
    "software":     "update installed software",
    "ai":           "AI-powered full system analysis",
}

# Keyword → nav key fallback (used if the model omits a TOOL: line)
INTENT_TOOL_MAP: list[tuple[tuple[str, ...], str]] = [
    (("slow", "lag", "speed up", "faster", "sluggish"), "speedup"),
    (("clean", "junk", "temp", "cache", "space free"),  "autopilot"),
    (("disk full", "storage", "space", "what's using"), "disk_analyzer"),
    (("largest", "big files", "biggest"),               "space_hogs"),
    (("ram", "memory"),                                  "turbo"),
    (("virus", "malware", "defender", "antivirus"),     "protect"),
    (("privacy", "telemetry", "tracking"),              "protect"),
    (("game", "fps", "gaming"),                          "game"),
    (("startup", "boot", "starts with windows"),        "startup"),
    (("driver",),                                        "drivers"),
    (("wifi", "internet", "network", "dns", "ping"),    "internet"),
    (("backup", "restore point"),                       "backup"),
    (("benchmark", "score", "how fast"),                "bench"),
    (("health", "overall"),                              "health"),
    (("recover", "deleted", "undelete"),                "recovery"),
]


def _context() -> dict:
    try:
        data = ai_agent.collect_system_data()
    except Exception:
        data = {}
    cpu = data.get("cpu_percent") or data.get("cpu") or "?"
    ram = data.get("ram_percent") or data.get("memory_percent") or data.get("ram") or "?"
    score = data.get("health_score", "?")
    issues = data.get("detected_issues", []) or []
    return {"cpu": cpu, "ram": ram, "score": score, "issues": ", ".join(issues[:4]) or "none noted"}


def _build_prompt(query: str, ctx: dict) -> str:
    catalog = "\n".join(f"  {k}: {v}" for k, v in TOOL_CATALOG.items())
    return (
        "You are the built-in assistant in FreeSystemDoctor, a Windows optimizer.\n"
        f"System snapshot: CPU {ctx['cpu']}% used, RAM {ctx['ram']}% used, "
        f"health {ctx['score']}/100. Noted issues: {ctx['issues']}.\n\n"
        "Available tools (key: purpose):\n" + catalog + "\n\n"
        f'User question: "{query}"\n\n'
        "Reply in 2-4 short, plain-language sentences a non-technical user understands. "
        "Do not invent features. If one tool best helps, end your reply with a final line "
        "exactly in the form:\nTOOL: <key>\n"
        "where <key> is one of the keys above. If no tool fits, omit the TOOL line."
    )


def _extract_tool(text: str) -> str | None:
    m = re.search(r"TOOL:\s*([a-z_]+)", text or "", re.IGNORECASE)
    if m:
        key = m.group(1).strip().lower()
        if key in TOOL_CATALOG:
            return key
    return None


def _keyword_fallback(query: str) -> str | None:
    q = (query or "").lower()
    for needles, key in INTENT_TOOL_MAP:
        if any(n in q for n in needles):
            return key
    return None


def answer(query: str) -> dict:
    """Return {text, suggested_key, suggested_label, error}."""
    query = (query or "").strip()
    if not query:
        return {"text": "", "suggested_key": None, "suggested_label": None, "error": "empty query"}

    ctx = _context()
    prompt = _build_prompt(query, ctx)
    text, err = ai_agent.ask(prompt)

    if not text:
        return {"text": "", "suggested_key": _keyword_fallback(query),
                "suggested_label": None, "error": err or "no response"}

    key = _extract_tool(text) or _keyword_fallback(query)
    # strip the TOOL: line from the visible answer
    clean = re.sub(r"\n?TOOL:\s*[a-z_]+\s*$", "", text, flags=re.IGNORECASE).strip()
    label = TOOL_CATALOG.get(key, "").strip() if key else None
    return {"text": clean, "suggested_key": key,
            "suggested_label": label, "error": None}
