# Todo API Backend

This directory is the backend project root. In the original learning workspace,
it is located at `backend/app`.

```text
./
|- main.py                 # FastAPI application entry point
|- config.py               # Environment configuration
|- database.py             # SQLAlchemy database session
|- auth.py                 # Authentication dependencies
|- security.py             # Password hashing and JWT helpers
|- rate_limit.py           # Redis rate limiting
|- models/                 # SQLAlchemy ORM models
|  |- task.py
|  `- user.py
|- schemas/                # Pydantic request and response schemas
|  |- task.py
|  |- user.py
|  |- auth.py
|  `- ai.py
|- routers/                # HTTP endpoints and HTTP error conversion
|  |- tasks.py
|  |- users.py
|  |- auth.py
|  `- ai.py
|- services/               # Business logic and database operations
|  |- tasks.py
|  |- users.py
|  `- ai.py
|- migrations/             # Alembic database migrations
`- tests/                  # Automated tests
```

## Run

```powershell
& 'python_practice/day31/.venv/Scripts/python.exe' -m uvicorn backend.app.main:app --reload
```

## Test

```powershell
& 'python_practice/day31/.venv/Scripts/python.exe' -m pytest backend/app/tests/test_tasks_api.py -q
```
