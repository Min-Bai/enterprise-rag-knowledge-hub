#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$project_dir/backend/app/.env"
backup_dir="${BACKUP_DIR:-$HOME/backups/enterprise-rag}"
retention_days="${BACKUP_RETENTION_DAYS:-7}"

if [[ ! -f "$env_file" ]]; then
  echo "Missing environment file: $env_file" >&2
  exit 1
fi

set -a
source "$env_file"
set +a

for name in MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE; do
  if [[ -z "${!name:-}" ]]; then
    echo "$name is required in $env_file" >&2
    exit 1
  fi
done

mkdir -p "$backup_dir"
timestamp="$(date +%F-%H%M%S)"
backup_file="$backup_dir/${MYSQL_DATABASE}-${timestamp}.sql"

cd "$project_dir"
sudo docker compose exec -T -e MYSQL_PWD="$MYSQL_PASSWORD" mysql \
  mysqldump --no-tablespaces --single-transaction \
  -u"$MYSQL_USER" "$MYSQL_DATABASE" > "$backup_file"

if [[ ! -s "$backup_file" ]]; then
  rm -f "$backup_file"
  echo "MySQL backup is empty" >&2
  exit 1
fi

find "$backup_dir" -maxdepth 1 -type f -name "${MYSQL_DATABASE}-*.sql" \
  -mtime +"$retention_days" -delete

echo "MySQL backup created: $backup_file"
