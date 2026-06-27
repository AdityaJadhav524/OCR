import re

with open("core/parsers/coordinate_parser_v2.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add value_date extraction
date_ext_start = content.find('    # --- Pass 0: Claim Date by merging tokens in date_zone ---')
date_ext_end = content.find('    # --- Phase B: Candidate-Based Zone Reconstruction ---')

value_date_addition = """    # --- Pass 0.5: Claim Value Date ---
    value_date = None
    value_date_zone = zones.get("value_date_zone")
    if value_date_zone:
        vd_candidates = []
        for idx, tok in enumerate(all_tokens):
            if _in_zone(tok["x0"], value_date_zone) and idx not in claimed:
                vd_candidates.append((idx, tok))
        
        if vd_candidates:
            for idx, tok in vd_candidates:
                d = _prove_date(tok, value_date_zone)
                if d:
                    value_date = d
                    claimed.add(idx)
                    break
            if not value_date:
                merged_vd_str = " ".join([t["text"] for _, t in vd_candidates])
                m = _DATE_RE.search(merged_vd_str)
                if m:
                    value_date = m.group(1)
                    for idx, _ in vd_candidates:
                        claimed.add(idx)
                else:
                    m2 = _DATE_PREFIX_RE.match(merged_vd_str)
                    if m2:
                        value_date = m2.group(1)
                        for idx, _ in vd_candidates:
                            claimed.add(idx)

"""

content = content[:date_ext_end] + value_date_addition + content[date_ext_end:]

# 2. Add value_date to candidate output
candidate_start = content.find('    candidate = {\n        "date":           date,\n        "narration":      narration,')
candidate_replacement = """    _evidence = {
        "candidate_count": len(_zone_candidates.get("debit", [])) + len(_zone_candidates.get("credit", [])) + len(_zone_candidates.get("balance", [])),
        "selected_candidates": {
            "debit": _zone_candidates.get("debit", [])[0] if _zone_candidates.get("debit") and debit is not None else None,
            "credit": _zone_candidates.get("credit", [])[0] if _zone_candidates.get("credit") and credit is not None else None,
            "balance": _zone_candidates.get("balance", [])[0] if _zone_candidates.get("balance") and balance is not None else None
        },
        "all_candidates": _zone_candidates,
        "ownership": ownership,
        "claimed_tokens": list(claimed)
    }

    candidate = {
        "date":           date,
        "value_date":     value_date,
        "narration":      narration,
        "_evidence":      _evidence,"""

content = content.replace('    candidate = {\n        "date":           date,\n        "narration":      narration,', candidate_replacement)

with open("core/parsers/coordinate_parser_v2.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched coordinate_parser_v2.py successfully!")
