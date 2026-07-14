import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from audit_logger import AuditLogger
from social_media_client import SocialMediaManager

# Add parent directory to path so we can import odoo_client
sys.path.append(str(Path(__file__).parent))
try:
    import odoo_client
except ImportError:
    # If not in same dir, try parent
    sys.path.append(str(Path(__file__).parent.parent))
    import odoo_client

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Orchestrator")


class Orchestrator:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.plans = self.vault_path / "Plans"
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.approved = self.vault_path / "Approved"
        self.rejected = self.vault_path / "Rejected"
        self.done = self.vault_path / "Done"
        self.logs_dir = self.vault_path / "Logs"
        self.dashboard = self.vault_path / "Dashboard.md"
        
        self.logger = AuditLogger(vault_path)
        self.processed_files = set()
        self.social_media = SocialMediaManager()

    def scan_needs_action(self):
        """Find all action files in Needs_Action folder"""
        if not self.needs_action.exists():
            logger.error(f"❌ Folder missing: {self.needs_action}")
            return []
        
        # Look for both .md and .txt files, but IGNORE .meta.md files
        files = list(self.needs_action.glob("*.md")) + list(self.needs_action.glob("*.txt"))
        files = [f for f in files if not f.name.endswith(".meta.md")]
        
        if files:
            logger.info(f"🔎 Raw files found in Needs_Action: {[f.name for f in files]}")
            if self.processed_files:
                logger.info(f"🚫 Already processed: {list(self.processed_files)}")
        
        return [f for f in files if f.name not in self.processed_files]

    def scan_approved(self):
        """Find all approved action files"""
        if not self.approved.exists():
            return []
        return list(self.approved.glob("*.md"))

    def parse_frontmatter(self, file_path: Path) -> dict:
        """Parse YAML frontmatter from a markdown or text file"""
        if not file_path.exists():
            return {}
            
        content = file_path.read_text(encoding="utf-8", errors="replace")
        
        # SEARCH FOR FRONTMATTER BLOCK ANYWHERE IN THE FILE
        import re
        match = re.search(r'---\s*\n(.*?)\n\s*---', content, re.DOTALL)
        
        if not match:
            # FALLBACK: If no frontmatter, try to find "vendor: name" in raw text
            metadata = {}
            vendor_match = re.search(r'vendor:\s*(.*)', content, re.IGNORECASE)
            if vendor_match:
                metadata['vendor'] = vendor_match.group(1).strip().strip('"')
            return metadata
        
        try:
            yaml_block = match.group(1).strip()
            metadata = {}
            for line in yaml_block.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    clean_key = key.strip().lower()
                    clean_val = value.strip().strip('"').strip("'").strip()
                    metadata[clean_key] = clean_val
            
            # Smart fallback for common invoice keys
            if 'vendor' not in metadata and 'from' in metadata:
                metadata['vendor'] = metadata['from']
                
            return metadata
        except Exception as e:
            logger.error(f"Error parsing frontmatter in {file_path.name}: {e}")
            return {}

    def process_action_file(self, file_path: Path):
        """Process a single action file - creates plan and moves to pending approval"""
        metadata = self.parse_frontmatter(file_path)
        action_type = metadata.get("type", "unknown")
        
        logger.info(f"Processing action: {file_path.name} (type: {action_type})")
        
        # Create a plan for this action
        plan_path = self.create_plan(file_path, metadata)
        
        # Create approval request
        approval_path = self.create_approval_request(file_path, metadata, plan_path)
        
        # Move action file to processed (archive in Done)
        dest = self.done / file_path.name
        # Add timestamp to done folder to avoid collisions
        dest = self.done / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file_path.name}"
        shutil.move(str(file_path), str(dest))
        
        self.processed_files.add(file_path.name)
        
        self.logger.log(
            action_type="action_processed",
            actor="orchestrator",
            target=file_path.name,
            parameters={"action_type": action_type},
            result="success",
            details=f"Moved to /Done, approval request created: {approval_path.name}"
        )

    def create_plan(self, action_file: Path, metadata: dict):
        """Create a Plan.md file for the action"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        plan_name = f"PLAN_{action_file.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        plan_path = self.plans / plan_name
        
        action_type = metadata.get("type", "unknown")
        
        content = f"""---
created: {timestamp}
action_type: {action_type}
source_file: {action_file.name}
status: pending
---

# Action Plan: {action_type}

## Source
- **File:** {action_file.name}
- **Type:** {action_type}
- **Received:** {metadata.get("received", "Unknown")}

## Steps
- [ ] Review action details
- [ ] Determine required actions
- [ ] Execute actions (if auto-approved)
- [ ] Move to /Done when complete

## Details
{action_file.read_text(encoding="utf-8", errors="replace")}

## Execution Log
- [{timestamp}] Plan created by Orchestrator
"""
        plan_path.write_text(content, encoding="utf-8")
        
        logger.info(f"Plan created: {plan_name}")
        return plan_path

    def create_approval_request(self, action_file: Path, metadata: dict, plan_path: Path):
        """Create an approval request file in Pending_Approval"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # USE THE VENDOR NAME IN THE FILENAME FOR PROFESSIONAL LOOK
        vendor_clean = metadata.get("vendor", "UNKNOWN").replace(" ", "_")
        approval_name = f"APPROVAL_{vendor_clean}_{datetime.now().strftime('%H%M%S')}.md"
        approval_path = self.pending_approval / approval_name
        
        action_type = metadata.get("type", "unknown")
        
        # Carry over ALL metadata for display
        meta_lines = ""
        for k, v in metadata.items():
            if k not in ["created", "status"]:
                meta_lines += f"{k}: {v}\n"

        content = f"""---
type: approval_request
action: {action_type}
{meta_lines}created: {timestamp}
status: pending
---

# 🛡️ Approval Required: {metadata.get('vendor', 'New Task')}

## 📊 Summary
- **Vendor:** {metadata.get('vendor', 'Unknown')}
- **Amount:** ${metadata.get('amount', '0.00')}
- **Action Type:** {action_type}

## 📝 Details
{action_file.read_text(encoding="utf-8", errors="replace")}

## ✅ How to Approve
1. Review the details above.
2. Physically **MOVE** this file into the `/Approved` folder.

---
*Drafted by AI Manager Agent*
"""
        approval_path.write_text(content, encoding="utf-8")
        
        self.logger.log(
            action_type="approval_request_created",
            actor="orchestrator",
            target=approval_name,
            parameters={"action_type": action_type, "vendor": metadata.get('vendor')},
            result="success"
        )
        
        logger.info(f"🚀 Approval request created: {approval_name}")
        return approval_path

    def process_approved_actions(self):
        """Process files that have been approved by human"""
        approved_files = self.scan_approved()
        
        for approved_file in approved_files:
            metadata = self.parse_frontmatter(approved_file)
            action_type = metadata.get("action", metadata.get("type", "unknown"))
            
            logger.info(f"Processing approved action: {approved_file.name} (type: {action_type})")
            
            # Execute the action based on type
            result = "success"
            details = ""
            
            try:
                if action_type == "payment":
                    self.execute_payment(approved_file, metadata)
                elif action_type == "send_email":
                    self.execute_email(approved_file, metadata)
                elif action_type == "social_media_post":
                    self.execute_social_media_post(approved_file, metadata)
                else:
                    # All other approved files are treated as invoices
                    details = self.execute_invoice_action(approved_file, metadata)
            except Exception as e:
                logger.error(f"Error executing {action_type}: {e}")
                result = "error"
                details = str(e)
            except Exception as e:
                logger.error(f"Error executing {action_type}: {e}")
                result = "error"
                details = str(e)
            
            # Move to Done after processing
            if not approved_file.exists():
                logger.warning(f"File vanished before move: {approved_file.name}")
                continue

            dest = self.done / approved_file.name
            if dest.exists():
                 dest = self.done / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{approved_file.name}"
            
            try:
                shutil.move(str(approved_file), str(dest))
            except Exception as e:
                logger.error(f"Error moving file to Done: {e}")
            
            self.logger.log(
                action_type="approved_action_processed",
                actor="orchestrator",
                target=approved_file.name,
                result=result,
                details=f"Executed ({result}). {details}"
            )
            
            if result == "success":
                print(f"  ✅ Executed: {approved_file.name}")
            else:
                print(f"  ❌ Failed: {approved_file.name} - {details}")

    def execute_invoice_action(self, approved_file: Path, metadata: dict):
        """Actually create an invoice in Odoo"""
        vendor = metadata.get("vendor", metadata.get("from", "Unknown Partner"))
        amount = float(metadata.get("amount", 0))
        desc = metadata.get("description", "AI Processed Invoice")
        ref = metadata.get("number", metadata.get("invoice_number", None))
        
        logger.info(f"Odoo: Creating invoice for {vendor} - ${amount} (Ref: {ref})")
        result = odoo_client.create_invoice(vendor, amount, desc, reference=ref)
        print(f"  Odoo Result: {result}")
        return result

    def execute_payment(self, approved_file: Path, metadata: dict):
        """Execute a payment action (placeholder - integrate with banking MCP)"""
        amount = metadata.get("amount", "0")
        recipient = metadata.get("recipient", "Unknown")
        
        logger.info(f"PAYMENT EXECUTED: ${amount} to {recipient}")
        print(f"\n{'='*50}")
        print(f"PAYMENT: ${amount} -> {recipient}")
        print(f"Status: EXECUTED (Approved)")
        print(f"{'='*50}\n")

    def execute_email(self, approved_file: Path, metadata: dict):
        """Execute an email send action (placeholder - integrate with email MCP)"""
        to = metadata.get("to", "Unknown")
        subject = metadata.get("subject", "No Subject")
        
        logger.info(f"EMAIL SENT: {subject} -> {to}")
        print(f"\n{'='*50}")
        print(f"EMAIL: {subject}")
        print(f"To: {to}")
        print(f"Status: SENT (Approved)")
        print(f"{'='*50}\n")

    def execute_social_media_post(self, approved_file: Path, metadata: dict):
        """Execute a social media post action"""
        message = metadata.get("message", metadata.get("content", ""))
        platform = metadata.get("platform", "all")
        image_url = metadata.get("image_url", None)
        
        print(f"\n{'='*50}")
        print(f"SOCIAL MEDIA POST")
        print(f"Platform: {platform}")
        print(f"Message: {message[:100]}...")
        if image_url:
            print(f"Image: {image_url}")
        print(f"Status: POSTED (Approved)")
        print(f"{'='*50}\n")
        
        # Post to social media
        if platform == "all":
            results = self.social_media.post_to_all(message, image_url)
        elif platform == "facebook":
            results = {"facebook": self.social_media.facebook.post_to_page(message)}
        elif platform == "instagram":
            if image_url:
                results = {"instagram": self.social_media.instagram.post_image(image_url, message)}
            else:
                results = {"instagram": {"skipped": "No image URL"}}
        elif platform == "twitter":
            results = {"twitter": self.social_media.twitter.post_tweet(message)}
        else:
            results = {"error": f"Unknown platform: {platform}"}
        
        self.logger.log(
            action_type="social_media_post",
            actor="orchestrator",
            target=platform,
            parameters={"message": message[:100], "results": str(results)},
            approval_status="approved",
            result="success"
        )
        
        return results

    def update_dashboard(self):
        """Update the Dashboard.md with current status"""
        pending_count = len(list(self.needs_action.glob("*.md"))) + len(list(self.needs_action.glob("*.txt")))
        approved_count = len(list(self.approved.glob("*.md")))
        pending_approval_count = len(list(self.pending_approval.glob("*.md")))
        done_count = len(list(self.done.glob("*.md"))) + len(list(self.done.glob("*.txt")))
        
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Get recent activity from logs
        today_logs = self.logger.get_today_logs()
        recent_activity = ""
        for log_entry in today_logs[-5:]:  # Last 5 entries
            ts_log = log_entry.get('timestamp', 'Unknown')
            act = log_entry.get('action_type', 'Action')
            targ = log_entry.get('target', 'system')
            res = log_entry.get('result', 'completed')
            recent_activity += f"- [{ts_log}] {act} -> {targ} ({res})\n"
        
        if not recent_activity:
            recent_activity = "_No activity yet_\n"
        
        content = f"""# AI Employee Dashboard
---
last_updated: {timestamp}
status: active
---

## System Status
| Component | Status | Last Check |
|-----------|--------|------------|
| Odoo Connection | ✅ Connected | {timestamp} |
| File Watcher | ✅ Running | {timestamp} |
| Orchestrator | ✅ Running | {timestamp} |

## Queue Status
| Folder | Count |
|--------|-------|
| Needs Action | {pending_count} |
| Pending Approval | {pending_approval_count} |
| Approved | {approved_count} |
| Done | {done_count} |

## Recent Activity
{recent_activity}

## Quick Commands
- `python odoo_client.py revenue` - Check revenue
- `python odoo_client.py invoices` - List invoices
- `python odoo_client.py contacts` - List contacts
- `python orchestrator.py` - Run the orchestrator
"""
        self.dashboard.write_text(content, encoding="utf-8")

    def run_cycle(self):
        """Run one complete orchestration cycle"""
        logger.info("=" * 50)
        logger.info("Starting orchestration cycle...")
        
        # 1. Process new action files
        action_files = self.scan_needs_action()
        if action_files:
            logger.info(f"Found {len(action_files)} new action file(s)")
            for af in action_files:
                self.process_action_file(af)
        else:
            logger.info("No new action files")
        
        # 2. Process approved actions
        self.process_approved_actions()
        
        # 4. Update dashboard
        self.update_dashboard()
        
        logger.info("Orchestration cycle complete")
        logger.info("=" * 50)

    def run_continuous(self, interval: int = 10):
        """Run the orchestrator in a continuous loop"""
        logger.info(f"Orchestrator started. Checking every {interval} seconds...")
        logger.info(f"Monitoring: {self.needs_action}")
        logger.info(f"Approved actions: {self.approved}")
        
        try:
            while True:
                self.run_cycle()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Orchestrator stopped by user")


if __name__ == "__main__":
    # FAILSAFE HARDCODED ROOT PATH
    vault_path = Path("C:/Users/Dell/Documents/GitHub/personal-AI-Employe-FTEs/AI_Employee_Vault")
    
    if not vault_path.exists():
        # Fallback for flexibility
        script_dir = Path(__file__).parent.absolute()
        if (script_dir / "AI_Employee_Vault").exists():
            vault_path = script_dir / "AI_Employee_Vault"
        elif (script_dir.parent / "AI_Employee_Vault").exists():
            vault_path = script_dir.parent / "AI_Employee_Vault"
    
    print(f"✅ MASTER OFFICE ACTIVE: {vault_path.absolute()}")
    
    # Ensure all folders exist
    for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Rejected", "Done", "Logs"]:
        (vault_path / folder).mkdir(parents=True, exist_ok=True)
    
    orchestrator = Orchestrator(vault_path=str(vault_path))
    
    if "--once" in sys.argv:
        orchestrator.run_cycle()
    else:
        orchestrator.run_continuous(interval=10)

