# GHCR Production Deployment

The production workflow has two stages:

1. Pull requests run CI only.
2. A successful CI run for a commit merged into `main` builds immutable API and web images, publishes them to GitHub Container Registry, then has the Windows runner transfer those exact images to the VM over SSH.

The VM checks out the deployed commit only to obtain the matching Compose file. It does not build application images or need direct access to GHCR.

## One-time setup

The Windows self-hosted runner must be able to reach GitHub and GHCR. The workflow downloads the native daemonless `crane.exe` client on that runner, so Docker Desktop and WSL are not required there. The VM requires Docker and SSH access from that runner, but does not store a GHCR token.

Grant the repository read access to both GHCR packages, `enterprise-rag-api` and `enterprise-rag-web`, under each package's **Manage Actions access** settings. The deployment job then uses its automatically generated `GITHUB_TOKEN` to read the immutable images; no long-lived package token is stored in GitHub Actions.

## Deployment and rollback

`Build and Deploy Enterprise RAG` deploys tags in the form `sha-<full-commit-sha>`. The runner uses `crane` to export and transfer temporary Docker archives; the VM loads them locally before starting Compose.

Do not retag `latest` to roll back production. A rollback should deploy a previously published SHA tag through a reviewed manual workflow input.
