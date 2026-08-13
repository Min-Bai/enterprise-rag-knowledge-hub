#!/usr/bin/env bash
set -euo pipefail

# This migrates production resources from the former Todo deployment once.
source_dir="${SOURCE_DIR:-$HOME/todo-api}"
target_dir="${TARGET_DIR:-$HOME/enterprise-rag-knowledge-hub}"
backup_dir="${BACKUP_DIR:-$HOME/backups/enterprise-rag}"
source_env=""
target_env="$target_dir/backend/app/.env"
old_project="todo-api"
completed=false

old_volume_names=(
  "todo-api-data"
  "${old_project}_todo-document-data"
  "${old_project}_todo-model-cache"
  "${old_project}_todo-qdrant-data"
)
new_volume_names=(
  "enterprise-rag-api-data"
  "enterprise-rag-document-data"
  "enterprise-rag-model-cache"
  "enterprise-rag-qdrant-data"
)

restore_previous_deployment() {
  if [[ "$completed" == true ]]; then
    return
  fi

  echo "Migration failed. Restoring the previous deployment." >&2
  sudo docker compose -f "$target_dir/compose.yaml" down --remove-orphans || true
  sudo docker compose -f "$source_dir/compose.yaml" up -d || true
}

trap restore_previous_deployment ERR

for candidate in "$source_dir/backend/app/.env" "$source_dir/python_practice/day57/.env"; do
  if [[ -f "$candidate" ]]; then
    source_env="$candidate"
    break
  fi
done

if [[ -z "$source_env" ]]; then
  echo "Missing source environment file in $source_dir" >&2
  exit 1
fi

if [[ -e "$target_dir" ]]; then
  echo "Target directory already exists: $target_dir" >&2
  exit 1
fi

set -a
source <(sed 's/\r$//' "$source_env")
set +a

for name in MYSQL_DATABASE MYSQL_USER MYSQL_PASSWORD MYSQL_ROOT_PASSWORD; do
  if [[ -z "${!name:-}" ]]; then
    echo "$name is required in $source_env" >&2
    exit 1
  fi
done

old_mysql_database="$MYSQL_DATABASE"
old_mysql_user="$MYSQL_USER"
old_mysql_password="$MYSQL_PASSWORD"
old_mysql_root_password="$MYSQL_ROOT_PASSWORD"

mkdir -p "$backup_dir"
timestamp="$(date +%F-%H%M%S)"
dump_file="$backup_dir/${old_mysql_database}-before-enterprise-rag-${timestamp}.sql"

echo "Creating MySQL backup: $dump_file"
cd "$source_dir"
sudo docker compose exec -T -e MYSQL_PWD="$MYSQL_PASSWORD" mysql \
  mysqldump --no-tablespaces --single-transaction \
  -u"$old_mysql_user" "$old_mysql_database" > "$dump_file"

if [[ ! -s "$dump_file" ]]; then
  echo "MySQL backup is empty" >&2
  exit 1
fi

source_remote="$(git -C "$source_dir" remote get-url origin)"
echo "Cloning current repository into $target_dir"
git clone --branch main "$source_remote" "$target_dir"
cp "$source_env" "$target_env"
sed -i 's/\r$//' "$target_env"

python3 - "$target_env" "$old_mysql_password" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
password = sys.argv[2]
values = {
    "MYSQL_DATABASE": "enterprise_rag",
    "MYSQL_USER": "enterprise_rag",
    "DATABASE_URL": (
        "mysql+pymysql://enterprise_rag:"
        f"{password}@mysql:3306/enterprise_rag?charset=utf8mb4"
    ),
}
lines = path.read_text(encoding="utf-8").splitlines()
path.write_text(
    "\n".join(
        f"{key}={values.get(key, value)}"
        for line in lines
        if "=" in line
        for key, value in [line.split("=", 1)]
    )
    + "\n",
    encoding="utf-8",
)
PY

MYSQL_DATABASE="enterprise_rag"
MYSQL_USER="enterprise_rag"
MYSQL_PASSWORD="$old_mysql_password"
MYSQL_ROOT_PASSWORD="$old_mysql_root_password"

echo "Stopping the previous deployment before copying volume data"
sudo docker compose -f "$source_dir/compose.yaml" down --remove-orphans

for volume in "${new_volume_names[@]}" "enterprise-rag-mysql-data"; do
  sudo docker volume create "$volume" >/dev/null
done

# Redis only contains queue and rate-limit state. Start the new deployment with
# a clean queue so interrupted jobs from the old deployment are not replayed.
sudo docker volume create enterprise-rag-redis-data >/dev/null

for index in "${!old_volume_names[@]}"; do
  old_volume="${old_volume_names[$index]}"
  new_volume="${new_volume_names[$index]}"
  sudo docker volume inspect "$old_volume" >/dev/null
  echo "Copying volume $old_volume to $new_volume"
  sudo docker run --rm \
    -v "$old_volume":/from:ro \
    -v "$new_volume":/to \
    docker.m.daocloud.io/library/alpine:3.20 \
    sh -c 'cd /from && tar cf - . | tar xf - -C /to'
done

echo "Initializing Enterprise RAG MySQL"
cd "$target_dir"
sudo docker compose up -d mysql

for attempt in {1..18}; do
  if sudo docker compose exec -T mysql \
    mysqladmin ping -h 127.0.0.1 -u"$MYSQL_USER" \
    -p"$MYSQL_PASSWORD" --silent; then
    break
  fi
  if [[ "$attempt" == 18 ]]; then
    echo "Enterprise RAG MySQL did not become ready" >&2
    exit 1
  fi
  sleep 5
done

echo "Importing MySQL backup into enterprise_rag"
sudo docker compose exec -T -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql \
  mysql -uroot "$MYSQL_DATABASE" < "$dump_file"

echo "Updating migrated document storage paths"
sudo docker compose exec -T -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql \
  mysql -uroot "$MYSQL_DATABASE" -e "
    UPDATE documents
    SET storage_path = REPLACE(
      storage_path,
      '/app/python_practice/day57/data/',
      '/app/backend/app/data/'
    )
    WHERE storage_path LIKE '/app/python_practice/day57/data/%';
    UPDATE documents
    SET storage_path = REPLACE(
      storage_path,
      '/app/python_practice/data/',
      '/app/backend/app/data/'
    )
    WHERE storage_path LIKE '/app/python_practice/data/%';
    UPDATE documents
    SET storage_path = REPLACE(
      storage_path,
      '/app/backend/data/',
      '/app/backend/app/data/'
    )
    WHERE storage_path LIKE '/app/backend/data/%';
  "

sudo install -m 755 "$target_dir/scripts/deploy_enterprise_rag.sh" \
  "$HOME/deploy-enterprise-rag.sh"

echo "Starting Enterprise RAG services"
sudo docker compose up -d --build api worker frontend

for attempt in {1..12}; do
  if curl -fsS http://localhost:8000/health; then
    completed=true
    trap - ERR
    echo
    echo "Migration succeeded. Previous resources were retained for rollback."
    exit 0
  fi
  sleep 5
done

echo "Enterprise RAG API health check failed" >&2
exit 1
