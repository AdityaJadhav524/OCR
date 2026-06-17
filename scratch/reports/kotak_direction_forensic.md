# Kotak First Transaction Direction Forensic

## Zones Detected

- `date_zone`: [200.0, 331.0]
- `narration_zone`: [323.0, 950.0]
- `debit_zone`: [942.0, 1319.0]
- `balance_zone`: [1311.0, 9999.0]
- `credit_zone`: **NOT DETECTED**

## Column Header Analysis

The header row that drove zone detection:

| Token | x0 | Matched As |
|-------|----|-----------|
| `Date` | 210 | DATE |
| `Description` | 333 | **CREDIT** |
| `Chq/Ret.No.` | 742 | NONE |
| `Withdrawal (Dr.)Deposit (Cr.)` | 952 | **DEBIT** |
| `Balance` | 1321 | BALANCE |

## Scenario Analysis

| Scenario | Calculation | Result | Matches OCR Balance (664.45)? |
|----------|------------|--------|---------------------------------------|
| If DEBIT | 1.45 - 663.0 | -661.55 | **False** |
| If CREDIT | 1.45 + 663.0 | 664.45 | **True** |

## Block 19 Token x-Coordinates vs Zone Boundaries

Zones: debit=[[942.0, 1319.0]]  credit=[None]  balance=[[1311.0, 9999.0]]

| Token | x0 | in_debit_zone | in_credit_zone | in_balance_zone | Parsed Value |
|-------|-----|--------------|----------------|-----------------|-------------|
| `1` | 110 | False | False | False | 1.0 |
| `02 Feb 2026` | 200 | False | False | False | 2.0 |
| `UPI/Shridhan Sanjay/338827314489/Payment` | 321 | False | False | False | 338827314489.0 |
| `UPI-603376894422` | 733 | False | False | False | -603376894422.0 |
| `663.00` | 1245 | True | False | False | 663.0 |
| `664.45` | 1425 | False | False | True | 664.45 |

## Root Cause Hypothesis

**HYPOTHESIS CONFIRMED: Debit/Credit assignment failure.**

Evidence:
1. `credit_zone` was NOT detected by column_detector
2. Kotak header uses combined `Withdrawal (Dr.)Deposit (Cr.)` token
3. column_detector matched this as a single DEBIT column
4. 663.00 (a credit transaction) falls in `debit_zone` by x-coordinate
5. Parser assigns it as `debit=663` instead of `credit=663`
6. Conservation: `1.45 - 663 = -661.55` fails
7. If correctly assigned as credit: `1.45 + 663 = 664.45` PASSES

**Fix target:** column_detector — split combined header tokens.
**NOT a fix target:** _DATE_RE, conservation logic, balance repair
