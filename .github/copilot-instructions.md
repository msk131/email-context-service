# FastAPI Engineering Standards & Best Practices

## Project Architecture
* Use a structured layout (`app/main.py`, `app/api/`, `app/core/`, `app/models/`, `app/schemas/`).
* Keep the `main.py` file clean; only initialize the app, lifespan, middleware, and routers.
* Group related endpoints into dedicated router files using `APIRouter`.
* Use explicit tags and prefixes for all routers to ensure clean OpenAPI documentation.

## Code Style & Type Safety
* Enforce strict PEP 8 compliance.
* Use Python type hints for all function arguments, return types, and variables.
* Prefer `Pydantic v2` for data validation, serialization, and settings management.
* Use `Field` to define validation constraints, descriptions, and examples in schemas.
* Prefer standard Python collections (`list`, `dict`, `set`) over `typing.List` or `typing.Dict`.

## Asynchronous Programming
* Use `async def` for endpoints interacting with async libraries (e.g., databases, HTTP clients).
* Use standard `def` for endpoints executing synchronous, blocking operations to prevent event loop starvation.
* Always await asynchronous calls explicitly.

## Dependency Injection
* Utilize `fastapi.Depends` for shared logic like authentication, database sessions, and configuration.
* Prefer dependency injection over global variables or direct instantiations.
* Use `Annotated` syntax for dependencies to improve readability and type safety.
  * Example: `current_user: Annotated[User, Depends(get_current_user)]`

## Database & Session Management
* Use SQLAlchemy 2.0 async style or Tortoise ORM for database communication.
* Manage database sessions using a context manager or a lifespan event handler.
* Yield sessions in dependencies to guarantee cleanup and connection release.
  * Example: `async with async_session() as session: yield session`

## Error Handling & HTTP Responses
* Raise `fastapi.HTTPException` with explicit numeric status codes from `status` module.
* Create custom exception handlers for domain-specific errors to keep routers clean.
* Always define explicit `response_model` or return types on route decorators.
* Never expose raw database exceptions or internal stack traces to the client.

## Security & Configuration
* Manage application configuration using `pydantic-settings`.
* Load environment variables into a typed `Settings` object; never read `os.environ` inside business logic.
* Implement OAuth2 with Password bearer and JWT tokens for authentication.
* Use `passlib` with `bcrypt` for secure password hashing.
