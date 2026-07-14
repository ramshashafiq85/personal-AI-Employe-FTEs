import time
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from audit_logger import AuditLogger

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FileSystemWatcher")


class FileSystemWatcher:
    def __init__(self, vault_path: str, drop_folder: str, check_interval: int = 5):
        self.vault_path = Path(vault_path)
        self.drop_folder = Path(drop_folder)
        self.needs_action = self.vault_path / "Needs_Action"
        self.check_interval = check_interval
        self.logger = AuditLogger(vault_path)
        self.known_files = {}  # filename -> hash

    def get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file contents"""
        try:
            return hashlib.md5(file_path.read_bytes()).hexdigest()
        except Exception:
            return ""

    def check_for_new_files(self):
        """Poll the drop folder for new or modified files"""
        if not self.drop_folder.exists():
            self.drop_folder.mkdir(parents=True, exist_ok=True)
            return

        for file_path in self.drop_folder.iterdir():
            if not file_path.is_file():
                continue
            
            # Skip hidden files
            if file_path.name.startswith('.'):
                continue

            current_hash = self.get_file_hash(file_path)
            
            # Check if this is a new or modified file
            if file_path.name not in self.known_files or self.known_files[file_path.name] != current_hash:
                self.known_files[file_path.name] = current_hash
                self._process_file(file_path)

    def _process_file(self, source: Path):
        """Create an action file in Needs_Action for the dropped file"""
        logger.info(f"New/modified file detected: {source.name}")

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        action_filename = f"FILE_{source.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        action_path = self.needs_action / action_filename

        # Get file size
        file_size = source.stat().st_size
        size_kb = file_size / 1024

        # Read file contents if it's text
        try:
            file_content = source.read_text(encoding="utf-8", errors="replace")
        except Exception:
            file_content = "[Binary file - content not displayed]"

        content = f"""---
type: file_drop
original_name: {source.name}
size_kb: {size_kb:.2f}
received: {timestamp}
status: pending
---

## File Drop Detected

A new file has been dropped for processing:

- **Original Name:** {source.name}
- **Size:** {size_kb:.2f} KB
- **Received:** {timestamp}

## File Contents
```
{file_content}
```

## Suggested Actions
- [ ] Review file contents
- [ ] Determine required action
- [ ] Process and move to /Done

## Notes
_Add any additional context here_
"""
        action_path.write_text(content, encoding="utf-8")
        
        # Log the action
        self.logger.log(
            action_type="file_drop_detected",
            actor="filesystem_watcher",
            target=source.name,
            parameters={"size_kb": round(size_kb, 2)},
            result="success",
            details=f"Created action file: {action_filename}"
        )

        logger.info(f"Action file created: {action_filename}")

    def run(self):
        """Start polling the drop folder"""
        self.drop_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"File System Watcher started (polling mode).")
        logger.info(f"Monitoring: {self.drop_folder}")
        logger.info(f"Action files will be created in: {self.needs_action}")
        logger.info(f"Checking every {self.check_interval} seconds...")
        
        try:
            while True:
                self.check_for_new_files()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Stopping File System Watcher...")


if __name__ == "__main__":
    project_root = Path(__file__).parent
    vault_path = project_root / "AI_Employee_Vault"
    drop_folder = vault_path / "DropFolder"
    
    watcher = FileSystemWatcher(
        vault_path=str(vault_path),
        drop_folder=str(drop_folder),
        check_interval=5
    )
    watcher.run()
