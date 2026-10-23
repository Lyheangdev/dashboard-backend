from enum import Enum


class EAuditingStatus(Enum):
    SUCCESS = 1
    FAILED = 2


class ERole(Enum):
    SUPERADMIN = "Superadmin"
    ADMIN = "Admin"
    AUTHOR = "Author"
    EDITOR = "Editor"


class EResource(Enum):
    LOGIN = "LOGIN"
    USER = "USER"
    ROLE = "ROLE"
    PERMISSION = "PERMISSION"
    SYSTEM_ACCESS = "SYSTEM_ACCESS"


class EAction(Enum):
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
    USER_READ = f"{EAction.READ.value}:{EResource.USER.value}"
    USER_WRITE = f"{EAction.WRITE.value}:{EResource.USER.value}"
    USER_UPDATE = f"{EAction.UPDATE.value}:{EResource.USER.value}"
    USER_DELETE = f"{EAction.DELETE.value}:{EResource.USER.value}"
    USER_BAN = f"{EAction.BAN.value}:{EResource.USER.value}"
    USER_UNBAN = f"{EAction.UNBAN.value}:{EResource.USER.value}"
    USER_UPDATE_STATUS = f"{EAction.UPDATE_STATUS.value}:{EResource.USER.value}"

    ROLE_READ = f"{EAction.READ.value}:{EResource.ROLE.value}"
    ROLE_WRITE = f"{EAction.WRITE.value}:{EResource.ROLE.value}"
    ROLE_UPDATE = f"{EAction.UPDATE.value}:{EResource.ROLE.value}"
    ROLE_DELETE = f"{EAction.DELETE.value}:{EResource.ROLE.value}"

    PERMISSION_READ = f"{EAction.READ.value}:{EResource.PERMISSION.value}"
    PERMISSION_WRITE = f"{EAction.WRITE.value}:{EResource.PERMISSION.value}"
    PERMISSION_UPDATE = f"{EAction.UPDATE.value}:{EResource.PERMISSION.value}"
    PERMISSION_DELETE = f"{EAction.DELETE.value}:{EResource.PERMISSION.value}"

    SYSTEM_ACCESS_READ = f"{EAction.READ.value}:{EResource.SYSTEM_ACCESS.value}"
    SYSTEM_ACCESS_ADD = f"{EAction.WRITE.value}:{EResource.SYSTEM_ACCESS.value}"
    SYSTEM_ACCESS_REMOVE = f"{EAction.UPDATE.value}:{EResource.SYSTEM_ACCESS.value}"
    SYSTEM_ACCESS_UPDATE = f"{EAction.DELETE.value}:{EResource.SYSTEM_ACCESS.value}"
