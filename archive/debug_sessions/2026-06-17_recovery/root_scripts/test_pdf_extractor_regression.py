import re
from core.extractors.pdf_extractor import (
    DATE_RE, 
    _can_safely_overlay, 
    _merge_continuation_rows,
    _has_date_at_left
)

def test_regex_numeric_dates():
    dates = [
        "01/10/2024", "01-10-2024", "01.10.2024", 
        "2024-10-01", "2024/10/01"
    ]
    for d in dates:
        assert DATE_RE.search(d) is not None, f"Failed to match numeric date: {d}"

def test_regex_alpha_dates():
    dates = [
        "01 OCT 2024", "01 Oct 2024", "01 October 2024",
        "01-OCT-2024", "01.OCT.2024", "01 OCT-24", "01-Oct-24"
    ]
    for d in dates:
        assert DATE_RE.search(d) is not None, f"Failed to match alpha date: {d}"

def test_safe_overlay_pass():
    line1 = "Account             "
    line2 = "        Type  Amount"
    assert _can_safely_overlay(line1, line2) is True

def test_safe_overlay_collision():
    line1 = "TXN123  ATM WITHDRAWAL      5000.00"
    line2 = "TXN124  POS RETAIL          1000.00"
    # 'T' and 'T', 'X' and 'X' collide.
    assert _can_safely_overlay(line1, line2) is False

def test_merge_preserves_rows():
    lines = [
        "UNKNOWN_DATE  DEPOSIT        100.00",
        "UNKNOWN_DATE  WITHDRAWAL     50.00",
        "UNKNOWN_DATE  FEE            5.00"
    ]
    merged = _merge_continuation_rows(lines)
    assert len(merged) == 3, "Rows were destructively overlaid!"
    assert "DEPOSIT" in merged[0]
    assert "WITHDRAWAL" in merged[1]
    assert "FEE" in merged[2]

def test_hdfc_digital_statement():
    lines = [
        "Date        Narration                     Chq/Ref No.    Value Dt     Withdrawal Amt.  Deposit Amt.  Closing Balance",
        "02/11/25    UPI-Redbus India Private-redbus1online.gpay@...           02/11/25    2680.00          566438.40",
        "02/11/25    UPI-SWAPNIL DHANYAKUMAR-swapnilpatil93...                 02/11/25             2000.00 568438.40",
        "            IMPS-530618983562-Akshata Dhanyakumar -F...",
        "            ACH D- FIN INDIAN CLEARING-225039246 Valu...              04/11/25    200000.00        468438.40"
    ]
    merged = _merge_continuation_rows(lines)
    assert len(merged) >= 3

def test_bank_of_india_statement():
    lines = [
        "Date        Narration                     Chq No.   Withdrawal    Deposit     Balance",
        "01 OCT 2024 UPI/1234567890/PAYMENT                  1,500.00                  24,549.30",
        "02 OCT 2024 ATM WITHDRAWAL                          5,000.00                  19,549.30",
        "05 OCT 2024 ACH CREDIT SALARY                                     50,000.00   69,549.30",
    ]
    merged = _merge_continuation_rows(lines)
    assert len(merged) == 4

def test_scanned_statement():
    lines = [
        "12/04/2024 CASH DEPOSIT 500",
        "15/04/2024 ATM WITHDRAW 100"
    ]
    merged = _merge_continuation_rows(lines)
    assert len(merged) == 2

if __name__ == "__main__":
    test_regex_numeric_dates()
    test_regex_alpha_dates()
    test_safe_overlay_pass()
    test_safe_overlay_collision()
    test_merge_preserves_rows()
    test_hdfc_digital_statement()
    test_bank_of_india_statement()
    test_scanned_statement()
    print("ALL TESTS PASSED SUCCESSFULLY")
