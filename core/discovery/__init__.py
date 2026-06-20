"""
core/discovery/__init__.py

Transaction Discovery Engine — parallel parser prototype.

Architecture:
    Layer 1 — transaction_discovery.py  →  Find candidate rows (no zones, no headers)
    Layer 2 — balance_discovery.py      →  Identify running balance column from sequence
    Layer 3 — amount_discovery.py       →  Identify transaction amount per row
    Layer 4 — direction_discovery.py    →  Derive debit/credit from balance delta

Design principles:
    - Zero dependency on coordinate_parser_v2 or column_detector
    - Never rejects a row — produces confidence scores instead
    - Runs in parallel with the existing parser for comparison
    - Graduates to production only when recall >= baseline parser recall

Current status: PROTOTYPE — not used in production pipeline.
"""
