# Enterprise RAG Knowledge Hub

Enterprise knowledge-base question answering with FastAPI, React, MySQL,
Redis, RQ, Qdrant, and Docker Compose. It supports private-document
processing, LangChain recursive text splitting, vector retrieval, and
source-grounded RAG answers with PDF page citations. Users can ask across every
ready document in one knowledge base or constrain a question to one document.
LangChain prompt templates isolate retrieved reference material from model
instructions before requests reach DeepSeek. Conversations remain scoped to the
selected document or knowledge base for follow-up questions.

## Implemented Capabilities

- Private knowledge bases with owner, editor, and viewer roles.
- PDF validation, SHA-256 duplicate detection per knowledge base, and secure
  original-file downloads.
- Background PDF extraction, LangChain recursive chunking, embeddings, and
  Qdrant indexing with retry and reindex operations.
- Document tags for organization, vector-search filtering, and RAG-answer
  filtering. Updating tags on a ready document automatically rebuilds its
  vectors so metadata and retrieval stay consistent.
- Processing metadata in the document list: status, chunk count, and last
  successful index time.
- Knowledge-base and single-document answers with DeepSeek, streaming SSE,
  source citations, conversation history, and citation follow-up actions.
- Retrieval search with tag filters, matching snippets, page numbers, and
  relevance scores.
- Answer feedback summaries, retrieval-quality evaluation, structured audit
  logs, and MySQL backup/restore verification scripts.

## Key Workflows

### Document lifecycle

```text
upload PDF -> SHA-256 duplicate check -> uploaded -> Redis/RQ
    -> processing -> PDF chunks -> embeddings -> Qdrant -> ready
                                                \-> failed -> retry
```

The document list exposes the final chunk count and index completion time. A
reindex or a tag change on a ready document removes its old vectors before the
worker queues a replacement index.

### Grounded answer lifecycle

```text
question + optional tags -> authorization -> Qdrant filtered retrieval
    -> relevance threshold -> LangChain prompt -> DeepSeek SSE response
    -> conversation + cited sources persisted in MySQL
```

Sources include PDF pages where available. A user can search matching chunks,
open the original authorized PDF, or switch directly into a cited document for
a focused follow-up question.

## Architecture

```text
React frontend
    |
    v
Nginx /api proxy
    |
    v
FastAPI API ---- MySQL
    |               |
    |               +-- users, knowledge_bases, documents
    |
    +-- Redis / RQ queue --> RQ worker --> Qdrant
```

Document processing flow:

```text
upload -> uploaded -> Redis queue -> processing -> ready / failed
```

The worker validates documents, extracts text, splits chunks, creates
embeddings, and stores vectors in Qdrant. Failed documents can be retried.
Editors can reindex a ready document after changing document-processing or
embedding settings; reindexing clears that document's old vectors and queues a
fresh processing job.
The upload flow fingerprints PDF content and rejects an identical file within
the same knowledge base, preventing duplicate vectors and duplicate retrieval
results.
Each question is saved with its answer and citations; a follow-up uses only the
latest history from the same user's selected document.

Knowledge bases are private by default. An owner can share a knowledge base by
username: editors can upload, retry, and delete documents; viewers can only
read, search, and ask questions. The API enforces these roles for every
knowledge-base, document, and retrieval request.

## Services

| Service | Responsibility |
| --- | --- |
| `frontend` | React application served by Nginx |
| `api` | FastAPI REST API and Alembic migrations |
| `worker` | RQ background document processor |
| `mysql` | Persistent relational data |
| `redis` | RQ queue and rate-limit storage |
| `qdrant` | Document vector search |

## Configuration

Copy `backend/app/.env.example` to `backend/app/.env`, then set real secrets
and passwords. Do not commit `.env`.

Required production database settings:

```env
MYSQL_DATABASE=enterprise_rag
MYSQL_USER=enterprise_rag
MYSQL_PASSWORD=replace-with-a-private-password
MYSQL_ROOT_PASSWORD=replace-with-a-different-private-password
DATABASE_URL=mysql+pymysql://enterprise_rag:replace-with-a-private-password@mysql:3306/enterprise_rag?charset=utf8mb4
MAX_DOCUMENT_SIZE_MB=10
```

PDF uploads default to 10 MB. Increase `MAX_DOCUMENT_SIZE_MB` only after
confirming that API, worker, and storage capacity support the larger files.

`RAG_QUERY_REWRITE_ENABLED` defaults to `false`. Enable it only after measuring
retrieval quality on the evaluation set: each enabled question makes one
additional DeepSeek request before vector retrieval and safely falls back to
the original question when rewriting fails.

## Run With Docker Compose

Create the persistent volumes once before the first production startup:

```bash
for volume in \
  enterprise-rag-api-data \
  enterprise-rag-document-data \
  enterprise-rag-model-cache \
  enterprise-rag-mysql-data \
  enterprise-rag-redis-data \
  enterprise-rag-qdrant-data; do
  docker volume create "$volume"
done
```

Then start the services:

```bash
docker compose up -d --build
docker compose ps
```

The API runs Alembic migrations on startup. Health endpoints:

```text
GET /health/live
GET /health/ready
GET /health
```

The frontend is served on port `8080`; the API is served on port `8000`.

## Tests

```bash
python -m pytest backend/app/tests -q
```

Tests use isolated SQLite databases. Development and production application
data use MySQL.

## Retrieval Evaluation

Use a small, versioned set of representative questions to measure retrieval
quality before changing chunking, embeddings, or the relevance threshold. Copy
`backend/app/evaluations/retrieval_cases.example.json`, replace the example IDs
with documents from a non-production evaluation knowledge base, and label the
expected document page or exact chunk for every question.

Run the evaluation where Qdrant and the embedding model are available:

```bash
python scripts/evaluate_retrieval.py path/to/retrieval_cases.json --k 3
```

The report contains `recall_at_k`, `mrr_at_k`, and failed case names. The tool
only reads vectors; it does not modify documents, Qdrant, or MySQL.

## Backups

Create a MySQL backup from the production host:

```bash
set -a
source backend/app/.env
set +a

sudo docker compose exec -T -e MYSQL_PWD="$MYSQL_PASSWORD" mysql \
  mysqldump --no-tablespaces --single-transaction \
  -u"$MYSQL_USER" "$MYSQL_DATABASE" \
  > ~/backups/enterprise-rag/enterprise_rag-mysql-$(date +%F).sql
```

Run the repository helpers from the production checkout for routine checks:

```bash
sudo bash scripts/check_production.sh
sudo bash scripts/backup_mysql.sh
```

The production check verifies that the document worker container is running and
reports the registered RQ worker count and pending document jobs before it
checks API health and backups.

Validate backups periodically by restoring the newest dump into a temporary
database and comparing table counts. A successful `mysqldump` alone does not
prove that a restore will work.

## Production Resource Migration

The repository includes `scripts/migrate_production_resources.sh` for the
one-time migration from the former Todo deployment. It creates new
`enterprise-rag-*` Docker volumes and an `enterprise_rag` MySQL database,
copies MySQL, document, Qdrant, and model-cache data, and retains the old
resources for rollback. Redis starts with an empty queue intentionally.

Run the script only on the production VM after this release is merged and the
automatic deploy workflow is disabled. Do not update the old `~/todo-api`
checkout before migration: it is needed to access the old Compose resources.
Clone the current repository to a temporary directory and run the migration
script from there:

```bash
git clone https://github.com/Min-Bai/enterprise-rag-knowledge-hub.git \
  ~/enterprise-rag-migration

cd ~/enterprise-rag-migration
bash scripts/migrate_production_resources.sh
```

After migration, update the Windows runner SSH configuration so the same VM is
available through the `enterprise-rag-vm` host alias. The deployment workflows
use that alias and `~/deploy-enterprise-rag.sh`.
