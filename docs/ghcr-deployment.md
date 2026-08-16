# GHCR Production Deployment

The production workflow has two stages:

1. Pull requests run CI only.
2. A successful CI run for a commit merged into `main` builds immutable API and web images, publishes them to GitHub Container Registry, then deploys those exact tags to the VM.

The VM checks out the deployed commit only to obtain the matching Compose file. It does not build application images.

## One-time VM setup

Create a GitHub personal access token with only the `read:packages` permission. Store it outside the repository on the VM:

```bash
mkdir -p ~/.config/enterprise-rag
chmod 700 ~/.config/enterprise-rag
cat > ~/.config/enterprise-rag/ghcr.env <<'EOF'
GHCR_USERNAME=YOUR_GITHUB_USERNAME
GHCR_READ_TOKEN=YOUR_READ_PACKAGES_TOKEN
EOF
chmod 600 ~/.config/enterprise-rag/ghcr.env
```

Do not put this token in `.env`, GitHub Actions files, shell history, or Git.

After the first workflow publishes `enterprise-rag-api` and `enterprise-rag-web`, keep each package private unless public images are explicitly required.

## Deployment and rollback

`Build and Deploy Enterprise RAG` deploys tags in the form `sha-<full-commit-sha>`. The deployment log reports the checked-out source commit and Docker pulls the matching immutable images.

Do not retag `latest` to roll back production. A rollback should deploy a previously published SHA tag through a reviewed manual workflow input.
