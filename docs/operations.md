# Production Operations

Run all commands from the production checkout, `~/enterprise-rag-knowledge-hub`.

## Daily check

```bash
sudo bash scripts/check_production.sh
```

The check verifies Compose service state, the RQ worker, queue depth, API
dependencies, disk capacity, and the latest backup.

## Deploy

Deploy the checked-out `main` branch after CI passes:

```bash
sudo bash scripts/deploy_enterprise_rag.sh
```

The script rebuilds API, worker, and frontend, then waits for `/health`.
For a failed deployment, inspect the API first:

```bash
sudo docker compose logs api --tail 100
sudo docker compose logs worker --tail 100
```

## Backup and restore verification

Create a backup manually or through the scheduled job:

```bash
sudo bash scripts/backup_mysql.sh
```

Confirm a backup can be restored into a temporary database before relying on
it for recovery. Do not restore over the production database during a test.

## Common recovery actions

| Symptom | First action |
| --- | --- |
| API health fails | Inspect API logs and MySQL/Redis/Qdrant service state. |
| Document remains `uploaded` or `processing` | Inspect worker logs and RQ queue; retry from the workspace after the worker recovers. |
| Document is `failed` | Read the document error, correct the input or dependency failure, then retry. |
| Retrieval quality declines | Run the versioned retrieval evaluation before changing chunking, embeddings, or score thresholds. |
| Disk capacity is low | Check Docker images, backup retention, and document volume usage before deleting anything. |

## Security operations

- Keep `backend/app/.env` out of Git and use distinct MySQL application and
  root passwords.
- Self-registration remains disabled by default. Create the first admin with
  `scripts/create_admin.py`; promote verified existing users with
  `scripts/promote_user.py`.
- Do not expose MySQL outside localhost. Use an SSH tunnel for administrative
  database access.
