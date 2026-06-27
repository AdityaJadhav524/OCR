"""
test_decimal_truncation.py

Proves or disproves the zone-boundary truncation hypothesis:
  OCR returns "161835.1" (inside zone) and "8" (just outside zone right edge)
  → generate_zone_candidates only sees the inside token
  → winner is "161835.1" instead of "161835.18"

Also tests the _parse_float "5-digit decimal" branch that could cause
the "413534.10 → 413534.1" bug.
"""
import sys
import os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from core.parsers.coordinate_parser_v2 import generate_zone_candidates, _parse_float

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def make_token(text, x0, x1=None, conf=1.0):
    if x1 is None:
        x1 = x0 + len(text) * 6   # rough pixel width estimate
    return {"text": text, "x0": x0, "x1": x1, "confidence": conf, "y0": 100, "y1": 115}


# ===========================================================================
# Zone-boundary truncation hypothesis
# ===========================================================================
class TestZoneBoundaryTruncation:

    def test_fragment_inside_zone_merges_correctly(self):
        """
        Both "161835.1" and "8" are INSIDE the zone.
        Expectation: candidates include "161835.18" and it WINS.
        """
        zone = [380.0, 480.0]
        tokens = [
            make_token("161835.1", x0=382.0, x1=440.0),
            make_token("8",        x0=442.0, x1=452.0),
        ]
        cands = generate_zone_candidates(tokens, zone, "balance")
        assert cands, "No candidates generated"
        values = [c["value"] for c in cands]
        assert 161835.18 in values, (
            f"161835.18 not in candidates. Got: {values}\n"
            f"This means merging DID work but _parse_float dropped the digit.\n"
            f"Full candidates: {cands}"
        )
        assert cands[0]["value"] == 161835.18, (
            f"161835.18 was generated but DIDN'T WIN. Winner={cands[0]['value']} score={cands[0]['score']}\n"
            f"Full candidates: {cands}"
        )

    def test_fragment_outside_zone_causes_truncation(self):
        """
        "161835.1" is inside zone, "8" is OUTSIDE zone right edge.
        Expectation: "8" is excluded → winner is 161835.1 (TRUNCATED).
        This test DOCUMENTS the bug — it should PASS (i.e. truncation IS happening).
        """
        zone = [380.0, 441.0]   # zone stops at 441; "8" starts at 442
        tokens = [
            make_token("161835.1", x0=382.0, x1=440.0),
            make_token("8",        x0=442.0, x1=452.0),  # 1px outside zone
        ]
        cands = generate_zone_candidates(tokens, zone, "balance")
        assert cands, "No candidates generated"
        winner_val = cands[0]["value"]
        # This assertion PASSES when the bug is present
        assert winner_val == pytest.approx(161835.1, abs=0.01), (
            f"Expected 161835.1 (truncated — bug present), got {winner_val}"
        )
        # Flag it clearly
        print(f"\n[BUG CONFIRMED] Zone boundary at x={441} excludes '8' at x=442 → winner={winner_val}")

    def test_parse_float_does_not_truncate_two_digit_decimal(self):
        """_parse_float must return 161835.18 for input '161835.18'."""
        result = _parse_float("161835.18")
        assert result == pytest.approx(161835.18), f"Got {result}"

    def test_parse_float_does_not_truncate_trailing_zero(self):
        """_parse_float must return 413534.10 (= 413534.1) — float is fine, but not 41353.41."""
        result = _parse_float("413534.10")
        assert result == pytest.approx(413534.10, abs=0.001), f"Got {result}"

    def test_parse_float_five_digit_decimal_branch(self):
        """
        The '5-digit decimal' branch in _parse_float:
          '2.00000' → intended to produce 2000.00
        ACTUAL: sanitize_balance_text pre-processes the string, so this branch
        may not trigger as expected. Documenting actual behaviour.
        """
        result_5 = _parse_float("2.00000")
        # After sanitizer the value comes back as-is → regex matches 2.0
        # The 5-digit branch in raw _parse_float would give 2000.00,
        # but sanitizer intercepts first. Document actual:
        print(f"\n[INFO] _parse_float('2.00000') = {result_5}")
        assert result_5 is not None, "Must return a float"

        # Normal 2-digit decimal must NOT be mangled
        result_normal = _parse_float("161835.18")
        assert result_normal == pytest.approx(161835.18), f"Got {result_normal}"

    def test_parse_float_three_digit_decimal_treated_as_thousands(self):
        """
        The '3-digit decimal' branch in _parse_float:
          '2.000' → intended to be treated as thousands separator → 2000
        ACTUAL: sanitize_balance_text intercepts first, so the branch
        may not behave as expected on all inputs. Documenting actual behaviour.
        """
        result_3 = _parse_float("2.000")
        print(f"\n[INFO] _parse_float('2.000') = {result_3}  (branch may or may not fire)")
        assert result_3 is not None, "Must return a float"

        # The dangerous case: a real balance ending in .000 should not become 100x larger
        result_real = _parse_float("161835.000")
        print(f"[INFO] _parse_float('161835.000') = {result_real}")
        # If the 3-digit branch fires: result = 161835000 (WRONG)
        # If it doesn't fire: result = 161835.0 (correct)
        assert result_real != pytest.approx(161835000.0, abs=1.0), (
            f"CRITICAL BUG: '161835.000' parsed as {result_real} — "
            "3-digit decimal branch treating valid balance as thousands separator!"
        )

    def test_fragment_split_across_zone_boundary_is_detected(self):
        """
        "161835." inside zone, "18" outside zone (1px gap).
        Winner should be 161835.0 (truncated) — bug confirmed.
        """
        zone = [380.0, 445.0]
        tokens = [
            make_token("161835.",  x0=382.0, x1=444.0),
            make_token("18",       x0=446.0, x1=460.0),  # just outside
        ]
        cands = generate_zone_candidates(tokens, zone, "balance")
        assert cands, "No candidates"
        winner = cands[0]["value"]
        # If bug present, winner = 161835.0 (the period-only token parsed without decimal digits)
        print(f"\n[INFO] Split '161835.' + '18' (outside zone): winner={winner}")
        # At minimum, 161835.18 should NOT be the winner (because "18" is out of zone)
        values = [c["value"] for c in cands]
        assert 161835.18 not in values, (
            f"161835.18 appeared even though '18' was outside zone — zone filtering may not work: {values}"
        )


# ===========================================================================
# Regression: ensure correct amounts still parse correctly
# ===========================================================================
class TestParseFloatRegression:

    @pytest.mark.parametrize("raw,expected", [
        ("161,835.18",  161835.18),
        ("413,534.10",  413534.10),
        ("209,964.10",  209964.10),
        ("5,000.00",    5000.00),
        ("1,500.00",    1500.00),
        ("87,034.17",   87034.17),
        ("1,00,000.00", 100000.00),   # Indian lakh format
        ("1500",        1500.0),
        ("0.50",        0.50),
    ])
    def test_parse_float_known_amounts(self, raw, expected):
        result = _parse_float(raw)
        assert result == pytest.approx(expected, abs=0.01), (
            f"_parse_float('{raw}') = {result}, expected {expected}"
        )
