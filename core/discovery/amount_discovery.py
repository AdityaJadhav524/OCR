"""
amount_discovery.py
===================

Layer 3: Extract the transaction amount.

If a row has multiple numeric values, which one is the transaction amount?
We know the balance value from Layer 2. The remaining numeric value(s)
must contain the transaction amount.

If there's only one remaining value: that's the amount.
If there are multiple remaining values (e.g. cheque number parsed as amount):
we wait for Layer 4 (Direction Discovery) which uses ledger math to pick
the correct amount.

Status: STUB — not yet implemented.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.discovery.amount_discovery")


def discover_amounts(
    candidates: List[Dict[str, Any]],
    balance_info: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Find the transaction amount per candidate row.

    Args:
        candidates: Output from transaction_discovery.py
        balance_info: Output from balance_discovery.py

    Returns:
        List of candidates updated with 'amount' fields.

    Status: NOT YET IMPLEMENTED.
    """
    logger.debug("amount_discovery: STUB — not yet implemented")
    return candidates
