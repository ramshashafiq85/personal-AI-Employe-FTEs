"""
Platinum Tier Demo Script
Demonstrates the complete Cloud → Local flow:
1. Email arrives while Local is offline
2. Cloud drafts reply + writes approval file
3. When Local returns, user approves
4. Local executes send via MCP → logs → moves task to /Done
"""

import time
import json
import shutil
from pathlib import Path
from datetime import datetime


def main():
    print("\n" + "="*70)
    print("PLATINUM TIER DEMO: Cloud → Local Executive Flow")
    print("="*70)
    
    # Setup paths
    project_root = Path(__file__).parent
    cloud_vault = project_root / "cloud-vault"
    local_vault = project_root / "AI_Employee_Vault"
    
    # Create cloud vault structure
    for folder in ["Needs_Action/cloud", "Pending_Approval/cloud", "Updates", 
                   "Signals/cloud", "Signals/local", "Done/cloud", "Logs"]:
        (cloud_vault / folder).mkdir(parents=True, exist_ok=True)
    
    print("\n[STEP 1] Simulating: Email arrives while Local is OFFLINE")
    print("-" * 70)
    
    # Cloud detects new email
    email_data = {
        "from": "client@example.com",
        "subject": "Urgent: Project Update Needed",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "body": "Hi, I need the project status update by EOD. Can you send it?"
    }
    
    print(f"  Email received from: {email_data['from']}")
    print(f"  Subject: {email_data['subject']}")
    print(f"  Local Agent: OFFLINE")
    print(f"  Cloud Agent: Processing...")
    
    # Cloud creates draft reply
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    draft_file = cloud_vault / "Pending_Approval" / "cloud" / f"DRAFT_REPLY_client_{timestamp}.md"
    
    draft_content = f"""---
type: approval_request
action: send_email
to: {email_data['from']}
subject: Re: {email_data['subject']}
created: {datetime.now().isoformat()}
status: pending
agent: cloud
---

# Draft Reply

## Original Email
- **From:** {email_data['from']}
- **Subject:** {email_data['subject']}

## Draft Reply
Thank you for reaching out. The project is on track. I'll have the full status update to you by 3 PM today.

Best regards,
AI Employee

## To Approve
Move this file to `/Approved` to send.
"""
    
    draft_file.write_text(draft_content, encoding="utf-8")
    print(f"  ✅ Cloud created draft reply: {draft_file.name}")
    
    # Cloud writes update for Local
    update_file = cloud_vault / "Updates" / f"email_draft_{timestamp}.json"
    update_file.write_text(json.dumps({
        "type": "email_draft",
        "to": email_data['from'],
        "subject": email_data['subject'],
        "timestamp": datetime.now().isoformat(),
        "status": "pending_approval"
    }, indent=2))
    print(f"  ✅ Cloud wrote update: {update_file.name}")
    
    # Cloud sends A2A message
    from a2a_messenger import A2AMessenger
    cloud_messenger = A2AMessenger(str(cloud_vault), "cloud")
    msg_id = cloud_messenger.send_command(
        "email_draft_ready",
        {"to": email_data['from'], "subject": email_data['subject']}
    )
    print(f"  ✅ Cloud sent A2A message: {msg_id}")
    
    print("\n[STEP 2] Local Agent comes ONLINE")
    print("-" * 70)
    
    # Simulate Local coming online
    print("  Local Agent starting...")
    print("  Checking for Cloud updates...")
    
    # Local checks updates
    local_updates = local_vault / "Updates"
    local_updates.mkdir(parents=True, exist_ok=True)
    
    # Copy cloud updates to local (simulating sync)
    for update_file in (cloud_vault / "Updates").glob("*.json"):
        shutil.copy(str(update_file), str(local_updates / update_file.name))
        print(f"  ✅ Synced update: {update_file.name}")
    
    # Local checks A2A messages
    local_messenger = A2AMessenger(str(local_vault), "local")
    messages = local_messenger.check_inbox()
    if messages:
        print(f"  ✅ Received {len(messages)} A2A message(s) from Cloud")
        for msg in messages:
            print(f"     - [{msg['type']}] {msg['payload']}")
    
    print("\n[STEP 3] User reviews and approves the draft")
    print("-" * 70)
    
    # Copy draft to local pending approval
    local_pending = local_vault / "Pending_Approval"
    local_pending.mkdir(parents=True, exist_ok=True)
    local_draft = local_pending / draft_file.name
    shutil.copy(str(draft_file), str(local_draft))
    print(f"  Draft available for review: {local_draft.name}")
    print("  User reviews draft...")
    print("  User approves! Moving to /Approved...")
    
    local_approved = local_vault / "Approved"
    local_approved.mkdir(parents=True, exist_ok=True)
    approved_file = local_approved / local_draft.name
    shutil.move(str(local_draft), str(approved_file))
    print(f"  ✅ Moved to Approved: {approved_file.name}")
    
    print("\n[STEP 4] Local executes send via MCP → logs → moves to /Done")
    print("-" * 70)
    
    # Local processes approved action
    print("  Local Agent processing approved action...")
    print(f"  EXECUTING: Send email to {email_data['from']}")
    print(f"  Subject: Re: {email_data['subject']}")
    print(f"  Status: SENT ✅")
    
    # Move to Done
    local_done = local_vault / "Done"
    local_done.mkdir(parents=True, exist_ok=True)
    done_file = local_done / approved_file.name
    shutil.move(str(approved_file), str(done_file))
    print(f"  ✅ Moved to Done: {done_file.name}")
    
    # Log the action
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": "email_send",
        "actor": "local_agent",
        "target": email_data['from'],
        "parameters": {"subject": f"Re: {email_data['subject']}"},
        "approval_status": "approved",
        "approved_by": "human",
        "result": "success"
    }
    
    log_file = local_vault / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text())
        except json.JSONDecodeError:
            logs = []
    logs.append(log_entry)
    log_file.write_text(json.dumps(logs, indent=2))
    print(f"  ✅ Action logged")
    
    # Final status
    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print(f"  Cloud Vault Drafts:   {len(list((cloud_vault / 'Pending_Approval' / 'cloud').glob('*.md')))}")
    print(f"  Local Pending:        {len(list(local_pending.glob('*.md')))}")
    print(f"  Local Approved:       {len(list(local_approved.glob('*.md')))}")
    print(f"  Local Done:           {len(list(local_done.glob('*.md')))}")
    print("="*70 + "\n")
    
    print("✅ Platinum Tier Demo Successful!")
    print("   - Cloud drafted reply while Local was offline")
    print("   - Local synced and presented for approval")
    print("   - User approved, Local executed and logged")
    print("   - Complete audit trail maintained\n")


if __name__ == "__main__":
    main()
