#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vault Sync - Git-based synchronization between Cloud and Local vaults.

Phase 1 Platinum: Syncs state/markdown files only. Secrets NEVER sync.
Uses Git for version control, tracking, and conflict resolution.

Architecture:
- Local vault: AI_Employee_Vault/ (source of truth for approvals, payments, WhatsApp)
- Cloud vault: cloud-vault/ (source of truth for email drafts, social drafts)
- Both push/pull to a shared Git remote (GitHub private repo, GitLab, etc.)

Sync Rules:
- Sync: *.md files in Needs_Action/, Plans/, Pending_Approval/, Approved/, Rejected/, Done/, Signals/, Updates/, A2A_Messages/
- Sync: *.json files in Signals/, Updates/, A2A_Messages/
- NEVER sync: .env, *.pickle, credentials.json, .whatsapp_session/, ssl/, Logs/*.json, *.key, *.pem, *.crt
- Claim-by-move: First agent to move a file from Needs_Action/ to In_Progress/<agent>/ owns it

Usage:
    python vault_sync.py <vault_path> <agent_role> [--push] [--pull] [--sync]

Example:
    python vault_sync.py ./AI_Employee_Vault local --sync
    python vault_sync.py ./cloud-vault cloud --sync
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VaultSync')


# ============================================================
# SECRET FILES BLOCKLIST - NEVER synced to cloud
# ============================================================
SECRET_PATTERNS = [
    '.env',
    '.env.*',
    '*.pickle',
    'credentials.json',
    '*.key',
    '*.pem',
    '*.crt',
    '.whatsapp_session',
    'ssl/',
    'token.pickle',
    'gmail_token.pickle',
    '*.token',
    'odoo-data',
    'postgres-data',
    '__pycache__',
    '*.pyc',
    '.git',
    '.obsidian',
]

# ============================================================
# SYNC DIRECTORIES - only these are synced
# ============================================================
SYNC_DIRS = [
    'Needs_Action',
    'Plans',
    'Pending_Approval',
    'Approved',
    'Rejected',
    'Done',
    'Signals',
    'Updates',
    'A2A_Messages',
    'In_Progress',
]

# ============================================================
# SYNC FILE EXTENSIONS
# ============================================================
SYNC_EXTENSIONS = {'.md', '.json', '.txt'}


class VaultSync:
    """Git-based vault synchronization."""

    def __init__(self, vault_path: str, agent_role: str, git_remote: str = None):
        """
        Initialize Vault Sync.

        Args:
            vault_path: Path to vault directory
            agent_role: 'cloud' or 'local'
            git_remote: Git remote URL (GitHub/GitLab private repo)
        """
        self.vault_path = Path(vault_path).resolve()
        self.agent_role = agent_role
        self.git_remote = git_remote or os.getenv('VAULT_SYNC_REMOTE')
        self.git_branch = f'{agent_role}/main'

        # Ensure required directories exist
        for d in SYNC_DIRS:
            (self.vault_path / d).mkdir(parents=True, exist_ok=True)

        # In_Progress subdirectories
        (self.vault_path / 'In_Progress' / agent_role).mkdir(parents=True, exist_ok=True)

        # Secret files tracking
        self.secret_patterns = SECRET_PATTERNS

    # ──────────────────────────────────────────────
    #  Git Operations
    # ──────────────────────────────────────────────

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command."""
        result = subprocess.run(
            ['git', *args],
            cwd=str(self.vault_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            logger.error(f'git {" ".join(args)} failed: {result.stderr.strip()}')
            raise RuntimeError(f'git {" ".join(args)} failed: {result.stderr.strip()}')
        return result

    def init_git(self) -> bool:
        """Initialize git repo in vault if not already done."""
        git_dir = self.vault_path / '.git'
        if not git_dir.exists():
            logger.info(f'Initializing git repo in {self.vault_path}')
            self._run_git('init')
            self._run_git('checkout', '-b', self.git_branch)
            self._run_git('add', '.gitignore')
            self._run_git('commit', '-m', 'Initial vault setup', '--allow-empty')
            if self.git_remote:
                self._run_git('remote', 'add', 'origin', self.git_remote)
                self._run_git('push', '-u', 'origin', self.git_branch, '--force')
            return True
        return False  # Already initialized

    def stage_syncable_files(self) -> List[str]:
        """
        Stage all syncable files (excluding secrets).
        Returns list of staged file paths.
        """
        staged = []
        for sync_dir in SYNC_DIRS:
            dir_path = self.vault_path / sync_dir
            if not dir_path.exists():
                continue
            for file_path in dir_path.rglob('*'):
                if file_path.is_file() and self._is_syncable(file_path):
                    rel = file_path.relative_to(self.vault_path)
                    self._run_git('add', str(rel), check=False)
                    staged.append(str(rel))
        return staged

    def _is_syncable(self, file_path: Path) -> bool:
        """Check if a file should be synced (not a secret)."""
        # Check extension
        if file_path.suffix not in SYNC_EXTENSIONS:
            return False

        # Check against secret patterns
        name = file_path.name
        for pattern in self.secret_patterns:
            if pattern.endswith('/'):
                # Directory pattern
                if pattern.rstrip('/') in file_path.parts:
                    return False
            elif '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(name, pattern):
                    return False
            else:
                if name == pattern:
                    return False

        # Check file size (skip files > 10MB)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:
                return False
        except OSError:
            return False

        return True

    def commit(self, message: str = None) -> Optional[str]:
        """Commit staged changes."""
        if not message:
            message = f'Sync by {self.agent_role} agent - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        # Check if there's anything to commit
        status = self._run_git('status', '--porcelain')
        if not status.stdout.strip():
            return None  # Nothing to commit

        self._run_git('commit', '-m', message)
        commit_hash = self._run_git('rev-parse', 'HEAD').stdout.strip()
        logger.info(f'Committed: {commit_hash[:8]} - {message}')
        return commit_hash

    def push(self) -> bool:
        """Push commits to remote."""
        if not self.git_remote:
            logger.warning('No git remote configured. Skipping push.')
            return False

        try:
            self._run_git('push', 'origin', self.git_branch)
            logger.info('Pushed to remote successfully')
            return True
        except RuntimeError as e:
            logger.error(f'Push failed: {e}')
            return False

    def pull(self) -> bool:
        """Pull and merge from remote."""
        if not self.git_remote:
            logger.warning('No git remote configured. Skipping pull.')
            return False

        try:
            # Fetch all branches
            self._run_git('fetch', 'origin')

            # Try to merge cloud branch
            cloud_branch = 'cloud/main' if self.agent_role == 'local' else 'local/main'
            result = self._run_git('merge', f'origin/{cloud_branch}', check=False)

            if result.returncode == 0:
                logger.info(f'Merged {cloud_branch} successfully')
                return True
            else:
                # Merge conflict - auto-resolve by keeping local changes for conflicts
                logger.warning(f'Merge conflict with {cloud_branch}, auto-resolving')
                self._resolve_merge_conflicts()
                return True
        except RuntimeError as e:
            logger.error(f'Pull failed: {e}')
            return False

    def _resolve_merge_conflicts(self):
        """Auto-resolve merge conflicts: keep local for same-role files, accept cloud for cloud files."""
        status = self._run_git('status', '--porcelain')
        conflicted = [
            line.strip() for line in status.stdout.splitlines()
            if line.startswith('UU') or line.startswith('AA') or line.startswith('DU')
        ]

        for file_path in conflicted:
            # Accept "ours" (local agent) for approval/payment files
            if 'Pending_Approval' in file_path or 'Approved' in file_path or 'Accounting' in file_path:
                self._run_git('checkout', '--ours', file_path, check=False)
            else:
                # For other files, accept "theirs" (cloud agent drafts)
                self._run_git('checkout', '--theirs', file_path, check=False)
            self._run_git('add', file_path, check=False)

        # Commit the merge resolution
        self.commit('Auto-resolved merge conflicts')

    # ──────────────────────────────────────────────
    #  Claim-by-Move Logic
    # ──────────────────────────────────────────────

    def claim_item(self, source_file: str) -> Optional[Path]:
        """
        Claim a file from Needs_Action/ by moving it to In_Progress/<agent>/.
        First agent to move the file owns it. Other agents must ignore it.

        Args:
            source_file: Relative path within vault (e.g., Needs_Action/email.md)

        Returns:
            Path to claimed file, or None if already claimed
        """
        source = self.vault_path / source_file
        if not source.exists():
            logger.debug(f'Source file not found: {source_file}')
            return None

        # Check if another agent already claimed it
        claim_marker = self.vault_path / f'{source_file}.claimed'
        if claim_marker.exists():
            try:
                claim_data = json.loads(claim_marker.read_text())
                if claim_data.get('agent') != self.agent_role:
                    logger.debug(f'File already claimed by {claim_data["agent"]}: {source_file}')
                    return None
            except (json.JSONDecodeError, KeyError):
                pass

        # Move to In_Progress/<agent>/
        dest = self.vault_path / 'In_Progress' / self.agent_role / Path(source_file).name
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(source), str(dest))

            # Create claim marker
            claim_marker = self.vault_path / f'{source_file}.claimed'
            claim_marker.write_text(json.dumps({
                'agent': self.agent_role,
                'timestamp': datetime.now().isoformat(),
                'source': source_file,
                'destination': str(dest.relative_to(self.vault_path))
            }, indent=2))

            logger.info(f'Claimed: {source_file} -> In_Progress/{self.agent_role}/')
            return dest
        except Exception as e:
            logger.error(f'Failed to claim {source_file}: {e}')
            return None

    def release_item(self, source_file: str, destination: str = 'Done') -> bool:
        """
        Release a claimed item by moving it to Done/ (or another folder).
        Removes the claim marker.

        Args:
            source_file: Original filename
            destination: Target folder (Done, Rejected, etc.)

        Returns:
            True if released successfully
        """
        in_progress = self.vault_path / 'In_Progress' / self.agent_role / source_file
        dest_dir = self.vault_path / destination

        if not in_progress.exists():
            logger.debug(f'File not in In_Progress: {source_file}')
            return False

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(in_progress), str(dest_dir / source_file))

            # Remove claim marker
            claim_marker = self.vault_path / f'Needs_Action/{source_file}.claimed'
            if claim_marker.exists():
                claim_marker.unlink()

            logger.info(f'Released: {source_file} -> {destination}/')
            return True
        except Exception as e:
            logger.error(f'Failed to release {source_file}: {e}')
            return False

    def get_claims(self) -> List[dict]:
        """Get all active claims."""
        claims = []
        in_progress_dir = self.vault_path / 'In_Progress'
        if not in_progress_dir.exists():
            return claims

        for agent_dir in in_progress_dir.iterdir():
            if agent_dir.is_dir():
                for file_path in agent_dir.iterdir():
                    if file_path.is_file():
                        claims.append({
                            'agent': agent_dir.name,
                            'file': file_path.name,
                            'path': str(file_path)
                        })
        return claims

    # ──────────────────────────────────────────────
    #  Full Sync Cycle
    # ──────────────────────────────────────────────

    def sync_cycle(self) -> dict:
        """
        Run a full sync cycle:
        1. Pull from remote
        2. Stage syncable files
        3. Commit changes
        4. Push to remote

        Returns:
            Sync status dict
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'agent': self.agent_role,
            'pull': False,
            'staged': [],
            'committed': None,
            'push': False,
            'errors': []
        }

        try:
            # Step 1: Pull
            result['pull'] = self.pull()

            # Step 2: Stage
            result['staged'] = self.stage_syncable_files()

            # Step 3: Commit
            result['committed'] = self.commit()

            # Step 4: Push
            if result['committed']:
                result['push'] = self.push()

            logger.info(
                f'Sync cycle complete: '
                f'pull={result["pull"]}, '
                f'staged={len(result["staged"])}, '
                f'committed={result["committed"]}, '
                f'push={result["push"]}'
            )

        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f'Sync cycle failed: {e}', exc_info=True)

        return result

    # ──────────────────────────────────────────────
    #  Dashboard Sync Signal
    # ──────────────────────────────────────────────

    def write_sync_status(self, status: dict):
        """Write sync status signal file for other agents to read."""
        signals_dir = self.vault_path / 'Signals'
        signals_dir.mkdir(parents=True, exist_ok=True)

        status_file = signals_dir / f'{self.agent_role}_sync_status.json'
        status_file.write_text(json.dumps(status, indent=2))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Vault Git Sync')
    parser.add_argument('vault_path', help='Path to vault directory')
    parser.add_argument('agent_role', choices=['cloud', 'local'], help='Agent role')
    parser.add_argument('--remote', help='Git remote URL')
    parser.add_argument('--init', action='store_true', help='Initialize git repo')
    parser.add_argument('--push', action='store_true', help='Push to remote')
    parser.add_argument('--pull', action='store_true', help='Pull from remote')
    parser.add_argument('--sync', action='store_true', help='Run full sync cycle')
    parser.add_argument('--claim', help='Claim a file from Needs_Action/')
    parser.add_argument('--release', help='Release a claimed file to Done/')
    parser.add_argument('--claims', action='store_true', help='List active claims')

    args = parser.parse_args()

    sync = VaultSync(args.vault_path, args.agent_role, git_remote=args.remote)

    if args.init:
        sync.init_git()
        print('Git repo initialized')

    elif args.claim:
        result = sync.claim_item(args.claim)
        if result:
            print(f'Claimed: {args.claim} -> {result}')
        else:
            print(f'Could not claim {args.claim} (already claimed or not found)')

    elif args.release:
        success = sync.release_item(args.release)
        print(f'Released: {args.release} -> Done/ ({success})')

    elif args.claims:
        claims = sync.get_claims()
        if claims:
            print(f'Active claims ({len(claims)}):')
            for c in claims:
                print(f'  [{c["agent"]}] {c["file"]}')
        else:
            print('No active claims')

    elif args.sync:
        status = sync.sync_cycle()
        sync.write_sync_status(status)
        print(json.dumps(status, indent=2))

    elif args.push:
        sync.stage_syncable_files()
        sync.commit()
        sync.push()
        print('Pushed successfully')

    elif args.pull:
        sync.pull()
        print('Pulled successfully')

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
