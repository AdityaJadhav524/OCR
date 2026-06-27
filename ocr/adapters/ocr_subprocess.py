"""
core/adapters/ocr_subprocess.py
────────────────────────────────
Subprocess bridge from the Python 3.13 main application to the
Python 3.11 + PaddleOCR 2.7.3 OCR environment.

Why this exists:
  PaddlePaddle 3.x crashes on Windows CPU (oneDNN / PIR executor bug).
  PaddlePaddle 2.x has no Python 3.13 wheels.
  Solution: run OCR in a dedicated Python 3.11 environment, communicate via JSON over stdout.

Contract:
  Caller:  document_router._extract_scanned()
  Input:   absolute path to a PDF file
  Output:  (full_text: str, pages: List[str])  — identical to what document_to_text() returns
  Errors:  RuntimeError  with descriptive message (timeout, bad JSON, non-zero exit, etc.)

The OCR environment is treated as a black box.
This file has NO knowledge of Paddle, PaddleOCR, or any OCR internals.
"""
import json
import logging
import os
import subprocess
from typing import List, Tuple

logger = logging.getLogger("ocr.adapters.ocr_subprocess")

# ── Configuration ──────────────────────────────────────────────────────────────
_WORKSPACE_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

# Python 3.11 interpreter inside the proven OCR environment.
# Override via env var OCR_PYTHON_EXECUTABLE for CI / alternative setups.
_OCR_PYTHON = os.environ.get(
    "OCR_PYTHON_EXECUTABLE",
    os.path.join(_WORKSPACE_ROOT, "ocr_legacy_env", "Scripts", "python.exe"),
)

# Subprocess entry point — runs inside the Python 3.11 env.
_EXTRACT_JSON_SCRIPT = os.path.join(_WORKSPACE_ROOT, "ocr_core", "extract_json.py")

# Hard timeout: total document execution (e.g. 5 minutes watchdog)
_TIMEOUT_SECONDS = 600


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_via_subprocess(pdf_path: str, password: str = None) -> Tuple[str, List[str], dict, list]:
    """
    Execute OCR in the isolated Python 3.11 + PaddleOCR 2.7.3 environment.

    Spawns:
        <ocr_legacy_env>/Scripts/python.exe  ocr_core/extract_json.py  <pdf_path>

    The subprocess writes a single JSON line to stdout:
        {"full_text": "...", "pages": ["...", ...]}

    This function validates the JSON, checks types, and returns the tuple
    (full_text, pages) which is the exact contract that document_to_text() returns.

    Args:
        pdf_path: Absolute path to the PDF file to process.

    Returns:
        Tuple of (full_text: str, pages: List[str], telemetry: dict, page_tokens: list).

    Raises:
        FileNotFoundError : pdf_path does not exist.
        FileNotFoundError : OCR python or script not found.
        TimeoutError      : subprocess exceeded _TIMEOUT_SECONDS.
        RuntimeError      : subprocess exited non-zero, produced no output,
                            or returned invalid/malformed JSON.
    """
    _validate_paths(pdf_path)

    logger.info(
        "ocr_subprocess: starting OCR worker for '%s'  (timeout=%ds)",
        os.path.basename(pdf_path), _TIMEOUT_SECONDS,
    )

    # ── Launch subprocess ──────────────────────────────────────────────────────
    cmd = [_OCR_PYTHON, _EXTRACT_JSON_SCRIPT, pdf_path]
    if password:
        cmd.append(password)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=600.0,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stderr_tail = ""
        if exc.stderr:
            stderr_tail = exc.stderr.decode("utf-8", errors="replace")[-2000:]
        raise TimeoutError(
            f"OCR subprocess timed out after 600.0s "
            f"processing '{os.path.basename(pdf_path)}'.\n"
            f"Stderr tail:\n{stderr_tail}\n"
            "Consider increasing OCR timeout or splitting the document."
        )

    # ── Check exit code ────────────────────────────────────────────────────────
    stderr_text = proc.stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        # Log the full stderr for debugging, then raise with a summary.
        logger.error(
            "ocr_subprocess: worker exited %d for '%s'.\nSTDERR:\n%s",
            proc.returncode, os.path.basename(pdf_path), stderr_text,
        )
        # Surface the last 600 chars of stderr in the exception message.
        stderr_tail = stderr_text[-600:] if len(stderr_text) > 600 else stderr_text
        raise RuntimeError(
            f"OCR subprocess failed (exit code {proc.returncode}) "
            f"for '{os.path.basename(pdf_path)}':\n{stderr_tail}"
        )

    # Log any warnings the OCR environment produced (paddle logs, etc.)
    if stderr_text:
        logger.debug("ocr_subprocess: worker stderr:\n%s", stderr_text)

    # ── Parse JSON from stdout ─────────────────────────────────────────────────
    stdout_raw = proc.stdout.decode("utf-8", errors="replace").strip()

    if not stdout_raw:
        raise RuntimeError(
            f"OCR subprocess produced no output for '{os.path.basename(pdf_path)}'. "
            f"stderr: {stderr_text[-300:]}"
        )

    try:
        result = json.loads(stdout_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"OCR subprocess returned invalid JSON for '{os.path.basename(pdf_path)}': {exc}. "
            f"stdout[:300]={stdout_raw[:300]!r}"
        ) from exc

    # ── Validate JSON structure ────────────────────────────────────────────────
    full_text   = result.get("full_text")
    pages       = result.get("pages")
    page_tokens = result.get("page_tokens", [])
    telemetry   = result.get("telemetry", {})

    if not isinstance(full_text, str):
        raise RuntimeError(
            f"OCR subprocess JSON missing/wrong-type 'full_text' "
            f"(got {type(full_text).__name__!r}) for '{os.path.basename(pdf_path)}'"
        )
    if not isinstance(pages, list):
        raise RuntimeError(
            f"OCR subprocess JSON missing/wrong-type 'pages' "
            f"(got {type(pages).__name__!r}) for '{os.path.basename(pdf_path)}'"
        )

    logger.info(
        "ocr_subprocess: OK — '%s' → %d page(s), %d chars, %d tokens (OCR time: %.2fs)",
        os.path.basename(pdf_path), len(pages), len(full_text), len(page_tokens), telemetry.get("total_ocr_time", 0.0)
    )
    return full_text, pages, telemetry, page_tokens


# ── Internal helpers ───────────────────────────────────────────────────────────

def _validate_paths(pdf_path: str) -> None:
    """Raise descriptive errors if any required path is missing."""
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not os.path.isfile(_OCR_PYTHON):
        raise FileNotFoundError(
            f"OCR Python interpreter not found: {_OCR_PYTHON}\n"
            "Ensure the ocr_legacy_env is set up:\n"
            "  C:\\Users\\adity\\AppData\\Local\\Programs\\Python\\Python311\\python.exe "
            "-m venv Z:\\CA\\ocr_legacy_env\n"
            "  Z:\\CA\\ocr_legacy_env\\Scripts\\pip install paddlepaddle==2.6.2 paddleocr==2.7.3\n"
            "Or set the OCR_PYTHON_EXECUTABLE environment variable."
        )

    if not os.path.isfile(_EXTRACT_JSON_SCRIPT):
        raise FileNotFoundError(
            f"OCR entry point not found: {_EXTRACT_JSON_SCRIPT}\n"
            "Expected: ocr_core/extract_json.py to exist in the workspace."
        )
