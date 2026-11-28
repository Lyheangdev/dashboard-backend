from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums.api_entities.api_user_entity_enum import EUserStatus
from src.domain.enums.authorities_enum import EPermission, ERole
from src.domain.enums.system_credentials_enum import ESystemCredentials
from src.domain.utils.security.password_security_helper import verifyPassword


@dataclass
class UserEntity:
    # -- These fields will automatically map into pydantic obj
    id: int | None
    email: str
    full_name: str | None = None
    bio: str | None = None
    profile_url: str | None = None
    role: str | None = None
    isBanned: bool = False
    status: int | None = None
    code: str | None = None
    permissions: list[str] | None = field(default_factory=list)
    views: list[str] | None = field(default_factory=list)
    resources: list[str] | None = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # -- Spares fields
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None

    # -- Run after init called
    def __post__init__(self):
        self.superadminEmail = ESystemCredentials.EMAIL.value

    def deActivateStatus(self) -> None:
        self.status = EUserStatus.INACTIVE.value

    def activateStatus(self) -> None:
        self.status = EUserStatus.ACTIVE.value

    def setToBan(self) -> None:
        self.isBanned = True

    def setToUnban(self) -> None:
        self.isBanned = False

    @property
    def hasUser(self) -> bool:
        return bool(self.id)

    def getRole(self) -> str | None:
        return self.role

    def getPermissions(self) -> list[str]:
        return self.permissions

    @property
    def checkIsSuperadminEmail(self) -> bool:
        return self.email == self.superadminEmail

    @property
    def checkHasView(self) -> bool:
        return len(self.views) > 0

    # Validate whether user contain any roles
    @property
    def checkHasRole(self) -> bool:
        return bool(self.role)

    # Validate whether user contains any permissions
    @property
    def checkHasPermissions(self) -> bool:
        return len(self.permissions) > 0

    # Validate for banned user
    @property
    def checkIsBanned(self) -> bool:
        return self.isBanned

    # Validate for active user
    @property
    def checkIsInactive(self) -> bool:
        return self.status == EUserStatus.INACTIVE.value

    # Validate whether credentials is satisy
    def checkIsCredentialsVerified(self, *, email: str, password: str) -> bool:
        return email == self.email and verifyPassword(password, self.password)

    # Validate only ownership
    def checkIsOwner(self, user_id) -> bool:
        return self.id == user_id

    # Validate only role is allowed
    def checkIsRoleAllowed(self, roles: list[ERole] | None) -> bool:
        return (
            self.role in [r.value for r in roles]
            if roles is not None and len(roles) > 0
            else False
        )

    # Validate only permission is allowed
    def checkIsPermissionAllowed(self, permission: EPermission | None) -> bool:
        return permission.value in self.permissions if permission is not None else False

    # Validate both ownership & permission
    def checkIsAuthorized(self, user_id: int | None, permission: EPermission | None) -> bool:
        if user_id is None or permission is None:
            return False
        return self.checkIsOwner(user_id=user_id) and self.checkIsPermissionAllowed(
            permission=permission
        )
