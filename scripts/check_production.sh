#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backup_dir="${BACKUP_DIR:-$HOME/backups/todo-api}"

cd "$project_dir"

echo "== Docker Compose services =="
sudo docker compose ps

echo
echo "== API health =="
curl --fail --silent --show-error http://localhost:8000/health
echo

echo "== Root filesystem =="
df -h /

echo
echo "== Latest MySQL backup =="
latest_backup="$(find "$backup_dir" -maxdepth 1 -type f -name '*.sql' \
  -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)"

if [[ -z "$latest_backup" ]]; then
  echo "No MySQL backup found in $backup_dir" >&2
  exit 1
fi

ls -lh "$latest_backup"

echo
echo "Production check passed."
