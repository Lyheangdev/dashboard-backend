from enum import Enum


class ApiTagEnum(Enum):
    PRODUCTION_LINE = "PRODUCTION LINE"
    SYSTEM_USER = "SYSTEM USER"
    AUTH = "AUTHENTICATION"
    PERMISSION = "PERMISSION"
    ROLE = "ROLE"
    SSE = "SSE"
    SYSTEM_ACCESS = "SYSTEM ACCESS"
    ASSETS = "ASSETS"
    THIRD_PARTY = "THIRD_PARTY"
    MENU_VIEW = "MENU VIEW"


class SortOrderEnum(Enum):
    ASC = "asc"
    DESC = "desc"
