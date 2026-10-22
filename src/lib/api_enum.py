from enum import Enum


class ApiTagEnum(Enum):
    PRODUCTION_LINE = "PRODUCTION LINE"
    SYSTEM_USER = "系统用户 | SYSTEM USER"
    AUTH = "登陆验证 | AUTHENTICATION"
    PERMISSION = "权限 | PERMISSION"
    ROLE = "作用 | ROLE"
    SSE = "SSE"
    SYSTEM_ACCESS = "系统访问 | SYSTEM ACCESS"
    ASSETS = "资产 | ASSETS"


class SortOrderEnum(Enum):
    ASC = "asc"
    DESC = "desc"
