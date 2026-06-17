"""
ocr_core/extract_json.py
────────────────────────
Subprocess entry point for the OCR pipeline.

MUST run inside the Python 3.11 + PaddleOCR 2.7.3 environment:
    Z:\\CA\\ocr_legacy_env\\Scripts\\python.exe extract_json.py <pdf_path>

Contract:
  stdin  : nothing
  stdout : one line of UTF-8 JSON:
               {"full_text": "...", "pages": ["...", "..."]}
           NOTHING else — any extra text will break json.loads() in the caller.
  stderr : all logging, PaddleOCR warnings, and error tracebacks
  exit 0 : success (JSON written to stdout)
  exit 1 : failure  (traceback written to stderr, nothing on stdout)

This script is called exclusively by core/adapters/ocr_subprocess.py.
Do NOT run it manually in the Python 3.13 environment — it will crash.
"""
import json
import logging
import os
import sys

# ── Resolve workspace paths ────────────────────────────────────────────────────
_THIS_DIR      = os.path.dirname(os.path.abspath(__file__))  # ocr_core/
_WORKSPACE     = os.path.dirname(_THIS_DIR)                  # Z:\CA\

# Extend sys.path so all sibling packages resolve correctly.
for _p in [_THIS_DIR, _WORKSPACE, os.path.join(_WORKSPACE, "core")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Argument validation ────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    sys.stderr.write("extract_json.py: ERROR — usage: python extract_json.py <pdf_path>\n")
    sys.exit(1)

PDF_PATH = sys.argv[1]
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else None

if not os.path.isfile(PDF_PATH):
    sys.stderr.write(f"extract_json.py: ERROR — file not found: {PDF_PATH}\n")
    sys.exit(1)

# ── Silence all logging to stderr (never stdout) ──────────────────────────────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
# logging.disable(logging.DEBUG)   # suppress DEBUG/INFO; WARNING+ still shows on stderr

# ── Redirect stdout → stderr during OCR execution ─────────────────────────────
# PaddleOCR and its dependencies occasionally call print() directly.
# Redirecting sys.stdout → sys.stderr ensures no stray text contaminates
# the JSON we write at the very end.
_real_stdout = sys.stdout
sys.stdout   = sys.stderr

try:
    # ── Load pipeline and adapter (imports paddle, cv2, etc.) ─────────────────
    from pipeline import run_pipeline                          # ocr_core/pipeline.py
    from core.adapters.ocr_adapter import document_to_text    # core/adapters/ocr_adapter.py

    # ── Read PDF bytes ─────────────────────────────────────────────────────────
    with open(PDF_PATH, "rb") as fh:
        file_bytes = fh.read()

    filename = os.path.basename(PDF_PATH)

    # ── Run OCR pipeline ───────────────────────────────────────────────────────
    doc = run_pipeline(file_bytes=file_bytes, filename=filename, password=PASSWORD)

    # ── Convert Document → (full_text, pages, page_tokens) ─────────────────────────────────
    full_text, pages, page_tokens = document_to_text(doc)

except Exception as exc:
    # Write traceback to stderr, nothing to stdout.
    import traceback
    sys.stderr.write(f"extract_json.py: PIPELINE ERROR — {exc}\n")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

finally:
    # Always restore real stdout before we write JSON.
    sys.stdout = _real_stdout

# ── Emit result as JSON on stdout ─────────────────────────────────────────────
# This is the ONLY write to stdout in the entire script.
result = {
    "full_text": full_text,
    "pages":     pages,
    "page_tokens": page_tokens,
    "telemetry": getattr(doc, "telemetry", {})
}
sys.stdout.write(json.dumps(result, ensure_ascii=False))
sys.stdout.flush()
sys.exit(0)
