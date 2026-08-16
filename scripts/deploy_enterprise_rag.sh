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

# The repository now standardizes on a root .env. Migrate the prior location
# once on existing servers without exposing values through Git or logs.
if [[ ! -f .env && -f backend/app/.env ]]; then
  cp backend/app/.env .env
  chmod 600 .env
  echo "Migrated legacy backend/app/.env to .env"
fi

if [[ ! -f .env ]]; then
  echo "Missing environment file: $project_dir/.env" >&2
  exit 1
fi

compose_start_failed=0
if ! sudo docker compose up -d --build api worker beat frontend; then
  # Compose can report a transient dependency-health failure while the API is
  # still applying migrations and restarting. The checks below decide whether
  # the deployment actually failed.
  compose_start_failed=1
  echo "Docker Compose reported a startup error; verifying final service state."
fi

for attempt in {1..12}; do
  running_services="$(sudo docker compose ps --status running --services)"
  required_services_ready=1
  for service in api worker beat frontend; do
    if ! grep -qx "$service" <<<"$running_services"; then
      required_services_ready=0
      break
    fi
  done

  if [[ "$required_services_ready" -eq 1 ]] && curl -fsS http://localhost:8000/health; then
    echo
    if [[ "$compose_start_failed" -eq 1 ]]; then
      echo "Services recovered after the transient Compose startup error."
    fi
    echo "Enterprise RAG deployment succeeded."
    exit 0
  fi

  echo "Waiting for required services and API health check ($attempt/12)..."
  sleep 5
done

echo "Deployment did not reach the required final state."
sudo docker compose ps
sudo docker compose logs api worker beat frontend --tail 100
exit 1
