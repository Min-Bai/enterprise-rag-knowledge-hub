#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backup_dir="${BACKUP_DIR:-$HOME/backups/enterprise-rag}"

cd "$project_dir"

echo "== Docker Compose services =="
sudo docker compose ps

echo
echo "== Document worker =="
if ! sudo docker compose ps --status running --services | grep -qx "worker"; then
  echo "Document worker is not running" >&2
  exit 1
fi

sudo docker compose exec -T worker python -c '
from rq import Worker
from backend.app.services.document_queue import get_document_queue

queue = get_document_queue()
workers = Worker.all(connection=queue.connection)
if not workers:
    raise SystemExit("No RQ workers are registered")
print(f"registered workers: {len(workers)}")
print(f"queued document jobs: {len(queue)}")
'

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
