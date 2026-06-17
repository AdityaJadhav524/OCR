import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.validators.financial_audit import _parse_float
from core.validators.ledger_truth import annotate_ledger_truth

def main():
    report_lines = []
    report_lines.append("# DECIMAL TRACE REPORT")
    report_lines.append("")
    report_lines.append("| STAGE | VALUE | FILE | FUNCTION |")
    report_lines.append("|-------|-------|------|----------|")
    
    # Target value to trace
    target_string = "81,510.17"
    
    # Stage 1: OCR token
    ocr_token = {"text": target_string, "x0": 500, "y0": 120, "page": 1, "x1": 550, "y1": 130}
    report_lines.append(f"| 1. OCR Token | `{ocr_token['text']}` | `paddle/mineru` | `OCR Engine` |")
    
    # Setup mock page context
    tokens = [
        # Headers
        {"text": "Date", "x0": 50, "y0": 100, "page": 1, "x1": 80, "y1": 110},
        {"text": "Narration", "x0": 150, "y0": 100, "page": 1, "x1": 200, "y1": 110},
        {"text": "Withdrawal", "x0": 300, "y0": 100, "page": 1, "x1": 350, "y1": 110},
        {"text": "Deposit", "x0": 400, "y0": 100, "page": 1, "x1": 450, "y1": 110},
        {"text": "Balance", "x0": 500, "y0": 100, "page": 1, "x1": 550, "y1": 110},
        
        # Row 1 (Seed row to make balance math valid)
        {"text": "01/01/2026", "x0": 50, "y0": 115, "page": 1, "x1": 100, "y1": 118},
        {"text": "Txn1", "x0": 150, "y0": 115, "page": 1, "x1": 200, "y1": 118},
        {"text": "0.00", "x0": 300, "y0": 115, "page": 1, "x1": 330, "y1": 118}, # Debit
        {"text": "0.00", "x0": 500, "y0": 115, "page": 1, "x1": 530, "y1": 118}, # 0.0 balance
        
        # Row 2 (Transaction with target token)
        {"text": "02/01/2026", "x0": 50, "y0": 120, "page": 1, "x1": 100, "y1": 130},
        {"text": "TestTxn", "x0": 150, "y0": 120, "page": 1, "x1": 200, "y1": 130},
        {"text": target_string, "x0": 400, "y0": 120, "page": 1, "x1": 450, "y1": 130}, # Credit of 81,510.17
        ocr_token # Balance of 81,510.17
    ]
    
    # Stage 2: Row detector token
    rows = detect_rows(tokens)
    target_tok = None
    for r in rows:
        for t in r['tokens']:
            if t['text'] == target_string:
                target_tok = t
    
    if target_tok:
        report_lines.append(f"| 2. Row Detector Token | `{target_tok['text']}` | `row_detector.py` | `detect_rows` |")
    else:
        report_lines.append(f"| 2. Row Detector Token | NOT FOUND | `row_detector.py` | `detect_rows` |")
    
    # Stage 3: Column detector token
    zones, _ = detect_columns(rows)
    report_lines.append(f"| 3. Column Zone | `[ {zones['balance_zone'][0]}, {zones['balance_zone'][1]} ]` | `column_detector.py` | `detect_columns` |")
    
    # Let's extract block
    blocks = detect_transaction_blocks(rows, date_x_bounds=zones.get("date_zone"))
    
    # Stage 4: coordinate_parser_v2 internal logic -> _prove_balance -> _parse_float
    # We call coordinate_parser_v2.parse_with_coordinates which does all this
    parsed_txns, telemetry = parse_with_coordinates(tokens, pdf_name="test.pdf", statement_id="test", job_id="test", bank="Test", pdf_type="digital", identity={"id": "Test"})
    
    if parsed_txns:
        # We need the one with 81,510.17
        txn = parsed_txns[-1]
        
        # Extracted Candidate (pre-ledger)
        report_lines.append(f"| 4. Candidate Txn | `debit={txn.get('debit')}, credit={txn.get('credit')}, balance={txn.get('balance')}` | `coordinate_parser_v2.py` | `_extract_block` |")
        
        # Financial audit happens inside _extract_block
        report_lines.append(f"| 5. coordinate_parser_v2 | `balance={txn.get('balance')} (type: {type(txn.get('balance')).__name__})` | `coordinate_parser_v2.py` | `parse_with_coordinates` |")
        report_lines.append(f"| 6. financial_audit | `_parse_float('{target_string}') -> {_parse_float(target_string)}` | `financial_audit.py` | `_parse_float` |")
        
        # Stage 7: ledger truth
        # It's already applied by parse_with_coordinates at the end.
        report_lines.append(f"| 7. ledger_truth | `curr_balance={txn.get('raw_extraction', {}).get('parsed_balance')}` | `ledger_truth.py` | `annotate_ledger_truth` |")
        
        # Stage 8: API response JSON
        # Simulate JSON dump
        json_dump = json.dumps({"balance": txn.get("balance")})
        report_lines.append(f"| 8. API JSON | `{json_dump}` | `api.py` | `JSONResponse` |")
        
        # Stage 9: Frontend
        # Frontend renders string value
        bal = txn.get('balance')
        rendered = f"{bal if bal is not None else '—'}"
        report_lines.append(f"| 9. Frontend render | `{rendered}` | `App.tsx` | `TableCell` |")
    else:
        report_lines.append("| ERROR | Extraction failed in mock | | |")
        if telemetry.get("reject_log"):
            report_lines.append(f"| REASON | {telemetry['reject_log'][0]['reject_reason']} | | |")
    
    output_path = r"C:\Users\adity\.gemini\antigravity-ide\brain\a91c24b3-da82-413c-9098-5cc87be0fb55\DECIMAL_TRACE.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    main()
