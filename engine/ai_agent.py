"""AI system health analyzer — multi-provider LLM chain including Anthropic and local Ollama."""

import os
import json
import logging
import platform
import re
import subprocess
from typing import Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    import anthropic as _anthropic_sdk
except ImportError:
    _anthropic_sdk = None

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

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


# ── Analysis modes ────────────────────────────────────────────────────────────
ANALYSIS_MODES = {
    "full":      "Full System Analysis",
    "hardware":  "Hardware Health & Advice",
    "optimize":  "Optimization Score & Tips",
    "gaming":    "Gaming Performance Analysis",
    "security":  "Security Audit",
}


@dataclass
class HealthReport:
    overall_score: int
    critical_issues: list[str]
    recommendations: list[str]
    analysis_text: str
    error: Optional[str] = None
    api_used: str = ""
    mode: str = "full"
    hardware_score: int = 0
    optimization_score: int = 0
    security_score: int = 0
    hardware_advice: list[str] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)


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

# ── Ollama (local LLM — no API key, offline) ──────────────────────────────────
# Recommended: qwen2.5:0.5b (~394 MB) or tinyllama (~638 MB)
OLLAMA_BASE_URL: str = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL: str = "qwen2.5:0.5b"   # <1 GB, very capable for its size


def ollama_is_running() -> bool:
    """Return True if local Ollama server is reachable."""
    if not requests:
        return False
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def ollama_list_models() -> list[str]:
    """Return list of model names available in the local Ollama install."""
    if not requests:
        return []
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


def ollama_pull_model(model: str, progress_cb: Callable = None) -> tuple[bool, str]:
    """
    Pull (download) a model from Ollama registry.
    Streams progress lines; calls progress_cb(pct, status_str) if provided.
    Returns (success, message).
    """
    if not requests:
        return False, "requests not installed"
    try:
        with requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model, "stream": True},
            stream=True, timeout=600,
        ) as resp:
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    status = data.get("status", "")
                    total  = data.get("total", 0)
                    compl  = data.get("completed", 0)
                    pct    = int(compl * 100 / total) if total else 0
                    if progress_cb:
                        progress_cb(pct, status)
                    if data.get("status") == "success":
                        return True, f"Model '{model}' ready"
                except Exception:
                    pass
        return True, f"Model '{model}' downloaded"
    except Exception as e:
        return False, str(e)


def set_ollama_model(model: str):
    """Change the active Ollama model at runtime."""
    global OLLAMA_DEFAULT_MODEL
    OLLAMA_DEFAULT_MODEL = model
    _logger.info(f"Ollama model set to: {model}")


def get_api_names() -> list[str]:
    """Return list of API display names for the GUI dropdown."""
    return ["auto"] + [name for name, *_ in API_REGISTRY] + ["Ollama"]


def set_preferred_api(name: str):
    global PREFERRED_API
    PREFERRED_API = name
    _logger.info(f"Preferred API set to: {name}")


# ── system data ───────────────────────────────────────────────────────────────

def _wmi_query(query: str) -> list[dict]:
    """Run a WMI query via PowerShell and return parsed results."""
    try:
        ps = f"Get-WmiObject -Query \"{query}\" | ConvertTo-Json -Depth 2"
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0 and r.stdout.strip():
            raw = json.loads(r.stdout)
            return raw if isinstance(raw, list) else [raw]
    except Exception:
        pass
    return []


def collect_hardware_data() -> dict:
    """Collect detailed hardware information via WMI + psutil."""
    hw: dict = {}

    # CPU
    cpu_rows = _wmi_query("SELECT Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed FROM Win32_Processor")
    if cpu_rows:
        c = cpu_rows[0]
        hw["cpu"] = {
            "name":        c.get("Name", ""),
            "cores":       c.get("NumberOfCores", 0),
            "threads":     c.get("NumberOfLogicalProcessors", 0),
            "max_mhz":     c.get("MaxClockSpeed", 0),
        }

    # RAM
    ram_rows = _wmi_query("SELECT Capacity,Speed,MemoryType,DeviceLocator FROM Win32_PhysicalMemory")
    if ram_rows:
        hw["ram_sticks"] = [
            {
                "slot":     r.get("DeviceLocator", ""),
                "size_gb":  round(int(r.get("Capacity", 0)) / (1024**3), 1),
                "speed_mhz":r.get("Speed", 0),
                "type":     {20: "DDR", 21: "DDR2", 22: "DDR2 FB", 24: "DDR3",
                             26: "DDR4", 34: "DDR5"}.get(r.get("MemoryType", 0), "Unknown"),
            }
            for r in ram_rows
        ]
        total_gb = sum(s["size_gb"] for s in hw["ram_sticks"])
        hw["ram_total_gb"] = total_gb
        hw["ram_speed_mhz"] = hw["ram_sticks"][0]["speed_mhz"] if hw["ram_sticks"] else 0

    # GPU
    gpu_rows = _wmi_query("SELECT Name,AdapterRAM,DriverVersion FROM Win32_VideoController WHERE AdapterRAM > 0")
    if gpu_rows:
        hw["gpus"] = [
            {
                "name":       g.get("Name", ""),
                "vram_mb":    round(int(g.get("AdapterRAM", 0)) / (1024**2)),
                "driver":     g.get("DriverVersion", ""),
            }
            for g in gpu_rows
        ]

    # Disks
    disk_rows = _wmi_query("SELECT Model,MediaType,Size FROM Win32_DiskDrive")
    if disk_rows:
        hw["disks"] = [
            {
                "model":    d.get("Model", ""),
                "type":     d.get("MediaType", "Unknown"),
                "size_gb":  round(int(d.get("Size", 0)) / (1024**3)),
            }
            for d in disk_rows
        ]

    # Temperatures via WMI (requires admin; may fail gracefully)
    try:
        temp_rows = _wmi_query("SELECT CurrentTemperature,InstanceName FROM MSAcpi_ThermalZoneTemperature")
        if temp_rows:
            hw["temperatures"] = [
                {
                    "zone": t.get("InstanceName", ""),
                    "celsius": round((int(t.get("CurrentTemperature", 2731)) - 2731) / 10, 1),
                }
                for t in temp_rows
            ]
    except Exception:
        pass

    # Motherboard
    mb_rows = _wmi_query("SELECT Manufacturer,Product,Version FROM Win32_BaseBoard")
    if mb_rows:
        mb = mb_rows[0]
        hw["motherboard"] = f"{mb.get('Manufacturer','')} {mb.get('Product','')} {mb.get('Version','')}".strip()

    # psutil live metrics
    if _PSUTIL:
        try:
            hw["cpu_usage_pct"]  = psutil.cpu_percent(interval=0.5)
            hw["ram_used_pct"]   = psutil.virtual_memory().percent
            hw["cpu_freq_mhz"]   = round(psutil.cpu_freq().current) if psutil.cpu_freq() else 0
            io = psutil.disk_io_counters()
            hw["disk_read_mb"]   = round(io.read_bytes  / (1024**2)) if io else 0
            hw["disk_write_mb"]  = round(io.write_bytes / (1024**2)) if io else 0
        except Exception:
            pass

    return hw


def collect_system_data() -> dict:
    """Gather comprehensive system health metrics."""
    try:
        score, issues = system_info.get_health_score()
        info  = system_info.get_static_info()
        disks = system_info.get_disk_info()
        memory = memory_optimizer.get_memory_detail()
        live  = system_info.get_live_metrics() or {}
        def_status = prot.get_defender_status()
        fw_status  = prot.get_firewall_status()
        tel_status = pc.get_telemetry_status()
        hardware   = collect_hardware_data()

        return {
            "health_score":    score,
            "detected_issues": issues,
            "system_info":     info,
            "disks":           disks,
            "memory":          memory,
            "live_metrics":    live,
            "defender":        def_status,
            "firewall":        fw_status,
            "telemetry":       tel_status,
            "hardware":        hardware,
            "os_version":      platform.version(),
            "windows_edition": platform.win32_edition() if hasattr(platform, "win32_edition") else "",
        }
    except Exception as e:
        logging.error(f"Failed to collect system data: {e}")
        return {"error": str(e)}


# ── Prompt templates per analysis mode ────────────────────────────────────────

def _build_compact_prompt(data: dict, mode: str = "full") -> str:
    """
    Short, highly-structured prompt for small (<1 GB) local models.
    Avoids long context; demands strict section headers so the parser works.
    """
    hw  = data.get("hardware", {})
    cpu = hw.get("cpu", {}).get("name", "?")
    ram = hw.get("ram_total_gb", "?")
    gpu = (hw.get("gpus") or [{}])[0].get("name", "?")
    cpu_use = hw.get("cpu_usage_pct", "?")
    ram_use = hw.get("ram_used_pct", "?")
    score   = data.get("health_score", 0)
    issues  = ", ".join(data.get("detected_issues", [])[:3]) or "none"

    base = (
        f"CPU:{cpu} RAM:{ram}GB GPU:{gpu} "
        f"Load:CPU{cpu_use}%,RAM{ram_use}% Score:{score}/100 Issues:{issues}"
    )

    if mode == "hardware":
        return (
            f"You are a PC hardware expert. System: {base}\n"
            "Reply ONLY using these exact headers (no extra text):\n"
            "## Hardware Score: [0-100]\n"
            "## Bottleneck Analysis\n[one sentence]\n"
            "## Upgrade Priority\n1. [upgrade]\n2. [upgrade]\n3. [upgrade]\n"
            "Max 200 words."
        )
    elif mode == "optimize":
        return (
            f"You are a Windows optimization expert. System: {base}\n"
            "Reply ONLY using these exact headers:\n"
            "## Optimization Score: [0-100]\n"
            "## Critical Tweaks (apply immediately)\n- [tweak]\n- [tweak]\n- [tweak]\n"
            "## Performance Recommendations\n1. [rec]\n2. [rec]\n3. [rec]\n"
            "Max 200 words."
        )
    elif mode == "gaming":
        return (
            f"You are a gaming PC expert. System: {base}\n"
            "Reply ONLY using these exact headers:\n"
            "## Gaming Performance Score: [0-100]\n"
            "## Gaming Bottleneck\n[one sentence]\n"
            "## System Tweaks for Gaming\n1. [tweak]\n2. [tweak]\n3. [tweak]\n"
            "Max 200 words."
        )
    elif mode == "security":
        return (
            f"You are a Windows security expert. System: {base} "
            f"Defender:{data.get('defender',{})} Firewall:{data.get('firewall',{})}\n"
            "Reply ONLY using these exact headers:\n"
            "## Security Score: [0-100]\n"
            "## Critical Vulnerabilities\n- [vuln]\n- [vuln]\n"
            "## Security Recommendations\n1. [action]\n2. [action]\n3. [action]\n"
            "Max 200 words."
        )
    else:  # full
        return (
            f"You are a PC expert. System: {base}\n"
            "Reply ONLY using these exact headers:\n"
            "## Overall Score: [0-100]\n"
            "## Hardware Score: [0-100]\n"
            "## Optimization Score: [0-100]\n"
            "## Security Score: [0-100]\n"
            "## Critical Issues\n- [issue]\n- [issue]\n"
            "## Top Recommendations\n1. [rec]\n2. [rec]\n3. [rec]\n4. [rec]\n"
            "Max 250 words."
        )


def _build_prompt(data: dict, mode: str = "full") -> str:
    """Build mode-specific analysis prompt."""

    hw = data.get("hardware", {})
    cpu_name  = hw.get("cpu", {}).get("name", "Unknown CPU")
    ram_gb    = hw.get("ram_total_gb", "?")
    ram_spd   = hw.get("ram_speed_mhz", "?")
    gpus      = ", ".join(g["name"] for g in hw.get("gpus", [])) or "Unknown GPU"
    disks     = "; ".join(f"{d['model']} ({d['type']}, {d['size_gb']}GB)"
                          for d in hw.get("disks", [])) or "Unknown"
    cpu_use   = hw.get("cpu_usage_pct", "?")
    ram_use   = hw.get("ram_used_pct", "?")
    score     = data.get("health_score", 0)
    issues    = data.get("detected_issues", [])

    hw_summary = (
        f"CPU: {cpu_name} ({hw.get('cpu',{}).get('cores','?')}C/{hw.get('cpu',{}).get('threads','?')}T)\n"
        f"RAM: {ram_gb} GB @ {ram_spd} MHz\n"
        f"GPU: {gpus}\n"
        f"Storage: {disks}\n"
        f"Motherboard: {hw.get('motherboard','Unknown')}\n"
        f"Live load: CPU {cpu_use}%, RAM {ram_use}%"
    )

    if mode == "hardware":
        return f"""You are an expert PC hardware analyst. Evaluate this system's hardware and give concrete upgrade advice.

Hardware Profile:
{hw_summary}

REQUIRED OUTPUT FORMAT (use exact headers):
## Hardware Score: [0-100]
## Bottleneck Analysis
[Identify the weakest component limiting performance]
## Component Assessment
- CPU: [rating and comment]
- RAM: [rating, speed, and if dual-channel]
- GPU: [rating and comment]
- Storage: [SSD/HDD, speed tier]
## Upgrade Priority
1. [Most impactful upgrade with estimated cost range]
2. [Second upgrade]
3. [Third upgrade]
## Compatibility Notes
[Any relevant compatibility warnings]

Be specific with model names, speeds, and prices in USD. Keep total response under 600 words."""

    elif mode == "optimize":
        return f"""You are a Windows optimization expert. Score and analyze this PC's software optimization level.

Hardware: {hw_summary}
Health Score: {score}/100
Known Issues: {', '.join(issues) if issues else 'None detected'}
OS: {data.get('os_version', 'Unknown')}
Telemetry: {data.get('telemetry', {})}
Firewall: {data.get('firewall', {})}
Defender: {data.get('defender', {})}

REQUIRED OUTPUT FORMAT:
## Optimization Score: [0-100]
## Software Efficiency Rating
[1-2 sentences on current state]
## Critical Tweaks (apply immediately)
- [tweak 1]
- [tweak 2]
- [tweak 3]
## Performance Recommendations
1. [recommendation with expected impact]
2. [recommendation]
3. [recommendation]
4. [recommendation]
5. [recommendation]
## Windows Settings to Change
[Specific registry keys, settings, or features to enable/disable]

Be concrete and actionable. Include specific settings paths. Under 500 words."""

    elif mode == "gaming":
        return f"""You are a PC gaming performance expert. Analyze this system for gaming and give specific optimizations.

Hardware: {hw_summary}
Live Load: CPU {cpu_use}%, RAM {ram_use}%
Health Score: {score}/100

REQUIRED OUTPUT FORMAT:
## Gaming Performance Score: [0-100]
## Expected Gaming Performance
[FPS estimates for 1080p/1440p/4K for typical AAA games]
## Gaming Bottleneck
[What limits gaming performance most]
## Game-Specific Config Recommendations
- Recommended settings for Valorant/CS2: [settings]
- Recommended settings for AAA titles: [settings]
## System Tweaks for Gaming
1. [Windows tweak with exact steps]
2. [tweak]
3. [tweak]
4. [tweak]
## Upgrade Impact on Gaming
[How specific upgrades would improve gaming performance]

Be specific with FPS numbers, settings names, and concrete steps. Under 550 words."""

    elif mode == "security":
        return f"""You are a Windows security expert. Audit this system's security posture.

Defender: {data.get('defender', {})}
Firewall: {data.get('firewall', {})}
Telemetry: {data.get('telemetry', {})}
OS: {data.get('os_version', 'Unknown')}
Known Issues: {', '.join(issues) if issues else 'None'}

REQUIRED OUTPUT FORMAT:
## Security Score: [0-100]
## Security Posture
[Overall assessment]
## Critical Vulnerabilities
- [issue 1]
- [issue 2]
## Security Recommendations
1. [action with specific steps]
2. [action]
3. [action]
4. [action]
5. [action]
## Privacy Settings to Change
[Specific Windows privacy settings to adjust]

Be precise about CVEs, Windows settings paths, and specific actions. Under 500 words."""

    else:  # full
        return f"""You are an expert Windows system analyst. Provide a comprehensive analysis of this PC.

Hardware: {hw_summary}
Health Score: {score}/100
Issues: {', '.join(issues) if issues else 'None'}
Full Data: {json.dumps({k: v for k, v in data.items() if k != 'hardware'}, indent=2, default=str)[:2000]}

REQUIRED OUTPUT FORMAT:
## Overall Score: [0-100]
## System Assessment
[2-3 sentence overview]
## Hardware Score: [0-100]
## Optimization Score: [0-100]
## Security Score: [0-100]
## Critical Issues
- [issue 1]
- [issue 2]
- [issue 3]
## Top Recommendations
1. [recommendation]
2. [recommendation]
3. [recommendation]
4. [recommendation]
5. [recommendation]
## Hardware Advice
[Key upgrade suggestion if applicable]

Be technical and actionable. Under 600 words."""


# ── Anthropic (native SDK) ────────────────────────────────────────────────────

def call_anthropic(data: dict, stream_cb: Callable = None,
                   mode: str = "full") -> tuple[Optional[str], Optional[str]]:
    """Call Anthropic API using the official SDK. Returns (content, error)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    if not api_key:
        return None, "Anthropic: No API key configured"

    prompt = _build_prompt(data, mode)

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
                "max_tokens": 1200,
                "messages": [{"role": "user", "content": prompt}],
            },
            response_parser=_parse_anthropic_response,
            stream_cb=stream_cb,
        )

    try:
        _logger.info(f"Calling Anthropic SDK (model={model}, mode={mode})")
        client = _anthropic_sdk.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
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

def _call_cerebras(data: dict, stream_cb=None, mode: str = "full"):
    key   = os.getenv("CEREBRAS_API_KEY")
    model = os.getenv("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507")
    if not key:
        return None, "Cerebras: No API key configured"
    return _call_api_raw(
        "Cerebras", "https://api.cerebras.ai/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"model": model, "messages": [{"role": "user", "content": _build_prompt(data, mode)}],
         "max_tokens": 1200, "temperature": 0.7},
        stream_cb=stream_cb,
    )


def _call_groq(data: dict, stream_cb=None, mode: str = "full"):
    key   = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not key:
        return None, "Groq: No API key configured"
    return _call_api_raw(
        "Groq", "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"model": model, "messages": [{"role": "user", "content": _build_prompt(data, mode)}],
         "max_tokens": 1200, "temperature": 0.7},
        stream_cb=stream_cb,
    )


def _call_openrouter(data: dict, stream_cb=None, mode: str = "full"):
    key   = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
    if not key:
        return None, "OpenRouter: No API key configured"
    return _call_api_raw(
        "OpenRouter", "https://openrouter.ai/api/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "HTTP-Referer": "https://github.com/kajetan-dev/FreeSystemDoctor",
         "X-Title": "FreeSystemDoctor"},
        {"model": model, "messages": [{"role": "user", "content": _build_prompt(data, mode)}],
         "max_tokens": 1200, "temperature": 0.7},
        stream_cb=stream_cb,
    )


# ── Ollama caller ─────────────────────────────────────────────────────────────

def _call_ollama(data: dict, stream_cb=None, mode: str = "full"):
    """
    Call local Ollama server (http://localhost:11434).
    Uses the compact prompt optimised for small (<1 GB) models.
    Falls back to the full prompt if the model name suggests a larger model.
    """
    if not requests:
        return None, "Ollama: requests library not installed"
    if not ollama_is_running():
        return None, "Ollama: server not running (start with 'ollama serve')"

    model = OLLAMA_DEFAULT_MODEL
    models_available = ollama_list_models()

    # If no model installed at all, tell the user
    if not models_available:
        return None, (
            f"Ollama: no models installed. "
            f"Run: ollama pull {OLLAMA_DEFAULT_MODEL}  (~394 MB)"
        )

    # If configured model not present, use first available
    if model not in models_available:
        model = models_available[0]
        _logger.info(f"Ollama: model '{OLLAMA_DEFAULT_MODEL}' not found, using '{model}'")

    # Choose compact prompt for sub-1 GB models (heuristic: 0.5b / 1b / tinyllama tags)
    small_tags = ("0.5b", "1b", "1.1b", "135m", "360m", "1.7b", "tinyllama", "smollm")
    is_small   = any(t in model.lower() for t in small_tags)
    prompt     = _build_compact_prompt(data, mode) if is_small else _build_prompt(data, mode)

    _logger.info(f"Calling Ollama (model={model}, compact={is_small}, mode={mode})")

    # Use Ollama native /api/chat (more reliable than /v1 compat)
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model":    model,
                "messages": [{"role": "user", "content": prompt}],
                "stream":   False,
                "options":  {
                    "temperature": 0.7,
                    "num_predict": 512,   # max tokens — enough for structured output
                },
            },
            timeout=120,    # small models are fast; give 2 min for slow CPUs
        )
    except Exception as e:
        return None, f"Ollama: connection error — {e}"

    if resp.status_code == 404:
        return None, f"Ollama: model '{model}' not found — run: ollama pull {model}"
    if resp.status_code != 200:
        return None, f"Ollama: HTTP {resp.status_code}"

    try:
        content = resp.json()["message"]["content"].strip()
    except (KeyError, ValueError):
        return None, "Ollama: unexpected response format"

    if not content:
        return None, "Ollama: empty response"

    _logger.info(f"Ollama success ({len(content)} chars, model={model})")
    if stream_cb:
        try:
            stream_cb(content)
        except Exception:
            pass
    return content, None


# Map display name → caller function
_CALLERS = {
    "Anthropic":  call_anthropic,
    "Cerebras":   _call_cerebras,
    "Groq":       _call_groq,
    "OpenRouter": _call_openrouter,
    "Ollama":     _call_ollama,
}

# Default chain order — Ollama first (free, local, private); cloud APIs as fallback
_DEFAULT_CHAIN = ["Ollama", "Anthropic", "Cerebras", "Groq", "OpenRouter"]


# ── structured output parser ──────────────────────────────────────────────────

def _extract_score(text: str, label: str) -> int:
    """Extract numeric score from '## Label: 75' style headers."""
    pattern = rf"##\s*{re.escape(label)}[:\s]*(\d{{1,3}})"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return min(100, max(0, int(m.group(1))))
    return 0


def _extract_section(text: str, header: str) -> list[str]:
    """Extract bullet/numbered list from a markdown section."""
    pattern = rf"##\s*{re.escape(header)}.*?\n(.*?)(?=##|\Z)"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return []
    block = m.group(1)
    items = []
    for line in block.split("\n"):
        line = line.strip()
        clean = re.sub(r"^[-•*\d]+[.)]\s*", "", line)
        if len(clean) > 8:
            items.append(clean)
    return items


def _parse_report(text: str, mode: str, base_score: int) -> HealthReport:
    """Parse LLM output into a structured HealthReport."""

    overall = _extract_score(text, "Overall Score") or base_score
    hw_score  = _extract_score(text, "Hardware Score")
    opt_score = _extract_score(text, "Optimization Score")
    sec_score = _extract_score(text, "Security Score")
    gaming_score = _extract_score(text, "Gaming Performance Score")

    # Mode-specific score fallbacks
    if mode == "hardware"  and not hw_score:
        hw_score = overall
    if mode == "optimize"  and not opt_score:
        opt_score = overall
    if mode == "gaming"    and not gaming_score:
        gaming_score = overall
    if mode == "security"  and not sec_score:
        sec_score = overall

    # Overall from mode score if missing
    if not overall:
        overall = hw_score or opt_score or sec_score or gaming_score or base_score

    critical   = _extract_section(text, "Critical Issues") or _extract_section(text, "Critical Vulnerabilities")
    recs       = (_extract_section(text, "Top Recommendations") or
                  _extract_section(text, "Performance Recommendations") or
                  _extract_section(text, "System Tweaks for Gaming") or
                  _extract_section(text, "Security Recommendations"))
    hw_advice  = _extract_section(text, "Upgrade Priority") or _extract_section(text, "Upgrade Impact on Gaming")
    bottlenecks = _extract_section(text, "Bottleneck Analysis") or _extract_section(text, "Gaming Bottleneck")

    return HealthReport(
        overall_score=overall,
        critical_issues=critical[:4],
        recommendations=recs[:6],
        analysis_text=text,
        mode=mode,
        hardware_score=hw_score,
        optimization_score=opt_score,
        security_score=sec_score,
        hardware_advice=hw_advice[:4],
        bottlenecks=bottlenecks[:3],
    )


# ── main entry point ──────────────────────────────────────────────────────────

def analyze_system(stream_cb: Callable = None, mode: str = "full") -> HealthReport:
    """
    Analyze system health using the configured LLM API.
    mode: 'full' | 'hardware' | 'optimize' | 'gaming' | 'security'
    If PREFERRED_API == 'auto', tries all providers in chain order.
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
        chain = [PREFERRED_API] + [n for n in _DEFAULT_CHAIN if n != PREFERRED_API]

    analysis   = None
    api_used   = ""
    api_errors: list[str] = []

    for api_name in chain:
        caller = _CALLERS.get(api_name)
        if not caller:
            continue
        content, error = caller(data, stream_cb=stream_cb, mode=mode)
        if content:
            analysis = content
            api_used = api_name
            _logger.info(f"Successfully used {api_name} (mode={mode})")
            break
        if error:
            api_errors.append(error)
            _logger.warning(f"{api_name} failed: {error}")

    if not analysis:
        error_summary = " | ".join(api_errors) if api_errors else "No API keys configured"
        _logger.error(f"All APIs failed: {error_summary}")
        return HealthReport(score, data.get("detected_issues", []), [], "",
                            error=error_summary, mode=mode)

    report = _parse_report(analysis, mode, score)
    report.api_used = api_used

    # Inject detected_issues as critical_issues if LLM returned none
    if not report.critical_issues:
        report.critical_issues = data.get("detected_issues", [])[:3]

    _logger.info(f"Parsed: overall={report.overall_score} hw={report.hardware_score} "
                 f"opt={report.optimization_score} sec={report.security_score} "
                 f"issues={len(report.critical_issues)} recs={len(report.recommendations)}")

    return report


# ── generic free-form prompt (used by "Ask your PC") ──────────────────────────

def _ask_provider(name: str, prompt: str) -> tuple[Optional[str], Optional[str]]:
    """Send an arbitrary prompt to a single provider. Returns (text, error)."""
    if name == "Ollama":
        if not requests:
            return None, "Ollama: requests not installed"
        if not ollama_is_running():
            return None, "Ollama: server not running"
        models = ollama_list_models()
        if not models:
            return None, f"Ollama: no models installed (try: ollama pull {OLLAMA_DEFAULT_MODEL})"
        model = OLLAMA_DEFAULT_MODEL if OLLAMA_DEFAULT_MODEL in models else models[0]
        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": model,
                      "messages": [{"role": "user", "content": prompt}],
                      "stream": False,
                      "options": {"temperature": 0.6, "num_predict": 400}},
                timeout=120)
            if resp.status_code != 200:
                return None, f"Ollama: HTTP {resp.status_code}"
            return (resp.json()["message"]["content"].strip() or None), None
        except Exception as e:
            return None, f"Ollama: {type(e).__name__}"

    if name == "Anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None, "Anthropic: No API key configured"
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        return _call_api_raw(
            "Anthropic", "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01",
             "Content-Type": "application/json"},
            {"model": model, "max_tokens": 600,
             "messages": [{"role": "user", "content": prompt}]},
            response_parser=_parse_anthropic_response)

    # OpenAI-compatible providers
    cfg = {
        "Cerebras":   ("CEREBRAS_API_KEY", "CEREBRAS_MODEL",
                       "qwen-3-235b-a22b-instruct-2507",
                       "https://api.cerebras.ai/v1/chat/completions", {}),
        "Groq":       ("GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile",
                       "https://api.groq.com/openai/v1/chat/completions", {}),
        "OpenRouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL",
                       "meta-llama/llama-3.2-3b-instruct:free",
                       "https://openrouter.ai/api/v1/chat/completions",
                       {"HTTP-Referer": "https://github.com/kajetan-dev/FreeSystemDoctor",
                        "X-Title": "FreeSystemDoctor"}),
    }.get(name)
    if not cfg:
        return None, f"{name}: unknown provider"
    key_env, model_env, default_model, url, extra_headers = cfg
    key = os.getenv(key_env)
    if not key:
        return None, f"{name}: No API key configured"
    model = os.getenv(model_env, default_model)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    headers.update(extra_headers)
    return _call_api_raw(
        name, url, headers,
        {"model": model, "messages": [{"role": "user", "content": prompt}],
         "max_tokens": 600, "temperature": 0.6})


def ask(prompt: str) -> tuple[Optional[str], Optional[str]]:
    """Run an arbitrary prompt through the same provider chain as analyze_system
    (Ollama-first ⇒ offline-capable). Returns (answer_text, error)."""
    if PREFERRED_API == "auto":
        chain = _DEFAULT_CHAIN
    else:
        chain = [PREFERRED_API] + [n for n in _DEFAULT_CHAIN if n != PREFERRED_API]

    errors: list[str] = []
    for name in chain:
        text, err = _ask_provider(name, prompt)
        if text:
            return text, None
        if err:
            errors.append(err)
    return None, (" | ".join(errors) if errors else "No AI provider configured")


# ── public aliases for backwards compat ───────────────────────────────────────
def call_cerebras(data, stream_cb=None, mode="full"):
    c, _ = _call_cerebras(data, stream_cb, mode); return c

def call_groq(data, stream_cb=None, mode="full"):
    c, _ = _call_groq(data, stream_cb, mode); return c

def call_openrouter(data, stream_cb=None, mode="full"):
    c, _ = _call_openrouter(data, stream_cb, mode); return c
