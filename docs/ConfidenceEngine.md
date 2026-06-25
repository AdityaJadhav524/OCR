# Statement Confidence Engine

The Confidence Engine orchestrates the Validation Pipeline and computes a final Trust Score.

## The Heuristics
The Engine starts at **100 points** and deducts penalties based on independent failure signals:

- **Continuity Penalty:** If the running balance breaks, up to 40 points are deducted.
- **Reconciliation Penalty:** If the final computed ledger does not match the printed Closing Balance, up to 35 points are deducted.
- **Direction Penalty:** If transaction directions are inverted and cannot be healed, up to 15 points are deducted.
- **Completeness Penalty:** If the extracted transaction count misses the heuristically expected count, up to 10 points are deducted.

## Explainability
Instead of a black-box score, the Confidence Engine uses the exact validator outputs (e.g., number of continuity breaks, specific reconciliation diffs, suspected OCR corruptions) to generate a plain-text Explanation. 

For `AUTO_APPROVE` statements, it lists the passing validation criteria.
For `MANUAL_CHECK` statements, it surfaces a root cause attribution breakdown (e.g., "Primary Causes: 82% OCR Corruption, 18% Page Ordering Anomalies") to guide the human reviewer.
