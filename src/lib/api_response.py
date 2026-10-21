from typing import Any, Generic, List, Literal, TypeVar

from pydantic import BaseModel, Field

from src.lib.api_enum import SortOrderEnum

T = TypeVar("T")


class BasePagination(BaseModel):
    page: int = 1
    page_size: int = 20


class Pagination(BasePagination):
    order_by: SortOrderEnum | None = None


class PaginationMetadata(Pagination):
    total_page: int = 0
    total: int = 0


class ApiError(BaseModel):
    code: str | None = None
    details: Any | None = None
    message: str | None = None


class ApiBase(BaseModel):
    status: Literal["success", "failed"]
    message: str


class ApiCollectionResponse(ApiBase, Generic[T]):
    data: List[T] = Field(default_factory=list)
    error: ApiError | None = None
    metadata: PaginationMetadata | None = None


class ApiSingletonResponse(ApiBase, Generic[T]):
    data: T | None = None
    error: ApiError | None = None
