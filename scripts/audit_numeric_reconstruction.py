"""
audit_numeric_reconstruction.py

Diagnostic script — NO code changes, pure evidence.

For every transaction row in a statement, prints the full numeric
reconstruction trace:
  1. Raw OCR tokens on the row
  2. Zone boundaries (balance / debit / credit)
  3. Tokens INSIDE each zone
  4. Tokens that fall just OUTSIDE each zone (near-miss — the key suspect)
  5. All candidates generated per zone (every window span)
  6. Winning candidate + its score
  7. Final float that goes into JSON

Run:
    python scripts/audit_numeric_reconstruction.py --pdf PATH_TO_PDF [--password PASS]

Output goes to stdout AND scripts/audit_output/<pdf_name>_numeric_audit.txt
"""

import argparse
import os
import sys
import re

# ── Path setup ──────────────────────────────────────────────────────────────
_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _ROOT)

from core.extractors.document_router import detect_document_type, _extract_digital, _extract_scanned, check_pdf_security
from core.layout.row_detector import detect_rows
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import generate_zone_candidates, _parse_float, _in_zone, _prove_date

# ── Constants ────────────────────────────────────────────────────────────────
NEAR_MISS_MARGIN = 15.0   # px: tokens within this margin of zone boundary count as "near miss"


def _fmt(v):
    if v is None:
        return "None"
    if isinstance(v, float):
        return f"{v:,.4f}"
    return str(v)


def _zone_str(z):
    if not z:
        return "NOT DETECTED"
    return f"[{z[0]:.1f} → {z[1]:.1f}]"


def audit_row(row_idx, tokens, zones, out_lines):
    def emit(msg=""):
        out_lines.append(msg)
        print(msg)

    balance_zone = zones.get("balance_zone")
    debit_zone   = zones.get("debit_zone")
    credit_zone  = zones.get("credit_zone")
    date_zone    = zones.get("date_zone")

    emit(f"\n{'='*72}")
    emit(f"ROW {row_idx:>4}  |  {len(tokens)} tokens")
    emit(f"{'='*72}")

    # ── 1. Raw tokens ─────────────────────────────────────────────────────
    emit("RAW OCR TOKENS:")
    for i, t in enumerate(tokens):
        text = t.get("text", "")
        x0   = t.get("x0", 0)
        x1   = t.get("x1", 0)
        conf = t.get("confidence", 1.0)
        emit(f"  [{i:02d}] x0={x0:7.1f}  x1={x1:7.1f}  conf={conf:.2f}  '{text}'")

    # ── 2. Zone boundaries ────────────────────────────────────────────────
    emit("")
    emit("ZONES:")
    emit(f"  date    = {_zone_str(date_zone)}")
    emit(f"  debit   = {_zone_str(debit_zone)}")
    emit(f"  credit  = {_zone_str(credit_zone)}")
    emit(f"  balance = {_zone_str(balance_zone)}")

    # ── 3 & 4. Tokens inside / near-miss each zone ───────────────────────
    for zone_name, zone in [("balance", balance_zone), ("debit", debit_zone), ("credit", credit_zone)]:
        if not zone:
            continue
        emit(f"\n  [{zone_name.upper()} ZONE {_zone_str(zone)}]")
        inside     = []
        near_miss  = []
        for i, t in enumerate(tokens):
            x0 = t.get("x0", -1)
            x1 = t.get("x1", -1)
            txt = t.get("text", "")
            if zone[0] <= x0 <= zone[1]:
                inside.append((i, txt, x0, x1))
            elif (x0 > zone[1]) and (x0 - zone[1] <= NEAR_MISS_MARGIN):
                near_miss.append((i, txt, x0, x1, "RIGHT of zone"))
            elif (x0 < zone[0]) and (zone[0] - x0 <= NEAR_MISS_MARGIN):
                near_miss.append((i, txt, x0, x1, "LEFT of zone"))
            # Also check x1 (right edge of token) falling just outside the left of zone
            elif (x1 > zone[1]) and (x1 - zone[1] <= NEAR_MISS_MARGIN):
                near_miss.append((i, txt, x0, x1, "right EDGE outside zone"))

        if inside:
            emit(f"    INSIDE ({len(inside)} tokens):")
            for i, txt, x0, x1 in inside:
                emit(f"      [{i:02d}] x0={x0:.1f}  '{txt}'")
        else:
            emit(f"    INSIDE: (none)")

        if near_miss:
            emit(f"    ⚠  NEAR-MISS ({len(near_miss)} tokens — just outside zone boundary):")
            for i, txt, x0, x1, side in near_miss:
                gap = abs(x0 - zone[1]) if "RIGHT" in side else abs(zone[0] - x0)
                emit(f"      [{i:02d}] x0={x0:.1f}  x1={x1:.1f}  gap={gap:.1f}px  [{side}]  '{txt}'")
        else:
            emit(f"    near-miss: (none)")

    # ── 5. All candidates per zone ────────────────────────────────────────
    for zone_name, zone in [("balance", balance_zone), ("debit", debit_zone), ("credit", credit_zone)]:
        if not zone:
            continue
        cands = generate_zone_candidates(tokens, zone, zone_name)
        emit(f"\n  [{zone_name.upper()} CANDIDATES — {len(cands)} total]")
        if not cands:
            emit("    (no candidates generated)")
            continue
        for ci, c in enumerate(cands[:8]):   # show top 8
            marker = "  WINNER →" if ci == 0 else "          "
            emit(f"  {marker}  score={c['score']:+.1f}  value={_fmt(c['value'])}  raw='{c['raw_text']}'  tokens={c['claimed_tokens']}")

        # ── 6. Winner detail ──────────────────────────────────────────────
        w = cands[0]
        emit(f"\n  {zone_name.upper()} WINNER:")
        emit(f"    raw_text        = '{w['raw_text']}'")
        emit(f"    value           = {_fmt(w['value'])}")
        emit(f"    score           = {w['score']:+.1f}")
        emit(f"    claimed_tokens  = {w['claimed_tokens']}")

        # ── 7. What _parse_float saw step-by-step ────────────────────────
        emit(f"\n  _parse_float trace for '{w['raw_text']}':")
        _trace_parse_float(w['raw_text'], emit)

    emit("")


def _trace_parse_float(val, emit):
    """Re-implement _parse_float with step-by-step logging."""
    from core.cleaners.balance_text_sanitizer import sanitize_balance_text

    text = str(val).strip()
    emit(f"    step 0 (input)     : '{text}'")

    text = sanitize_balance_text(text)
    emit(f"    step 1 (sanitize)  : '{text}'")
    if not text:
        emit(f"    → RESULT: None (empty after sanitize)")
        return

    text = re.sub(r'[^\d.,-]', '', text)
    emit(f"    step 2 (strip non-numeric) : '{text}'")

    # Comma-as-decimal fix
    if '.' not in text and ',' in text:
        last_comma_idx = text.rfind(',')
        if len(text) - last_comma_idx - 1 == 2:
            text = text[:last_comma_idx] + '.' + text[last_comma_idx+1:]
            emit(f"    step 3 (comma→decimal fix) : '{text}'")
        else:
            emit(f"    step 3 (no comma→decimal needed)")
    else:
        emit(f"    step 3 (no comma→decimal needed)")

    text = text.replace(',', '')
    emit(f"    step 4 (strip commas) : '{text}'")

    if text.count('.') > 1:
        parts = text.rsplit('.', 1)
        text = parts[0].replace('.', '') + '.' + parts[1]
        emit(f"    step 5 (multi-dot fix) : '{text}'")
    elif text.count('.') == 1:
        parts = text.split('.')
        decimal_len = len(parts[1])
        if decimal_len == 3:
            text = text.replace('.', '')
            emit(f"    step 5 (3-digit decimal → treat as thousands sep) : '{text}'")
        elif decimal_len == 5:
            text = parts[0] + parts[1][:3] + '.' + parts[1][3:]
            emit(f"    step 5 (5-digit decimal → split) : '{text}'")
        else:
            emit(f"    step 5 (decimal OK, len={decimal_len}) : '{text}'")
    else:
        emit(f"    step 5 (no decimal point)")

    m = re.search(r'-?\d+(?:\.\d+)?', text)
    if not m:
        emit(f"    → RESULT: None (no numeric match found)")
        return

    emit(f"    step 6 (regex match) : '{m.group()}'")
    result = float(m.group())
    emit(f"    → RESULT: {_fmt(result)}")

    # Flag suspicious truncation
    if val != str(result) and '.' in str(val):
        original_dec = str(val).split('.')[-1].rstrip('0') if '.' in str(val) else ''
        result_dec   = str(result).split('.')[-1].rstrip('0') if '.' in str(result) else ''
        if original_dec and result_dec and original_dec != result_dec:
            emit(f"    ⚠  DECIMAL MISMATCH: input had '.{original_dec}', output has '.{result_dec}'")


def run_audit(pdf_path: str, password: str = None):
    print(f"\nAuditing: {pdf_path}")
    print("=" * 72)

    # ── Security check ────────────────────────────────────────────────────
    from core.extractors.document_router import check_pdf_security
    sec = check_pdf_security(pdf_path, password)
    if sec["status"] == "PASSWORD_REQUIRED":
        print("ERROR: PDF is password-protected. Use --password.")
        sys.exit(1)
    if sec["status"] == "INVALID_PASSWORD":
        print("ERROR: Wrong password.")
        sys.exit(1)

    # ── OCR ───────────────────────────────────────────────────────────────
    doc_type, _ = detect_document_type(pdf_path, password)
    print(f"Document type: {doc_type}")

    if doc_type == "digital":
        full_text, pages, merge_stats, page_tokens = _extract_digital(pdf_path, password=password)
    else:
        full_text, pages, merge_stats, page_tokens = _extract_scanned(pdf_path, password=password)

    print(f"Tokens extracted: {len(page_tokens)}")

    # ── Row detection ─────────────────────────────────────────────────────
    rows = detect_rows(page_tokens)
    print(f"Rows detected: {len(rows)}")

    # ── Column detection ──────────────────────────────────────────────────
    zones, header_row = detect_columns(rows)
    print(f"\nDetected zones:")
    for k, v in zones.items():
        print(f"  {k}: {v}")

    if not zones:
        print("\nERROR: No zones detected — column detector failed. Aborting.")
        sys.exit(1)

    # ── Prepare output file ───────────────────────────────────────────────
    out_dir = os.path.join(_ROOT, "scripts", "audit_output")
    os.makedirs(out_dir, exist_ok=True)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(out_dir, f"{pdf_name}_numeric_audit.txt")

    out_lines = []
    out_lines.append(f"NUMERIC RECONSTRUCTION AUDIT: {pdf_path}")
    out_lines.append(f"Zones: {zones}")
    out_lines.append("")

    # ── Per-row audit ─────────────────────────────────────────────────────
    date_zone    = zones.get("date_zone")
    balance_zone = zones.get("balance_zone")
    debit_zone   = zones.get("debit_zone")
    credit_zone  = zones.get("credit_zone")

    _DATE_RE = re.compile(
        r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+\w{3}\s+\d{2,4})',
        re.IGNORECASE
    )

    skipped   = 0
    audited   = 0
    truncated = []   # rows where we suspect decimal truncation

    for row_idx, row in enumerate(rows):
        tokens = row.get("tokens", [])
        if not tokens:
            continue

        # Only audit rows that look like transaction rows (have a date token)
        row_text = " ".join(t.get("text", "") for t in tokens)
        if not _DATE_RE.search(row_text[:40]):
            skipped += 1
            continue

        audited += 1
        audit_row(row_idx, tokens, zones, out_lines)

        # ── Truncation detector ───────────────────────────────────────────
        # Check if any near-miss token is a 1-2 digit number that could be
        # a detached decimal fragment (e.g. "8" after "161835.1")
        for zone_name, zone in [("balance", balance_zone), ("debit", debit_zone), ("credit", credit_zone)]:
            if not zone:
                continue
            cands = generate_zone_candidates(tokens, zone, zone_name)
            if not cands:
                continue
            winner_text = cands[0]["raw_text"]
            winner_val  = cands[0]["value"]

            # Check for detached fragment: winner ends with a single decimal digit
            # and there's a 1-2 digit token just outside the right zone boundary
            if '.' in winner_text:
                decimal_part = winner_text.rsplit('.', 1)[-1]
                if len(decimal_part) == 1:   # only ONE digit after decimal → suspect
                    for t in tokens:
                        x0 = t.get("x0", -1)
                        txt = t.get("text", "").strip()
                        if (x0 > zone[1]) and (x0 - zone[1] <= NEAR_MISS_MARGIN):
                            if re.fullmatch(r'\d{1,2}', txt):
                                truncated.append({
                                    "row": row_idx,
                                    "zone": zone_name,
                                    "winner_raw": winner_text,
                                    "winner_val": winner_val,
                                    "fragment": txt,
                                    "fragment_x0": x0,
                                    "zone_right": zone[1],
                                    "gap_px": x0 - zone[1],
                                    "reconstructed": f"{winner_text}{txt}",
                                })

    # ── Summary ───────────────────────────────────────────────────────────
    summary = [
        "",
        "=" * 72,
        "TRUNCATION SUSPECTS",
        "=" * 72,
    ]
    if truncated:
        summary.append(f"Found {len(truncated)} rows where a decimal fragment may be outside zone:\n")
        for t in truncated:
            summary.append(
                f"  Row {t['row']:>4}  [{t['zone'].upper()}]  "
                f"winner='{t['winner_raw']}' ({t['winner_val']:.4f})  "
                f"fragment='{t['fragment']}' at x0={t['fragment_x0']:.1f}  "
                f"zone_right={t['zone_right']:.1f}  gap={t['gap_px']:.1f}px  "
                f"→ reconstructed='{t['reconstructed']}'"
            )
    else:
        summary.append("No truncation suspects found via zone-boundary analysis.")
        summary.append("(Truncation may be at OCR level — check raw text for single decimal digits.)")

    summary.append("")
    summary.append(f"Rows audited:  {audited}")
    summary.append(f"Rows skipped (non-transaction): {skipped}")

    for line in summary:
        out_lines.append(line)
        print(line)

    # ── Write file ────────────────────────────────────────────────────────
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

    print(f"\nFull audit written to: {out_path}")
    return truncated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit numeric reconstruction for a bank PDF")
    parser.add_argument("--pdf",      required=True, help="Path to the PDF file")
    parser.add_argument("--password", default=None,  help="PDF password if encrypted")
    args = parser.parse_args()

    suspects = run_audit(args.pdf, args.password)
    sys.exit(0 if not suspects else 1)
