"""
core/models/transaction.py
──────────────────────────
Transaction data model.

Plain dataclass — no ORM, no DB, no serialisation framework.
OCR extractor and digital PDF extractor both produce this shape.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
import json


@dataclass
class Transaction:
    """
    A single normalised bank transaction.

    Fields
    ------
    date      : ISO-8601 date string  (YYYY-MM-DD)
    narration : Transaction description / narration text
    debit     : Amount debited from account  (None if credit transaction)
    credit    : Amount credited to account   (None if debit transaction)
    balance   : Running account balance after this transaction (None if unknown)
    """
    date:      str
    narration: str
    debit:     Optional[float] = None
    credit:    Optional[float] = None
    balance:   Optional[float] = None
    
    # Truth Layer telemetry
    ocr_amount:      Optional[float] = None
    delta_amount:    Optional[float] = None
    amount_conflict: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(
            date=d.get("date") or "",
            narration=d.get("narration") or d.get("details") or "",
            debit=d.get("debit"),
            credit=d.get("credit"),
            balance=d.get("balance"),
            ocr_amount=d.get("ocr_amount"),
            delta_amount=d.get("delta_amount"),
            amount_conflict=d.get("amount_conflict", False),
        )

    def is_valid(self) -> bool:
        """True when date is non-empty and at least one of debit/credit is set."""
        return bool(self.date) and (self.debit is not None or self.credit is not None)


def transactions_to_json(transactions: list, indent: int = None) -> str:
    """Serialise a list of Transaction objects (or dicts) to a JSON string."""
    rows = []
    for t in transactions:
        rows.append(t.to_dict() if isinstance(t, Transaction) else t)
    return json.dumps(rows, indent=indent, ensure_ascii=False)
