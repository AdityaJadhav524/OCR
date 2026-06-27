import re
import sys

with open("core/parsers/coordinate_parser_v2.py", "r", encoding="utf-8") as f:
    content = f.read()

# We need to inject generate_zone_candidates right before _extract_block
generator_code = """
def generate_zone_candidates(tokens: list, zone_bounds: list, zone_type: str) -> list:
    if not zone_bounds:
        return []
        
    zone_tokens = []
    for idx, t in enumerate(tokens):
        # We need a quick in_zone check
        x0 = t.get("x0", -1)
        if zone_bounds[0] <= x0 <= zone_bounds[1]:
            zone_tokens.append((idx, t))
            
    if not zone_tokens:
        return []
        
    normalized = []
    _CR_DR_RE = re.compile(r'(CR|DR)$', re.IGNORECASE)
    for orig_idx, t in zone_tokens:
        text = t.get("text", "").strip()
        if not text:
            continue
        m = _CR_DR_RE.search(text)
        if m and text != m.group(1):
            numeric_part = text[:m.start()].strip()
            suffix_part = m.group(1)
            if numeric_part:
                normalized.append({"orig_idx": orig_idx, "text": numeric_part, "x0": t["x0"], "x1": t["x1"], "conf": t.get("confidence", 1.0)})
            normalized.append({"orig_idx": orig_idx, "text": suffix_part, "x0": t["x1"], "x1": t["x1"], "conf": t.get("confidence", 1.0)})
        else:
            normalized.append({"orig_idx": orig_idx, "text": text, "x0": t["x0"], "x1": t["x1"], "conf": t.get("confidence", 1.0)})
            
    from core.validators.financial_audit import _parse_float
    candidates = []
    n = len(normalized)
    
    for i in range(n):
        for j in range(i + 1, n + 1):
            window = normalized[i:j]
            merged_text = "".join(w["text"] for w in window)
            val = _parse_float(merged_text)
            
            if val is not None and val > 0:
                score = 0.0
                if j == n or (j == n - 1 and normalized[-1]["text"].upper() in ["CR", "DR"]):
                    score += 5.0
                if '.' in merged_text and merged_text.rsplit('.', 1)[1].isdigit():
                    score += 5.0
                if "CR" in merged_text.upper() or "DR" in merged_text.upper():
                    score += 4.0
                if (j - i) > 1:
                    score += 4.0
                avg_conf = sum(w.get("conf", 1.0) for w in window) / len(window)
                score += (avg_conf * 3.0)
                if re.search(r',\\d{3}\\.', merged_text) or re.search(r',\\d{3}$', merged_text):
                    score += 2.0
                if merged_text.count('.') > 1:
                    score -= 6.0
                if (j - i) == 1 and n > 1 and "CR" not in merged_text.upper() and "DR" not in merged_text.upper():
                    score -= 5.0
                    
                used_indices = list(set(w["orig_idx"] for w in window))
                candidates.append({
                    "zone": zone_type,
                    "raw_text": merged_text,
                    "value": val,
                    "score": score,
                    "claimed_tokens": used_indices
                })
                
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates

def _extract_block(row: Dict, zones: Dict) -> Dict:
"""

content = content.replace("def _extract_block(row: Dict, zones: Dict) -> Dict:", generator_code)

# Now find Pass 1 and replace it
pass1_start = content.find("    # --- Pass 1: Claim structural roles in priority order ---")
pass2_start = content.find("    # --- Pass 2: All unclaimed tokens → narration")

if pass1_start != -1 and pass2_start != -1:
    new_pass1 = """    # --- Phase B: Candidate-Based Zone Reconstruction ---
    ownership = {}
    
    # Track existing dates in ownership
    for idx in claimed:
        ownership[idx] = "date"
    
    # 1. Balance candidates
    balance_candidates = generate_zone_candidates(all_tokens, balance_zone, "balance")
    if balance_candidates:
        winner = balance_candidates[0]
        balance = winner["value"]
        _raw_balance_text = winner["raw_text"]
        for idx in winner["claimed_tokens"]:
            claimed.add(idx)
            ownership[idx] = "balance"
            
    # 2. Debit candidates
    debit_candidates = generate_zone_candidates(all_tokens, debit_zone, "debit")
    if debit_candidates:
        winner = debit_candidates[0]
        debit = winner["value"]
        ocr_amount = debit
        ocr_x = all_tokens[winner["claimed_tokens"][0]].get("x0") if winner["claimed_tokens"] else None
        assigned_column = "debit"
        _raw_debit_text = winner["raw_text"]
        for idx in winner["claimed_tokens"]:
            claimed.add(idx)
            ownership[idx] = "debit"
            
    # 3. Credit candidates
    credit_candidates = generate_zone_candidates(all_tokens, credit_zone, "credit")
    if credit_candidates:
        # Prevent stealing the same token if debit and credit zones overlap
        valid_credits = [c for c in credit_candidates if not any(idx in claimed for idx in c["claimed_tokens"])]
        if valid_credits:
            winner = valid_credits[0]
            credit = winner["value"]
            ocr_amount = credit
            ocr_x = all_tokens[winner["claimed_tokens"][0]].get("x0") if winner["claimed_tokens"] else None
            assigned_column = "credit"
            _raw_credit_text = winner["raw_text"]
            for idx in winner["claimed_tokens"]:
                claimed.add(idx)
                ownership[idx] = "credit"

    # Save candidates for telemetry
    _zone_candidates = {
        "balance": balance_candidates,
        "debit": debit_candidates,
        "credit": credit_candidates
    }
"""
    content = content[:pass1_start] + new_pass1 + content[pass2_start:]

# Inject ownership into raw_extraction
raw_extract_start = content.find('"parsed_balance":   balance,')
if raw_extract_start != -1:
    content = content.replace('"parsed_balance":   balance,', '"parsed_balance":   balance,\n        "ownership":        ownership,\n        "_zone_candidates": _zone_candidates,')

with open("core/parsers/coordinate_parser_v2.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched coordinate_parser_v2.py successfully!")
