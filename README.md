# Todo API

Full-stack Todo application with FastAPI, MySQL, Redis, React, and Docker.

```text
./
|- python_practice/day57/  # FastAPI backend
|- frontend/               # React frontend
|- Dockerfile              # Backend image
|- compose.yaml            # API, Redis, and frontend services
`- requirements.txt        # Backend dependencies
```

## Deployment

Create `python_practice/day57/.env` from `.env.example`, then run:

```bash
docker compose up -d --build
```
