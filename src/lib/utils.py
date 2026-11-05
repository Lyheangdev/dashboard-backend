import math
from datetime import datetime
from zoneinfo import ZoneInfo

from src.lib.api_response import PaginationMetadata


def calculateOffset(page: int, page_size: int):
    return (page - 1) * page_size


def calculatePaginationParmas(*, page: int, page_size: int, total: int) -> PaginationMetadata:
    return PaginationMetadata(
        page=page, page_size=page_size, total_page=math.ceil(total / page_size), total=total
    )


def getFullName(*, fname: str | None, lname: str | None) -> str:
    return f"{fname} {lname}"


def combineLog(*, fname: str | None, lname: str | None, msg: str | None):
    return f"{fname} {lname} {msg}"


def getCurrentTime() -> str:
    now = datetime.now(ZoneInfo("Asia/Phnom_Penh"))
    return now.strftime("%Y-%m-%d %H:%M:%S")
