from typing import Generic, TypeVar

from pydantic import BaseModel

from ...request_context import get_request_id

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: str = "OK"
    message: str = "success"
    data: T
    request_id: str | None = None


def ok(data: T, message: str = "success") -> ApiResponse[T]:
    return ApiResponse(data=data, message=message, request_id=get_request_id())
