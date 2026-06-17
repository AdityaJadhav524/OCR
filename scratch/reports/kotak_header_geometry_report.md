# Kotak Header Geometry Forensic

## 1. Header Token Geometry

- Token: `Withdrawal (Dr.)Deposit (Cr.)`
- x0: 952.00
- x1: 1290.00
- width: 338.00
- 50/50 split point: 1121.00

## 2. Empirical Amount Positions

### Debits
- Value: 40.0, x0: 1071.00
- Value: 130.0, x0: 1062.00
- Value: 30.0, x0: 1071.00
- Value: 188.0, x0: 1061.00
- Value: 50.0, x0: 1071.00
- Value: 229.0, x0: 1064.00

Average Debit x0: 1066.67
Max Debit x0: 1071.00

### Credits
- Value: 663.0, x0: 1245.00
- Value: 2.16, x0: 1260.00

Average Credit x0: 1252.50
Min Credit x0: 1245.00

## 3. Recommended Split Boundary

- The actual gap between debit/credit clusters is from 1071.00 to 1245.00 (gap = 174.00)
- The empirical midpoint is **1158.00**
- The 50/50 header split point was 1121.00

**CONCLUSION: The 50/50 split (1121.00) is perfectly valid.**
It falls completely within the gap between the debit and credit amount clusters.
