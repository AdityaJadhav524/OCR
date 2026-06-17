# Phase 5 â€” Regression Audit Report

Scanned 20 production files.

## Explicit Hack Annotations

| File | Line | Pattern | Code |
|------|------|---------|------|
| core/extractors/pdf_extractor.py | 351 | SBI FIX | `    # 0.85x height captures vertically-offset components (SBI/YesBank fix)` |
| core/detection/bank_detector.py | 307 | SBI FIX | `    # We do this BEFORE stripping legal suffixes to catch "SBI LTD"` |
| validation_lab/backend/api.py | 326 | DEBUG comment | `    # 2. Deterministic extraction returned nothing — hard fail with debug dump` |

## Implicit Bank-Specific Patterns

| File | Line | Pattern | Code |
|------|------|---------|------|
| core/extractors/pdf_extractor.py | 351 | 0.85x multiplier (SBI/YesBank fix comment) | `    # 0.85x height captures vertically-offset components (SBI/YesBank fix)` |
| core/extractors/pdf_extractor.py | 370 | force_break row splitting | `        force_break = this_date and has_date # Start new row on second date foun` |
| core/extractors/pdf_extractor.py | 401 | 0.52x multiplier (financial fonts comment) | `    return max(3.0, median_h * 0.52) # 0.52x height for financial fonts` |
| core/detection/bank_detector.py | 435 | BOI conditional | `  WARNING: DO NOT assume a bank mentioned in a single transaction (e.g., "BOI EM` |
| core/parsers/coordinate_parser_v2.py | 488 | P9A Provisional Fallback | `            # P9A Provisional Fallback: balance zone never detected, so don't re` |
| core/parsers/coordinate_parser_v2.py | 653 | E-Statement Layout Masking Rescue | `        # --- E-Statement Layout Masking Rescue ---` |

## Header Suppression Asymmetry

`suppress_headers_and_footers()` call sites in `api.py`:

- Line 792: `from core.detection.header_suppression import suppress_headers_and_footers`
- Line 831: `page_tokens = suppress_headers_and_footers(page_tokens)`

**suppress_headers_and_footers NOT called in do_extraction()**
- run_benchmark_job() DOES call it
- do_extraction() does NOT
- Production uploads see more tokens than benchmark runs

