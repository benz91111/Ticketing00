"""
Logger System
"""
import datetime
import json
import os
from pathlib import Path

if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME"):
    BASE_DIR = Path("/data")
else:
    BASE_DIR = Path(__file__).parent.parent.parent

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log_to_file(action, user_id, target_id=None, details=None):
    """Write log entry to file"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.datetime.now().strftime('%Y-%m')}.log"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "user_id": str(user_id),
        "target_id": str(target_id) if target_id else None,
        "details": details
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def get_logs_file():
    """Get all log files"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(LOGS_DIR.glob("*.log"), key=lambda x: x.name)
