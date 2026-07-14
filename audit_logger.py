import json
import os
from datetime import datetime
from pathlib import Path

class AuditLogger:
    def __init__(self, vault_path: str):
        self.logs_dir = Path(vault_path) / "Logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log(self, action_type: str, actor: str, target: str, 
            parameters: dict = None, approval_status: str = "auto", 
            result: str = "success", details: str = ""):
        """Log an action to the daily JSON log file"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "parameters": parameters or {},
            "approval_status": approval_status,
            "result": result,
            "details": details
        }

        # Load existing logs or create new
        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except json.JSONDecodeError:
                logs = []

        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2))
        print(f"[AUDIT] {action_type} -> {target} ({result})")

    def get_today_logs(self):
        """Get all log entries for today"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"
        if not log_file.exists():
            return []
        return json.loads(log_file.read_text())

    def get_logs_for_date(self, date_str: str):
        """Get logs for a specific date (YYYY-MM-DD)"""
        log_file = self.logs_dir / f"{date_str}.json"
        if not log_file.exists():
            return []
        return json.loads(log_file.read_text())
