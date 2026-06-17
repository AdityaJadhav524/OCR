# Kotak Conservation Forensic Report

Total rows: 32
Transaction rows (date proven): 9
Accepted: 0
Conservation fails: 9

## 1. Opening Balance / Seed Audit

Page seeds extracted: `{1: 1.45}`

Rows matched by _PAGE_BALANCE_RE:

| Page | Row Text | RE Match | Balance Found | Is Opening | Is Closing |
|------|----------|----------|---------------|------------|------------|
| 1 | `Opening Balance 1.45` | True | 1.45 | True | False |

## 2. First Conservation Failure

**Block 19** — Date: `02 Feb 2026`

| Field | Value |
|-------|-------|
| date | `02 Feb 2026` |
| debit | 663.0 |
| credit | None |
| ocr_balance | 664.45 |
| prev_balance (entering block) | **1.45** |
| expected_balance | -661.55 |
| residual | 1326.0 |
| seeded this block | False |

Raw tokens on block: `['1', '02 Feb 2026', 'UPI/Shridhan Sanjay/338827314489/Payment', 'UPI-603376894422', '663.00', '664.45']`

## 3. Balance Chain Replay — All Transaction Rows

| Block | Date | Debit | Credit | OCR Balance | prev_balance | Expected Balance | Residual | Result |
|-------|------|-------|--------|-------------|--------------|------------------|----------|--------|
| 19 | `02 Feb 2026` | 663.0 | None | 664.45 | 1.45 | -661.55 | 1326.0 | **conservation_fail(residual=1326.00)** |
| 21 | `03 Feb 2026` | 40.0 | None | 624.45 | 1.45 | -38.55 | 663.0 | **conservation_fail(residual=663.00)** |
| 22 | `03 Feb 2026` | 1.0 | None | 625.45 | 1.45 | 0.45 | 625.0 | **conservation_fail(residual=625.00)** |
| 24 | `04 Feb 2026` | 130.0 | None | 495.45 | 1.45 | -128.55 | 624.0 | **conservation_fail(residual=624.00)** |
| 25 | `05 Feb 2026` | 2.16 | None | 497.61 | 1.45 | -0.71 | 498.32 | **conservation_fail(residual=498.32)** |
| 27 | `05 Feb 2026` | 30.0 | None | 467.61 | 1.45 | -28.55 | 496.16 | **conservation_fail(residual=496.16)** |
| 28 | `06 Feb 2026` | 188.0 | None | 279.61 | 1.45 | -186.55 | 466.16 | **conservation_fail(residual=466.16)** |
| 29 | `09 Feb 2026` | 50.0 | None | 229.61 | 1.45 | -48.55 | 278.16 | **conservation_fail(residual=278.16)** |
| 30 | `09 Feb 2026` | 229.0 | None | 0.61 | 1.45 | -227.55 | 228.16000000000003 | **conservation_fail(residual=228.16)** |

## 4. Cascade Detection

First failure at block 19, date `02 Feb 2026`

All subsequent transaction rows also fail: **True**

**CONCLUSION: Cascade failure. Fix the first row only.**

## 5. OCR Token Analysis — First Failing Block

Block 19 raw tokens:

- `1` — numeric=True, parsed=1.0
- `02 Feb 2026` — numeric=True, parsed=2.0
- `UPI/Shridhan Sanjay/338827314489/Payment` — numeric=True, parsed=338827314489.0
- `UPI-603376894422` — numeric=True, parsed=-603376894422.0
- `663.00` — numeric=True, parsed=663.0
- `664.45` — numeric=True, parsed=664.45

## 6. Root Cause Conclusion

**ROOT CAUSE: OCR / AMOUNT CORRUPTION.** Seeds were applied but conservation still fails.
Review the balance chain replay table for specific failures.
