"""
A2A (Agent-to-Agent) Communication Protocol
Enables direct messaging between Cloud and Local agents
while keeping the vault as the audit record.
"""

import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime


class A2AMessenger:
    """
    Agent-to-Agent communication system.
    
    Phase 1: File-based (vault sync)
    Phase 2: Direct A2A messages (optional upgrade)
    
    Messages are written to:
    - /Signals/<agent>/outbox/  (messages to send)
    - /Signals/<agent>/inbox/   (messages received)
    
    Each message has:
    - Unique ID (hash-based)
    - Timestamp
    - Sender/Receiver
    - Type (command, status, data)
    - Payload
    - Acknowledgment status
    """
    
    def __init__(self, vault_path: str, agent_role: str):
        """
        Initialize A2A Messenger.
        
        Args:
            vault_path: Path to the vault
            agent_role: 'cloud' or 'local'
        """
        self.vault_path = Path(vault_path)
        self.agent_role = agent_role
        self.signals_dir = self.vault_path / "Signals"
        self.outbox = self.signals_dir / agent_role / "outbox"
        self.inbox = self.signals_dir / agent_role / "inbox"
        
        # Ensure directories exist
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)
    
    def create_message(self, message_type: str, payload: dict, receiver: str = None) -> str:
        """
        Create a message and write to outbox.
        
        Args:
            message_type: 'command', 'status', 'data', 'heartbeat'
            payload: Message content
            receiver: 'cloud' or 'local'
        
        Returns:
            Message ID
        """
        if receiver is None:
            receiver = "local" if self.agent_role == "cloud" else "cloud"
        
        timestamp = datetime.now().isoformat()
        message_id = hashlib.md5(f"{timestamp}{payload}".encode()).hexdigest()[:12]
        
        message = {
            "id": message_id,
            "type": message_type,
            "sender": self.agent_role,
            "receiver": receiver,
            "timestamp": timestamp,
            "payload": payload,
            "status": "sent",
            "acknowledged": False
        }
        
        message_file = self.outbox / f"msg_{message_id}.json"
        message_file.write_text(json.dumps(message, indent=2))
        
        return message_id
    
    def check_inbox(self) -> list:
        """
        Check inbox for new messages.
        
        Returns:
            List of new messages
        """
        if not self.inbox.exists():
            return []
        
        messages = []
        for msg_file in self.inbox.glob("msg_*.json"):
            try:
                data = json.loads(msg_file.read_text())
                if data.get("status") == "sent" and not data.get("acknowledged"):
                    messages.append(data)
                    
                    # Mark as acknowledged
                    data["acknowledged"] = True
                    data["status"] = "read"
                    msg_file.write_text(json.dumps(data, indent=2))
            except (json.JSONDecodeError, KeyError):
                continue
        
        return messages
    
    def send_command(self, command: str, params: dict = None) -> str:
        """Send a command to the other agent"""
        payload = {"command": command, "params": params or {}}
        return self.create_message("command", payload)
    
    def send_status(self, status: str, details: dict = None) -> str:
        """Send status update to the other agent"""
        payload = {"status": status, "details": details or {}}
        return self.create_message("status", payload)
    
    def send_data(self, data_type: str, data: dict) -> str:
        """Send data to the other agent"""
        payload = {"data_type": data_type, "data": data}
        return self.create_message("data", payload)
    
    def send_heartbeat(self) -> str:
        """Send heartbeat signal"""
        payload = {"agent": self.agent_role, "timestamp": datetime.now().isoformat()}
        return self.create_message("heartbeat", payload)
    
    def get_message_status(self, message_id: str) -> dict:
        """Get status of a sent message"""
        message_file = self.outbox / f"msg_{message_id}.json"
        if not message_file.exists():
            return {"error": "Message not found"}
        
        return json.loads(message_file.read_text())
    
    def acknowledge_message(self, message_id: str):
        """Acknowledge receipt of a message"""
        # Check if message is in inbox
        message_file = self.inbox / f"msg_{message_id}.json"
        if not message_file.exists():
            return False
        
        data = json.loads(message_file.read_text())
        data["acknowledged"] = True
        data["status"] = "acknowledged"
        data["acknowledged_at"] = datetime.now().isoformat()
        message_file.write_text(json.dumps(data, indent=2))
        
        return True
    
    def clear_old_messages(self, max_age_hours: int = 24):
        """Clear old messages from outbox and inbox"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for folder in [self.outbox, self.inbox]:
            if not folder.exists():
                continue
            
            for msg_file in folder.glob("msg_*.json"):
                try:
                    data = json.loads(msg_file.read_text())
                    msg_time = datetime.fromisoformat(data["timestamp"]).timestamp()
                    
                    if msg_time < cutoff:
                        msg_file.unlink()
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python a2a_messenger.py <agent_role> <command> [args]")
        print("Commands:")
        print("  send_command <command> [json_params]  - Send command")
        print("  send_status <status> [json_details]   - Send status")
        print("  check_inbox                           - Check for new messages")
        print("  heartbeat                             - Send heartbeat")
        sys.exit(1)
    
    agent_role = sys.argv[1]
    command = sys.argv[2]
    
    messenger = A2AMessenger(vault_path="./AI_Employee_Vault", agent_role=agent_role)
    
    if command == "send_command":
        cmd = sys.argv[3] if len(sys.argv) > 3 else "test"
        params = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        msg_id = messenger.send_command(cmd, params)
        print(f"Command sent. Message ID: {msg_id}")
    
    elif command == "send_status":
        status = sys.argv[3] if len(sys.argv) > 3 else "ok"
        details = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        msg_id = messenger.send_status(status, details)
        print(f"Status sent. Message ID: {msg_id}")
    
    elif command == "check_inbox":
        messages = messenger.check_inbox()
        if messages:
            print(f"Found {len(messages)} new message(s):")
            for msg in messages:
                print(f"  - [{msg['type']}] {msg['payload']}")
        else:
            print("No new messages")
    
    elif command == "heartbeat":
        msg_id = messenger.send_heartbeat()
        print(f"Heartbeat sent. Message ID: {msg_id}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
