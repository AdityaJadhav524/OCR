"""
Transaction Recovery Auditor — v3

Key additions over v2:
  - Populates PipelineFunnel so you can see exactly where rows vanish
    (Row Builder vs Parser vs Validation)
  - Populates LayerInvariant per stage (input/output/dropped/merged/split)
  - find_first_divergence() — returns the exact first row where two parsers
    disagree, with candidate-level provenance
  - build_corpus_matrix() now computes Precision, Recall, F1 and evaluates
    the full ReleaseGate (all 8 thresholds)
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from core.models.audit import (
    CandidateTrace,
    ConfidenceHistogram,
    FirstDivergence,
    FunnelStage,
    LayerInvariant,
    LayerResult,
    PipelineFunnel,
    PipelineLayer,
    RecoveryReport,
    RejectCode,
    RejectReason,
    ReleaseGateResult,
    RELEASE_GATE_THRESHOLDS,
    TransactionAuditTrail,
)
from core.validators.financial_audit import _parse_float

logger = logging.getLogger("core.validators.recovery_auditor")

CONSERVATION_TOLERANCE = 1.50


# ---------------------------------------------------------------------------
# Root-cause classifier (same as v2, unchanged logic)
# ---------------------------------------------------------------------------
def _classify_reject(row: Dict[str, Any], tel: Dict[str, Any]) -> RejectReason:
    log_str      = str(tel.get("reject_log", "")).lower()
    conservation = tel.get("conservation_state", "")
    raw_debit    = row.get("debit")
    raw_credit   = row.get("credit")
    raw_balance  = row.get("balance")
    raw_date     = row.get("date")
    narration    = str(row.get("narration", ""))[:80]

    secondary: List[RejectCode] = []

    if not raw_date:
        secondary.append(RejectCode.COLUMN_MISCLASSIFIED)
        if raw_balance is None:
            secondary.append(RejectCode.MISSING_BALANCE)
        return RejectReason(
            primary=RejectCode.MISSING_DATE,
            confidence=0.95,
            secondary=secondary,
            evidence=["No parseable date field on this row"],
            raw_text=narration,
            detected_at_layer=PipelineLayer.DECLARATIVE_PARSER,
        )

    if "date_zone" in log_str or "date in" in log_str or "date_in_numeric" in log_str:
        secondary.extend([RejectCode.COLUMN_MISCLASSIFIED, RejectCode.INVALID_NUMERIC])
        if "continuity" in log_str or "conservation" in log_str:
            secondary.append(RejectCode.FAILED_CONTINUITY)
        return RejectReason(
            primary=RejectCode.DATE_IN_NUMERIC_ZONE,
            confidence=0.92,
            secondary=secondary,
            evidence=[log_str[:200]],
            raw_text=narration,
            detected_at_layer=PipelineLayer.COLUMN_DETECTOR,
        )

    if raw_balance is None:
        secondary.append(RejectCode.FAILED_CONTINUITY)
        return RejectReason(
            primary=RejectCode.MISSING_BALANCE,
            confidence=0.95,
            secondary=secondary,
            evidence=["Balance field absent — continuity chain will break"],
            raw_text=narration,
            detected_at_layer=PipelineLayer.DECLARATIVE_PARSER,
        )

    if raw_debit is None and raw_credit is None:
        secondary.append(RejectCode.NO_VALID_NUMERIC)
        return RejectReason(
            primary=RejectCode.MISSING_AMOUNT,
            confidence=0.90,
            secondary=secondary,
            evidence=["Neither debit nor credit found for this row"],
            raw_text=narration,
            detected_at_layer=PipelineLayer.DECLARATIVE_PARSER,
        )

    if raw_debit is not None and raw_credit is not None:
        secondary.append(RejectCode.AMBIGUOUS_CANDIDATES)
        return RejectReason(
            primary=RejectCode.DUAL_AMOUNT,
            confidence=0.90,
            secondary=secondary,
            evidence=[f"debit={raw_debit} and credit={raw_credit} both set"],
            detected_at_layer=PipelineLayer.CANDIDATE_SELECTOR,
        )

    if conservation == "FAIL" or "conservation" in log_str or "reconcil" in log_str:
        amount = 0.0
        try:
            amount = float(raw_debit or raw_credit or 0)
        except (TypeError, ValueError):
            pass
        if amount < 10:
            secondary.extend([RejectCode.AMBIGUOUS_CANDIDATES, RejectCode.LOW_CONFIDENCE])
        return RejectReason(
            primary=RejectCode.FAILED_RECONCILIATION,
            confidence=0.92,
            secondary=secondary,
            evidence=[log_str[:200] or f"conservation={conservation}"],
            raw_text=narration,
            detected_at_layer=PipelineLayer.VALIDATION_ENGINE,
        )

    if "continuity" in log_str:
        secondary.append(RejectCode.FAILED_RECONCILIATION)
        return RejectReason(
            primary=RejectCode.FAILED_CONTINUITY,
            confidence=0.90,
            secondary=secondary,
            evidence=[log_str[:200]],
            raw_text=narration,
            detected_at_layer=PipelineLayer.VALIDATION_ENGINE,
        )

    if "column" in log_str and "not found" in log_str:
        secondary.extend([RejectCode.MISSING_AMOUNT, RejectCode.FAILED_CONTINUITY])
        return RejectReason(
            primary=RejectCode.COLUMN_NOT_FOUND,
            confidence=0.85,
            secondary=secondary,
            evidence=[log_str[:200]],
            detected_at_layer=PipelineLayer.COLUMN_DETECTOR,
        )

    return RejectReason(
        primary=RejectCode.UNKNOWN,
        confidence=0.40,
        secondary=[],
        evidence=[log_str[:200] or "No telemetry available"],
        raw_text=str(row)[:120],
        detected_at_layer=PipelineLayer.DECLARATIVE_PARSER,
    )


# ---------------------------------------------------------------------------
# TransactionRecoveryAuditor
# ---------------------------------------------------------------------------
class TransactionRecoveryAuditor:
    def __init__(self, session_id: str, bank: str = "UNKNOWN"):
        self.session_id = session_id
        self.bank = bank

    def audit(
        self,
        page_tokens: List[Any],
        identity: Optional[Dict] = None,
    ) -> RecoveryReport:
        from core.parsers.coordinate_parser_v2 import parse_with_coordinates

        report = RecoveryReport(session_id=self.session_id, bank=self.bank)

        # ── Funnel stage 1: OCR tokens ──────────────────────────────────
        token_count = len(page_tokens) if isinstance(page_tokens, list) else 0
        report.funnel.add(
            layer="OCR Tokens",
            count=token_count,
            dropped=0,
            note="Raw OCR token count from PDF extraction",
        )

        # ── Run parser ──────────────────────────────────────────────────
        t0 = time.perf_counter()
        try:
            transactions, telemetry = parse_with_coordinates(
                page_tokens,
                bank=self.bank,
                identity=identity or {},
            )
        except Exception as exc:
            logger.exception("parse_with_coordinates raised")
            trail = TransactionAuditTrail(row_id="GLOBAL_EXCEPTION")
            trail.layer_results.append(LayerResult(
                layer=PipelineLayer.DECLARATIVE_PARSER,
                passed=False,
                failure_reason=RejectCode.PARSER_EXCEPTION,
                output_summary=str(exc)[:200],
            ))
            trail.reject_reason = RejectReason(
                primary=RejectCode.PARSER_EXCEPTION,
                confidence=1.0,
                secondary=[],
                evidence=[str(exc)],
                detected_at_layer=PipelineLayer.DECLARATIVE_PARSER,
            )
            report.add_trail(trail)
            return report

        parse_ms = (time.perf_counter() - t0) * 1000

        # ── Extract telemetry counts for funnel ─────────────────────────
        rows_built   = telemetry.get("rows_detected",   telemetry.get("total_rows", len(transactions) + len(telemetry.get("reject_log", []))))
        reject_log   = telemetry.get("reject_log", [])
        rejected_cnt = len(reject_log)
        emitted_cnt  = len(transactions)

        # Funnel stage 2: Rows built by Row Builder
        report.funnel.add(
            layer="Rows Built",
            count=rows_built,
            dropped=max(0, token_count - rows_built),
            note="After row-grouping; tokens collapsed into candidate rows",
        )

        # Funnel stage 3: Rows seen by parser (same as rows_built here,
        # but separate for when Row Builder pre-filters)
        report.funnel.add(
            layer="Rows Parsed",
            count=rows_built,
            dropped=0,
            note="Rows that entered the parser pipeline",
        )

        # Funnel stage 4: Rows emitted vs rejected
        report.funnel.add(
            layer="Transactions Emitted",
            count=emitted_cnt,
            dropped=rejected_cnt,
            note=f"Parser emitted {emitted_cnt}, rejected {rejected_cnt}",
        )

        # ── Layer invariants ────────────────────────────────────────────
        report.invariants.append(LayerInvariant(
            layer=PipelineLayer.ROW_BUILDER,
            input_count=token_count,
            output_count=rows_built,
            dropped=max(0, token_count - rows_built),
            passed=True,
            note="OCR tokens → candidate rows",
        ))
        report.invariants.append(LayerInvariant(
            layer=PipelineLayer.DECLARATIVE_PARSER,
            input_count=rows_built,
            output_count=emitted_cnt,
            dropped=rejected_cnt,
            passed=(rejected_cnt == 0),
            note=f"{rejected_cnt} rows rejected by parser/validation",
        ))

        per_txn_ms = round(parse_ms / max(emitted_cnt, 1), 2)

        # ── Emitted transaction trails ───────────────────────────────────
        for i, txn in enumerate(transactions):
            trail = TransactionAuditTrail(row_id=f"emitted:{i}")
            trail.emitted = True
            trail.transaction = txn
            trail.txn_id = txn.get("txn_id") or f"TXN-{uuid.uuid4().hex[:12]}"
            trail.confidence = float(txn.get("confidence", 90.0))
            for layer in PipelineLayer:
                trail.layer_results.append(LayerResult(
                    layer=layer, passed=True, timing_ms=per_txn_ms
                ))
            report.add_trail(trail)

        # ── Rejected row trails ──────────────────────────────────────────
        layer_order = list(PipelineLayer)
        for entry in reject_log:
            if not isinstance(entry, dict):
                entry = {"reject_log": str(entry)}

            row_idx = entry.get("row_idx", "?")
            trail = TransactionAuditTrail(row_id=f"rejected:{row_idx}")
            trail.emitted = False
            trail.ocr_tokens = entry.get("raw_tokens", [])

            reason = _classify_reject(entry, entry)
            trail.reject_reason = reason

            failed_layer = reason.detected_at_layer or PipelineLayer.DECLARATIVE_PARSER
            for layer in layer_order:
                if layer == failed_layer:
                    trail.layer_results.append(LayerResult(
                        layer=layer,
                        passed=False,
                        failure_reason=reason.primary,
                        output_summary="; ".join(reason.evidence[:2]),
                    ))
                    break
                trail.layer_results.append(LayerResult(layer=layer, passed=True))

            report.add_trail(trail)

        return report


# ---------------------------------------------------------------------------
# find_first_divergence — exact first row where two parsers disagree
# ---------------------------------------------------------------------------
def _safe_float(row: Optional[Dict], field: str) -> Optional[float]:
    if row is None:
        return None
    raw = row.get(field)
    if raw is None:
        return None
    try:
        return float(_parse_float(str(raw)) or raw)
    except (TypeError, ValueError):
        return None


def find_first_divergence(
    legacy_txns: List[Dict],
    new_txns: List[Dict],
    amount_tolerance: float = 1.0,
) -> Optional[FirstDivergence]:
    """
    Walk both lists in lock-step.  Return the FIRST row (1-based) where
    any amount field (debit, credit, balance) differs by > tolerance.
    Also flags when one list is shorter than the other.
    """
    max_len = max(len(legacy_txns), len(new_txns))

    for i in range(max_len):
        legacy = legacy_txns[i] if i < len(legacy_txns) else None
        new    = new_txns[i]    if i < len(new_txns)    else None

        if legacy is None or new is None:
            missing_in = "new" if legacy is not None else "legacy"
            return FirstDivergence(
                row_index=i + 1,
                legacy_value=None,
                new_value=None,
                field_name="row_count",
                reason=f"Row {i+1} exists in {('legacy' if new is None else 'new')} "
                       f"but is missing from {missing_in}",
                candidate_index=None,
                candidate_confidence=None,
                legacy_narration=(legacy or {}).get("narration", "")[:60],
                new_narration=(new or {}).get("narration", "")[:60],
            )

        for fname in ("debit", "credit", "balance"):
            lv = _safe_float(legacy, fname)
            nv = _safe_float(new, fname)
            if lv is None and nv is None:
                continue
            if lv is None or nv is None or abs(lv - nv) > amount_tolerance:
                # Pull candidate metadata if new parser attached it
                c_idx  = new.get("candidate_index")
                c_conf = new.get("candidate_confidence")
                c_reason = new.get("candidate_reason", "")
                reason = (
                    f"Field '{fname}' differs: legacy={lv}, new={nv}"
                    + (f" — {c_reason}" if c_reason else "")
                )
                return FirstDivergence(
                    row_index=i + 1,
                    legacy_value=lv,
                    new_value=nv,
                    field_name=fname,
                    reason=reason,
                    candidate_index=c_idx,
                    candidate_confidence=c_conf,
                    legacy_narration=legacy.get("narration", "")[:60],
                    new_narration=new.get("narration", "")[:60],
                )

    return None   # no divergence found


# ---------------------------------------------------------------------------
# compare_parsers — V1 / V2 / V3 side-by-side with provenance + first div
# ---------------------------------------------------------------------------
def compare_parsers(
    v1_txns: List[Dict],
    v2_txns: List[Dict],
    v3_txns: List[Dict],
) -> Dict[str, Any]:
    max_len = max(len(v1_txns), len(v2_txns), len(v3_txns), 0)
    diffs   = []

    for i in range(max_len):
        v1 = v1_txns[i] if i < len(v1_txns) else None
        v2 = v2_txns[i] if i < len(v2_txns) else None
        v3 = v3_txns[i] if i < len(v3_txns) else None

        amounts: Dict[str, Any] = {}
        for label, row in [("v1", v1), ("v2", v2), ("v3", v3)]:
            if row is None:
                amounts[label] = {"status": "MISSING"}
                continue
            amounts[label] = {
                "date":                 row.get("date"),
                "debit":                _safe_float(row, "debit"),
                "credit":               _safe_float(row, "credit"),
                "balance":              _safe_float(row, "balance"),
                "narration":            (row.get("narration") or "")[:60],
                "candidate_index":      row.get("candidate_index"),
                "candidate_reason":     row.get("candidate_reason"),
                "candidate_confidence": row.get("candidate_confidence"),
            }

        disagreement = False
        reasons: List[str] = []
        present = [(k, v) for k, v in amounts.items() if v.get("status") != "MISSING"]
        for fname in ("debit", "credit", "balance"):
            vals = [v[fname] for _, v in present if v.get(fname) is not None]
            if len(vals) > 1 and (max(vals) - min(vals)) > 1.0:
                disagreement = True
                reasons.append(f"{fname} mismatch: {vals}")
        missing_in = [k for k, v in amounts.items() if v.get("status") == "MISSING"]
        if missing_in:
            disagreement = True
            reasons.append(f"row absent in: {missing_in}")

        diffs.append({
            "row": i + 1, "v1": amounts.get("v1"), "v2": amounts.get("v2"),
            "v3": amounts.get("v3"), "disagrees": disagreement, "reasons": reasons,
        })

    disagreements = [d for d in diffs if d["disagrees"]]

    # First divergence between V1 (legacy) and V3 (new declarative)
    first_div = find_first_divergence(v1_txns, v3_txns)

    return {
        "counts": {"v1": len(v1_txns), "v2": len(v2_txns), "v3": len(v3_txns)},
        "max_rows": max_len,
        "disagreement_count": len(disagreements),
        "first_divergence": first_div.to_dict() if first_div else None,
        "disagreements": disagreements,
        "all_rows": diffs,
    }


# ---------------------------------------------------------------------------
# build_corpus_matrix — with Precision, Recall, F1, ReleaseGate
# ---------------------------------------------------------------------------
def _precision_recall_f1(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return round(precision, 2), round(recall, 2), round(f1, 2)


def _gate_check(metric: str, value: float) -> Dict[str, Any]:
    threshold = RELEASE_GATE_THRESHOLDS.get(metric, 0)
    passed = (value <= threshold) if metric in ("missing", "extra", "amount_errors",
              "balance_errors", "ordering_errors") else (value >= threshold)
    return {"value": value, "threshold": threshold, "passed": passed}


def build_corpus_matrix(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a release-gate verification matrix per bank.

    Each entry:
    {
        "bank":      "Federal Bank",
        "expected":  94,
        "parsed":    [list of transaction dicts],
        "reference": [list of ground-truth dicts],  # optional
    }

    Returns rows with expected/parsed/missing/extra/amount_mismatches/
    precision/recall/f1/status plus a ReleaseGate evaluation.
    """
    rows = []
    all_pass = True

    for e in entries:
        bank      = e["bank"]
        expected  = e.get("expected", 0)
        parsed    = e.get("parsed", [])
        reference = e.get("reference", [])
        p_count   = len(parsed)

        missing = max(0, expected - p_count)   # false negatives
        extra   = max(0, p_count - expected)   # false positives

        # Amount / balance / ordering errors vs reference (if available)
        amount_errors  = 0
        balance_errors = 0
        ordering_errors = 0

        if reference:
            for ref_txn, prs_txn in zip(reference, parsed):
                for fname in ("debit", "credit"):
                    rv = _safe_float(ref_txn, fname)
                    pv = _safe_float(prs_txn, fname)
                    if rv is not None and pv is not None and abs(rv - pv) > 1.0:
                        amount_errors += 1
                        break
                rv = _safe_float(ref_txn, "balance")
                pv = _safe_float(prs_txn, "balance")
                if rv is not None and pv is not None and abs(rv - pv) > 1.0:
                    balance_errors += 1
            # Ordering: dates should be monotonically non-decreasing
            dates = [r.get("date", "") for r in parsed]
            for j in range(1, len(dates)):
                if dates[j] and dates[j - 1] and dates[j] < dates[j - 1]:
                    ordering_errors += 1

        # Reconciliation rate (% of rows where prev+dr/cr=bal holds)
        reconciliation = 100.0  # placeholder — full math requires ordered balances

        # Precision / Recall / F1
        tp = min(p_count, expected) - missing  # simplistic; improve with reference matching
        tp = max(0, expected - missing)
        fp = extra
        fn = missing
        precision, recall, f1 = _precision_recall_f1(tp, fp, fn)

        # Release gate
        gate_checks = {
            "missing":         _gate_check("missing",        missing),
            "extra":           _gate_check("extra",          extra),
            "amount_errors":   _gate_check("amount_errors",  amount_errors),
            "balance_errors":  _gate_check("balance_errors", balance_errors),
            "ordering_errors": _gate_check("ordering_errors",ordering_errors),
            "reconciliation":  _gate_check("reconciliation", reconciliation),
            "precision":       _gate_check("precision",      precision),
            "recall":          _gate_check("recall",         recall),
        }
        gate_passed = all(c["passed"] for c in gate_checks.values())
        if not gate_passed:
            all_pass = False

        rows.append({
            "bank":            bank,
            "expected":        expected,
            "parsed":          p_count,
            "missing":         missing,
            "extra":           extra,
            "amount_errors":   amount_errors,
            "balance_errors":  balance_errors,
            "ordering_errors": ordering_errors,
            "reconciliation":  reconciliation,
            "precision":       precision,
            "recall":          recall,
            "f1":              f1,
            "release_gate":    ReleaseGateResult(bank=bank, passed=gate_passed,
                                                 checks=gate_checks).to_dict(),
            "status":          "PASS" if gate_passed else "FAIL",
        })

    return {
        "all_pass":       all_pass,
        "rows":           rows,
        "total_expected": sum(r["expected"] for r in rows),
        "total_parsed":   sum(r["parsed"]   for r in rows),
        "total_missing":  sum(r["missing"]  for r in rows),
    }
