#!/usr/bin/env bash
set -euo pipefail

target_commit="${1:-}"
api_image="${2:-}"
web_image="${3:-}"
project_dir="$HOME/enterprise-rag-knowledge-hub"

if [[ -z "$target_commit" || -z "$api_image" || -z "$web_image" ]]; then
  echo "Usage: $0 <commit-sha> <api-image> <web-image>" >&2
  exit 2
fi

cd "$project_dir"
git fetch origin main

# The VM keeps secrets in the ignored root .env. Source files must not block a
# release, so preserve any tracked local edits as a patch before fast-forwarding
# to the reviewed deployment commit. Do not run git clean: it could remove .env.
if ! git diff --quiet || ! git diff --cached --quiet; then
  backup_dir="$HOME/enterprise-rag-deploy-backups"
  backup_file="$backup_dir/tracked-changes-$(date +%Y%m%d-%H%M%S).patch"
  mkdir -p "$backup_dir"
  {
    git diff
    git diff --cached
  } > "$backup_file"
  git reset --hard
  echo "Backed up tracked VM source changes to $backup_file"
fi

git cat-file -e "${target_commit}^{commit}"
git checkout main
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

compose_start_failed=0
echo "Pulling immutable images from GHCR..."
check_ghcr_connectivity() {
  local status
  status="$(curl --connect-timeout 10 --max-time 30 --silent --show-error \
    --output /dev/null --write-out '%{http_code}' https://ghcr.io/v2/ || true)"

  case "$status" in
    200|401|405)
      echo "GHCR registry connectivity check returned HTTP $status"
      ;;
    *)
      echo "GHCR registry connectivity check failed (HTTP ${status:-no response})." >&2
      return 1
      ;;
  esac
}

pull_image() {
  local image="$1"
  # Docker retries transient layer failures itself. A new API image includes
  # the CPU ML runtime, so an eight-minute outer timeout aborts healthy but
  # slow first pulls on the VM's network.
  echo "Pulling $image (Docker retries transient layer failures; maximum 35 minutes)..."
  if timeout --foreground --signal=INT --kill-after=30s 35m docker pull "$image"; then
    return 0
  fi
  echo "Unable to pull $image from GHCR within 35 minutes. Check VM network access and Docker login." >&2
  return 1
}

check_ghcr_connectivity
pull_image "$api_image"
pull_image "$web_image"

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
