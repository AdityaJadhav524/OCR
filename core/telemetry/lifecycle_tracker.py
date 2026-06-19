import datetime
import json
import os
import time

class LifecycleTracker:
    def __init__(self, job_id, pdf_name):
        self.job_id = job_id
        self.pdf_name = pdf_name
        self.timestamps = {
            "uploaded_at": None,
            "password_detected_at": None,
            "password_received_at": None,
            "password_validated_at": None,
            
            "classification_at": None,
            
            "backend_state_available_at": None,
            "frontend_polled_at": None,
            
            "engine": None,
            "engine_start": None,
            "engine_end": None,
            "engine_result": None,
            
            "extraction_started_at": None,
            "extraction_finished_at": None,
            "parser_started_at": None,
            "parser_finished_at": None,
            "validation_completed_at": None,
            "completed_at": None
        }
        
        self.status_transition_log = []
        
    def stamp(self, event_name, value=None):
        if event_name in self.timestamps:
            if value is not None:
                self.timestamps[event_name] = value
            else:
                self.timestamps[event_name] = datetime.datetime.now().isoformat()
            
    def log_state(self, state_name, details=None):
        entry = [state_name, datetime.datetime.now().isoformat()]
        if details is not None:
            entry.append(details)
        self.status_transition_log.append(entry)
            
    def dump(self, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        file_path = os.path.join(out_dir, f"{self.pdf_name}_timeline.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({
                "job_id": self.job_id,
                "pdf_name": self.pdf_name,
                "timestamps": self.timestamps,
                "status_transition_log": self.status_transition_log
            }, f, indent=2)
