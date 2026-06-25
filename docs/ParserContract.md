# Parser API Contract

**Version:** 1.0.0

This contract dictates the strict JSON schema required for all transactions output by the Extraction/Parsing layer. 

**CRITICAL RULE:** OCR engines and extraction logic may change to improve token quality, but the parser contract NEVER changes without a version bump. The Validation Engine expects this exact schema.

## Transaction Object Schema

Every extracted transaction must be a dictionary containing the following structure:

### Required Fields
- `date` *(string or null)*: The transaction date as a string (e.g. "17/05/2025").
- `description` *(string)*: The textual description or narration of the transaction.
- `debit` *(float or null)*: The withdrawal amount. 
- `credit` *(float or null)*: The deposit amount.
- `balance` *(float or null)*: The running balance after the transaction.
- `page` *(int)*: The physical page index where the transaction was found.

### Optional Fields
- `value_date` *(string or null)*: The effective date of the transaction if separated from the main date.
- `chq_no` *(string or null)*: The cheque number associated with the transaction.
- `type` *(string)*: The inferred transaction type (e.g., 'UPI', 'NEFT', 'IMPS').

### Internal/Debug Fields (For Validation & Discovery)
- `_source_tokens` *(list)*: The raw OCR tokens that built this transaction.
- `_source_page` *(int)*: The original source page index (preserved even if sorting happens).
- `balance_zone` *(tuple)*: `(x0, x1)` bounding box coordinates of the balance column, used by the Candidate Generator.
- `confidence` *(dict)*: Sub-system confidence flags (e.g. OCR suspicion).
- `telemetry` *(dict)*: Additional context about how the transaction was parsed (e.g., folded row merges).

### Example Payload
```json
{
  "schema_version": "1.0.0",
  "date": "17/05/2025",
  "description": "UPI/P2A/113612345/GROCERY",
  "debit": 1500.0,
  "credit": null,
  "balance": 24500.50,
  "page": 1,
  "confidence": {},
  "telemetry": {},
  "_source_tokens": [{"text": "17/05/2025", "x0": 50, "y0": 100}],
  "_source_page": 1
}
```
