# Kotak Fix Impact Measurement

## 1. Simulated Zones

- debit_zone:  `[942.0, 1119.0]`
- credit_zone: `[1111.0, 1319.0]`

## 2. Amount Distribution Proof

| Date | Token | x0 | in_debit | in_credit | Assigned Direction |
|------|-------|----|----------|-----------|--------------------|
| `02 Feb 202` | `663.00` | 1245 | False | True | **CREDIT** |
| `03 Feb 202` | `40.00` | 1071 | True | False | **DEBIT** |
| `03 Feb 202` | `1.00` | 1264 | False | True | **CREDIT** |
| `04 Feb 202` | `130.00` | 1062 | True | False | **DEBIT** |
| `05 Feb 202` | `2.16` | 1260 | False | True | **CREDIT** |
| `05 Feb 202` | `30.00` | 1071 | True | False | **DEBIT** |
| `06 Feb 202` | `188.00` | 1061 | True | False | **DEBIT** |
| `09 Feb 202` | `50.00` | 1071 | True | False | **DEBIT** |
| `09 Feb 202` | `229.00` | 1064 | True | False | **DEBIT** |

## 3. Conclusion

Amounts assigned to DEBIT: 6
Amounts assigned to CREDIT: 3
Amounts overlapping BOTH: 0

**CONCLUSION: The geometric split of the header perfectly separates debit and credit transactions.**
Safe to implement in `column_detector.py`.