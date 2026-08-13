# Enterprise RAG Knowledge Hub

企业 RAG 知识库问答系统，基于 FastAPI、React、MySQL、Redis、RQ、Qdrant
和 Docker Compose 构建，支持私有文档处理、向量检索和带来源引用的问答。

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
    |               +-- users, tasks, documents
    |
    +-- Redis / RQ queue --> RQ worker --> Qdrant
```

Document processing flow:

```text
upload -> uploaded -> Redis queue -> processing -> ready / failed
```

The worker validates PDFs, extracts text, splits chunks, creates embeddings,
and stores vectors in Qdrant. Failed documents can be retried.

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

Copy `backend/app/.env.example` to
`backend/app/.env`, then set real secrets and passwords.

Required production database settings:

```env
MYSQL_DATABASE=todo_app
MYSQL_USER=todo_app
MYSQL_PASSWORD=replace-with-a-private-password
MYSQL_ROOT_PASSWORD=replace-with-a-different-private-password
DATABASE_URL=mysql+pymysql://todo_app:replace-with-a-private-password@mysql:3306/todo_app?charset=utf8mb4
```

Do not commit `.env`.

## Run With Docker Compose

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

## Backups

Create a MySQL backup from the production host:

```bash
set -a
source backend/app/.env
set +a

sudo docker compose exec -T -e MYSQL_PWD="$MYSQL_PASSWORD" mysql \
  mysqldump --no-tablespaces --single-transaction \
  -u"$MYSQL_USER" "$MYSQL_DATABASE" \
  > ~/backups/enterprise-rag/todo_app-mysql-$(date +%F).sql
```
