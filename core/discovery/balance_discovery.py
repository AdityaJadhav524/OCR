"""
balance_discovery.py
====================

Layer 2: Identify the running balance column from monotonic sequence detection.

The running balance is the most reliable column in a bank statement.
Debit/Credit column headers vary wildly between banks.
The running balance is always present and always monotonically changing.

Algorithm:
    1. Collect all numeric values per x-position cluster across transaction rows.
    2. Find the cluster whose values form a mostly-monotonic sequence
       (each value ≈ previous ± some delta).
    3. That cluster is the running balance column.
    4. Extract balance value per transaction row.

A sequence is "mostly monotonic" if ≥ 80% of consecutive pairs satisfy:
    |next - prev| < 5 * median_delta

Status: STUB — not yet implemented.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("core.discovery.balance_discovery")


def discover_balance_column(
    candidates: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Identify the balance column from transaction candidates.

    Args:
        candidates: Output from transaction_discovery.discover_transactions()

    Returns:
        {
            "balance_x_range": [min_x, max_x],   # x-coordinate range of balance column
            "confidence": 0.0–1.0,
            "values": { row_index: float }        # balance value per row
        }

    Status: NOT YET IMPLEMENTED.
    """
    logger.debug("balance_discovery: STUB — not yet implemented")
    return {"balance_x_range": None, "confidence": 0.0, "values": {}}


def is_monotonic_sequence(values: List[float], tolerance: float = 0.05) -> bool:
    """
    Return True if the sequence is mostly monotonic (either mostly increasing
    or mostly decreasing), with at most `tolerance` fraction of violations.

    Used to identify the balance column.
    """
    if len(values) < 3:
        return False
    increases = sum(1 for a, b in zip(values, values[1:]) if b > a)
    decreases = sum(1 for a, b in zip(values, values[1:]) if b < a)
    total = len(values) - 1
    dominant = max(increases, decreases)
    return dominant / total >= (1.0 - tolerance)
