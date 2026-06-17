# YES Bank Ground Truth Report

## Summary

| Item | Count |
|------|-------|
| Total transaction anchors (date in date_zone) | 83 |
| Transactions extracted (accepted) | 83 |
| Transactions rejected | 144 |
| Expected = Accepted + Rejected | 227 |

## Rejected Transactions (Full Detail)

Total rejects with a date (likely real transactions): **0**
Total rejects without a date (headers/footers): **144**

## Accepted Transactions — First 3

- [03/11/21] ATW.416021XXXXXX8811-S1ANPZ50-JALANDHAR 03/07/21 | D=5000.0 C=None BAL=309919.1 PAGE=1 STATE=UNSEEDED
- [09/11/21] ATW-416021XXXXXX8811-S1ANPZ50- JALANDHAR 09/07/21 | D=5000.0 C=None BAL=304919.1 PAGE=1 STATE=PASS
- [07/11/21] UPI-SARABIT SINGH-SARAB SINGH1994@OKHDF 07/07/21 | D=None C=10000.0 BAL=314919.1 PAGE=1 STATE=PASS

## Accepted Transactions — Last 3

- [07/02/22] ATW-416021XXXXXX8811-S1ANPZ50- 000000000000681708/10/21 | D=5000.0 C=None BAL=464850.5 PAGE=4 STATE=PASS
- [07/02/22] UPI-HARPREET SINGH- 000012860877458713/10/21 | D=None C=25000.0 BAL=489850.5 PAGE=4 STATE=PASS
- [07.09/22] CASHDEP 0000000000003372 07/02/2022 | D=None C=40000.0 BAL=529850.5 PAGE=4 STATE=PASS

## Target Transaction Investigation

### Searching for '07/02/22' + 'HARPREET' in accepted:

- FOUND IN ACCEPTED: [07/02/22] ATW-416021XXXXXX8811-S1ANPZ50- 000000000000681708/10/21 | D=5000.0 C=None BAL=464850.5 STATE=PASS
- FOUND IN ACCEPTED: [07/02/22] UPI-HARPREET SINGH- 000012860877458713/10/21 | D=None C=25000.0 BAL=489850.5 STATE=PASS

### Searching for '07/02/22' + 'HARPREET' in rejected:

- NOT FOUND in rejected transactions either.

## Ground Truth Verdict

- **Transaction anchors in PDF:** 83
- **Extracted by parser:** 83
- **Missing from output:** 0

```
VERDICT: Expected = Extracted = Missing = 0
All 83 transactions extracted. Nothing is missing.
```