import sys
import os
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))

from core.extractors.document_router import _extract_digital
from core.parsers.coordinate_parser_v2 import parse_with_coordinates
from core.detection.bank_detector import classify_document_llm

if __name__ == "__main__":
    file_path = r'C:\Users\adity\Downloads\DetailedStatement24-25 2.pdf'
    full_text, pages, merge_stats, page_tokens = _extract_digital(file_path)
    identity = classify_document_llm(pages)
    txns, telemetry = parse_with_coordinates(page_tokens, bank=identity.get("institution_name"), identity=identity)
    
    print(f"Total Transactions: {len(txns)}")
    
    reject_log = telemetry.get('reject_log', [])
    reasons = [r.get('reject_reason') for r in reject_log]
    print(f"Reject reasons count: {dict(Counter(reasons))}")
