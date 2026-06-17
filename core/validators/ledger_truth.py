"""
ledger_truth.py

Implements the Truth Preservation Engine annotation pass.
Creates ledger_truth, agreement_state, and conflict_record.
Strips _source_tokens from FULL_AGREEMENT rows to save memory.
NEVER modifies extracted values (debit, credit, balance).
"""
from typing import List, Dict, Optional
from core.validators.ledger_suspicion_detector import detect_ledger_suspicion

def annotate_ledger_truth(transactions: List[Dict]) -> List[Dict]:
    unresolved_chain_error = 0.0
    unresolved_chain_root = None
    unresolved_chain_root_idx = None   # index of the primary anomaly txn
    anomaly_counter = 0                # monotonic anomaly ID within this document

    for i, txn in enumerate(transactions):
        raw = txn.get("raw_extraction", {})
        curr_balance = raw.get("parsed_balance")

        # Ensure ledger_truth exists
        txn["ledger_truth"] = {
            "available": False,
            "reason": None
        }

        # First row or unknown balance -> UNSEEDED
        if i == 0 or curr_balance is None:
            txn["ledger_truth"]["reason"] = "NO_PREVIOUS_BALANCE" if i == 0 else "NO_CURRENT_BALANCE"
            txn["agreement_state"] = "UNSEEDED"
            continue

        prev_txn = transactions[i - 1]
        prev_raw = prev_txn.get("raw_extraction", {})
        # Get prev_balance, using the recovered balance if the previous row was a RECOVERY_CANDIDATE
        if prev_txn.get("agreement_state") == "RECOVERY_CANDIDATE":
            prev_balance = prev_txn.get("ledger_truth", {}).get("expected_balance", prev_raw.get("parsed_balance"))
        else:
            prev_balance = prev_raw.get("parsed_balance")

        if prev_balance is None:
            txn["ledger_truth"]["reason"] = "NO_PREVIOUS_BALANCE"
            txn["agreement_state"] = "UNSEEDED"
            continue

        # Local delta computation
        delta = round(curr_balance - prev_balance, 2)
        expected_delta = abs(delta)
        expected_direction = "credit" if delta > 0 else "debit"
        # If delta is 0, we'll conventionally call it debit but the amount matches 0.
        if expected_delta == 0.0:
            expected_direction = "none"

        # Geometry amount
        geo_debit = raw.get("parsed_debit")
        geo_credit = raw.get("parsed_credit")
        
        geo_amount = geo_debit if geo_debit is not None else (geo_credit if geo_credit is not None else 0.0)
        geo_direction = "debit" if geo_debit is not None else ("credit" if geo_credit is not None else "none")

        # ── Phase 1B/1C: Ledger Suspicion & Evidence Correlation ─────────────────
        # Find single-digit OCR substitutions using the ledger math context
        # and resolve dipoles (+error then -error) as downstream chain effects.
        
        expected_balance = round(prev_balance + (geo_credit if geo_credit else 0.0) - (geo_debit if geo_debit else 0.0), 2)
        
        if curr_balance is not None:
            raw_error = round(curr_balance - expected_balance, 2)
            
            if abs(raw_error) > 0.001:
                # Is this the downstream half of a dipole?
                if unresolved_chain_root is not None and abs(raw_error + unresolved_chain_error) <= 0.01:
                    txn.setdefault("suspicious_fields", {})["balance"] = {
                        "reason": "DOWNSTREAM_CHAIN_EFFECT",
                        "severity": "LOW",
                        "diff": abs(raw_error),
                        "root_row": unresolved_chain_root,
                        "detail": f"Ledger mismatch exactly offsets previous error from {unresolved_chain_root}"
                    }
                    # Back-annotate the primary anomaly with this affected row
                    if unresolved_chain_root_idx is not None:
                        primary_txn = transactions[unresolved_chain_root_idx]
                        primary_sig = primary_txn.get("suspicious_fields", {}).get("balance", {})
                        primary_sig.setdefault("affected_rows", []).append(txn.get("date", f"Row {i}"))
                    # Dipole resolved
                    unresolved_chain_error = 0.0
                    unresolved_chain_root = None
                    unresolved_chain_root_idx = None
                else:
                    # New primary anomaly — assign an ID
                    anomaly_counter += 1
                    anomaly_id = f"A{anomaly_counter:04d}"
                    ledger_suspicion = detect_ledger_suspicion(
                        ocr_balance=curr_balance,
                        prev_balance=prev_balance,
                        debit=geo_debit if geo_debit else 0.0,
                        credit=geo_credit if geo_credit else 0.0
                    )
                    if ledger_suspicion:
                        sig = ledger_suspicion["balance"]
                        sig["anomaly_id"] = anomaly_id
                        sig["affected_rows"] = []
                        txn.setdefault("suspicious_fields", {}).update(ledger_suspicion)
                    else:
                        # Unclassified primary anomaly
                        txn.setdefault("suspicious_fields", {})["balance"] = {
                            "reason": "PRIMARY_BALANCE_ANOMALY",
                            "severity": "HIGH",
                            "anomaly_id": anomaly_id,
                            "diff": abs(raw_error),
                            "affected_rows": [],
                            "detail": f"Unexplained ledger drift of {raw_error}"
                        }
                    unresolved_chain_error = raw_error
                    unresolved_chain_root = txn.get("date", f"Row {i}")
                    unresolved_chain_root_idx = i
            else:
                # If error is 0, the chain is clean here. 
                # If we had an unresolved error, it means the true sequence baked the error in.
                if unresolved_chain_error != 0.0:
                    unresolved_chain_error = 0.0
                    unresolved_chain_root = None

        # Determine Local Trust
        within_tol = abs(geo_amount - expected_delta) <= 1.50
        direction_match = (geo_direction == expected_direction) or (expected_delta == 0.0 and geo_amount == 0.0)

        if within_tol and direction_match:
            trust = "HIGH"
        elif within_tol or direction_match:
            trust = "MEDIUM"
        else:
            trust = "LOW"

        # Annotate ledger truth
        txn["ledger_truth"] = {
            "available": True,
            "prev_balance": prev_balance,
            "expected_delta": expected_delta,
            "expected_direction": expected_direction,
            "balance_trust": trust,
            "trust_reason": "LOCAL_CONSERVATION"
        }

        # Map trust to Agreement State
        if trust == "HIGH":
            txn["agreement_state"] = "FULL_AGREEMENT"
        elif trust == "MEDIUM":
            txn["agreement_state"] = "PARTIAL_AGREEMENT"
        else:
            txn["agreement_state"] = "CONFLICT"

        # (Recovery logic using forward-chain proof removed to prevent chain-healing mutations)
        # We now rely purely on DOWNSTREAM_CHAIN_EFFECT evidence collection.

        # Add conflict record if necessary
        if txn["agreement_state"] == "CONFLICT":
            unexplained = round(abs(geo_amount - expected_delta), 2)
            txn["conflict_record"] = {
                "unexplained_delta": unexplained,
                "candidate_causes": [
                    "ocr_amount_corruption",
                    "column_boundary_failure",
                    "token_ownership_failure",
                    "statement_contradiction"
                ]
            }

        # Memory optimization: drop full source tokens for perfect matches
        if txn["agreement_state"] == "FULL_AGREEMENT":
            txn.pop("_source_tokens", None)

    return transactions
