from fastapi import status

from app.common.exceptions import AccessDeniedError, EntityNotFoundError, UnauthorizedError


def test_entity_not_found_error():
    exception = EntityNotFoundError("client", 123)
    assert exception.status_code == status.HTTP_404_NOT_FOUND
    assert exception.detail == "client with id 123 not found"


def test_access_denied_error():
    exception = AccessDeniedError("Operation blocked")
    assert exception.status_code == status.HTTP_403_FORBIDDEN
    assert exception.detail == "Operation blocked"


def test_unauthorized_error():
    exception = UnauthorizedError()
    assert exception.status_code == status.HTTP_401_UNAUTHORIZED
    assert exception.detail == "Unauthorized"
