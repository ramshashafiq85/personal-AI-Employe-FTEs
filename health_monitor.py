"""
Health Monitor - Platinum Tier
Monitors all services and alerts on failures
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime


class HealthMonitor:
    def __init__(self):
        self.check_interval = int(os.getenv("CHECK_INTERVAL", "60"))
        self.alert_email = os.getenv("ALERT_EMAIL", "")
        self.webhook_url = os.getenv("WEBHOOK_URL", "")
        self.logs_dir = Path("/app/logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Services to monitor
        self.services = {
            "odoo": {"url": "http://odoo:8069", "port": 8069},
            "postgres": {"host": "db", "port": 5432},
            "redis": {"host": "redis", "port": 6379},
            "cloud-agent": {"url": "http://cloud-agent:8080", "port": 8080}
        }
    
    def check_http_service(self, url: str) -> bool:
        """Check if an HTTP service is responding"""
        try:
            response = requests.get(url, timeout=5)
            return response.status_code < 500
        except requests.RequestException:
            return False
    
    def check_tcp_port(self, host: str, port: int) -> bool:
        """Check if a TCP port is open"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def check_all_services(self) -> dict:
        """Check all services and return status"""
        status = {}
        
        for name, config in self.services.items():
            if "url" in config:
                is_healthy = self.check_http_service(config["url"])
            else:
                is_healthy = self.check_tcp_port(config["host"], config["port"])
            
            status[name] = {
                "healthy": is_healthy,
                "last_check": datetime.now().isoformat()
            }
        
        return status
    
    def send_alert(self, service: str, status: str):
        """Send alert email or webhook"""
        message = f"[ALERT] Service '{service}' is {status} at {datetime.now().isoformat()}"
        
        # Log alert
        alert_file = self.logs_dir / f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        alert_file.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "status": status,
            "message": message
        }, indent=2))
        
        # Send webhook if configured
        if self.webhook_url:
            try:
                requests.post(self.webhook_url, json={
                    "text": message
                }, timeout=5)
            except requests.RequestException:
                pass
        
        print(f"[ALERT] {message}")
    
    def run(self):
        """Run health monitoring loop"""
        print(f"Health Monitor started. Checking every {self.check_interval}s...")
        
        try:
            while True:
                status = self.check_all_services()
                
                for service, info in status.items():
                    if not info["healthy"]:
                        self.send_alert(service, "DOWN")
                    else:
                        print(f"[OK] {service} is healthy")
                
                # Write status report
                status_file = self.logs_dir / f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                status_file.write_text(json.dumps(status, indent=2))
                
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("Health Monitor stopped")


if __name__ == "__main__":
    monitor = HealthMonitor()
    monitor.run()
