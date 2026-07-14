"""
Cloud Agent - Platinum Tier
Owns: Email triage, draft replies, social post drafts/scheduling
Draft-only mode - requires Local approval before send/post
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from audit_logger import AuditLogger
from vault_sync import VaultSync
from secrets_boundary import SyncGuard, EnvGuard

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CloudAgent")


class CloudAgent:
    """
    Cloud Agent runs 24/7 on a cloud VM.
    It handles:
    - Email triage and draft replies
    - Social media post drafts and scheduling
    - Writing updates to /Updates/ folder for Local to merge
    
    It NEVER:
    - Sends emails without Local approval
    - Posts to social media without Local approval
    - Handles payments or banking
    - Stores WhatsApp sessions or banking credentials
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action" / "cloud"
        self.plans = self.vault_path / "Plans" / "cloud"
        self.pending_approval = self.vault_path / "Pending_Approval" / "cloud"
        self.updates = self.vault_path / "Updates"
        self.signals = self.vault_path / "Signals"
        self.done = self.vault_path / "Done" / "cloud"
        self.logs_dir = self.vault_path / "Logs"

        self.logger = AuditLogger(vault_path)
        self.processed_files = set()

        # Platinum Tier: Vault sync & Secrets boundary
        git_remote = os.getenv('VAULT_SYNC_REMOTE')
        self.vault_sync = VaultSync(vault_path, agent_role='cloud', git_remote=git_remote)
        self.sync_guard = SyncGuard(vault_path, agent_role='cloud')
        self.env_guard = EnvGuard(vault_path)
        self.env_guard.load()

        # Ensure folders exist
        for folder in [self.needs_action, self.plans, self.pending_approval,
                       self.updates, self.signals, self.done, self.logs_dir]:
            folder.mkdir(parents=True, exist_ok=True)

        # Initialize git sync if remote is configured
        if git_remote:
            self.vault_sync.init_git()
    
    def check_for_new_emails(self):
        """
        Simulate checking Gmail for new emails.
        In production, integrate with Gmail API.
        """
        # Placeholder - replace with actual Gmail API call
        return []
    
    def create_draft_reply(self, email_data: dict):
        """Create a draft reply email (doesn't send - Local approves)"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        draft_name = f"DRAFT_REPLY_{email_data.get('from', 'unknown').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        draft_path = self.pending_approval / draft_name
        
        content = f"""---
type: approval_request
action: send_email
to: {email_data.get('from', '')}
subject: Re: {email_data.get('subject', '')}
created: {timestamp}
status: pending
agent: cloud
---

# Draft Reply

## Original Email
- **From:** {email_data.get('from', '')}
- **Subject:** {email_data.get('subject', '')}
- **Date:** {email_data.get('date', '')}

## Draft Reply
{email_data.get('draft_body', 'Draft reply content here...')}

## To Approve
Move this file to `/Approved` to send.
Move to `/Rejected` to cancel.
"""
        draft_path.write_text(content, encoding="utf-8")
        
        # Write update for Local to pick up
        update_file = self.updates / f"email_draft_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        update_file.write_text(json.dumps({
            "type": "email_draft",
            "to": email_data.get('from', ''),
            "subject": email_data.get('subject', ''),
            "timestamp": timestamp,
            "status": "pending_approval"
        }, indent=2))
        
        self.logger.log(
            action_type="email_draft_created",
            actor="cloud_agent",
            target=draft_name,
            parameters={"to": email_data.get('from', '')},
            result="success"
        )
        
        logger.info(f"Draft reply created: {draft_name}")
        return draft_path
    
    def create_social_post_draft(self, platform: str, message: str, image_url: str = None, schedule_time: str = None):
        """Create a social media post draft (doesn't post - Local approves)"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        draft_name = f"DRAFT_SOCIAL_{platform}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        draft_path = self.pending_approval / draft_name
        
        content = f"""---
type: approval_request
action: social_media_post
platform: {platform}
message: {message}
image_url: {image_url or 'none'}
schedule_time: {schedule_time or 'immediate'}
created: {timestamp}
status: pending
agent: cloud
---

# Social Media Post Draft

## Details
- **Platform:** {platform}
- **Message:** {message}
- **Image:** {image_url or 'None'}
- **Schedule:** {schedule_time or 'Immediate'}

## To Approve
Move this file to `/Approved` to post.
Move to `/Rejected` to cancel.
"""
        draft_path.write_text(content, encoding="utf-8")
        
        # Write update for Local
        update_file = self.updates / f"social_draft_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        update_file.write_text(json.dumps({
            "type": "social_draft",
            "platform": platform,
            "message": message[:100],
            "timestamp": timestamp,
            "status": "pending_approval"
        }, indent=2))
        
        self.logger.log(
            action_type="social_draft_created",
            actor="cloud_agent",
            target=draft_name,
            parameters={"platform": platform},
            result="success"
        )
        
        logger.info(f"Social post draft created: {draft_name}")
        return draft_path
    
    def process_cloud_actions(self):
        """Process pending cloud actions"""
        if not self.needs_action.exists():
            return
        
        for action_file in self.needs_action.glob("*.md"):
            if action_file.name in self.processed_files:
                continue
            
            logger.info(f"Processing cloud action: {action_file.name}")
            content = action_file.read_text(encoding="utf-8", errors="replace")
            
            # Parse frontmatter
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
            
            action_type = metadata.get("type", "unknown")
            
            if action_type == "email_triage":
                # Create draft reply
                email_data = {
                    "from": metadata.get("from", ""),
                    "subject": metadata.get("subject", ""),
                    "date": metadata.get("date", ""),
                    "draft_body": f"Thank you for your email. We will review and respond shortly."
                }
                self.create_draft_reply(email_data)
            
            elif action_type == "social_post":
                # Create social draft
                self.create_social_post_draft(
                    platform=metadata.get("platform", "all"),
                    message=metadata.get("message", ""),
                    image_url=metadata.get("image_url"),
                    schedule_time=metadata.get("schedule_time")
                )

            elif action_type == "invoice_request":
                # Process invoice via Odoo (simulated or real client)
                logger.info(f"Logging invoice to Odoo: {metadata.get('from', 'Unknown')}")
                
                # Write update for Local to approve payment
                update_file = self.updates / f"invoice_approval_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                update_file.write_text(json.dumps({
                    "type": "invoice_approval",
                    "vendor": metadata.get("from", "Unknown"),
                    "amount": metadata.get("amount", "0.00"),
                    "currency": metadata.get("currency", "USD"),
                    "timestamp": datetime.now().isoformat(),
                    "status": "pending_local_approval"
                }, indent=2))
                
                logger.info(f"Invoice logged. Approval request sent to Local Agent.")
            
            # Move to done
            dest = self.done / action_file.name
            shutil.move(str(action_file), str(dest))
            self.processed_files.add(action_file.name)
            
            self.logger.log(
                action_type="cloud_action_processed",
                actor="cloud_agent",
                target=action_file.name,
                result="success"
            )
    
    def run_continuous(self, interval: int = 30):
        """Run cloud agent continuously"""
        logger.info("Cloud Agent started. Running 24/7...")
        logger.info(f"Vault: {self.vault_path}")
        logger.info(f"Checking every {interval} seconds...")

        sync_counter = 0
        sync_interval = max(interval * 6, 300)  # Sync every 5 min minimum

        try:
            while True:
                # Check for new emails
                emails = self.check_for_new_emails()
                for email in emails:
                    self.create_draft_reply(email)

                # Process cloud actions
                self.process_cloud_actions()

                # Write heartbeat signal
                heartbeat = self.signals / "cloud_heartbeat.json"
                heartbeat.write_text(json.dumps({
                    "agent": "cloud",
                    "timestamp": datetime.now().isoformat(),
                    "status": "alive"
                }, indent=2))

                # Run vault sync periodically
                sync_counter += interval
                if sync_counter >= sync_interval:
                    sync_counter = 0
                    try:
                        sync_status = self.vault_sync.sync_cycle()
                        self.vault_sync.write_sync_status(sync_status)
                    except Exception as e:
                        logger.error(f'Vault sync failed: {e}')

                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Cloud Agent stopped by user")


if __name__ == "__main__":
    vault_path = os.getenv("VAULT_PATH", "./cloud-vault")
    agent = CloudAgent(vault_path=vault_path)
    agent.run_continuous(interval=30)
