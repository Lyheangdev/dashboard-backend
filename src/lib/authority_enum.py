from enum import Enum


class EAuditingStatus(Enum):
    SUCCESS = 1
    FAILED = 2


class ERole(Enum):
    SUPERADMIN = "Superadmin"
    ADMIN = "Admin"
    EDITOR = "Editor"
    AUTHOR = "Author"


class EResource(Enum):
    DASHBOARD = "DASHBOARD"
    LOGIN = "LOGIN"
    USER = "USER"
    ROLE = "ROLE"
    PERMISSION = "PERMISSION"
    SYSTEM_ACCESS = "SYSTEM_ACCESS"
    REAMLTIME_SSE = "REALTIME_SSE"
    LOG = "LOG"
    VIEW = "VIEW"
    PROJECT = "PROJECT"
    PROJECT_LINE = "PROJECT_LINE"
    CUSTOMER = "CUSTOMER"
    WORKORDER = "WORKORDER"
    JOBORDER = "JOBORDER"
    LINE = "LINE"
    LINE_OWNER = "LINE_OWNER"
    PROCESS = "PROCESS"
    YIELD = "YIELD"


class EAction(Enum):
    ADD = "ADD"
    READ = "READ"
    WRITE = "WRITE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DELETE_ALL = "DELETE_ALL"
    EXPORT = "EXPORT"
    BAN = "BAN"
    UNBAN = "UNBAN"
    UPDATE_STATUS = "UPDATE_STATUS"


class EPermission(Enum):
    USER_READ = f"{EResource.USER.value}:{EAction.READ.value}"
    USER_WRITE = f"{EResource.USER.value}:{EAction.WRITE.value}"
    USER_UPDATE = f"{EResource.USER.value}:{EAction.UPDATE.value}"
    USER_DELETE = f"{EResource.USER.value}:{EAction.DELETE.value}"
    USER_BAN = f"{EResource.USER.value}:{EAction.BAN.value}"
    USER_UNBAN = f"{EResource.USER.value}:{EAction.UNBAN.value}"
    USER_UPDATE_STATUS = f"{EResource.USER.value}:{EAction.UPDATE_STATUS.value}"

    ROLE_READ = f"{EResource.ROLE.value}:{EAction.READ.value}"
    ROLE_WRITE = f"{EResource.ROLE.value}:{EAction.WRITE.value}"
    ROLE_UPDATE = f"{EResource.ROLE.value}:{EAction.UPDATE.value}"
    ROLE_DELETE = f"{EResource.ROLE.value}:{EAction.DELETE.value}"

    PERMISSION_READ = f"{EResource.PERMISSION.value}:{EAction.READ.value}"
    PERMISSION_WRITE = f"{EResource.PERMISSION.value}:{EAction.WRITE.value}"
    PERMISSION_UPDATE = f"{EResource.PERMISSION.value}:{EAction.UPDATE.value}"
    PERMISSION_DELETE = f"{EResource.PERMISSION.value}:{EAction.DELETE.value}"

    SYSTEM_ACCESS_READ = f"{EResource.SYSTEM_ACCESS.value}:{EAction.READ.value}"
    SYSTEM_ACCESS_ADD = f"{EResource.SYSTEM_ACCESS.value}:{EAction.WRITE.value}"
    SYSTEM_ACCESS_REMOVE = f"{EResource.SYSTEM_ACCESS.value}:{EAction.UPDATE.value}"
    SYSTEM_ACCESS_UPDATE = f"{EResource.SYSTEM_ACCESS.value}:{EAction.DELETE.value}"

    VIEW_READ = f"{EResource.VIEW.value}:{EAction.READ.value}"
    VIEW_WRITE = f"{EResource.VIEW.value}:{EAction.WRITE.value}"
    VIEW_UPDATE = f"{EResource.VIEW.value}:{EAction.UPDATE.value}"
    VIEW_DELETE = f"{EResource.VIEW.value}:{EAction.DELETE.value}"

    LOG_READ = f"{EResource.LOG.value}:{EAction.READ.value}"
    LOG_DELETE = f"{EResource.LOG.value}:{EAction.DELETE.value}"

    PROJECT_READ = f"{EResource.PROJECT.value}:{EAction.READ.value}"
    PROJECT_WRITE = f"{EResource.PROJECT.value}:{EAction.WRITE.value}"
    PROJECT_UPDATE = f"{EResource.PROJECT.value}:{EAction.UPDATE.value}"
    PROJECT_DELETE = f"{EResource.PROJECT.value}:{EAction.DELETE.value}"

    PROJECT_LINE_READ = f"{EResource.PROJECT_LINE.value}:{EAction.READ.value}"
    PROJECT_LINE_WRITE = f"{EResource.PROJECT_LINE.value}:{EAction.WRITE.value}"
    PROJECT_LINE_UPDATE = f"{EResource.PROJECT_LINE.value}:{EAction.UPDATE.value}"
    PROJECT_LINE_DELETE = f"{EResource.PROJECT_LINE.value}:{EAction.DELETE.value}"

    CUSTOMER_READ = f"{EResource.CUSTOMER.value}:{EAction.READ.value}"
    CUSTOMER_WRITE = f"{EResource.CUSTOMER.value}:{EAction.WRITE.value}"
    CUSTOMER_UPDATE = f"{EResource.CUSTOMER.value}:{EAction.UPDATE.value}"
    CUSTOMER_DELETE = f"{EResource.CUSTOMER.value}:{EAction.DELETE.value}"

    WORKORDER_READ = f"{EResource.WORKORDER.value}:{EAction.READ.value}"
    WORKORDER_WRITE = f"{EResource.WORKORDER.value}:{EAction.WRITE.value}"
    WORKORDER_UPDATE = f"{EResource.WORKORDER.value}:{EAction.UPDATE.value}"
    WORKORDER_DELETE = f"{EResource.WORKORDER.value}:{EAction.DELETE.value}"

    JOBORDER_READ = f"{EResource.JOBORDER.value}:{EAction.READ.value}"
    JOBORDER_WRITE = f"{EResource.JOBORDER.value}:{EAction.WRITE.value}"
    JOBORDER_UPDATE = f"{EResource.JOBORDER.value}:{EAction.UPDATE.value}"
    JOBORDER_DELETE = f"{EResource.JOBORDER.value}:{EAction.DELETE.value}"

    LINE_READ = f"{EResource.LINE.value}:{EAction.READ.value}"
    LINE_WRITE = f"{EResource.LINE.value}:{EAction.WRITE.value}"
    LINE_UPDATE = f"{EResource.LINE.value}:{EAction.UPDATE.value}"
    LINE_DELETE = f"{EResource.LINE.value}:{EAction.DELETE.value}"

    PROCESS_READ = f"{EResource.PROCESS.value}:{EAction.READ.value}"
    PROCESS_WRITE = f"{EResource.PROCESS.value}:{EAction.WRITE.value}"
    PROCESS_UPDATE = f"{EResource.PROCESS.value}:{EAction.UPDATE.value}"
    PROCESS_DELETE = f"{EResource.PROCESS.value}:{EAction.DELETE.value}"

    YIELD_READ = f"{EResource.YIELD.value}:{EAction.READ.value}"
    YIELD_WRITE = f"{EResource.YIELD.value}:{EAction.WRITE.value}"
    YIELD_UPDATE = f"{EResource.YIELD.value}:{EAction.UPDATE.value}"
    YIELD_DELETE = f"{EResource.YIELD.value}:{EAction.DELETE.value}"

    LINE_OWNER_READ = f"{EResource.LINE_OWNER.value}:{EAction.READ.value}"
    LINE_OWNER_WRITE = f"{EResource.LINE_OWNER.value}:{EAction.WRITE.value}"
    LINE_OWNER_UPDATE = f"{EResource.LINE_OWNER.value}:{EAction.UPDATE.value}"
    LINE_OWNER_DELETE = f"{EResource.LINE_OWNER.value}:{EAction.DELETE.value}"

    DASHBOARD_READ = f"{EResource.DASHBOARD.value}:{EAction.READ.value}"
    DASHBOARD_WRITE = f"{EResource.DASHBOARD.value}:{EAction.WRITE.value}"
    DASHBOARD_UPDATE = f"{EResource.DASHBOARD.value}:{EAction.UPDATE.value}"
    DASHBOARD_DELETE = f"{EResource.DASHBOARD.value}:{EAction.DELETE.value}"
