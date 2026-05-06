"""AI system health analyzer — multi-provider LLM chain including Anthropic."""

import os
import json
import logging
import re
from typing import Optional, Callable
from dataclasses import dataclass
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    import anthropic as _anthropic_sdk
except ImportError:
    _anthropic_sdk = None

from . import system_info, memory_optimizer, privacy_cleaner as pc, protection as prot

# ── logging ───────────────────────────────────────────────────────────────────
_LOG_DIR = Path(os.getenv("TEMP", "C:\\Temp")) / "FreeSystemDoctor"
_LOG_DIR.mkdir(exist_ok=True, parents=True)

_logger = logging.getLogger("ai_agent")
if not _logger.handlers:
    _h = logging.FileHandler(_LOG_DIR / "ai_agent.log", encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.DEBUG)


@dataclass
class HealthReport:
    overall_score: int
    critical_issues: list[str]
    recommendations: list[str]
    analysis_text: str
    error: Optional[str] = None
    api_used: str = ""


# ── API registry ──────────────────────────────────────────────────────────────
# Each entry: (display_name, env_key_for_key, env_key_for_model, default_model, url_hint)
API_REGISTRY = [
    ("Anthropic",   "ANTHROPIC_API_KEY",   "ANTHROPIC_MODEL",   "claude-haiku-4-5-20251001", "anthropic"),
    ("Cerebras",    "CEREBRAS_API_KEY",    "CEREBRAS_MODEL",    "qwen-3-235b-a22b-instruct-2507", "cerebras"),
    ("Groq",        "GROQ_API_KEY",        "GROQ_MODEL",        "llama-3.3-70b-versatile",    "groq"),
    ("OpenRouter",  "OPENROUTER_API_KEY",  "OPENROUTER_MODEL",  "meta-llama/llama-3.2-3b-instruct:free", "openrouter"),
]

# Preferred API — can be changed at runtime by GUI
PREFERRED_API: str = "auto"   # "auto" = try all in order; or display_name e.g. "Anthropic"


def get_api_names() -> list[str]:
    """Return list of API display names for the GUI dropdown."""
    return ["auto"] + [name for name, *_ in API_REGISTRY]


def set_preferred_api(name: str):
    global PREFERRED_API
    PREFERRED_API = name
    _logger.info(f"Preferred API set to: {name}")


# ── system data ───────────────────────────────────────────────────────────────

def collect_system_data() -> dict:
    """Gather comprehensive system health metrics."""
    try:
        score, issues = system_info.get_health_score()
        info = system_info.get_static_info()
        disks = system_info.get_disk_info()
        memory = memory_optimizer.get_memory_detail()
        live = system_info.get_live_metrics() or {}
        def_status = prot.get_defender_status()
        fw_status = prot.get_firewall_status()
        tel_status = pc.get_telemetry_status()

        return {
            "health_score": score,
            "detected_issues": issues,
            "system_info": info,
            "disks": disks,
            "memory": memory,
            "live_metrics": live,
            "defender": def_status,
            "firewall": fw_status,
            "telemetry": tel_status,
        }
    except Exception as e:
        logging.error(f"Failed to collect system data: {e}")
        return {"error": str(e)}


def _build_prompt(data: dict) -> str:
    """Build analysis prompt from system data."""
    return f"""Analyze this Windows system health data concisely. Provide:
1. Overall assessment (1-2 sentences)
2. Critical issues (up to 3)
3. Top 5 actionable recommendations

Be technical and specific. Format each recommendation as a bullet point.

System Data:
{json.dumps(data, indent=2, default=str)}"""


# ── Anthropic (native SDK) ────────────────────────────────────────────────────

def call_anthropic(data: dict, stream_cb: Callable = None) -> tuple[Optional[str], Optional[str]]:
    """Call Anthropic API using the official SDK. Returns (content, error)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    if not api_key:
        return None, "Anthropic: No API key configured"

    if _anthropic_sdk is None:
        # Fall back to raw HTTP if SDK not installed
        if not requests:
            return None, "Anthropic: install anthropic or requests library"
        return _call_api_raw(
            "Anthropic",
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": model,
                "max_tokens": 900,
                "messages": [{"role": "user", "content": _build_prompt(data)}],
            },
            response_parser=_parse_anthropic_response,
            stream_cb=stream_cb,
        )

    try:
        _logger.info(f"Calling Anthropic SDK (model={model})")
        client = _anthropic_sdk.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=900,
            messages=[{"role": "user", "content": _build_prompt(data)}],
        )
        content = msg.content[0].text if msg.content else ""
        if content:
            _logger.info(f"Anthropic SDK success ({len(content)} chars)")
            if stream_cb:
                try:
                    stream_cb(content)
                except Exception:
                    pass
            return content, None
        return None, "Anthropic: empty response"
    except Exception as e:
        err = str(e)
        _logger.warning(f"Anthropic SDK error: {err}")
        if "rate_limit" in err.lower() or "529" in err or "overloaded" in err.lower():
            return None, "Anthropic: Rate limit / overloaded — try again later"
        if "authentication" in err.lower() or "401" in err:
            return None, "Anthropic: Invalid API key (401)"
        return None, f"Anthropic: {type(e).__name__}: {err[:80]}"


def _parse_anthropic_response(resp_json: dict) -> Optional[str]:
    content = resp_json.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return None


# ── OpenAI-compatible raw HTTP helper ─────────────────────────────────────────

def _call_api_raw(name: str, url: str, headers: dict, payload: dict,
                  response_parser=None, stream_cb: Callable = None
                  ) -> tuple[Optional[str], Optional[str]]:
    """Raw HTTP call for OpenAI-compatible and custom endpoints."""
    if not requests:
        return None, "requests library not installed"
    try:
        _logger.info(f"Calling {name} API (raw HTTP)")
        resp = requests.post(url, headers=headers, json=payload, timeout=30)

        if resp.status_code == 200:
            result = resp.json()
            if response_parser:
                content = response_parser(result)
            else:
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                _logger.info(f"{name} success ({len(content)} chars)")
                if stream_cb:
                    try:
                        stream_cb(content)
                    except Exception:
                        pass
                return content, None
            return None, f"{name}: empty response"

        elif resp.status_code == 429:
            try:
                err  = resp.json()
                msg  = (err.get("message") or
                        err.get("error", {}).get("message") or "Rate limit exceeded")
                m    = re.search(r"try again in ([\d\w.]+)", msg, re.I)
                wait = m.group(1) if m else "a few minutes"
                return None, f"{name}: Rate limit — retry in {wait}"
            except Exception:
                return None, f"{name}: Rate limit (429)"

        elif resp.status_code in (401, 403):
            return None, f"{name}: Invalid API key ({resp.status_code})"
        else:
            _logger.warning(f"{name} HTTP {resp.status_code}: {resp.text[:200]}")
            return None, f"{name}: Error {resp.status_code}"

    except requests.exceptions.Timeout:
        return None, f"{name}: Timed out (30s)"
    except requests.exceptions.ConnectionError:
        return None, f"{name}: No internet connection"
    except Exception as e:
        _logger.warning(f"{name} error: {e}")
        return None, f"{name}: {type(e).__name__}"


# ── OpenAI-compatible providers ───────────────────────────────────────────────

def _call_api(name: str, url: str, headers: dict, payload: dict,
              stream_cb: Callable = None) -> tuple[Optional[str], Optional[str]]:
    """Thin wrapper — delegates to raw HTTP helper."""
    return _call_api_raw(name, url, headers, payload, stream_cb=stream_cb)


# ── per-provider callers ──────────────────────────────────────────────────────

def _call_cerebras(data: dict, stream_cb=None):
    key   = os.getenv("CEREBRAS_API_KEY")
    model = os.getenv("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507")
    if not key:
        return None, "Cerebras: No API key configured"
    return _call_api_raw(
        "Cerebras", "https://api.cerebras.ai/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"model": model, "messages": [{"role": "user", "content": _build_prompt(data)}],
         "max_tokens": 800, "temperature": 0.7},
        stream_cb=stream_cb,
    )


def _call_groq(data: dict, stream_cb=None):
    key   = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not key:
        return None, "Groq: No API key configured"
    return _call_api_raw(
        "Groq", "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"model": model, "messages": [{"role": "user", "content": _build_prompt(data)}],
         "max_tokens": 800, "temperature": 0.7},
        stream_cb=stream_cb,
    )


def _call_openrouter(data: dict, stream_cb=None):
    key   = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
    if not key:
        return None, "OpenRouter: No API key configured"
    return _call_api_raw(
        "OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "HTTP-Referer": "https://github.com/kajetan-dev/FreeSystemDoctor",
         "X-Title": "FreeSystemDoctor"},
        {"model": model, "messages": [{"role": "user", "content": _build_prompt(data)}],
         "max_tokens": 800, "temperature": 0.7},
        stream_cb=stream_cb,
    )


# Map display name → caller function
_CALLERS = {
    "Anthropic":  call_anthropic,
    "Cerebras":   _call_cerebras,
    "Groq":       _call_groq,
    "OpenRouter": _call_openrouter,
}

# Default chain order
_DEFAULT_CHAIN = ["Anthropic", "Cerebras", "Groq", "OpenRouter"]


# ── main entry point ──────────────────────────────────────────────────────────

def analyze_system(stream_cb: Callable = None) -> HealthReport:
    """
    Analyze system health using the configured LLM API.
    If PREFERRED_API == 'auto', tries all providers in chain order.
    Otherwise tries only the selected provider.
    """
    data  = collect_system_data()
    score = data.get("health_score", 0)

    if "error" in data:
        _logger.error(f"System data collection failed: {data['error']}")
        return HealthReport(0, [], [], "",
                            error=f"Failed to collect system data: {data['error']}")

    # Build the call order
    if PREFERRED_API == "auto":
        chain = _DEFAULT_CHAIN
    else:
        # Preferred first, rest as fallback
        chain = [PREFERRED_API] + [n for n in _DEFAULT_CHAIN if n != PREFERRED_API]

    analysis   = None
    api_used   = ""
    api_errors: list[str] = []

    for api_name in chain:
        caller = _CALLERS.get(api_name)
        if not caller:
            continue
        content, error = caller(data, stream_cb=stream_cb)
        if content:
            analysis = content
            api_used = api_name
            _logger.info(f"Successfully used {api_name}")
            break
        if error:
            api_errors.append(error)
            _logger.warning(f"{api_name} failed: {error}")

    if not analysis:
        error_summary = " | ".join(api_errors) if api_errors else "No API keys configured"
        _logger.error(f"All APIs failed: {error_summary}")
        return HealthReport(score, data.get("detected_issues", []), [], "",
                            error=error_summary)

    # Parse structured sections from free-form LLM text
    critical_issues: list[str] = []
    recommendations: list[str] = []
    in_issues = in_recs = False

    for line in analysis.split("\n"):
        line = line.strip()
        if not line:
            continue
        lo = line.lower()
        if "critical" in lo and ("issue" in lo or "problem" in lo):
            in_issues, in_recs = True, False
            continue
        if "recommendation" in lo or ("action" in lo and "action" not in lo[:3]):
            in_issues, in_recs = False, True
            continue
        if line.startswith("#"):
            continue
        clean = line.lstrip("- •*0123456789.)")
        if len(clean) > 10:
            if in_issues:
                critical_issues.append(clean)
            elif in_recs:
                recommendations.append(clean)

    _logger.info(f"Parsed {len(critical_issues)} issues, {len(recommendations)} recs")

    return HealthReport(
        overall_score=score,
        critical_issues=critical_issues[:3],
        recommendations=recommendations[:5],
        analysis_text=analysis,
        api_used=api_used,
    )


# public aliases for backwards compat
def call_cerebras(data, stream_cb=None):
    c, _ = _call_cerebras(data, stream_cb); return c

def call_groq(data, stream_cb=None):
    c, _ = _call_groq(data, stream_cb); return c

def call_openrouter(data, stream_cb=None):
    c, _ = _call_openrouter(data, stream_cb); return c
