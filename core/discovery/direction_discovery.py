"""
direction_discovery.py
======================

Layer 4: Derive debit/credit direction from balance delta.

Now that we have the balance value and amount candidates per row,
we use accounting math to determine direction.

    delta = balance_current - balance_previous

    If delta > 0:
        credit = delta
        debit = 0
    If delta < 0:
        debit = abs(delta)
        credit = 0

We then match this derived direction against the amount candidates from Layer 3.
This completely eliminates the need for header zone mapping.

Status: STUB — not yet implemented.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("core.discovery.direction_discovery")


def discover_direction(
    candidates: List[Dict[str, Any]],
    balance_info: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Determine debit/credit amounts based on balance deltas.

    Args:
        candidates: Output from amount_discovery.py
        balance_info: Output from balance_discovery.py

    Returns:
        List of candidates updated with 'debit' and 'credit' fields.

    Status: NOT YET IMPLEMENTED.
    """
    logger.debug("direction_discovery: STUB — not yet implemented")
    return candidates
