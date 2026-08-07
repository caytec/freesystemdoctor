"""
local_llm.py — a small language model that runs on this PC, with no account,
no API key and no data leaving the machine.

Ships llama.cpp's `llama-server` (~18 MB) plus Qwen2.5-0.5B-Instruct in GGUF
(~470 MB). llama-server speaks the OpenAI chat-completions protocol, so the
existing provider plumbing in ai_agent talks to it unchanged.

A word on what a 0.5B model can and cannot do, because it matters for how we
use it: it is far too small to *know* things about Windows reliably. Asked an
open question it will invent an answer. What it is genuinely good at is taking
facts it has been handed and phrasing them for a human. So everything here is
built around feeding it real measurements from our own engine and asking it to
explain them — never asking it to recall.

Layout (matching the LibreHardwareMonitor downloader's conventions):
    %APPDATA%\\FreeSystemDoctor\\LocalLLM\\
        bin\\llama-server.exe        (+ its DLLs)
        models\\qwen2.5-0.5b-instruct-q4_k_m.gguf
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_UA = {"User-Agent": "FreeSystemDoctor/2.3 (+https://kajetankupaj.pl)"}

APPDATA = Path(os.environ.get("APPDATA",
                              os.path.expanduser("~"))) / "FreeSystemDoctor"
LLM_DIR = APPDATA / "LocalLLM"
BIN_DIR = LLM_DIR / "bin"
MODEL_DIR = LLM_DIR / "models"
STATE_FILE = LLM_DIR / "local_llm.json"

# Qwen2.5-0.5B-Instruct, Apache-2.0 — redistributable, and the smallest model
# that still follows instructions well enough to be useful.
MODEL_NAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_URL = ("https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/"
             "resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf")
MODEL_SIZE_MB = 469

_LLAMA_RELEASES = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
LLAMA_SIZE_MB = 18

# 8080 is heavily used; pick something unlikely to collide.
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8177
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

_proc: Optional[subprocess.Popen] = None
_proc_lock = threading.Lock()

ProgressCb = Optional[Callable[[int, str], None]]


# ── state ────────────────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_state(state: dict) -> None:
    try:
        LLM_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, STATE_FILE)
    except Exception as exc:
        logger.debug("local_llm._save_state: %s", exc)


def _server_exe() -> Path:
    return BIN_DIR / "llama-server.exe"


def _model_path() -> Path:
    return MODEL_DIR / MODEL_NAME


def is_installed() -> bool:
    """Both halves present and plausibly complete."""
    try:
        exe, mdl = _server_exe(), _model_path()
        return (exe.exists() and mdl.exists()
                # a truncated download is worse than none — sanity-check size
                and mdl.stat().st_size > (MODEL_SIZE_MB - 20) * 1024 * 1024)
    except Exception:
        return False


def get_status() -> dict:
    """Everything the UI needs to describe the local model in one call."""
    mdl = _model_path()
    model_mb = 0
    try:
        if mdl.exists():
            model_mb = int(mdl.stat().st_size / (1024 * 1024))
    except Exception:
        pass
    state = _load_state()
    return {
        "installed": is_installed(),
        "server_exe": str(_server_exe()),
        "model_path": str(mdl),
        "model_mb": model_mb,
        "running": is_server_running(),
        "model_name": "Qwen2.5-0.5B-Instruct (Q4_K_M)",
        "download_mb": MODEL_SIZE_MB + LLAMA_SIZE_MB,
        "installed_at": state.get("installed_at", ""),
        "llama_version": state.get("llama_version", ""),
        "base_url": BASE_URL,
    }


# ── download ─────────────────────────────────────────────────────────────────

def _llamacpp_asset_url() -> tuple[Optional[str], str]:
    """Latest llama.cpp Windows CPU build for this architecture.

    CPU-only on purpose: the CUDA builds are 240 MB+ and need a matching
    driver. For a 0.5B model the CPU build is fast enough and always works.
    """
    try:
        req = urllib.request.Request(_LLAMA_RELEASES, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            rel = json.load(r)
    except Exception as exc:
        logger.warning("llama.cpp release lookup failed: %s", exc)
        return None, ""

    machine = platform.machine().lower()
    want = "bin-win-cpu-arm64" if machine in ("arm64", "aarch64") \
        else "bin-win-cpu-x64"
    for asset in rel.get("assets", []):
        name = asset.get("name", "")
        if want in name and name.endswith(".zip"):
            return asset.get("browser_download_url"), rel.get("tag_name", "")
    return None, rel.get("tag_name", "")


def _download(url: str, dest: Path, progress_cb: ProgressCb,
              lo: int, hi: int, label: str, max_attempts: int = 6) -> bool:
    """Stream a URL to disk, mapping its progress onto the lo..hi band.

    A ~470 MB transfer over a home connection WILL hit at least one stalled
    read — that isn't exceptional, it's normal. So this resumes via HTTP
    Range from wherever the .part file left off instead of restarting from
    zero, and retries several times before giving up. Only a definitive
    failure (server rejects the whole request, disk full) discards the
    partial file; a network hiccup just continues it on the next attempt.
    """
    part = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_attempts + 1):
        resume_from = part.stat().st_size if part.exists() else 0
        headers = dict(_UA)
        if resume_from:
            headers["Range"] = f"bytes={resume_from}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                resumed = (r.status == 206)
                if resume_from and not resumed:
                    # Server ignored our Range — it would send the whole file
                    # again onto an already-partial one. Start clean instead.
                    resume_from = 0
                    part.unlink(missing_ok=True)
                # A byte-serving CDN reports the true total via Content-Range
                # ("bytes 260000000-467999999/468000000"); Content-Length on a
                # 206 response is only the size of THIS chunk, not the whole
                # file, so it must not be used as the total when resuming.
                content_range = r.headers.get("Content-Range", "")
                range_total = 0
                if "/" in content_range:
                    try:
                        range_total = int(content_range.rsplit("/", 1)[-1])
                    except ValueError:
                        pass
                content_len = int(r.headers.get("Content-Length") or 0)
                total = range_total or ((resume_from + content_len)
                                        if resumed else content_len)
                done = resume_from
                last_pct = -1
                mode = "ab" if resumed else "wb"
                with open(part, mode) as f:
                    while True:
                        chunk = r.read(256 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if progress_cb and total:
                            pct = lo + int((done / total) * (hi - lo))
                            if pct != last_pct:
                                last_pct = pct
                                try:
                                    progress_cb(
                                        pct,
                                        f"{label} — {done // (1024 * 1024)} / "
                                        f"{total // (1024 * 1024)} MB")
                                except Exception:
                                    pass
            # A closed connection surfaces as a clean (empty) read, not an
            # exception — so an early EOF must be treated as a failure to
            # retry, or a truncated file silently becomes "the model".
            if total and done < total:
                raise IOError(f"connection closed early: got {done} of "
                              f"{total} bytes")
            os.replace(part, dest)
            return True
        except Exception as exc:
            logger.warning("download %s attempt %d/%d: %s",
                           label, attempt, max_attempts, exc)
            if attempt >= max_attempts:
                break
            if progress_cb:
                try:
                    progress_cb(lo, f"{label} — connection hiccup, "
                                    f"resuming ({attempt}/{max_attempts})…")
                except Exception:
                    pass
            time.sleep(min(2 ** attempt, 20))

    try:
        part.unlink(missing_ok=True)
    except Exception:
        pass
    return False


def download_and_install(progress_cb: ProgressCb = None) -> tuple[bool, str]:
    """Fetch llama-server and the model. Safe to re-run; skips what exists."""
    def emit(pct: int, msg: str):
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    LLM_DIR.mkdir(parents=True, exist_ok=True)

    # 1. llama-server (small, do it first so failures surface fast)
    version = _load_state().get("llama_version", "")
    if not _server_exe().exists():
        emit(2, "Looking up llama.cpp release…")
        url, version = _llamacpp_asset_url()
        if not url:
            return False, ("Could not reach GitHub to fetch the inference "
                           "engine. Check your connection and try again.")
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "llama.zip"
            emit(4, "Downloading inference engine…")
            if not _download(url, zip_path, progress_cb, 4, 12,
                             "Inference engine"):
                return False, "Failed to download the inference engine."
            emit(13, "Extracting inference engine…")
            try:
                BIN_DIR.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path) as z:
                    for member in z.namelist():
                        if member.endswith("/"):
                            continue
                        # The archive nests files under a build folder; we want
                        # llama-server.exe and its DLLs flat in bin/.
                        base = os.path.basename(member)
                        if not base:
                            continue
                        if base == "llama-server.exe" or base.endswith(".dll"):
                            with z.open(member) as src, \
                                    open(BIN_DIR / base, "wb") as dst:
                                shutil.copyfileobj(src, dst)
            except Exception as exc:
                return False, f"Could not extract the inference engine: {exc}"
        if not _server_exe().exists():
            return False, "The downloaded archive did not contain llama-server."

    # 2. the model (the big one)
    if not is_installed():
        emit(15, f"Downloading model ({MODEL_SIZE_MB} MB)…")
        if not _download(MODEL_URL, _model_path(), progress_cb, 15, 96,
                         "Model"):
            return False, ("Failed to download the model. Nothing was left "
                           "half-installed — you can retry safely.")

    emit(98, "Finishing up…")
    _save_state({"installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "llama_version": version,
                 "model": MODEL_NAME})
    emit(100, "Local AI ready")
    return True, "Local AI installed — it now answers without an internet connection."


def uninstall() -> tuple[bool, str]:
    """Remove the model and engine, freeing ~490 MB."""
    stop_server()
    try:
        if LLM_DIR.exists():
            shutil.rmtree(LLM_DIR, ignore_errors=True)
        return True, "Local AI removed (~490 MB freed)"
    except Exception as exc:
        return False, str(exc)


# ── server lifecycle ─────────────────────────────────────────────────────────

def is_server_running(timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(f"{BASE_URL}/health", headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def start_server(wait_seconds: int = 40) -> tuple[bool, str]:
    """Launch llama-server in the background and wait until it answers.

    Started with a small context and thread count: this runs alongside whatever
    the user is actually doing, so it must not monopolise the CPU.
    """
    global _proc
    if is_server_running():
        return True, "Local AI already running"
    if not is_installed():
        return False, "Local AI is not installed yet"

    try:
        cpu = os.cpu_count() or 4
        threads = max(2, min(4, cpu // 2))
        cmd = [str(_server_exe()),
               "-m", str(_model_path()),
               "--host", SERVER_HOST,
               "--port", str(SERVER_PORT),
               "-c", "4096",
               "-t", str(threads),
               "--no-warmup"]
        with _proc_lock:
            _proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_NO_WINDOW, cwd=str(BIN_DIR))
    except Exception as exc:
        return False, f"Could not start the local AI: {exc}"

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_server_running():
            return True, "Local AI ready"
        if _proc and _proc.poll() is not None:
            return False, "The local AI exited while starting up"
        time.sleep(0.7)
    return False, "The local AI did not start in time"


def stop_server() -> bool:
    global _proc
    with _proc_lock:
        p, _proc = _proc, None
    if p is None:
        return False
    try:
        p.terminate()
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
        return True
    except Exception:
        return False


def ensure_running(progress_cb: ProgressCb = None) -> tuple[bool, str]:
    """Start the server if it is installed but not up. Never downloads."""
    if is_server_running():
        return True, "ready"
    if not is_installed():
        return False, "not installed"
    if progress_cb:
        try:
            progress_cb(50, "Starting local AI…")
        except Exception:
            pass
    return start_server()


# ── inference ────────────────────────────────────────────────────────────────

def chat(messages: list[dict], max_tokens: int = 400,
         temperature: float = 0.3, timeout: int = 120
         ) -> tuple[Optional[str], Optional[str]]:
    """OpenAI-shaped chat call against the local server.

    Returns (content, error) — exactly the contract ai_agent's other providers
    use, so it slots into the existing fallback chain.
    """
    if not is_server_running():
        ok, msg = ensure_running()
        if not ok:
            return None, f"Local AI unavailable: {msg}"
    payload = json.dumps({
        "model": "local",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/v1/chat/completions", data=payload,
            headers={**_UA, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
        if content:
            return content.strip(), None
        return None, "Local AI returned an empty response"
    except Exception as exc:
        return None, f"Local AI error: {exc}"
