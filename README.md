# Day57 - Project Structure Todo API

This version keeps the same Todo API behavior as day56, but splits the code into a more realistic project structure.

```text
day57/
├── main.py
├── database.py
├── models/
│   └── task.py
├── schemas/
│   └── task.py
├── routers/
│   └── tasks.py
├── services/
│   └── tasks.py
└── tests/
    └── test_tasks_api.py
```

## Run

```powershell
& 'python_practice/day31/.venv/Scripts/python.exe' -m uvicorn python_practice.day57.main:app --reload
```

## Test

```powershell
& 'python_practice/day31/.venv/Scripts/python.exe' -m pytest python_practice/day57/tests/test_tasks_api.py -q
```
