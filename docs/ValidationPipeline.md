# The Validation Pipeline

The Validation Layer is responsible for recovering lost accounting data and mathematically auditing the ledger. It uses a phased "Sprint" architecture to apply non-destructive heals before executing strict audits.

## Layer 3: Candidate Generation
Rather than blindly trusting OCR string matches, the system searches the `balance_zone` bounding box to generate plausible balance candidates (stripping artifacts, accounting for decimal drops).

## Layer 4: Balance Sanity Validator
Filters out mathematically impossible candidates (e.g., watermark contamination resulting in a balance 100x the median of the document) before they reach the main engine.

## Sprint 0: Order & Sequence
- Detects global descending vs. ascending chronological order.
- Validates page boundaries for anomalies (date reversals).
- Executes `Page Sequence Repair` (greedy graph algorithm) to re-stitch physically scrambled chunks.

## Sprint 1: Direction Healing
Analyzes the text stream for explicit credits (`CR`) and debits (`DR`), and mathematically infers missing directionality by verifying:
`prev_balance + credit - debit == current_balance`.
Automatically heals the transactions in-place.

## Sprint 2: Continuity Audit
Computes the exact mathematical continuity (`Running Balance Match Percentage`) across all transactions. Unrecoverable token losses (dropped leading digits) establish the Continuity Ceiling.

## Sprint 3: Financial Reconciliation
Validates the entire document footprint by extracting `Opening Balance` and `Closing Balance` anchors from the raw PDF text, comparing them against the computed ledger delta.
