import math

from src.domain.dtos.response_dtos import PaginationMetadata


def calculateOffset(page: int, page_size: int):
    return (page - 1) * page_size


def calculatePaginationParmas(*, page: int, page_size: int, total: int) -> PaginationMetadata:
    return PaginationMetadata(
        page=page, page_size=page_size, total_page=math.ceil(total / page_size), total=total
    )