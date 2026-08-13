# Enterprise RAG Knowledge Hub Project Knowledge

## Authentication

Users authenticate through `POST /auth/login` with a username and password.
Successful authentication returns a JWT access token. Protected endpoints use
the `Authorization: Bearer <token>` header. Invalid tokens return HTTP 401 and
insufficient privileges return HTTP 403.

## Knowledge Bases And Documents

Each knowledge base belongs to one user. Documents are uploaded into a selected
knowledge base, stored durably, processed by an RQ worker, split into chunks,
embedded, and indexed in Qdrant. Document status progresses through `uploaded`,
`processing`, `ready`, or `failed`.

## RAG Answers

Document-answer endpoints retrieve relevant chunks from Qdrant, apply a minimum
similarity threshold, and use the matched context to generate answers. Responses
include source chunks so the user can inspect the grounding evidence.

## Supporting Task Workspace

The application retains authenticated task endpoints from the original learning
project. Tasks are user-scoped and are not part of the knowledge-base retrieval
index.

## Operations

MySQL stores relational application data. Redis provides RQ queues and rate
limiting. Qdrant stores vector data. The `/health` endpoint checks MySQL, Redis,
and Qdrant readiness.
