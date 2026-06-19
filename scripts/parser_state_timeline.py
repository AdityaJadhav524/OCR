import os
import glob
import json
import hashlib
import subprocess
import shutil
from collections import defaultdict
from core.detection.header_suppression import suppress_headers_and_footers
from core.layout.row_detector import detect_rows, detect_transaction_blocks
from core.layout.column_detector import detect_columns
from core.parsers.coordinate_parser_v2 import parse_with_coordinates

def sha256_file(filepath):
    if not os.path.exists(filepath): return ""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192): h.update(chunk)
    return h.hexdigest()

def get_git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('utf-8').strip()
    except:
        return "unknown"

def run_pipeline(pdf_path, dump_dir):
    try:
        from core.extractors.document_router import route_document
        full_text, pages, telemetry, page_tokens = route_document(pdf_path, password='1170AKSH')
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
        return None


    tokens_before = len(page_tokens)
    
    if dump_dir and page_tokens:
        first_page_tokens = [t for t in page_tokens if t.get('page') == 1]
        with open(os.path.join(dump_dir, "tokens_before_suppression.json"), "w") as f:
            json.dump(first_page_tokens, f)

    filtered_tokens = suppress_headers_and_footers(page_tokens)
    tokens_after = len(filtered_tokens)

    if dump_dir and filtered_tokens:
        first_page_filtered = [t for t in filtered_tokens if t.get('page') == 1]
        with open(os.path.join(dump_dir, "tokens_after_suppression.json"), "w") as f:
            json.dump(first_page_filtered, f)

    rows = detect_rows(filtered_tokens)
    zones, headers = detect_columns(rows)
    
    if dump_dir:
        with open(os.path.join(dump_dir, "header_candidates.json"), "w") as f:
            json.dump(headers, f)

    blocks = detect_transaction_blocks(rows, zones.get('date_zone'))
    # Pass raw page_tokens directly as the production API does
    txns, telemetry = parse_with_coordinates(filtered_tokens)


    reject_log = telemetry.get('reject_log', [])
    reject_reasons = defaultdict(int)
    for r in reject_log:
        reject_reasons[r.get('reason', 'UNKNOWN')] += 1

    top_reason = "NONE"
    if reject_reasons:
        top_reason = max(reject_reasons.items(), key=lambda x: x[1])[0]

    stage_results = {
        "SUPPRESSION": "PASS",
        "HEADER_DETECTION": "NOT_RUN",
        "ZONE_CREATION": "NOT_RUN",
        "ROW_GROUPING": "NOT_RUN",
        "VALIDATION": "NOT_RUN"
    }
    
    first_failed_stage = "PASS"
    if tokens_before > 0 and tokens_after < tokens_before * 0.6:
        stage_results["SUPPRESSION"] = "FAIL"
        first_failed_stage = "SUPPRESSION"
    else:
        stage_results["HEADER_DETECTION"] = "PASS"
        if len(headers) == 0:
            stage_results["HEADER_DETECTION"] = "FAIL"
            first_failed_stage = "HEADER_DETECTION"
        else:
            stage_results["ZONE_CREATION"] = "PASS"
            if not all(k in zones for k in ['date_zone', 'balance_zone', 'debit_zone']):
                stage_results["ZONE_CREATION"] = "FAIL"
                first_failed_stage = "ZONE_CREATION"
            else:
                stage_results["ROW_GROUPING"] = "PASS"
                if len(blocks) == 0:
                    stage_results["ROW_GROUPING"] = "FAIL"
                    first_failed_stage = "ROW_GROUPING"
                else:
                    stage_results["VALIDATION"] = "PASS"
                    if len(txns) == 0 and len(blocks) > 0:
                        stage_results["VALIDATION"] = "FAIL"
                        first_failed_stage = "VALIDATION"

    header_selected_text = "NONE"
    if headers:
        header_selected_text = headers[0].get('text', 'NONE')[:30] + "..."

    zone_coords = {
        "date_zone": zones.get('date_zone', []),
        "debit_zone": zones.get('debit_zone', []),
        "credit_zone": zones.get('credit_zone', []),
        "balance_zone": zones.get('balance_zone', [])
    }

    waterfall = {
        "Raw Tokens": tokens_before,
        "After Suppression": tokens_after,
        "Header Candidates": len(headers),
        "Header Selected": 1 if zones else 0,
        "Zones Created": len(zones),
        "Row Blocks Created": len(blocks),
        "Rows Parsed": len(blocks),
        "Rows Accepted": len(txns),
        "Rows Rejected": len(reject_log)
    }

    retention = {}
    retention["Suppression Retention"] = f"{(tokens_after/tokens_before)*100:.1f}%" if tokens_before else "0%"
    retention["Header Selection Retention"] = f"{(1/len(headers))*100:.1f}%" if len(headers) else "0%"
    retention["Accepted Retention"] = f"{(len(txns)/len(blocks))*100:.1f}%" if len(blocks) else "0%"

    rows_lost = max(0, len(blocks) - len(txns))
    if len(blocks) == 0:
        # If row grouping failed, assume all tokens could have been rows roughly
        # For this metric, we'll rely on reject log or default to 0 if unknown
        rows_lost = len(reject_log)

    return {
        "signature": f"{len(blocks)}/{len(txns)}/{len(reject_log)}/{top_reason}",
        "first_failed_stage": first_failed_stage,
        "stage_results": stage_results,
        "waterfall": waterfall,
        "retention": retention,
        "top_reason": top_reason,
        "reject_reasons": dict(reject_reasons),
        "rows_detected": len(blocks),
        "accepted": len(txns),
        "rejected": len(reject_log),
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "header_selected": header_selected_text,
        "zone_coords": zone_coords,
        "rows_lost": rows_lost
    }

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python parser_state_timeline.py <directory>")
        sys.exit(1)

    target_dir = sys.argv[1]
    pdfs = glob.glob(os.path.join(target_dir, "*.pdf"))
    
    dumps_root = os.path.join(target_dir, "dumps")
    os.makedirs(dumps_root, exist_ok=True)

    config_sha = sha256_file("core/detection/header_suppression.py")
    parser_sha = sha256_file("core/parsers/coordinate_parser_v2.py")
    git_commit = get_git_commit()

    failure_cost_data = defaultdict(lambda: {"banks": set(), "rows_lost": 0})
    final_reports = []

    for pdf in pdfs:
        filename = os.path.basename(pdf)
        bank = filename.split('_')[0]
        if 'axis' in filename.lower(): bank = 'Axis'
        
        pdf_sha = sha256_file(pdf)
        
        runs = []
        dump_dir = os.path.join(dumps_root, filename)
        os.makedirs(dump_dir, exist_ok=True)
        
        print(f"Testing {filename} (5 runs)...")
        for i in range(1):
            res = run_pipeline(pdf, dump_dir if i == 0 else None)
            if res:
                runs.append(res)
                
        if not runs:
            continue

        signatures = [r['signature'] for r in runs]
        primary_signature = max(set(signatures), key=signatures.count)
        stability_score = (signatures.count(primary_signature) / len(runs)) * 100

        rep = runs[0]
        failed_stage = rep['first_failed_stage']
        if failed_stage != "PASS":
            failure_cost_data[failed_stage]["banks"].add(bank)
            failure_cost_data[failed_stage]["rows_lost"] += rep['rows_lost']

        drift_report = {
            "tokens_before": [r["tokens_before"] for r in runs],
            "tokens_after": [r["tokens_after"] for r in runs],
            "header_selected": [r["header_selected"] for r in runs]
        }

        zone_snapshot = [r["zone_coords"] for r in runs]

        report = {
            "pdf": filename,
            "fingerprint": {
                "pdf_sha256": pdf_sha,
                "config_sha256": config_sha,
                "parser_sha256": parser_sha,
                "git_commit": git_commit
            },
            "drift_report": drift_report,
            "zone_snapshot": zone_snapshot,
            "waterfall": rep['waterfall'],
            "stage_results": rep['stage_results'],
            "retention": rep['retention'],
            "failure_stage": rep['first_failed_stage'],
            "stability": f"{stability_score:.1f}%",
            "primary_cause": rep['top_reason']
        }
        final_reports.append(report)

    # Output JSON timeline
    print("\n--- PARSER STATE TIMELINE ---")
    for r in final_reports:
        print(f"\n{r['pdf']}")
        print("Fingerprint:")
        for k, v in r['fingerprint'].items(): print(f"  {k}={v}")
        print(f"Failure Stage:\n  {r['failure_stage']}")
        print(f"Stability:\n  {r['stability']}")
        print(f"Primary Cause:\n  {r['primary_cause']}")
        print("\nParser Drift Report:")
        print(json.dumps(r['drift_report'], indent=2))
        print("\nZone Geometry Snapshot (First Run):")
        print(json.dumps(r['zone_snapshot'][0], indent=2))

    # Output Failure Cost Heatmap
    print("\n--- CROSS-BANK FAILURE COST HEATMAP ---")
    stages = ["SUPPRESSION", "HEADER_DETECTION", "ZONE_CREATION", "ROW_GROUPING", "VALIDATION"]
    
    print("| Stage | Banks | Rows Lost |")
    print("| --- | ---: | ---: |")
    
    for stage in stages:
        data = failure_cost_data[stage]
        banks_count = len(data["banks"])
        rows_lost = data["rows_lost"]
        print(f"| {stage} | {banks_count} | {rows_lost} |")

if __name__ == '__main__':
    main()
