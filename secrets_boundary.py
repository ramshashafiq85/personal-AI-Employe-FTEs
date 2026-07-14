#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secrets Boundary - Runtime enforcement of the Cloud ↔ Local security boundary.

This module actively prevents secrets from being synced, copied, or exposed
to the Cloud Agent. It provides:

1. `SecretsScanner` - Scans files/directories for secret patterns
2. `SyncGuard` - Wraps vault sync to filter out secrets at runtime
3. `FileGuard` - Validates individual files before they can be read by Cloud
4. `EnvGuard` - Loads secrets from .env but never exposes them in logs/state

Usage:
    from secrets_boundary import SecretsScanner, SyncGuard

    scanner = SecretsScanner(vault_path)
    scanner.scan()  # Returns list of exposed secrets

    guard = SyncGuard(vault_path, agent_role='cloud')
    safe_files = guard.filter_syncable(file_list)  # Returns only safe files
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Set, Optional, Tuple
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SecretsBoundary')


# ============================================================
# SECRET PATTERNS - detected in file content
# ============================================================
SECRET_PATTERNS = [
    # API Keys & Tokens
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}', 'API Key'),
    (r'(?i)(api[_-]?secret|apisecret)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}', 'API Secret'),
    (r'(?i)(access[_-]?token|accesstoken)\s*[=:]\s*["\']?[A-Za-z0-9_\-\.]{16,}', 'Access Token'),
    (r'(?i)(refresh[_-]?token|refreshtoken)\s*[=:]\s*["\']?[A-Za-z0-9_\-\.]{16,}', 'Refresh Token'),
    (r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}', 'Secret Key'),
    (r'(?i)(client[_-]?secret|clientsecret)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}', 'Client Secret'),
    (r'(?i)(client[_-]?id|clientid)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}', 'Client ID'),
    (r'(?i)(auth[_-]?token|authtoken)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{16,}', 'Auth Token'),
    (r'(?i)(bearer)\s+[A-Za-z0-9_\-\.]{20,}', 'Bearer Token'),

    # Passwords
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']{8,}', 'Password'),
    (r'(?i)(db[_-]?password)\s*[=:]\s*["\']?[^\s"\']{4,}', 'DB Password'),

    # Private Keys
    (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', 'Private Key'),

    # AWS / Cloud credentials
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    (r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*["\']?[A-Za-z0-9/+=]{20,}', 'AWS Secret'),

    # Database URLs with credentials
    (r'(?i)(mongodb|postgres|mysql|redis)://[^\s"]+:[^\s"]+@', 'Database URL with creds'),

    # Gmail OAuth pickle/token
    (r'gmail.*token.*pickle', 'Gmail Token'),
    (r'\.pickle$', 'Pickle File'),

    # Odoo Master Password
    (r'(?i)(odoo[_-]?master[_-]?password|admin[_-]?passwd)\s*[=:]', 'Odoo Password'),

    # WhatsApp session data
    (r'wa.*session.*secret', 'WhatsApp Secret'),
]

# ============================================================
# SECRET DIRECTORIES - never accessed by Cloud agent
# ============================================================
SECRET_DIRS = [
    '.whatsapp_session',
    'ssl',
    'odoo-data',
    'postgres-data',
    '__pycache__',
    '.git',
    '.obsidian',
]

# ============================================================
# SECRET FILES - never synced or read by Cloud
# ============================================================
SECRET_FILES = [
    '.env',
    '.env.local',
    '.env.production',
    '.env.example',
    'credentials.json',
    'token.pickle',
    'gmail_token.pickle',
    'service_account.json',
    'config.yaml',  # may contain secrets
    'secrets.json',
]


@dataclass
class SecretFinding:
    """A single secret finding."""
    file_path: str
    pattern_type: str
    line_number: int = 0
    matched_text: str = ''  # Truncated for safety
    severity: str = 'high'  # high, medium, low


class SecretsScanner:
    """Scans files and directories for exposed secrets."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.compiled_patterns = [
            (re.compile(pattern, re.MULTILINE), label)
            for pattern, label in SECRET_PATTERNS
        ]

    def scan(self, paths: List[str] = None) -> List[SecretFinding]:
        """
        Scan the vault for exposed secrets.

        Args:
            paths: Specific paths to scan (default: entire vault)

        Returns:
            List of SecretFinding objects
        """
        findings = []

        if paths:
            targets = [Path(p) for p in paths]
        else:
            targets = [self.vault_path]

        for target in targets:
            if target.is_file():
                findings.extend(self._scan_file(target))
            elif target.is_dir():
                findings.extend(self._scan_directory(target))

        return findings

    def _scan_directory(self, directory: Path) -> List[SecretFinding]:
        """Recursively scan a directory for secrets."""
        findings = []

        # Check for secret directories
        for part in directory.parts:
            if part in SECRET_DIRS:
                return findings  # Skip entirely

        for file_path in directory.rglob('*'):
            if not file_path.is_file():
                continue

            # Skip secret directories
            if any(part in SECRET_DIRS for part in file_path.parts):
                continue

            # Skip secret files
            if file_path.name in SECRET_FILES:
                continue

            # Skip binary files
            if self._is_binary(file_path):
                continue

            findings.extend(self._scan_file(file_path))

        return findings

    def _scan_file(self, file_path: Path) -> List[SecretFinding]:
        """Scan a single file for secret patterns."""
        findings = []

        # Check if filename matches secret files
        if file_path.name in SECRET_FILES:
            findings.append(SecretFinding(
                file_path=str(file_path),
                pattern_type='Secret File',
                severity='high',
                matched_text=f'Entire file: {file_path.name}'
            ))
            return findings

        # Check if path contains secret directories
        if any(part in SECRET_DIRS for part in file_path.parts):
            findings.append(SecretFinding(
                file_path=str(file_path),
                pattern_type='Secret Directory',
                severity='high',
                matched_text=f'Inside: {"/".join(p for p in file_path.parts if p in SECRET_DIRS)}/'
            ))
            return findings

        try:
            content = file_path.read_text(errors='ignore')
            for pattern, label in self.compiled_patterns:
                for match in pattern.finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    matched = match.group(0)[:50]  # Truncate for safety
                    findings.append(SecretFinding(
                        file_path=str(file_path),
                        pattern_type=label,
                        line_number=line_num,
                        matched_text=matched,
                        severity='high' if 'Key' in label or 'Password' in label else 'medium'
                    ))
        except (OSError, UnicodeDecodeError):
            pass  # Skip binary/unreadable files

        return findings

    def scan_file_for_cloud_access(self, file_path: str) -> Tuple[bool, List[SecretFinding]]:
        """
        Check if a file is safe for Cloud Agent to read.

        Args:
            file_path: Path to file (relative to vault)

        Returns:
            (is_safe, findings)
        """
        full_path = self.vault_path / file_path
        if not full_path.exists():
            return False, []

        findings = self._scan_file(full_path)
        is_safe = len(findings) == 0
        return is_safe, findings

    def _is_binary(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
                return b'\x00' in chunk
        except OSError:
            return True

    def report(self, findings: List[SecretFinding]) -> str:
        """Generate a human-readable report of findings."""
        if not findings:
            return '✅ No secrets detected.'

        lines = [f'🚨 {len(findings)} secret(s) detected:']
        for f in findings:
            lines.append(
                f'  [{f.severity.upper()}] {f.pattern_type} in {f.file_path}:{f.line_number} '
                f'match="{f.matched_text}"'
            )
        return '\n'.join(lines)


class SyncGuard:
    """Wraps vault sync to filter out secrets at runtime."""

    def __init__(self, vault_path: str, agent_role: str):
        self.vault_path = Path(vault_path)
        self.agent_role = agent_role
        self.scanner = SecretsScanner(vault_path)

    def is_syncable(self, file_path: str) -> bool:
        """
        Check if a file is safe to sync.

        Args:
            file_path: Path relative to vault

        Returns:
            True if safe to sync
        """
        full_path = self.vault_path / file_path
        if not full_path.exists():
            return False

        # Cloud agent can NEVER sync secret files
        if self.agent_role == 'cloud':
            # Check against secret files list
            if full_path.name in SECRET_FILES:
                logger.debug(f'Blocked sync of secret file: {file_path}')
                return False

            # Check against secret directories
            if any(part in SECRET_DIRS for part in full_path.parts):
                logger.debug(f'Blocked sync of secret dir file: {file_path}')
                return False

        # Scan file content for secret patterns
        is_safe, findings = self.scanner.scan_file_for_cloud_access(file_path)
        if not is_safe:
            logger.warning(
                f'Blocked sync of file with secrets: {file_path} '
                f'({len(findings)} finding(s))'
            )
            return False

        return True

    def filter_syncable(self, file_paths: List[str]) -> List[str]:
        """
        Filter a list of file paths, returning only syncable ones.

        Args:
            file_paths: List of paths relative to vault

        Returns:
            Filtered list of safe paths
        """
        return [f for f in file_paths if self.is_syncable(f)]

    def sanitize_for_cloud(self, data: dict) -> dict:
        """
        Sanitize a data dict before sending to Cloud Agent.
        Removes any secret values from the data.

        Args:
            data: Dict that may contain secrets

        Returns:
            Sanitized dict
        """
        secret_keys = {
            'password', 'passwd', 'pwd', 'token', 'secret', 'key',
            'api_key', 'api_secret', 'client_secret', 'client_id',
            'access_token', 'refresh_token', 'auth_token',
            'gmail_token', 'whatsapp_session', 'db_password',
            'odoo_password', 'admin_passwd', 'aws_secret',
            'bearer_token', 'private_key',
        }

        sanitized = {}
        for key, value in data.items():
            if key.lower() in secret_keys:
                sanitized[key] = '[REDACTED]'
                logger.debug(f'Redacted secret key: {key}')
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_for_cloud(value)
            elif isinstance(value, str):
                # Check if value looks like a secret
                is_secret = False
                for pattern, _ in self.scanner.compiled_patterns:
                    if pattern.search(value):
                        is_secret = True
                        break
                sanitized[key] = '[REDACTED]' if is_secret else value
            else:
                sanitized[key] = value

        return sanitized


class EnvGuard:
    """Loads secrets from .env but never exposes them in logs/state."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.env_file = self.vault_path / '.env'
        self._secrets = {}
        self._loaded = False

    def load(self) -> bool:
        """Load .env file into memory."""
        if not self.env_file.exists():
            logger.warning('.env file not found')
            return False

        for line in self.env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                self._secrets[key.strip()] = value.strip().strip('"\'')

        self._loaded = True
        logger.info(f'Loaded {len(self._secrets)} environment variables')
        return True

    def get(self, key: str, default: str = None) -> Optional[str]:
        """Get a secret value. Returns default if not found."""
        return self._secrets.get(key, default)

    def get_required(self, key: str) -> str:
        """Get a required secret. Raises if not found."""
        if key not in self._secrets:
            raise KeyError(f'Required secret not found: {key}')
        return self._secrets[key]

    def as_dict_for_agent(self, agent_role: str) -> dict:
        """
        Return env vars safe for the given agent role.
        Cloud agent gets heavily redacted vars.
        """
        if agent_role == 'cloud':
            # Cloud gets ONLY non-secret config vars
            allowed = {
                'VAULT_PATH', 'AGENT_ROLE', 'ODOO_URL', 'ODOO_DB',
                'CHECK_INTERVAL', 'ALERT_EMAIL',
            }
            return {k: v for k, v in self._secrets.items() if k in allowed}
        else:
            # Local agent gets everything (but we still don't log it)
            return dict(self._secrets)

    def __repr__(self):
        return f'EnvGuard(loaded={self._loaded}, keys={len(self._secrets)})'


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Secrets Boundary Scanner')
    parser.add_argument('vault_path', help='Path to vault directory')
    parser.add_argument('--scan', action='store_true', help='Scan vault for secrets')
    parser.add_argument('--check', metavar='FILE', help='Check if a file is safe for cloud')
    parser.add_argument('--agent-role', choices=['cloud', 'local'], default='cloud',
                        help='Agent role for security checks')

    args = parser.parse_args()

    scanner = SecretsScanner(args.vault_path)

    if args.scan:
        findings = scanner.scan()
        print(scanner.report(findings))

    elif args.check:
        guard = SyncGuard(args.vault_path, args.agent_role)
        is_safe, findings = scanner.scan_file_for_cloud_access(args.check)
        if is_safe:
            print(f'✅ {args.check} is safe for {args.agent_role} agent')
        else:
            print(f'🚨 {args.check} contains secrets:')
            print(scanner.report(findings))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
