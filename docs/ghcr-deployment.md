# GHCR Production Deployment

The production workflow has two stages:

1. Pull requests run CI only.
2. A successful CI run for a commit merged into `main` builds immutable API and web images and publishes them to GitHub Container Registry.
3. The Windows runner connects to the VM over SSH; the VM pulls the matching SHA-tagged images directly from GHCR and starts Compose.

The VM advances its local `main` branch to the deployed commit to obtain the matching Compose file. It does not build application images, and no image archive is downloaded to or transferred through the Windows runner.

## One-time setup

The Windows self-hosted runner must be able to reach GitHub Actions and the VM over SSH. It does not require Docker Desktop, WSL, or a GHCR package token. The VM requires Docker, outbound access to `ghcr.io`, and a read-only GHCR token stored in its Docker credential file.

Log in once on the VM as the same user that runs the deployment script:

```bash
echo 'YOUR_GHCR_READ_TOKEN' | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

The token needs the `read:packages` scope. Do not commit it or put it in the repository `.env` file.

## Deployment and rollback

`Build and Deploy Enterprise RAG` deploys tags in the form `sha-<full-commit-sha>`. Manual runs are accepted only from `main`. The VM pulls the CPU-only API image and web image directly from GHCR before starting Compose.

Do not retag `latest` to roll back production. A rollback should deploy a previously published SHA tag through a reviewed manual workflow input.
