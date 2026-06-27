import pytest
from core.detection.footer_detector import FooterDetector, FooterDecision

def test_federal_bank_final_transaction():
    """
    Test that a valid terminal transaction (like Federal Bank's 94th transaction) 
    is NEVER classified as a footer, even if it appears at the bottom of the page.
    """
    detector = FooterDetector()
    row = "31/12/2025 UPIOUT/837686843655/Q024125297@ybl/Sent via /5812 120.00 Dr 88,933.39"
    decision = detector.evaluate_row(row, page_pos=0.99, is_anchor=True)
    assert decision.is_footer == False
    assert "strong_transaction_structure" in decision.reasons

def test_footer_with_grand_total():
    """
    Test that GRAND TOTAL (even with amounts) is classified as a footer
    due to strong terminal keywords and lack of an anchor date.
    """
    detector = FooterDetector()
    row = "GRAND TOTAL 150000.00 150000.00"
    decision = detector.evaluate_row(row, page_pos=0.90, is_anchor=False)
    assert decision.is_footer == True
    assert "strong_terminal_keyword" in decision.reasons

def test_footer_with_only_disclaimer():
    """
    Test that a disclaimer with no amounts and no date at the bottom of the page is a footer.
    """
    detector = FooterDetector()
    row = "DISCLAIMER: This is a computer generated statement and does not require a signature."
    decision = detector.evaluate_row(row, page_pos=0.88, is_anchor=False)
    assert decision.is_footer == True
    assert "no_transaction_structure" in decision.reasons

def test_footer_containing_generation_date():
    """
    Test that a footer with a generation date (not a transaction date) is recognized as a footer.
    """
    detector = FooterDetector()
    row = "Generated on 31/12/2025 14:00:00"
    # Even though it contains a date, is_anchor=False because it's not at the start of the row or doesn't match anchor constraints
    decision = detector.evaluate_row(row, page_pos=0.95, is_anchor=False)
    assert decision.is_footer == True

def test_footer_containing_page_numbers():
    """
    Test that page numbering strings are treated as footers.
    """
    detector = FooterDetector()
    row = "PAGE 3 OF 8"
    decision = detector.evaluate_row(row, page_pos=0.98, is_anchor=False)
    assert decision.is_footer == True
    assert any("footer_keyword" in r for r in decision.reasons)

def test_narration_split_across_two_lines_near_page_bottom():
    """
    Test that a valid continuation row (narration) at the bottom of the page is NOT treated as a footer.
    """
    detector = FooterDetector()
    row = "transfer to Mr. Smith for the rent payment"
    # No date (is_anchor=False), no amounts. Page pos > 0.85
    decision = detector.evaluate_row(row, page_pos=0.95, is_anchor=False)
    # It shouldn't be a footer just because it's at the bottom with no amounts!
    # Because there are no footer keywords!
    assert decision.is_footer == False
    assert decision.confidence < 0.70  # Should be around 0.60 (0.4 for no_transaction_structure + 0.2 for geometric)
