#!/usr/bin/env bash
set -euo pipefail

target_commit="${1:-}"
project_dir="$HOME/enterprise-rag-knowledge-hub"
torch_base_image="enterprise-rag-python:torch-2.5.1-cpu"
torch_wheel_dir="$HOME/.cache/enterprise-rag/pip-wheels"
torch_wheel="$torch_wheel_dir/torch-2.5.1+cpu-cp312-cp312-linux_x86_64.whl"

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

if ! sudo docker image inspect "$torch_base_image" >/dev/null 2>&1; then
  if [[ ! -f "$torch_wheel" ]]; then
    echo "Missing server torch cache: $torch_wheel" >&2
    exit 1
  fi

  sudo docker build \
    --tag "$torch_base_image" \
    --file "$project_dir/Dockerfile.torch-cache" \
    "$torch_wheel_dir"
fi

sudo env BASE_IMAGE="$torch_base_image" \
  docker compose up -d --build api worker frontend

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
