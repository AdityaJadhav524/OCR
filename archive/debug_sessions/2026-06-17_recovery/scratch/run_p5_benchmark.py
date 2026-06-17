import os
import sys
import glob
import json
import time

# Add root to sys.path
_WORKSPACE_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _WORKSPACE_ROOT)
if os.path.join(_WORKSPACE_ROOT, "core") not in sys.path:
    sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "core"))
if os.path.join(_WORKSPACE_ROOT, "ocr_core") not in sys.path:
    sys.path.insert(0, os.path.join(_WORKSPACE_ROOT, "ocr_core"))

from core.adapters.ocr_subprocess import extract_via_subprocess
from core.detection.bank_detector import classify_document_llm
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth
from core.parsers.credit_card_parser import parse_credit_card_transactions

JOB_PREFIX = "JOB_20260614_233121_48AC"
EXPECTED_BANKS = {
    "AccountStatement_02022026": "SBI",
    "YESBANK": "YES BANK",
    "Acct Statement_3644": "HDFC",
    "axis": "AXIS",
    "CC_STMT": "INDUSIND",
    "DocScanner 17-Apr-2026 11-06": "BOI",
    "DocScanner 17-Apr-2026 11-07": "TJSB",
    "E_STATEMENT": "UNKNOWN",
    "SavingAccountStatement": "UNKNOWN",
    "24-25 -2": "UNKNOWN"
}

def get_expected_bank(filename):
    for k, v in EXPECTED_BANKS.items():
        if k in filename: return v
    return "UNKNOWN"
PDF_DIR = r"Z:\CA\validation_lab\backend\temp"
pdfs = glob.glob(os.path.join(PDF_DIR, f"{JOB_PREFIX}*.pdf"))

print(f"P5 Benchmark: Running {len(pdfs)} PDFs")
def classify_result(metrics, is_cc):
    # Rules
    # PASS: Rejects = 0, Contam = 0, HeaderLeaks = 0, Fallback = No, Primary <= 2
    # REVIEW: Rejects <= 3, Fallback used, Primary > 2
    # FAIL: Txn loss, mass rejects, wrong CC routing
    
    if is_cc:
        # Simplistic proxy for CC fail
        if metrics["txns"] == 0: return "FAIL"
        if metrics["fallback"]: return "REVIEW"
        return "PASS"
        
    if metrics["txns"] == 0:
        return "FAIL"
    if metrics["rejects"] == 0 and metrics["contam"] == 0 and metrics["header_leaks"] == 0 and not metrics["fallback"] and metrics["primary_anomalies"] <= 2:
        return "PASS"
    if metrics["rejects"] <= 3 or metrics["fallback"] or metrics["primary_anomalies"] > 2:
        if metrics["rejects"] > 5 or metrics["contam"] > 2:
            return "FAIL"
        return "REVIEW"
    return "FAIL"

def process_pdf(pdf_path):
    print(f"\nProcessing {os.path.basename(pdf_path)}")
    try:
        t0 = time.time()
        
        # 1. OCR
        print("  Running OCR...")
        try:
            full_text, pages_text, telemetry, tokens = extract_via_subprocess(pdf_path)
        except TimeoutError:
            return {
                "pdf_name": os.path.basename(pdf_path),
                "error": {
                    "status": "TIMEOUT",
                    "stage": "OCR",
                    "elapsed": 120
                }
            }
        
        if not pages_text:
            return {"error": "OCR failed or returned 0 pages"}
        
        # 2. Bank Detection
        print("  Detecting Bank...")
        time.sleep(2) # Avoid rate limits
        identity = {}
        for attempt in range(3):
            try:
                identity = classify_document_llm(pages_text)
                break
            except Exception as e:
                print(f"    Bank detect failed (attempt {attempt}): {e}")
                time.sleep(5)
        bank_name = identity.get("institution_name", "UNKNOWN")
        is_cc = identity.get("is_credit_card", False) or "_CC_" in pdf_path.upper()
        
        print(f"  Detected: {bank_name} (CC: {is_cc})")
        
        fallback_used = False
        fallback_reason = ""
        txns = []
        tel = {}
        
        # 3. Extraction
        if is_cc:
            print("  Using Credit Card Parser...")
            txns, tel = parse_credit_card_transactions(tokens)
            fallback_used = False
        else:
            print("  Running V2 Parser...")
            try:
                txns, tel = parse_with_coordinates(tokens)
                print(f"  V2 rows extracted = {len(txns)}")
            except Exception as e:
                print(f"  V2 crashed: {e}")
                txns, tel = [], {}
                fallback_reason = "V2_CRASH"
                
            if len(txns) == 0:
                print("  V2 returned 0 rows. Fallback to V1...")
                print("  fallback reason = ZERO_ROWS")
                fallback_used = True
                fallback_reason = fallback_reason or "ZERO_ROWS"
                # V1 fallback
                from core.parsers.statement_parser import parse_with_llm
                v1_resp = parse_with_llm(full_text, identity)
                txns = v1_resp.get("transactions", [])
                tel = {"contaminated_rows": 0, "reject_log": []}
        
        # 4. Audit
        if not is_cc and len(txns) > 0:
            print("  Running Ledger Audit...")
            try:
                txns = annotate_ledger_truth(txns)
            except Exception as e:
                print(f"  Audit crashed: {e}")
                
        # Calculate Metrics
        rejects = len(tel.get("reject_log", []))
        contam = tel.get("contaminated_rows", 0)
        
        header_leaks = 0
        primary_anomalies = 0
        downstream = 0
        
        if not is_cc:
            for t in txns:
                for f, sig in t.get("suspicious_fields", {}).items():
                    r = sig.get("reason", "")
                    if r in ("POWER_OF_TEN_DRIFT", "SMALL_DIGIT_SUBSTITUTION", "PRIMARY_BALANCE_ANOMALY"):
                        primary_anomalies += 1
                    elif r == "DOWNSTREAM_CHAIN_EFFECT":
                        downstream += 1
            
            # Simple heuristic for header leaks if not caught by contamination tracking
            for t in txns:
                nar = t.get("narration", "").upper()
                if "PAGE" in nar or "IFSC" in nar or "MICR" in nar or "STATEMENT" in nar:
                    header_leaks += 1
                    
        metrics = {
            "txns": len(txns),
            "rejects": rejects,
            "contam": contam,
            "primary_anomalies": primary_anomalies,
            "downstream": downstream,
            "fallback": fallback_used,
            "fallback_reason": fallback_reason,
            "ledger_pass": (primary_anomalies == 0) if not is_cc else None,
            "header_leaks": header_leaks,
            "confidence": None # assigned via classify_result
        }
        
        metrics["confidence"] = classify_result(metrics, is_cc)
        
        return {
            "pdf_name": os.path.basename(pdf_path),
            "bank": bank_name,
            "is_cc": is_cc,
            "metrics": metrics,
            "transactions": txns,
            "time_s": round(time.time() - t0, 1)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "pdf_name": os.path.basename(pdf_path),
            "error": {
                "status": "EXCEPTION",
                "stage": "PIPELINE",
                "details": str(e)
            }
        }

def save_results(results_dict):
    with open("Z:/CA/validation_lab/backend/temp/p5_raw_results.json", "w", encoding="utf-8") as f:
        json.dump(results_dict, f, indent=2)

    md = "# P5 Validation Matrix\n\n"
    md += "| PDF | Expected | Detected | Correct | CC | Txns | Rejects | Contam | Pri. Anomalies | Downstream | Fallback | Reason | Ledger | Leaks | Status |\n"
    md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"

    for p in pdfs:
        bname = os.path.basename(p)
        r = results_dict.get(bname)
        if not r: continue
        exp_bank = get_expected_bank(bname)
        if "error" in r:
            err = r["error"]
            err_str = err.get('status') if isinstance(err, dict) else "ERROR"
            md += f"| {bname} | {exp_bank} | - | - | - | - | - | - | - | - | - | - | - | - | **{err_str}** |\n"
            continue
        
        m = r["metrics"]
        det_bank = r['bank']
        
        # Simple string inclusion logic for classification correctness
        is_correct = "❌"
        if exp_bank != "UNKNOWN" and exp_bank.upper() in det_bank.upper():
            is_correct = "✅"
        elif exp_bank == "SBI" and "STATE BANK" in det_bank.upper():
            is_correct = "✅"
            
        lp = "N/A" if r["is_cc"] else ("PASS" if m["ledger_pass"] else "FAIL")
        fb_reason = m.get('fallback_reason', '')
        fb_str = "Yes" if m['fallback'] else "No"
        
        md += f"| {bname} | {exp_bank} | {det_bank} | {is_correct} | {r['is_cc']} | {m['txns']} | {m['rejects']} | {m['contam']} | {m['primary_anomalies']} | {m['downstream']} | {fb_str} | {fb_reason} | {lp} | {m['header_leaks']} | **{m['confidence']}** |\n"

    with open("Z:/CA/validation_lab/backend/temp/p5_matrix.md", "w", encoding="utf-8") as f:
        f.write(md)

results = {}
for p in pdfs:
    res = process_pdf(p)
    results[os.path.basename(p)] = res
    save_results(results)

print("\nDone. Saved to validation_lab/backend/temp/p5_matrix.md")
