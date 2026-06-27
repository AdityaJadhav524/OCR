import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

ROOT = Path(__file__).parent.parent
TELEMETRY_DIR = ROOT / "telemetry"

logger = logging.getLogger("TelemetryLogger")

def log_telemetry(trace_type: str, statement_id: str, payload: Dict[str, Any]):
    """
    Logs structured JSON telemetry traces.
    trace_type: e.g., 'extraction', 'validator', 'confidence', 'timing', 'profiling', 'audit'
    """
    try:
        TELEMETRY_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{trace_type}_{statement_id}_{timestamp}.json"
        filepath = TELEMETRY_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            
        logger.debug(f"Telemetry saved: {filepath}")
    except Exception as e:
        logger.error(f"Failed to log telemetry {trace_type}: {e}")
