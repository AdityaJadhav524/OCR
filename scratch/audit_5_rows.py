import os
import json
from core.adapters.ocr_subprocess import extract_via_subprocess
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.ledger_truth import annotate_ledger_truth

def run_ground_truth_audit():
    pdf_path = r"Z:\CA\validation_lab\backend\temp\YESBANK_page-0001.pdf"
    
    print("### Phase 1D — Ground Truth Audit (YES Bank) ###\n")
    
    try:
        full_text, pages, telemetry, page_tokens = extract_via_subprocess(pdf_path)
        txns, tel = parse_with_coordinates(page_tokens)
        final_txns = annotate_ledger_truth(txns)
        
        for i, txn in enumerate(final_txns):
            suspicious = txn.get("suspicious_fields", {})
            for k, field_data in suspicious.items():
                reason = field_data.get("reason")
                if reason in ("POWER_OF_TEN_DRIFT", "SMALL_DIGIT_SUBSTITUTION"):
                    
                    lt = txn.get("ledger_truth", {})
                    prev_bal = lt.get("prev_balance")
                    exp_bal = lt.get("expected_balance")
                    diff = field_data.get("diff")
                    
                    if exp_bal is None:
                        # Attempt to calculate expected balance manually
                        debit = txn.get("debit", 0.0) or 0.0
                        credit = txn.get("credit", 0.0) or 0.0
                        exp_bal = round(prev_bal + credit - debit, 2) if prev_bal else "UNKNOWN"
                    
                    tokens = [t.get("text") for t in txn.get("_source_tokens", [])]
                    
                    print(f"Date:             {txn.get('date')}")
                    print(f"OCR Balance:      {txn.get('balance')}")
                    print(f"Previous Balance: {prev_bal}")
                    print(f"Debit:            {txn.get('debit')}")
                    print(f"Credit:           {txn.get('credit')}")
                    print(f"Expected Balance: {exp_bal}")
                    print(f"Diff:             {diff} ({reason})")
                    print(f"Tokens:           {tokens}")
                    print("-" * 60)
                    
    except Exception as e:
        print(f"Failed to process YES Bank: {e}")

if __name__ == "__main__":
    run_ground_truth_audit()
