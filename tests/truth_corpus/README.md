# Truth Corpus

This directory contains the **gold dataset** for the bank statement parser.

Every file here represents one PDF with the manually-verified ground truth.

## Why this exists

Without a stable baseline, every parser improvement risks a silent regression.
The truth corpus enforces a contract:

```
New parser MUST match or exceed current parser on every file here.
```

## File format

```json
{
  "pdf_name": "human-readable name",
  "bank": "Bank Name",
  "type": "digital | scanned",
  "expected_transactions": 9,
  "expected_first_date": "02 Feb 2026",
  "expected_last_date": "20 Feb 2026",
  "expected_opening_balance": 1.45,
  "expected_closing_balance": 0.61,
  "notes": "manually verified against the actual PDF",
  "verified": true,
  "verified_by": "user",
  "corpus_file": "relative path to PDF in temp/"
}
```

## Fields

| Field | Required | Source |
|---|---|---|
| `expected_transactions` | Yes | Count from actual PDF |
| `expected_first_date` | Yes | First transaction date in PDF |
| `expected_last_date` | Yes | Last transaction date in PDF |
| `expected_opening_balance` | If visible | Opening balance on statement |
| `expected_closing_balance` | If visible | Closing/last balance on statement |
| `verified` | Yes | `true` = manually counted, `false` = parser estimate |
| `notes` | No | Any special parsing notes for this PDF |

## Adding a new entry

1. Open the PDF manually
2. Count the transaction rows (not header/footer rows)
3. Note the first and last transaction dates
4. Copy a template from below and fill it in
5. Set `"verified": true`

## Status

| PDF | Verified | Transactions |
|---|---|---|
| Kotak scanned | ✅ | 9 |
| TJSB digital | ❌ | ~60 (TBD) |
| BOI digital | ❌ | ~259 (TBD) |
| BOI scanned | ❌ | ~264 (TBD) |
| HDFC scanned | ❌ | ~121 (TBD) |
| YES digital | ❌ | ~83 (TBD) |
| Axis digital | ❌ | ~59 (TBD) |
