import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
BASELINE_PATH = ROOT / "evaluation" / "benchmarks" / "corpus_v1.0.0.json"

sys.path.insert(0, str(ROOT / "evaluation" / "reports"))
from run_confidence_benchmark import run_confidence_benchmark

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("RegressionGate")

def run_regression():
    if not BASELINE_PATH.exists():
        logger.error(f"Baseline file not found at {BASELINE_PATH}")
        sys.exit(1)
        
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        baseline = {b["bank"]: b for b in json.load(f)}
        
    logger.info("Running confidence benchmark for regression analysis...")
    current_stats = run_confidence_benchmark()
    
    regressions = []
    
    for stat in current_stats:
        bank = stat["bank"]
        if bank not in baseline:
            logger.info(f"Skipping baseline check for new bank: {bank}")
            continue
            
        base = baseline[bank]
        
        # We enforce checks:
        # 1. Healthy bank confidence shouldn't decrease
        if base["confidence"] >= 90 and stat["confidence"] < base["confidence"]:
            regressions.append(f"{bank}: Confidence dropped {base['confidence']} -> {stat['confidence']}")
            
        # 2. Accepted transaction completeness shouldn't decrease
        if stat["completeness"] < base["completeness"]:
            regressions.append(f"{bank}: Completeness dropped {base['completeness']}% -> {stat['completeness']}%")
            
        # 3. New continuity breaks shouldn't be introduced (allow 0.5% float delta)
        if stat["continuity"] < base["continuity"] - 0.5:
            regressions.append(f"{bank}: Continuity dropped {base['continuity']}% -> {stat['continuity']}%")
            
        # 4. Reconciliation shouldn't worsen
        if stat["reconciliation"] < base["reconciliation"] - 0.5:
            regressions.append(f"{bank}: Reconciliation dropped {base['reconciliation']}% -> {stat['reconciliation']}%")
            
    # Also print the nice Delta table
    logger.info("=== BENCHMARK DELTA ===")
    logger.info(f"{'Bank':<20} | {'v1.0.0':<8} | {'Current':<8} | {'Δ':<6}")
    logger.info("-" * 50)
    for stat in current_stats:
        bank = stat["bank"]
        if bank in baseline:
            base_conf = baseline[bank]["confidence"]
            curr_conf = stat["confidence"]
            delta = curr_conf - base_conf
            delta_str = f"+{delta}" if delta >= 0 else str(delta)
            logger.info(f"{bank:<20} | {base_conf:<8} | {curr_conf:<8} | {delta_str:<6}")
    logger.info("-" * 50)
            
    if regressions:
        logger.error("REGRESSION(S) DETECTED:")
        for r in regressions:
            logger.error(f"  - {r}")
        sys.exit(1)
    else:
        logger.info("✅ All regression checks passed! Architecture maintains V1.0.0 standards.")
        sys.exit(0)

if __name__ == "__main__":
    run_regression()
