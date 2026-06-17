import sys
import json

sys.path.insert(0, r"Z:\CA")
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.layout.row_detector import detect_rows

TOKENS_FILES = {
    "SBI": r"Z:\CA\scratch\latest_upload_tokens.json",
    "YES": r"Z:\CA\scratch\yes_tokens.json",
    "BOI": r"Z:\CA\scratch\boi_tokens.json"
}

def get_tokens(path):
    with open(path, "r", encoding="utf-8") as f:
        tokens = json.load(f)
    normalized = []
    for t in tokens:
        new_t = dict(t)
        if 'y1' in t and 'y2' in t and 'y0' not in t:
            new_t['y0'] = t['y1']; new_t['y1'] = t['y2']
            new_t['x0'] = t['x1']; new_t['x1'] = t['x2']
        new_t['page'] = t.get('page_number', t.get('page', 1))
        normalized.append(new_t)
    return normalized

def study():
    all_accepted_deltas = []
    all_rejected_deltas = []
    
    for bank, path in TOKENS_FILES.items():
        tokens = get_tokens(path)
        accepted, telemetry = parse_with_coordinates(tokens)
        
        zones = {}
        # Parse_with_coordinates doesn't return zones directly, it's in telemetry? No, it returns it in telemetry? 
        # Let's check: telemetry = {"v2_extracted_rows": ..., "zones_detected": list(zones.keys()), ...}
        # It doesn't return the zone bounds! We need to run detect_columns ourselves.
        from core.layout.column_detector import detect_columns
        rows = detect_rows(tokens)
        zones, _ = detect_columns(rows)
        if not zones or "date_zone" not in zones:
            print(f"[{bank}] skipped - no date zone")
            continue
            
        date_zone_left = zones["date_zone"][0]
        
        print(f"\n--- {bank} (date_zone_left={date_zone_left:.1f}) ---")
        
        # Analyze accepted rows (these include valid continuations)
        bank_acc_deltas = []
        for txn in accepted:
            bbox = txn.get("_source_bbox")
            if bbox:
                x0 = bbox[0]
                delta = x0 - date_zone_left
                bank_acc_deltas.append(delta)
                all_accepted_deltas.append((delta, bank, txn.get("narration", "")[:60]))
                
        if bank_acc_deltas:
            print(f"ACCEPTED (n={len(bank_acc_deltas)}): min_delta={min(bank_acc_deltas):.1f}, avg_delta={sum(bank_acc_deltas)/len(bank_acc_deltas):.1f}")
            
        # Analyze rejected rows (these include footers and headers)
        bank_rej_deltas = []
        for rej in telemetry.get("reject_log", []):
            bbox = rej.get("_source_bbox")
            if bbox:
                x0 = bbox[0]
                delta = x0 - date_zone_left
                bank_rej_deltas.append(delta)
                all_rejected_deltas.append((delta, bank, rej.get("block_text_snippet", "")[:60], rej.get("reject_reason")))
                
        if bank_rej_deltas:
            print(f"REJECTED (n={len(bank_rej_deltas)}): max_delta={max(bank_rej_deltas):.1f}, avg_delta={sum(bank_rej_deltas)/len(bank_rej_deltas):.1f}")

    print("\n=== GLOBAL DISTRIBUTIONS ===")
    
    print("\nTop 5 CLOSEST ACCEPTED rows to the left margin:")
    for d, b, t in sorted(all_accepted_deltas)[:5]:
        print(f"[{b}] delta: {d:>6.1f} | {t}")
        
    print("\nTop 5 FURTHEST REJECTED rows to the right:")
    for d, b, t, r in sorted(all_rejected_deltas, reverse=True)[:5]:
        print(f"[{b}] delta: {d:>6.1f} | [{r}] | {t}")

if __name__ == "__main__":
    study()
