# Todo API project knowledge

## Authentication

Users log in through `POST /auth/login` with a username and password. A successful login returns a JWT access token. Protected endpoints require the `Authorization: Bearer <token>` request header.

Passwords are stored as hashes. The authentication code verifies the password hash and then creates the JWT. A missing or invalid token returns HTTP 401. A logged-in user without the required role returns HTTP 403.

## Tasks

`GET /tasks/me` returns the current user's tasks. The current user comes from the JWT, not from a user ID supplied by the client. `POST /tasks` creates a task for the current user.

查询当前用户任务时使用 `GET /tasks/me`。当前用户由 JWT token 决定，客户端不需要也不应该传入 user_id。

Tasks have `title`, `done`, `archived`, and timestamps. `PATCH /tasks/{task_id}` performs a partial update. The `/done`, `/undone`, and `/archive` routes are action endpoints for explicit state changes.

## Application layers

Routers receive HTTP requests, validate request data with Pydantic schemas, and convert application errors to HTTP responses. Services contain business logic and database operations. ORM models define database tables. Alembic migrations change the database schema.

## Redis

Redis provides rate limiting for login and AI endpoints. The login limiter counts failed requests in a time window. AI endpoints are limited per current user so a single user cannot consume unlimited model requests.
