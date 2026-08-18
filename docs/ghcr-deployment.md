# GHCR Production Deployment

The production workflow has two stages:

1. Pull requests run CI only.
2. A successful CI run for a commit merged into `main` builds immutable API and web images, publishes them to GitHub Container Registry, then has the Windows runner ask the VM to pull those exact image tags over its own network connection.

The VM advances its local `main` branch to the deployed commit to obtain the matching Compose file. It does not build application images or need direct access to GHCR.

## One-time setup

The Windows self-hosted runner must be able to reach GitHub Actions and the VM over SSH. It does not require Docker Desktop, WSL, or GHCR access. The VM requires Docker, SSH access from that runner, and a GHCR login with read access to both private packages.

## Deployment and rollback

`Build and Deploy Enterprise RAG` deploys tags in the form `sha-<full-commit-sha>`. Manual runs are accepted only from `main`. The VM pulls both immutable tags directly from GHCR before starting Compose.

Do not retag `latest` to roll back production. A rollback should deploy a previously published SHA tag through a reviewed manual workflow input.
