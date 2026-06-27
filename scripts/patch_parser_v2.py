import re

with open("core/parsers/coordinate_parser_v2.py", "r", encoding="utf-8") as f:
    content = f.read()

generator_code = """
def generate_zone_candidates(tokens: list, zone_bounds: list, zone_type: str) -> list:
    if not zone_bounds:
        return []
        
    zone_tokens = []
    for idx, t in enumerate(tokens):
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

def _extract_block(
    block: List[Dict],
    zones: Dict[str, List[float]],
"""

content = re.sub(r'def _extract_block\(\s*block:\s*List\[Dict\],\s*zones:\s*Dict\[str,\s*List\[float\]\],\s*', generator_code, content)

# Check if injection succeeded
if 'def generate_zone_candidates' not in content:
    print("Injection 1 failed")
    sys.exit(1)

with open("core/parsers/coordinate_parser_v2.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patch successful!")
