from typing import Literal, TypedDict, Unpack

from fastapi import HTTPException, status

from src.domain.entities.user_entity import UserEntity
from src.domain.enums.authorities_enum import EPermission, ERole


class AuthorizeParams(TypedDict, total=False):
    roles: list[ERole] | None
    permission: EPermission | None
    owner_id: int | None
    operation: Literal["AND", "OR"]


class AuthorizationService:
    def __init__(self, user: UserEntity):
        self.isGranted = False
        self.user = user

    def authorize(self, **kwargs: Unpack[AuthorizeParams]) -> UserEntity:
        """
        @description: pre-check incomming trafic for authorization such as role, permission.

        @params: roles, permission, owner_id, operation

        @return: UserEntity
        """
        owner_id = kwargs.get("owner_id", None)
        roles = kwargs.get("roles", None)
        permission = kwargs.get("permission", None)
        operation = kwargs.get("operation", "OR")

        if self.user.checkIsBanned or self.user.checkIsInactive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your user is in inactive mode or got banned!",
            )

        if not self.user.checkHasRole or not self.user.checkHasPermissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lack of role and permissions config!",
            )

        if not self.user.checkHasView:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lack of system menus config!",
            )

        # @! if owner_id provide, so system will automatically process to check ownership only
        if owner_id is not None:
            self.isGranted = self.user.checkIsAuthorized(owner_id, permission=permission)
        # @! if owner is not provide, system will default to work based on role or permission
        else:
            is_granted_role = self.user.checkIsRoleAllowed(roles=roles)
            is_granted_permission = self.user.checkIsPermissionAllowed(permission=permission)

            self.isGranted = (
                (is_granted_role or is_granted_permission)
                if operation == "OR"
                else (is_granted_role and is_granted_permission)
            )

        if not self.isGranted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden!")

        return self.user
