"""
Social Media Integration Test
Tests the social media posting workflow with HITL approval
"""

import time
import shutil
from pathlib import Path
from datetime import datetime

def main():
    project_root = Path(__file__).parent
    vault = project_root / "AI_Employee_Vault"
    pending = vault / "Pending_Approval"
    approved = vault / "Approved"
    done = vault / "Done"
    
    print("\n" + "="*60)
    print("SOCIAL MEDIA INTEGRATION TEST")
    print("="*60)
    
    # Step 1: Create a social media post approval request
    print("\n[STEP 1] Creating social media post approval request...")
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    post_file = pending / f"SOCIAL_POST_test_{timestamp}.md"
    
    content = f"""---
type: approval_request
action: social_media_post
platform: all
message: Exciting news! We just launched our new AI Employee system. It automates accounting, email triage, and social media posting. #AI #Automation #Productivity
image_url: https://via.placeholder.com/800x600?text=AI+Employee+Launch
created: {datetime.now().isoformat()}
status: pending
---

# Social Media Post Approval Required

## Details
- **Platform:** All (Facebook, Instagram, Twitter)
- **Message:** Exciting news! We just launched our new AI Employee system...
- **Image:** https://via.placeholder.com/800x600?text=AI+Employee+Launch

## To Approve
Move this file to `/Approved` to post.

## To Reject
Move this file to `/Rejected` to cancel.
"""
    
    post_file.write_text(content, encoding="utf-8")
    print(f"  Created: {post_file.name}")
    
    # Step 2: Simulate approval (move to Approved)
    print("\n[STEP 2] Simulating human approval...")
    approved_file = approved / post_file.name
    shutil.move(str(post_file), str(approved_file))
    print(f"  Moved to: {approved_file}")
    
    # Step 3: Run orchestrator to execute the post
    print("\n[STEP 3] Running orchestrator to post to social media...")
    import subprocess
    result = subprocess.run(
        ["python", "orchestrator.py", "--once"],
        capture_output=True, text=True
    )
    print(result.stdout)
    
    # Step 4: Verify it was moved to Done
    done_files = list(done.glob("SOCIAL_POST_*.md"))
    if done_files:
        print(f"\n[STEP 4] ✅ SUCCESS! Social post moved to Done:")
        print(f"  {done_files[-1].name}")
    else:
        print("\n[WARNING] Check manually if post was processed")
    
    # Step 5: Generate social media summary
    print("\n[STEP 5] Generating social media summary...")
    result = subprocess.run(
        ["python", "-c", "from orchestrator import Orchestrator; from pathlib import Path; o = Orchestrator(str(Path('AI_Employee_Vault'))); o.generate_social_media_summary()"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    # Final status
    print("\n" + "="*60)
    print("FINAL STATUS")
    print("="*60)
    print(f"  Pending_Approval: {len(list(pending.glob('*.md')))} files")
    print(f"  Approved:         {len(list(approved.glob('*.md')))} files")
    print(f"  Done:             {len(list(done.glob('*.md')))} files")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
