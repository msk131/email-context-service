# Background Tasks

## Tools

- Database-backed task table
- Async worker loop
- FastAPI task submission endpoints

## Purpose

Report generation can involve LLM calls and embedding work, so refresh requests
enqueue work and return quickly with a task id. The worker processes pending
tasks outside the request lifecycle.

## Where It Lives

- Task model: `app/models/background_task.py`
- Task repository: `app/repositories/tasks.py`
- Task service: `app/services/tasks.py`
- Worker: `app/tasks/worker.py`
- API endpoints: `app/api/v1/tasks.py`

## Design Notes

- Tasks are claimed atomically before processing.
- Completed tasks receive TTLs for cleanup.
- Public task status sanitizes internal failure details.
- A distributed queue can replace the DB queue later without changing routes.
