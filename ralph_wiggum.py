"""
Ralph Wiggum Loop Plugin for Claude Code

This plugin intercepts Claude's exit and re-injects prompts until tasks complete.
It monitors the /Done folder to determine if a task has been completed.

Usage:
  /ralph-loop "Process all files in /Needs_Action" --max-iterations 10

How it works:
1. Orchestrator creates state file with prompt
2. Claude works on task
3. Claude tries to exit
4. Stop hook checks: Is task file in /Done?
5. YES -> Allow exit (complete)
6. NO -> Block exit, re-inject prompt (loop continues)
7. Repeat until complete or max iterations
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime


class RalphWiggumLoop:
    def __init__(self, vault_path: str, max_iterations: int = 10):
        self.vault_path = Path(vault_path)
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.state_file = self.vault_path / ".ralph_state.json"
        self.done_folder = self.vault_path / "Done"
        self.needs_action = self.vault_path / "Needs_Action"
        self.plans = self.vault_path / "Plans"
        self.pending_approval = self.vault_path / "Pending_Approval"
        
    def save_state(self, prompt: str, iteration: int = 0):
        """Save the current state to a JSON file"""
        state = {
            "prompt": prompt,
            "iteration": iteration,
            "max_iterations": self.max_iterations,
            "started": datetime.now().isoformat(),
            "last_check": datetime.now().isoformat(),
            "status": "running"
        }
        self.state_file.write_text(json.dumps(state, indent=2))
        
    def load_state(self) -> dict:
        """Load the current state"""
        if not self.state_file.exists():
            return {}
        return json.loads(self.state_file.read_text())
    
    def check_task_completion(self) -> bool:
        """
        Check if the current task has been completed.
        Returns True if task is done, False otherwise.
        """
        # Strategy 1: Check if all files moved from Needs_Action to Done
        pending_count = len(list(self.needs_action.glob("*.md"))) if self.needs_action.exists() else 0
        pending_approval_count = len(list(self.pending_approval.glob("*.md"))) if self.pending_approval.exists() else 0
        
        # If nothing is pending and nothing needs action, task is likely complete
        if pending_count == 0 and pending_approval_count == 0:
            return True
        
        # Strategy 2: Check if any plan files have "status: complete"
        if self.plans.exists():
            for plan_file in self.plans.glob("*.md"):
                content = plan_file.read_text(encoding="utf-8", errors="replace")
                if "status: complete" in content.lower():
                    return True
        
        return False
    
    def should_continue(self) -> bool:
        """Determine if the loop should continue"""
        if self.current_iteration >= self.max_iterations:
            print(f"\n[RALPH] Max iterations reached ({self.max_iterations}). Stopping.")
            return False
        
        if self.check_task_completion():
            print(f"\n[RALPH] Task completed! Exiting after {self.current_iteration} iterations.")
            return False
        
        return True
    
    def run_loop(self, prompt: str):
        """
        Run the Ralph Wiggum loop.
        This is called by the orchestrator to keep Claude working until done.
        """
        print("\n" + "="*60)
        print("RALPH WIGGUM LOOP STARTED")
        print("="*60)
        print(f"Prompt: {prompt}")
        print(f"Max iterations: {self.max_iterations}")
        print(f"Vault: {self.vault_path}")
        print("="*60 + "\n")
        
        self.save_state(prompt, 0)
        
        while self.should_continue():
            self.current_iteration += 1
            
            print(f"\n[RALPH] Iteration {self.current_iteration}/{self.max_iterations}")
            print(f"[RALPH] Checking task status...")
            
            pending_count = len(list(self.needs_action.glob("*.md"))) if self.needs_action.exists() else 0
            pending_approval_count = len(list(self.pending_approval.glob("*.md"))) if self.pending_approval.exists() else 0
            done_count = len(list(self.done_folder.glob("*.md"))) if self.done_folder.exists() else 0
            
            print(f"[RALPH] Pending: {pending_count} | Awaiting Approval: {pending_approval_count} | Done: {done_count}")
            
            if not self.should_continue():
                break
            
            # Update state
            self.save_state(prompt, self.current_iteration)
            
            # In a real Claude integration, this would:
            # 1. Block Claude's exit
            # 2. Re-inject the prompt with previous context
            # 3. Let Claude continue working
            #
            # For now, we simulate this by running the orchestrator
            print(f"[RALPH] Re-injecting prompt to Claude...")
            print(f"[RALPH] Running orchestrator cycle...")
            
            # Run orchestrator to process any new files
            from orchestrator import Orchestrator
            orchestrator = Orchestrator(vault_path=str(self.vault_path))
            orchestrator.run_cycle()
            
            # Wait a bit before next check
            time.sleep(2)
        
        # Final state update
        state = self.load_state()
        state["status"] = "completed" if self.check_task_completion() else "max_iterations_reached"
        state["ended"] = datetime.now().isoformat()
        state["total_iterations"] = self.current_iteration
        self.state_file.write_text(json.dumps(state, indent=2))
        
        print("\n" + "="*60)
        print("RALPH WIGGUM LOOP ENDED")
        print(f"Status: {state['status']}")
        print(f"Total iterations: {self.current_iteration}")
        print("="*60 + "\n")
        
        return state["status"] == "completed"


def create_ralph_plugin_config():
    """Create the Claude Code plugin configuration for Ralph Wiggum"""
    config = {
        "name": "ralph-wiggum",
        "version": "1.0.0",
        "description": "Autonomous persistence - keeps Claude working until tasks complete",
        "hooks": {
            "stop": {
                "enabled": True,
                "script": "ralph_wiggum.py",
                "condition": "check_task_completion",
                "action": "reinject_prompt"
            }
        },
        "settings": {
            "max_iterations": 10,
            "check_interval_seconds": 5,
            "vault_path": "./AI_Employee_Vault"
        }
    }
    
    config_path = Path(__file__).parent / ".claude" / "plugins" / "ralph-wiggum" / "plugin.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))
    
    print(f"Ralph Wiggum plugin config created at: {config_path}")
    return config_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ralph Wiggum Loop - Autonomous persistence for Claude Code")
    parser.add_argument("prompt", type=str, help="The prompt to keep re-injecting until task completes")
    parser.add_argument("--max-iterations", type=int, default=10, help="Maximum number of iterations (default: 10)")
    parser.add_argument("--vault", type=str, default="AI_Employee_Vault", help="Path to the vault (default: AI_Employee_Vault)")
    parser.add_argument("--setup", action="store_true", help="Create the Claude plugin config")
    
    args = parser.parse_args()
    
    if args.setup:
        create_ralph_plugin_config()
    
    vault_path = Path(args.vault)
    if not vault_path.exists():
        print(f"Error: Vault path not found: {vault_path}")
        sys.exit(1)
    
    ralph = RalphWiggumLoop(vault_path=str(vault_path), max_iterations=args.max_iterations)
    success = ralph.run_loop(args.prompt)
    
    sys.exit(0 if success else 1)
