#!/usr/bin/env bash
set -euo pipefail

target_commit="${1:-}"
api_image="${2:-}"
web_image="${3:-}"
api_image_archive="${4:-}"
web_image_archive="${5:-}"
project_dir="$HOME/enterprise-rag-knowledge-hub"

if [[ -z "$target_commit" || -z "$api_image" || -z "$web_image" || -z "$api_image_archive" || -z "$web_image_archive" ]]; then
  echo "Usage: $0 <commit-sha> <api-image> <web-image> <api-image-archive> <web-image-archive>" >&2
  exit 2
fi

cd "$project_dir"
git fetch origin main

git cat-file -e "${target_commit}^{commit}"
git switch main
git merge --ff-only "$target_commit"

if [[ "$(git rev-parse HEAD)" != "$target_commit" ]]; then
  echo "The main branch did not reach the requested deployment commit." >&2
  exit 1
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

if ! command -v gzip >/dev/null; then
  echo "gzip is required to load the staged image archives." >&2
  exit 1
fi

compose_start_failed=0
for image_archive in "$api_image_archive" "$web_image_archive"; do
  if [[ ! -f "$image_archive" ]]; then
    echo "Missing staged image archive: $image_archive" >&2
    exit 1
  fi
  gzip --decompress --stdout "$image_archive" | docker load
  rm -f "$image_archive"
done

if ! env API_IMAGE="$api_image" WEB_IMAGE="$web_image" docker compose up -d --no-build api worker beat frontend; then
  # Compose can report a transient dependency-health failure while the API is
  # still applying migrations and restarting. The checks below decide whether
  # the deployment actually failed.
  compose_start_failed=1
  echo "Docker Compose reported a startup error; verifying final service state."
fi

for attempt in {1..36}; do
  running_services="$(docker compose ps --status running --services)"
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

  echo "Waiting for required services and API health check ($attempt/36)..."
  sleep 5
done

echo "Deployment did not reach the required final state."
docker compose ps
docker compose logs api worker beat frontend --tail 100
exit 1
