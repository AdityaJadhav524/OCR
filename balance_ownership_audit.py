import sys, os, json, logging, glob, re
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.WARNING)

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.extractors.document_router import route_document, detect_document_type
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import _parse_float

CORPUS_DIR  = ROOT / "tests" / "truth_corpus"
TEMP_DIR    = ROOT / "validation_lab" / "backend" / "temp"

def find_latest_temp_file(corpus_file: str):
    pattern = str(TEMP_DIR / f"*{corpus_file}")
    matches = glob.glob(pattern)
    if not matches:
        exact = TEMP_DIR / corpus_file
        if exact.exists(): return exact
        return None
    return Path(sorted(matches, key=os.path.getmtime)[-1])

def audit_balance_ownership():
    truth_files = sorted(CORPUS_DIR.glob("*.json"))
    
    results = []
    
    for tf in truth_files:
        truth = json.loads(tf.read_text(encoding="utf-8"))
        pdf_name = truth.get("corpus_file", "")
        bank = truth.get("bank", "Unknown")
        pdf_type = truth.get("type", "digital")
        
        if not pdf_name: continue
        
        pdf_path = find_latest_temp_file(pdf_name)
        if not pdf_path:
            print(f"[{bank}] PDF NOT FOUND: {pdf_name}")
            continue
            
        print(f"Processing: {bank} - {pdf_name}")
        
        try:
            doc_type, _ = detect_document_type(str(pdf_path))
            full_text, pages, tel, page_tokens = route_document(str(pdf_path))
            identity = classify_document_llm(pages)
            detected_pdf_type = "SCANNED" if doc_type == "scanned" else "DIGITAL"
            
            txns, parser_tel = parse_with_coordinates(
                page_tokens,
                pdf_name=pdf_name,
                statement_id="audit",
                job_id="audit",
                bank=bank,
                pdf_type=detected_pdf_type,
                identity=identity
            )
            
            rejects = parser_tel.get("reject_log", [])
            
            # Combine accepted and rejected rows for full row audit
            all_rows = []
            for t in txns:
                t["_audit_status"] = "ACCEPTED"
                all_rows.append(t)
            for r in rejects:
                r["_audit_status"] = "REJECTED"
                all_rows.append(r)
                
            # Sort by evidence id or page/y to keep order
            all_rows.sort(key=lambda x: x.get("_evidence_id", ""))
            
            for row in all_rows:
                tokens = row.get("_source_tokens", [])
                tokens = sorted(tokens, key=lambda tk: tk.get("x0", 0))
                
                raw_ex = row.get("raw_extraction", {})
                parsed_balance = raw_ex.get("parsed_balance")
                parsed_debit = raw_ex.get("parsed_debit")
                parsed_credit = raw_ex.get("parsed_credit")
                
                ocr_balance_text = raw_ex.get("ocr_balance_text")
                ocr_debit_text = raw_ex.get("ocr_debit_text")
                ocr_credit_text = raw_ex.get("ocr_credit_text")
                
                balance_parsed = (parsed_balance is not None)
                balance_visible = False
                claimed_by = "none"
                
                # Find all numeric tokens
                numeric_tokens = []
                for tk in tokens:
                    text = tk.get("text", "").strip()
                    if '/' in text or '\\' in text: continue # date
                    if re.match(r'^\d{1,2}[A-Za-z]{3}\d{2,4}$', text): continue # date
                    val = _parse_float(text)
                    if val is not None and val > 0:
                        numeric_tokens.append({"text": text, "val": val, "x0": tk.get("x0")})
                        
                # If we successfully parsed a balance, we know it's visible and claimed by balance zone
                if balance_parsed:
                    balance_visible = True
                    claimed_by = "balance_zone"
                else:
                    # Balance wasn't parsed. Was it visible?
                    if numeric_tokens:
                        rightmost = numeric_tokens[-1]
                        balance_visible = True
                        
                        if ocr_credit_text and rightmost["text"] in ocr_credit_text:
                            claimed_by = "credit_zone"
                        elif ocr_debit_text and rightmost["text"] in ocr_debit_text:
                            claimed_by = "debit_zone"
                        else:
                            claimed_by = "narration_or_unclaimed"
                    else:
                        balance_visible = False
                        claimed_by = "none"
                        
                row_data = {
                    "bank": bank,
                    "pdf_name": pdf_name,
                    "status": row.get("_audit_status"),
                    "reject_reason": row.get("reject_reason", "ok"),
                    "balance_visible": balance_visible,
                    "balance_parsed": balance_parsed,
                    "claimed_by": claimed_by,
                    "numeric_tokens_count": len(numeric_tokens),
                    "text_snippet": " ".join([tk.get("text", "") for tk in tokens])
                }
                results.append(row_data)
        except Exception as e:
            print(f"[{bank}] Error processing {pdf_name}: {e}")

    # Analyze failure modes
    print("\n--- BALANCE OWNERSHIP AUDIT RESULTS ---")
    
    total = len(results)
    parsed = sum(1 for r in results if r["balance_parsed"])
    visible_not_parsed = sum(1 for r in results if r["balance_visible"] and not r["balance_parsed"])
    not_visible = sum(1 for r in results if not r["balance_visible"])
    
    print(f"Total Rows Analyzed: {total}")
    print(f"Balance Parsed: {parsed}")
    print(f"Balance Visible but NOT Parsed: {visible_not_parsed}")
    print(f"Balance NOT Visible: {not_visible}")
    
    print("\n--- CLAIMED BY (For Visible but NOT Parsed) ---")
    claimed_counts = Counter(r["claimed_by"] for r in results if r["balance_visible"] and not r["balance_parsed"])
    for claimer, count in claimed_counts.items():
        print(f"  {claimer}: {count}")
        
    print("\n--- FAILURE MODES (Visible but NOT Parsed) ---")
    for bank in sorted(set(r["bank"] for r in results)):
        bank_fails = [r for r in results if r["bank"] == bank and r["balance_visible"] and not r["balance_parsed"]]
        if bank_fails:
            print(f"\n{bank}: {len(bank_fails)} rows")
            claimers = Counter(r["claimed_by"] for r in bank_fails)
            reasons = Counter(r["reject_reason"] for r in bank_fails)
            print(f"  Claimed by: {dict(claimers)}")
            print(f"  Reject reasons: {dict(reasons)}")
            # Show a few examples
            for ex in bank_fails[:3]:
                print(f"    Ex: [{ex['claimed_by']}] {ex['text_snippet']}")

if __name__ == "__main__":
    audit_balance_ownership()
