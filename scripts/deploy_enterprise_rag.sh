#!/usr/bin/env bash
set -euo pipefail

target_commit="${1:-}"
project_dir="$HOME/enterprise-rag-knowledge-hub"

cd "$project_dir"
git fetch origin main

if [[ -n "$target_commit" ]]; then
  git cat-file -e "${target_commit}^{commit}"
  git checkout --detach "$target_commit"
else
  git checkout main
  git pull --ff-only origin main
fi

commit="$(git rev-parse --short HEAD)"
message="$(git log -1 --pretty=%s)"
echo "Deploying commit $commit: $message"

sudo docker compose up -d --build api worker beat frontend

for attempt in {1..12}; do
  if curl -fsS http://localhost:8000/health; then
    echo
    echo "Enterprise RAG deployment succeeded."
    exit 0
  fi

  echo "Waiting for API health check ($attempt/12)..."
  sleep 5
done

echo "API health check failed."
sudo docker compose logs api --tail 100
exit 1
