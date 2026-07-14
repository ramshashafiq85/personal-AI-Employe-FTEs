"""
HITL Workflow Test Script
Tests the complete Human-in-the-Loop approval flow:
1. Drop a file → Watcher detects it
2. Orchestrator creates plan + approval request
3. Human approves (simulated)
4. Orchestrator executes and moves to Done
"""

import time
import shutil
from pathlib import Path
from datetime import datetime

def main():
    project_root = Path(__file__).parent
    vault = project_root / "AI_Employee_Vault"
    drop_folder = vault / "DropFolder"
    needs_action = vault / "Needs_Action"
    pending = vault / "Pending_Approval"
    approved = vault / "Approved"
    done = vault / "Done"
    
    print("\n" + "="*60)
    print("HITL WORKFLOW TEST")
    print("="*60)
    
    # Step 1: Create a test file in DropFolder
    print("\n[STEP 1] Creating test file in DropFolder...")
    test_file = drop_folder / f"test_hitl_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    test_file.write_text("Test: Create invoice for consulting services - $800")
    print(f"  Created: {test_file.name}")
    
    # Step 2: Wait for watcher to detect (5 seconds)
    print("\n[STEP 2] Waiting 5 seconds for watcher to detect...")
    time.sleep(5)
    
    # Step 3: Run orchestrator to create approval request
    print("\n[STEP 3] Running orchestrator...")
    import subprocess
    result = subprocess.run(
        ["python", "orchestrator.py", "--once"],
        capture_output=True, text=True
    )
    print(result.stdout)
    
    # Step 4: Check if approval request was created
    pending_files = list(pending.glob("*.md"))
    if pending_files:
        approval_file = pending_files[0]
        print(f"\n[STEP 4] Approval request created: {approval_file.name}")
        print(f"  Location: {approval_file}")
    else:
        print("\n[ERROR] No approval request found!")
        return
    
    # Step 5: Simulate human approval (move to Approved)
    print("\n[STEP 5] Simulating human approval (moving to /Approved)...")
    approved_file = approved / approval_file.name
    shutil.move(str(approval_file), str(approved_file))
    print(f"  Moved to: {approved_file}")
    
    # Step 6: Run orchestrator to execute approved action
    print("\n[STEP 6] Running orchestrator to execute approved action...")
    result = subprocess.run(
        ["python", "orchestrator.py", "--once"],
        capture_output=True, text=True
    )
    print(result.stdout)
    
    # Step 7: Verify it was moved to Done
    done_files = list(done.glob("APPROVAL_*.md"))
    if done_files:
        print(f"\n[STEP 7] ✅ SUCCESS! Approved action moved to Done:")
        print(f"  {done_files[-1].name}")
    else:
        print("\n[WARNING] Check manually if action was processed")
    
    # Step 8: Show final status
    print("\n" + "="*60)
    print("FINAL STATUS")
    print("="*60)
    print(f"  DropFolder:       {len(list(drop_folder.glob('*')))} files")
    print(f"  Needs_Action:     {len(list(needs_action.glob('*.md')))} files")
    print(f"  Pending_Approval: {len(list(pending.glob('*.md')))} files")
    print(f"  Approved:         {len(list(approved.glob('*.md')))} files")
    print(f"  Done:             {len(list(done.glob('*.md')))} files")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
