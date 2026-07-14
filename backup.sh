#!/usr/bin/env bash
# ============================================================
# Platinum Tier: Automated Backup Script
# Backs up PostgreSQL, Odoo filestore, and Vault with 7-day retention.
#
# Usage:
#   ./backup.sh                    # Run backup
#   ./backup.sh --restore latest   # Restore from latest backup
#   ./backup.sh --list             # List available backups
#   ./backup.sh --cleanup          # Remove backups older than 7 days
#
# Cron (daily at 2 AM):
#   0 2 * * * /path/to/backup.sh >> /var/log/ai-employee-backup.log 2>&1
# ============================================================

set -euo pipefail

# ── Configuration ──
BACKUP_DIR="${BACKUP_DIR:-/opt/ai-employee/backups}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-odoo}"
POSTGRES_DB="${POSTGRES_DB:-postgres}"
PGPASSWORD="${PGPASSWORD:-odoo}"
export PGPASSWORD

ODOO_FILESTORE="${ODOO_FILESTORE:-/var/lib/odoo/filestore}"
VAULT_PATH="${VAULT_PATH:-/vault}"

RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================
# Functions
# ============================================================

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  (no args)       Run backup"
    echo "  --list          List available backups"
    echo "  --restore NAME  Restore from backup NAME (or 'latest')"
    echo "  --cleanup       Remove backups older than ${RETENTION_DAYS} days"
    echo "  --help          Show this help"
    exit 0
}

create_backup() {
    log "Starting backup: ${BACKUP_NAME}"

    # Create backup directory
    mkdir -p "${BACKUP_PATH}"

    # ── 1. PostgreSQL Database Backup ──
    log "Backing up PostgreSQL database..."
    if command -v pg_dump &> /dev/null; then
        pg_dump -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
            -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
            -F c -f "${BACKUP_PATH}/database.dump" 2>/dev/null \
            && log "✅ PostgreSQL backup created" \
            || warn "PostgreSQL backup failed (is the DB running?)"
    else
        # Fallback: try via docker
        if command -v docker &> /dev/null; then
            docker exec platinum-odoo-db pg_dump -U "${POSTGRES_USER}" \
                -d "${POSTGRES_DB}" -F c > "${BACKUP_PATH}/database.dump" 2>/dev/null \
                && log "✅ PostgreSQL backup created (via Docker)" \
                || warn "PostgreSQL backup failed (Docker container not running?)"
        else
            warn "pg_dump and docker not found. Skipping PostgreSQL backup."
        fi
    fi

    # ── 2. Odoo Filestore Backup ──
    log "Backing up Odoo filestore..."
    if [ -d "${ODOO_FILESTORE}" ]; then
        tar czf "${BACKUP_PATH}/filestore.tar.gz" \
            -C "$(dirname "${ODOO_FILESTORE}")" "$(basename "${ODOO_FILESTORE}")" 2>/dev/null \
            && log "✅ Odoo filestore backed up" \
            || warn "Odoo filestore backup failed"
    else
        warn "Odoo filestore not found at ${ODOO_FILESTORE}. Skipping."
    fi

    # ── 3. Vault Backup (Git-based, secrets excluded) ──
    log "Backing up vault (excluding secrets)..."
    if [ -d "${VAULT_PATH}" ]; then
        # Use rsync to copy only syncable files (excludes .env, ssl, etc.)
        mkdir -p "${BACKUP_PATH}/vault"
        rsync -a --exclude='.env' --exclude='.env.*' \
              --exclude='*.key' --exclude='*.pem' --exclude='*.crt' \
              --exclude='ssl/' --exclude='.whatsapp_session/' \
              --exclude='odoo-data/' --exclude='postgres-data/' \
              --exclude='__pycache__/' --exclude='*.pyc' \
              --exclude='.git/' --exclude='.obsidian/' \
              --exclude='Logs/*.json' \
              "${VAULT_PATH}/" "${BACKUP_PATH}/vault/" 2>/dev/null \
            && log "✅ Vault backed up" \
            || warn "Vault backup failed"
    else
        warn "Vault not found at ${VAULT_PATH}. Skipping."
    fi

    # ── 4. Create Backup Manifest ──
    cat > "${BACKUP_PATH}/manifest.json" <<EOF
{
    "name": "${BACKUP_NAME}",
    "timestamp": "${TIMESTAMP}",
    "date": "$(date -Iseconds)",
    "postgres_host": "${POSTGRES_HOST}",
    "postgres_db": "${POSTGRES_DB}",
    "odoo_filestore": "${ODOO_FILESTORE}",
    "vault_path": "${VAULT_PATH}",
    "files": [$(ls "${BACKUP_PATH}" 2>/dev/null | grep -v manifest.json | sed 's/.*/"&"/' | paste -sd,)]
}
EOF
    log "✅ Backup manifest created"

    # ── 5. Cleanup Old Backups ──
    cleanup

    log "✅ Backup complete: ${BACKUP_PATH}"
}

list_backups() {
    log "Available backups in ${BACKUP_DIR}:"
    echo ""

    if [ ! -d "${BACKUP_DIR}" ]; then
        warn "No backup directory found."
        return
    fi

    local count=0
    for backup in "${BACKUP_DIR}"/backup_*; do
        if [ -d "${backup}" ]; then
            local name
            name=$(basename "${backup}")
            local manifest="${backup}/manifest.json"
            local date="unknown"
            if [ -f "${manifest}" ]; then
                date=$(grep -o '"date": "[^"]*"' "${manifest}" | cut -d'"' -f4)
            fi
            echo "  ${name}  (${date})"
            count=$((count + 1))
        fi
    done

    if [ ${count} -eq 0 ]; then
        warn "No backups found."
    else
        echo ""
        log "Total: ${count} backup(s)"
    fi
}

restore_backup() {
    local target="$1"

    if [ "${target}" = "latest" ]; then
        # Find the latest backup
        target=$(ls -dt "${BACKUP_DIR}"/backup_* 2>/dev/null | head -1)
        if [ -z "${target}" ]; then
            error "No backups found to restore."
            exit 1
        fi
        target=$(basename "${target}")
    fi

    local backup_path="${BACKUP_DIR}/${target}"

    if [ ! -d "${backup_path}" ]; then
        error "Backup not found: ${backup_path}"
        exit 1
    fi

    log "Restoring from backup: ${target}"

    # ── 1. Restore PostgreSQL ──
    if [ -f "${backup_path}/database.dump" ]; then
        log "Restoring PostgreSQL database..."
        if command -v pg_restore &> /dev/null; then
            # Drop and recreate database
            dropdb -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
                -U "${POSTGRES_USER}" --if-exists "${POSTGRES_DB}" 2>/dev/null || true
            createdb -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
                -U "${POSTGRES_USER}" "${POSTGRES_DB}" 2>/dev/null || true
            pg_restore -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
                -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
                "${backup_path}/database.dump" \
                && log "✅ PostgreSQL restored" \
                || error "PostgreSQL restore failed"
        elif command -v docker &> /dev/null; then
            docker exec -i platinum-odoo-db pg_restore \
                -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
                < "${backup_path}/database.dump" \
                && log "✅ PostgreSQL restored (via Docker)" \
                || error "PostgreSQL restore failed"
        fi
    else
        warn "No database dump found. Skipping PostgreSQL restore."
    fi

    # ── 2. Restore Odoo Filestore ──
    if [ -f "${backup_path}/filestore.tar.gz" ]; then
        log "Restoring Odoo filestore..."
        mkdir -p "${ODOO_FILESTORE}"
        tar xzf "${backup_path}/filestore.tar.gz" \
            -C "$(dirname "${ODOO_FILESTORE}")" \
            && log "✅ Odoo filestore restored" \
            || warn "Odoo filestore restore failed"
    else
        warn "No filestore archive found. Skipping."
    fi

    # ── 3. Restore Vault ──
    if [ -d "${backup_path}/vault" ]; then
        log "Restoring vault..."
        rsync -a "${backup_path}/vault/" "${VAULT_PATH}/" \
            && log "✅ Vault restored" \
            || warn "Vault restore failed"
    else
        warn "No vault backup found. Skipping."
    fi

    log "✅ Restore complete: ${target}"
}

cleanup() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."

    if [ ! -d "${BACKUP_DIR}" ]; then
        return
    fi

    local count=0
    find "${BACKUP_DIR}" -maxdepth 1 -name "backup_*" -type d \
        -mtime +${RETENTION_DAYS} -print0 2>/dev/null | \
        while IFS= read -r -d '' dir; do
            log "Removing old backup: $(basename "${dir}")"
            rm -rf "${dir}"
            count=$((count + 1))
        done

    log "Cleanup complete. Removed ${count} old backup(s)."
}

# ============================================================
# Main
# ============================================================

case "${1:-}" in
    --help|-h)
        usage
        ;;
    --list)
        list_backups
        ;;
    --restore)
        if [ -z "${2:-}" ]; then
            error "Please specify a backup name or 'latest'"
            exit 1
        fi
        restore_backup "$2"
        ;;
    --cleanup)
        cleanup
        ;;
    "")
        create_backup
        ;;
    *)
        error "Unknown option: $1"
        usage
        ;;
esac
