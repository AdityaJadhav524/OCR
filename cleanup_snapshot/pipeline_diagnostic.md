# Pipeline Diagnostic Report

## BOI Pipeline Trace

- **Raw Tokens:** 65
- **Tokens after Header Suppression:** 65
- **Rows Detected:** 15
- **Column Zones Detected:** `['date_zone', 'narration_zone', 'debit_zone', 'credit_zone', 'balance_zone']`
  - Details: `{'date_zone': [0.0, 110.0], 'narration_zone': [110.0, 340.0], 'debit_zone': [340.0, 410.0], 'credit_zone': [410.0, 480.0], 'balance_zone': [480.0, 9999.0]}`
- **Transaction Blocks Detected:** 11
- **Accepted Transactions:** 10
- **Rejected Rows:** 1
- **Reject Reasons:**
  - `no_debit_or_credit`: 1

---

## HDFC Pipeline Trace

- **Raw Tokens:** 1257
- **Tokens after Header Suppression:** 1051
- **Rows Detected:** 134
- **Column Zones Detected:** `['credit_zone', 'balance_zone', 'debit_zone', 'date_zone']`
  - Details: `{'credit_zone': [0.0, 97.27], 'balance_zone': [97.27, 143.07], 'debit_zone': [143.07, 287.64], 'date_zone': [287.64, 9999.0]}`
- **Transaction Blocks Detected:** 3
- **Accepted Transactions:** 0
- **Rejected Rows:** 3
- **Reject Reasons:**
  - `no_balance`: 2
  - `no_debit_or_credit`: 1

---
