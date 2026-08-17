# GHCR Production Deployment

The production workflow has two stages:

1. Pull requests run CI only.
2. A successful CI run for a commit merged into `main` builds immutable API and web images, publishes them to GitHub Container Registry, exports the same images as a short-lived GitHub Actions Artifact, then has the Windows runner transfer that artifact to the VM over SSH.

The VM checks out the deployed commit only to obtain the matching Compose file. It does not build application images or need direct access to GHCR.

## One-time setup

The Windows self-hosted runner must be able to reach GitHub Actions and the VM over SSH. It does not require Docker Desktop, WSL, GHCR access, or a package token. The VM requires Docker and SSH access from that runner, but does not store a GHCR token.

## Deployment and rollback

`Build and Deploy Enterprise RAG` deploys tags in the form `sha-<full-commit-sha>`. The hosted build job exports the exact images to a one-day artifact; the runner transfers its temporary Docker archive and the VM loads it locally before starting Compose.

Do not retag `latest` to roll back production. A rollback should deploy a previously published SHA tag through a reviewed manual workflow input.
