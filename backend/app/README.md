# Enterprise RAG Knowledge Hub Backend

`backend/app` contains the FastAPI application for the Enterprise RAG
Knowledge Hub.

```text
backend/app/
|- main.py                 FastAPI application entry point
|- config.py               Environment configuration
|- database.py             SQLAlchemy engine and sessions
|- auth.py                 Authentication dependencies
|- security.py             Password hashing and JWT helpers
|- rate_limit.py           Redis-backed rate limiting
|- models/                 SQLAlchemy ORM models
|- schemas/                Pydantic request and response schemas
|- routers/                HTTP endpoints
|- services/               Business and RAG processing logic
|- migrations/             Alembic migrations
|- knowledge/              Project knowledge indexed for RAG
|- worker.py               RQ document-processing worker
`- tests/                  Automated tests
```

## Run

```bash
uvicorn backend.app.main:app --reload
```

## Test

```bash
python -m pytest backend/app/tests -q
```
