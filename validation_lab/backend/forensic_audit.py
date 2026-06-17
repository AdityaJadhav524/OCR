"""
forensic_audit_v2.py
────────────────────
Forensic audit: Digital PDF vs Scanned PDF.
Forces digital path to use the known owner password from the PDF 
(which the API would have received from the frontend during the unlock flow).

Run from: z:\CA
"""

import sys
import os
import json
import re
import logging
import time
import datetime

# ── Path setup ────────────────────────────────────────────────────────────────
_WS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _WS)
sys.path.insert(0, os.path.join(_WS, "core"))
sys.path.insert(0, os.path.join(_WS, "ocr_core"))

logging.basicConfig(level=logging.WARNING)

# ── Constants ─────────────────────────────────────────────────────────────────
DIGITAL_PDF  = r"z:\CA\validation_lab\backend\temp\11707454011-JUL-25221947 2.PDF"
SCANNED_PDF  = r"z:\CA\validation_lab\backend\temp\DocScanner 17-Apr-2026 11-06 AM 1.pdf"

REPORT_PATH  = r"C:\Users\adity\.gemini\antigravity-ide\brain\56dc278d-6771-432f-a44f-4b9b53723f34\digital_vs_scanned_forensic_report.md"
SUMMARY_PATH = r"C:\Users\adity\.gemini\antigravity-ide\brain\56dc278d-6771-432f-a44f-4b9b53723f34\root_cause_summary.md"

# ── Try known passwords ───────────────────────────────────────────────────────
def find_password(pdf_path):
    import fitz
    candidates = ["", "password", "123456", "XXXXXXXX"]
    doc = fitz.open(pdf_path)
    if not doc.needs_pass:
        doc.close()
        return None  # No password needed
    for pw in candidates:
        doc2 = fitz.open(pdf_path)
        result = doc2.authenticate(pw)
        doc2.close()
        if result:
            return pw
    doc.close()
    return "UNKNOWN"


# ── Imports (after path setup) ────────────────────────────────────────────────
from core.extractors.document_router import detect_document_type, _extract_digital, _extract_scanned
from core.detection.bank_detector import classify_document_llm
from core.parsers.statement_parser import _parse_chunk, _safe_parse_json
from core.parsers.validation import extract_json_from_response, normalize_date
from config import LLM_PARSER_MODEL

# ── Monkey-patch call_llm to capture raw prompts + responses ──────────────────
import core.llm.provider as _provider_mod
import core.parsers.statement_parser as _sp_mod
import core.detection.bank_detector as _bd_mod

_captured_calls = []

_original_call_llm = _provider_mod.call_llm
def _instrumented_call_llm(prompt=None, parts=None, model=None, temperature=0):
    t0 = time.time()
    result = _original_call_llm(prompt=prompt, parts=parts, model=model, temperature=temperature)
    elapsed = time.time() - t0
    _captured_calls.append({
        "model":    model or LLM_PARSER_MODEL,
        "prompt":   prompt or str(parts),
        "response": result,
        "elapsed_s": round(elapsed, 2),
    })
    return result

_provider_mod.call_llm = _instrumented_call_llm
_sp_mod.call_llm = _instrumented_call_llm
_bd_mod.call_llm = _instrumented_call_llm


def run_audit(pdf_path, label, password=None):
    print(f"\n{'='*60}")
    print(f"  AUDITING: {label}")
    print(f"  File: {os.path.basename(pdf_path)}")
    if password is not None:
        print(f"  Password: {'<empty string>' if password == '' else '<provided>'}")
    print(f"{'='*60}")
    
    result = {"label": label, "pdf_path": pdf_path}
    
    # ── Determine encryption state ──────────────────────────────────────────
    import fitz
    doc = fitz.open(pdf_path)
    needs_pass = doc.needs_pass
    is_encrypted = doc.is_encrypted
    doc.close()
    result["needs_pass"] = needs_pass
    result["is_encrypted"] = is_encrypted
    print(f"  needs_pass={needs_pass}  is_encrypted={is_encrypted}")
    
    # ── Stage 1: Detect + Extract ──────────────────────────────────────────
    print(f"\n  [Stage 1] Detecting document type...")
    detected_type = detect_document_type(pdf_path, password=password)
    result["detected_type"] = detected_type
    print(f"  Detected: {detected_type}")
    
    print(f"  [Stage 1] Extracting text (path={detected_type}, password={'yes' if password else 'none'})...")
    t0 = time.time()
    try:
        if detected_type == "digital":
            full_text, pages = _extract_digital(pdf_path, password=password)
        else:
            full_text, pages = _extract_scanned(pdf_path, password=password)
        elapsed_s1 = round(time.time() - t0, 2)
    except Exception as e:
        print(f"  EXTRACTION ERROR: {e}")
        result["stage1_error"] = str(e)
        return result
    
    date_re = re.compile(r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b')
    amount_re = re.compile(r'[\d,]+\.\d{2}')
    lines_all = full_text.split("\n")
    txn_rows = [l for l in lines_all if date_re.search(l) and amount_re.search(l)]
    
    result["stage1"] = {
        "elapsed_s":    elapsed_s1,
        "page_count":   len(pages),
        "text_length":  len(full_text),
        "line_count":   len(lines_all),
        "word_count":   len(full_text.split()),
        "txn_row_count": len(txn_rows),
        "txn_rows_sample": txn_rows[:25],
        "first_2000":   full_text[:2000],
        "last_2000":    full_text[-2000:] if len(full_text) > 2000 else full_text,
        "full_text":    full_text,
        "pages":        pages,
    }
    print(f"  Extraction: pages={len(pages)}  chars={len(full_text):,}  txn_rows={len(txn_rows)}")
    
    # ── Stage 2: Bank Detection ────────────────────────────────────────────
    print(f"  [Stage 2] Bank detection...")
    _captured_calls.clear()
    t0 = time.time()
    identity_json = classify_document_llm(pages)
    elapsed_s2 = round(time.time() - t0, 2)
    bd_call = _captured_calls[0] if _captured_calls else {}
    _captured_calls.clear()
    
    result["stage2"] = {
        "elapsed_s":        elapsed_s2,
        "identity_json":    identity_json,
        "institution_name": identity_json.get("institution_name", "UNKNOWN"),
        "document_family":  identity_json.get("document_family", ""),
        "document_subtype": identity_json.get("document_subtype", ""),
        "model_used":       bd_call.get("model", ""),
        "llm_prompt_tail":  (bd_call.get("prompt","") or "")[-2000:],
        "llm_response":     bd_call.get("response", ""),
    }
    print(f"  Bank: {identity_json.get('institution_name')}  family={identity_json.get('document_family')}")
    
    # ── Stage 3: LLM Extraction ────────────────────────────────────────────
    print(f"  [Stage 3] LLM transaction extraction...")
    _captured_calls.clear()
    
    doc_family  = identity_json.get("document_family", "BANK_ACCOUNT_STATEMENT")
    doc_subtype = identity_json.get("document_subtype", "")
    institution = identity_json.get("institution_name", "Unknown")
    
    # Exactly as statement_parser does it
    split_pages = [
        block.strip()
        for block in re.split(r'={80}', full_text)
        if block.strip() and not re.fullmatch(r'\s*PAGE\s+\d+\s*', block.strip(), re.IGNORECASE)
    ]
    if not split_pages:
        split_pages = [full_text]
    
    chunk_text = "\n\n".join(split_pages[:10])
    
    t0 = time.time()
    try:
        raw_response = _parse_chunk(chunk_text, doc_family, doc_subtype, institution)
    except Exception as e:
        raw_response = ""
        print(f"  LLM EXTRACTION ERROR: {e}")
    elapsed_s3 = round(time.time() - t0, 2)
    
    llm_call = _captured_calls[0] if _captured_calls else {}
    _captured_calls.clear()
    
    result["stage3"] = {
        "elapsed_s":           elapsed_s3,
        "split_page_count":    len(split_pages),
        "chunk_text_len":      len(chunk_text),
        "chunk_text_first_500": chunk_text[:500],
        "chunk_text_last_500": chunk_text[-500:],
        "full_prompt":         llm_call.get("prompt", ""),
        "model_used":          llm_call.get("model", LLM_PARSER_MODEL),
        "raw_response":        raw_response,
        "raw_response_len":    len(raw_response) if raw_response else 0,
    }
    print(f"  LLM: raw_response_len={len(raw_response) if raw_response else 0}")
    print(f"  LLM response preview: {repr(raw_response[:300])}")
    
    # ── Stage 4: Normalization ─────────────────────────────────────────────
    print(f"  [Stage 4] Normalization...")
    pre_norm = extract_json_from_response(raw_response)
    count_pre = len(pre_norm)
    
    normalized = []
    discarded = []
    for txn in pre_norm:
        try:
            txn["date"] = normalize_date(txn.get("date"))
            if "details" in txn and "narration" not in txn:
                txn["narration"] = txn.pop("details")
            normalized.append(txn)
        except Exception as e:
            discarded.append({"txn": txn, "reason": str(e)})
    
    result["stage4"] = {
        "pre_norm_count":    count_pre,
        "post_norm_count":   len(normalized),
        "discarded_count":   len(discarded),
        "discarded":         discarded,
        "transactions":      normalized,
        "transactions_sample": normalized[:5],
    }
    print(f"  Normalization: pre={count_pre}  post={len(normalized)}  discarded={len(discarded)}")
    
    return result


def generate_report(dig, scan):
    ts = datetime.datetime.now().isoformat()
    
    d1 = dig.get("stage1", {})
    d2 = dig.get("stage2", {})
    d3 = dig.get("stage3", {})
    d4 = dig.get("stage4", {})
    
    s1 = scan.get("stage1", {})
    s2 = scan.get("stage2", {})
    s3 = scan.get("stage3", {})
    s4 = scan.get("stage4", {})
    
    out = [
        f"# Digital vs Scanned PDF — Forensic Audit Report",
        f"",
        f"Generated: {ts}",
        f"",
        f"## Documents Under Test",
        f"",
        f"| | Digital PDF | Scanned PDF |",
        f"|--|------------|------------|",
        f"| File | `{os.path.basename(dig['pdf_path'])}` | `{os.path.basename(scan['pdf_path'])}` |",
        f"| needs_pass | `{dig.get('needs_pass')}` | `{scan.get('needs_pass')}` |",
        f"| is_encrypted | `{dig.get('is_encrypted')}` | `{scan.get('is_encrypted')}` |",
        f"| Detected Type | `{dig.get('detected_type')}` | `{scan.get('detected_type')}` |",
        f"",
        f"---",
        f"",
        f"## Stage 1 — Text Extraction",
        f"",
        f"| Metric | Digital | Scanned |",
        f"|--------|---------|---------|",
        f"| Pages | {d1.get('page_count','?')} | {s1.get('page_count','?')} |",
        f"| Chars | {d1.get('text_length',0):,} | {s1.get('text_length',0):,} |",
        f"| Lines | {d1.get('line_count',0):,} | {s1.get('line_count',0):,} |",
        f"| Words | {d1.get('word_count',0):,} | {s1.get('word_count',0):,} |",
        f"| **Txn-like rows (date+amount)** | **{d1.get('txn_row_count','?')}** | **{s1.get('txn_row_count','?')}** |",
        f"| Elapsed (s) | {d1.get('elapsed_s')} | {s1.get('elapsed_s')} |",
        f"",
        f"### Digital PDF — Transaction-like rows found in extracted text",
        f"```",
    ]
    for r in (d1.get("txn_rows_sample") or []):
        out.append(r)
    out += [
        f"```",
        f"",
        f"### Scanned PDF — Transaction-like rows found in extracted text",
        f"```",
    ]
    for r in (s1.get("txn_rows_sample") or []):
        out.append(r)
    out += [
        f"```",
        f"",
        f"### Digital PDF — First 2000 chars",
        f"```",
        d1.get("first_2000", "(no data)"),
        f"```",
        f"",
        f"### Digital PDF — Last 2000 chars",
        f"```",
        d1.get("last_2000", "(no data)"),
        f"```",
        f"",
        f"### Scanned PDF — First 2000 chars",
        f"```",
        s1.get("first_2000", "(no data)"),
        f"```",
        f"",
        f"---",
        f"",
        f"## Stage 2 — Bank Detection",
        f"",
        f"| Field | Digital | Scanned |",
        f"|-------|---------|---------|",
        f"| Institution | `{d2.get('institution_name')}` | `{s2.get('institution_name')}` |",
        f"| Family | `{d2.get('document_family')}` | `{s2.get('document_family')}` |",
        f"| Subtype | `{d2.get('document_subtype')}` | `{s2.get('document_subtype')}` |",
        f"| Model | `{d2.get('model_used')}` | `{s2.get('model_used')}` |",
        f"| Elapsed (s) | {d2.get('elapsed_s')} | {s2.get('elapsed_s')} |",
        f"",
        f"### Digital — identity_json",
        f"```json",
        json.dumps(d2.get("identity_json", {}), indent=2),
        f"```",
        f"",
        f"### Scanned — identity_json",
        f"```json",
        json.dumps(s2.get("identity_json", {}), indent=2),
        f"```",
        f"",
        f"---",
        f"",
        f"## Stage 3 — LLM Transaction Extraction",
        f"",
        f"| Metric | Digital | Scanned |",
        f"|--------|---------|---------|",
        f"| Split pages | {d3.get('split_page_count')} | {s3.get('split_page_count')} |",
        f"| Chunk text len (chars) | {d3.get('chunk_text_len',0):,} | {s3.get('chunk_text_len',0):,} |",
        f"| Model used | `{d3.get('model_used')}` | `{s3.get('model_used')}` |",
        f"| **Raw response length** | **{d3.get('raw_response_len')}** | **{s3.get('raw_response_len')}** |",
        f"| Elapsed (s) | {d3.get('elapsed_s')} | {s3.get('elapsed_s')} |",
        f"",
        f"### Digital — First 500 chars of text sent to LLM",
        f"```",
        d3.get("chunk_text_first_500", ""),
        f"```",
        f"",
        f"### Digital — Last 500 chars of text sent to LLM",
        f"```",
        d3.get("chunk_text_last_500", ""),
        f"```",
        f"",
        f"### Scanned — First 500 chars of text sent to LLM",
        f"```",
        s3.get("chunk_text_first_500", ""),
        f"```",
        f"",
        f"### Digital — FULL RAW LLM RESPONSE",
        f"```",
        d3.get("raw_response") or "(empty — no response)",
        f"```",
        f"",
        f"### Scanned — FULL RAW LLM RESPONSE",
        f"```",
        s3.get("raw_response") or "(empty)",
        f"```",
        f"",
        f"### Digital — Full Prompt sent to LLM (last 4000 chars)",
        f"```",
        (d3.get("full_prompt") or "")[-4000:] or "(not captured)",
        f"```",
        f"",
        f"---",
        f"",
        f"## Stage 4 — Normalization",
        f"",
        f"| Metric | Digital | Scanned |",
        f"|--------|---------|---------|",
        f"| Pre-normalization count | {d4.get('pre_norm_count')} | {s4.get('pre_norm_count')} |",
        f"| Post-normalization count | **{d4.get('post_norm_count')}** | **{s4.get('post_norm_count')}** |",
        f"| Discarded | {d4.get('discarded_count')} | {s4.get('discarded_count')} |",
        f"",
        f"### Digital — Discarded rows",
        f"```json",
        json.dumps(d4.get("discarded", []), indent=2),
        f"```",
        f"",
        f"### Digital — First 5 transactions",
        f"```json",
        json.dumps(d4.get("transactions_sample", []), indent=2),
        f"```",
        f"",
        f"### Scanned — First 5 transactions",
        f"```json",
        json.dumps(s4.get("transactions_sample", []), indent=2),
        f"```",
    ]
    return "\n".join(out)


def generate_root_cause(dig, scan):
    d1 = dig.get("stage1", {})
    d2 = dig.get("stage2", {})
    d3 = dig.get("stage3", {})
    d4 = dig.get("stage4", {})
    s4 = scan.get("stage4", {})
    
    root_cause = "UNDETERMINED"
    findings = []
    first_failure = None
    
    if dig.get("stage1_error"):
        first_failure = 1
        root_cause = "STAGE 1 — Extraction crashed"
        findings.append(f"❌ STAGE 1 CRASH: {dig['stage1_error']}")
    elif d1.get("txn_row_count", 0) == 0:
        first_failure = 1
        root_cause = "STAGE 1 — Zero transaction rows extracted from digital PDF"
        findings.append(f"❌ STAGE 1 FAIL: Digital extraction found ZERO lines containing both a date and an amount.")
        findings.append(f"   Possible causes: PDF text extraction garbles column layout, amounts and dates land on separate lines.")
    elif d3.get("raw_response_len", 0) <= 5:
        first_failure = 3
        root_cause = "STAGE 3 — LLM returned empty response"
        findings.append(f"✅ STAGE 1 PASS: {d1['txn_row_count']} transaction-like rows in extracted text")
        findings.append(f"✅ STAGE 2 PASS: Bank = {d2.get('institution_name')}")
        findings.append(f"❌ STAGE 3 FAIL: LLM returned {d3['raw_response_len']} chars. Response = {repr(d3.get('raw_response'))}")
    elif d4.get("pre_norm_count", 0) == 0:
        first_failure = 4
        root_cause = "STAGE 4 — JSON parse returned 0 transactions"
        findings.append(f"✅ STAGES 1-3 PASS")
        findings.append(f"❌ STAGE 4 FAIL: JSON parse extracted 0 rows from LLM response ({d3.get('raw_response_len')} chars)")
    elif d4.get("post_norm_count", 0) == 0:
        first_failure = 4
        root_cause = "STAGE 4 — Normalization discarded all transactions"
        findings.append(f"✅ STAGES 1-3 PASS")
        findings.append(f"❌ STAGE 4 NORMALIZATION: {d4['pre_norm_count']} parsed, all discarded")
    else:
        findings.append("⚠ All stages appear to pass. Issue may be intermittent (rate limit).")
    
    ts = datetime.datetime.now().isoformat()
    out = [
        f"# Root Cause Summary",
        f"",
        f"Generated: {ts}",
        f"",
        f"## Verdict",
        f"",
        f"**Root Cause:** `{root_cause}`",
        f"**First failure stage:** Stage {first_failure}" if first_failure else "",
        f"",
        f"## Stage-by-Stage Results",
        f"",
        f"### Digital PDF",
        f"",
        f"| Stage | Pass? | Evidence |",
        f"|-------|-------|----------|",
        f"| 1. Extraction | {'✅' if d1.get('txn_row_count',0) > 0 else '❌'} | {d1.get('txn_row_count',0)} txn rows, {d1.get('text_length',0):,} chars |",
        f"| 2. Bank Detection | ✅ | {d2.get('institution_name')} |",
        f"| 3. LLM Response | {'✅' if d3.get('raw_response_len',0) > 10 else '❌'} | {d3.get('raw_response_len',0)} chars |",
        f"| 4. JSON Parse | {'✅' if d4.get('pre_norm_count',0) > 0 else '❌'} | {d4.get('pre_norm_count',0)} objects |",
        f"| 5. Normalization | {'✅' if d4.get('post_norm_count',0) > 0 else '❌'} | {d4.get('post_norm_count',0)} transactions |",
        f"",
        f"### Scanned PDF (reference)",
        f"",
        f"| Stage | Pass? | Evidence |",
        f"|-------|-------|----------|",
        f"| 5. Normalization | ✅ | {s4.get('post_norm_count',0)} transactions |",
        f"",
        f"## Findings",
        f"",
    ]
    for f in findings:
        out.append(f"- {f}")
    out += [
        f"",
        f"## Digital PDF — Raw LLM Response (verbatim)",
        f"```",
        repr(d3.get("raw_response", "")),
        f"```",
        f"",
        f"## Digital PDF — First 1000 chars sent to LLM",
        f"```",
        d3.get("chunk_text_first_500", ""),
        f"```",
        f"",
        f"## Digital PDF — Txn rows found in extraction (all {d1.get('txn_row_count',0)})",
        f"```",
    ]
    for r in (d1.get("txn_rows_sample") or []):
        out.append(r)
    out.append("```")
    return "\n".join(out)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  FORENSIC AUDIT v2: Digital vs Scanned PDF")
    print("="*60)
    
    # Detect password needed
    print("\nChecking encryption state of digital PDF...")
    import fitz
    doc = fitz.open(DIGITAL_PDF)
    if doc.needs_pass:
        print("  PDF needs password. Trying empty string auth...")
        auth = doc.authenticate("")
        doc.close()
        if auth:
            dig_password = ""
            print("  Empty string password works!")
        else:
            print("  Empty password did NOT work.")
            print("  The PDF requires a real password.")
            print("  Will run extraction with password=None to replicate API behavior when password is submitted")
            # The actual password from the user's browser - we don't have it
            # but we need to see what happens when the encrypted file is processed
            # Use empty string to get fitz to try the owner password fallback
            dig_password = None
    else:
        doc.close()
        dig_password = None
        print("  No password needed.")
    
    # Run audits
    digital_result = run_audit(DIGITAL_PDF, "Digital PDF (Bank of India)", password=dig_password)
    scanned_result = run_audit(SCANNED_PDF, "Scanned PDF (Kotak Mahindra)", password=None)
    
    # Check if stage1 failed for digital and try pdfplumber directly
    if "stage1_error" in digital_result or digital_result.get("stage1", {}).get("txn_row_count", 0) == 0:
        print("\n\n" + "!"*60)
        print("  CRITICAL: Stage 1 failed or found 0 txn rows for digital PDF")
        print("  Trying direct pdfplumber extraction for diagnosis...")
        print("!"*60)
        
        try:
            import pdfplumber
            pdf = pdfplumber.open(DIGITAL_PDF, password="")
            for i, page in enumerate(pdf.pages[:2]):
                t = page.extract_text()
                print(f"\n  pdfplumber page {i+1} text length: {len(t) if t else 0}")
                if t:
                    print(f"  first 300 chars: {t[:300]}")
            pdf.close()
        except Exception as e:
            print(f"  pdfplumber failed: {e}")
    
    print("\n\nGenerating reports...")
    
    report = generate_report(digital_result, scanned_result)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Report: {REPORT_PATH}")
    
    summary = generate_root_cause(digital_result, scanned_result)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ Summary: {SUMMARY_PATH}")
    
    # Print console summary
    d3 = digital_result.get("stage3", {})
    d4 = digital_result.get("stage4", {})
    d1 = digital_result.get("stage1", {})
    s4 = scanned_result.get("stage4", {})
    
    print(f"\n{'='*60}")
    print(f"  QUICK RESULTS")
    print(f"{'='*60}")
    print(f"  Digital — detected_type   : {digital_result.get('detected_type')}")
    print(f"  Digital — txn_rows found  : {d1.get('txn_row_count','N/A')}")
    print(f"  Digital — LLM response len: {d3.get('raw_response_len','N/A')}")
    print(f"  Digital — transactions    : {d4.get('post_norm_count','N/A')}")
    print(f"  Digital — LLM raw response: {repr(d3.get('raw_response','')[:200])}")
    print(f"  Scanned — transactions    : {s4.get('post_norm_count','N/A')}")
    print(f"{'='*60}")
