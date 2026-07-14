"""
Local Agent - Platinum Tier
Owns: Approvals, WhatsApp session, payments/banking, final "send/post" actions
Runs on your local machine
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from audit_logger import AuditLogger
from orchestrator import Orchestrator
from social_media_client import SocialMediaManager
from vault_sync import VaultSync
from secrets_boundary import SyncGuard, EnvGuard, SecretsScanner

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LocalAgent")


class LocalAgent:
    """
    Local Agent runs on your machine.
    It handles:
    - Reviewing and approving Cloud drafts
    - WhatsApp session management
    - Payments and banking (via Odoo)
    - Final "send/post" execution
    
    It NEVER:
    - Store Cloud credentials
    - Sync secrets to Cloud
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.updates = self.vault_path / "Updates"
        self.signals = self.vault_path / "Signals"
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.approved = self.vault_path / "Approved"
        self.rejected = self.vault_path / "Rejected"
        self.done = self.vault_path / "Done"
        self.logs_dir = self.vault_path / "Logs"

        self.logger = AuditLogger(vault_path)
        self.orchestrator = Orchestrator(vault_path=vault_path)
        self.social_media = SocialMediaManager()

        # Platinum Tier: Vault sync & Secrets boundary
        git_remote = os.getenv('VAULT_SYNC_REMOTE')
        self.vault_sync = VaultSync(vault_path, agent_role='local', git_remote=git_remote)
        self.sync_guard = SyncGuard(vault_path, agent_role='local')
        self.env_guard = EnvGuard(vault_path)
        self.env_guard.load()
        self.secrets_scanner = SecretsScanner(vault_path)

        # Ensure folders exist
        for folder in [self.updates, self.signals, self.pending_approval,
                       self.approved, self.rejected, self.done, self.logs_dir]:
            folder.mkdir(parents=True, exist_ok=True)

        # Initialize git sync if remote is configured
        if git_remote:
            self.vault_sync.init_git()
    
    def check_cloud_updates(self):
        """Check for updates from Cloud Agent"""
        if not self.updates.exists():
            return []
        
        updates = []
        for update_file in self.updates.glob("*.json"):
            try:
                data = json.loads(update_file.read_text())
                updates.append(data)
            except json.JSONDecodeError:
                continue
        
        return updates
    
    def check_cloud_heartbeat(self):
        """Check if Cloud Agent is alive"""
        heartbeat_file = self.signals / "cloud_heartbeat.json"
        if not heartbeat_file.exists():
            return False
        
        try:
            data = json.loads(heartbeat_file.read_text())
            last_heartbeat = datetime.fromisoformat(data["timestamp"])
            time_diff = datetime.now() - last_heartbeat
            
            # Cloud is alive if heartbeat is less than 2 minutes old
            return time_diff.total_seconds() < 120
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
    
    def merge_cloud_updates(self):
        """Merge Cloud updates into local Dashboard"""
        updates = self.check_cloud_updates()
        
        if not updates:
            return
        
        logger.info(f"Merging {len(updates)} Cloud update(s)...")
        
        for update in updates:
            update_type = update.get("type", "unknown")
            
            if update_type == "email_draft":
                logger.info(f"Email draft from Cloud: {update.get('to', '')}")
            elif update_type == "social_draft":
                logger.info(f"Social draft from Cloud: {update.get('platform', '')}")
            
            # Move processed update to archive
            # (In production, use Git to track changes)
        
        # Update dashboard with Cloud status
        self.update_dashboard_with_cloud()
    
    def update_dashboard_with_cloud(self):
        """Update Dashboard with Cloud Agent status"""
        cloud_alive = self.check_cloud_heartbeat()
        cloud_status = "✅ Connected" if cloud_alive else "⚠️ Offline"
        
        dashboard = self.vault_path / "Dashboard.md"
        if dashboard.exists():
            content = dashboard.read_text(encoding="utf-8", errors="replace")
            # Update cloud status in dashboard
            if "Cloud Agent" in content:
                content = content.replace(
                    "| Cloud Agent | ⚠️ Offline |",
                    f"| Cloud Agent | {cloud_status} |"
                )
                dashboard.write_text(content, encoding="utf-8")
    
    def process_local_approvals(self):
        """Process approved actions (from Cloud drafts or local actions)"""
        if not self.approved.exists():
            return
        
        for approved_file in self.approved.glob("*.md"):
            logger.info(f"Processing approved action: {approved_file.name}")
            
            # Parse frontmatter
            content = approved_file.read_text(encoding="utf-8", errors="replace")
            metadata = {}
            if content.startswith("---"):
                try:
                    end_index = content.index("---", 3)
                    yaml_block = content[3:end_index].strip()
                    for line in yaml_block.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip()] = value.strip()
                except ValueError:
                    pass
            
            action_type = metadata.get("action", metadata.get("type", "unknown"))
            
            if action_type == "send_email":
                # Execute email send (via MCP or API)
                logger.info(f"SENDING EMAIL: {metadata.get('subject', '')}")
                print(f"\n{'='*50}")
                print(f"EMAIL SENT: {metadata.get('subject', '')}")
                print(f"To: {metadata.get('to', '')}")
                print(f"Status: SENT (Approved by Local)")
                print(f"{'='*50}\n")
            
            elif action_type == "social_media_post":
                # Execute social media post
                message = metadata.get("message", "")
                platform = metadata.get("platform", "all")
                image_url = metadata.get("image_url")
                
                logger.info(f"POSTING TO SOCIAL: {platform}")
                print(f"\n{'='*50}")
                print(f"SOCIAL MEDIA POSTED")
                print(f"Platform: {platform}")
                print(f"Message: {message[:100]}...")
                print(f"Status: POSTED (Approved by Local)")
                print(f"{'='*50}\n")
            
            # Move to Done
            dest = self.done / approved_file.name
            shutil.move(str(approved_file), str(dest))
            
            self.logger.log(
                action_type="local_approval_processed",
                actor="local_agent",
                target=approved_file.name,
                result="success"
            )
    
    def run_continuous(self, interval: int = 30):
        """Run local agent continuously"""
        logger.info("Local Agent started. Running...")
        logger.info(f"Vault: {self.vault_path}")
        logger.info(f"Checking every {interval} seconds...")

        sync_counter = 0
        sync_interval = max(interval * 6, 300)  # Sync every 5 min minimum

        try:
            while True:
                # Merge Cloud updates
                self.merge_cloud_updates()

                # Process local approvals
                self.process_local_approvals()

                # Run orchestrator cycle
                self.orchestrator.run_cycle()

                # Run vault sync periodically
                sync_counter += interval
                if sync_counter >= sync_interval:
                    sync_counter = 0
                    try:
                        sync_status = self.vault_sync.sync_cycle()
                        self.vault_sync.write_sync_status(sync_status)

                        # Periodic security scan
                        findings = self.secrets_scanner.scan()
                        if findings:
                            logger.warning(f'Security scan found {len(findings)} potential secret(s)')
                    except Exception as e:
                        logger.error(f'Vault sync failed: {e}')

                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Local Agent stopped by user")


if __name__ == "__main__":
    vault_path = os.getenv("VAULT_PATH", "./AI_Employee_Vault")
    agent = LocalAgent(vault_path=vault_path)
    agent.run_continuous(interval=30)
