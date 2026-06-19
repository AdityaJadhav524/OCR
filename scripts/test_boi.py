import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.extractors.document_router import route_document
from core.detection.bank_detector import classify_document_llm
from core.layout.structural_token_protection import protect_table_header_tokens
from core.detection.header_suppression import suppress_headers_and_footers
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.layout.column_detector import detect_columns

def main():
    pdf_path = os.path.abspath("validation_lab/backend/temp/JOB_20260618_121804_8C99_BOI_SAVINGS_DIGITAL.pdf")
    password = "1170AKSH"
    
    # EXACT API PIPELINE
    # 1. Extract
    full_text, pages, telemetry, page_tokens = route_document(pdf_path, password=password)
    
    # 2. Classify
    identity = classify_document_llm(pages)
    bank_name = identity.get("institution_name", "Unknown")
    
    # 3. Protect
    suppression_telemetry = {}
    page_tokens = protect_table_header_tokens(page_tokens, suppression_telemetry)
    
    header_row = None
    protected_tokens = 0
    if "protection_events" in suppression_telemetry and suppression_telemetry["protection_events"]:
        ev = suppression_telemetry["protection_events"][0]
        header_row = ev.get("protected_row")
        protected_tokens = len(ev.get("protected_tokens", []))
        
    # 4. Suppress
    page_tokens = suppress_headers_and_footers(page_tokens)
    
    # 5. Column Zones (extracted internally in parser, but we can verify it here)
    header_row_obj, zones = detect_columns(page_tokens)
    zones_created = len(zones) > 0
    
    # 6. Parse
    txns, parser_telemetry = parse_with_coordinates(page_tokens, bank=bank_name, identity=identity)
    
    rows_accepted = len(txns)
    abort_reason = None
    
    chosen_header_tokens = parser_telemetry.get("chosen_header")
    # Actually chosen_header is just the first token. The full row is not saved easily.
    # But wait, header_candidates is a list of tokens representing the header row.
    header_tokens = parser_telemetry.get("header_candidates", [])
    header_text = " ".join([t.get("text", "") for t in header_tokens]) if isinstance(header_tokens, list) else "Unknown"

    output = {
      "protected_header_row": header_row,
      "protected_tokens": protected_tokens,
      "detector_chosen_header_text": header_text,
      "zones_created": len(parser_telemetry.get("zones", {})) > 0,
      "parser_zones": parser_telemetry.get("zones"),
      "rows_detected": rows_accepted,
      "rows_accepted": rows_accepted,
      "abort_reason": parser_telemetry.get("abort_reason")
    }
    
    print("\n--- RESULTS ---")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
