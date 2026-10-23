from asyncio import run as async_runner
from asyncio import sleep
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from src.config.database import PostGresConnector
from src.lib.api_auth import hashMyPassword
from src.lib.authority_enum import EPermission, EResource, ERole
from src.lib.user_enum import EUserStatus
from src.models.asset_model import AssetModel
from src.models.line_model import LineModel
from src.models.permission_model import PermissionModel
from src.models.role_model import RoleModel
from src.models.role_permission_model import role_permission_model
from src.models.user_model import UserModel
from src.models.user_role_model import user_role_model

alchemy_session = PostGresConnector()

"""
Caution: PLEASE DO NOT RUN THIS FILE WIOUT UNDERSTANDING, IT WILL COMPROMISE ALL THE SYTEM DATA
Owner: lyheang.pic@svi-aec.com
Created date: October, 21 2026
"""


async def initalizeSession():
    async with alchemy_session.session_factory() as async_session:
        return async_session


# Removing all existing permissions
async def executeRemvingPermission():
    print()
    print("1. clean all permission table")
    print()
    print(f"-> Start removing permissions: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()

    try:
        stmt = delete(PermissionModel)

        await async_session.execute(stmt)
        await async_session.commit()

        print()
        print("✅ Delete all permissions successfully.")
        print()
        print(f"-> End removing permissions: [{datetime.now()}]")

    except Exception as e:
        await async_session.rollback()
        print("Error:", e)

    finally:
        await async_session.close()


# Removing all roles
async def executeRemvingRole():
    print()
    print("2. clean all role table")
    print()
    print(f"-> Start removing roles: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()

    try:
        stmt = delete(RoleModel)

        await async_session.execute(stmt)
        await async_session.commit()

        print()
        print("✅ Delete all roles successfully.")
        print()
        print(f"-> End removing roles: [{datetime.now()}]")

    except Exception as e:
        await async_session.rollback()
        print("Error:", e)

    finally:
        await async_session.close()


# Removing all existing users
async def executeRemvingUsers():
    print()
    print("2. clean all user table")
    print()
    print(f"-> Start removing users: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()

    try:
        stmt = delete(UserModel)

        await async_session.execute(stmt)
        await async_session.commit()

        print()
        print("✅ Delete all users successfully.")
        print()
        print(f"-> End removing users: [{datetime.now()}]")

    except Exception as e:
        await async_session.rollback()
        print("Error:", e)

    finally:
        await async_session.close()


# Insert all permissions into system
async def excuteAddAllPermission():
    print()
    print("2. Add permission table")
    print()
    print(f"-> Start adding permission: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()
    permisions: list[PermissionModel] = []

    try:
        for permission in EPermission:
            base = permission.value
            resource = base.split(":")[1]

            permissionModel = PermissionModel()
            permissionModel.resource = resource
            permissionModel.action = base

            permisions.append(permissionModel)

        async_session.add_all(permisions)
        await async_session.commit()
        await async_session.flush()

        print("✅ Adding permissions successfully.")

    except SQLAlchemyError as e:
        print("Original error:", repr(e))

    finally:
        await async_session.close()


# Insert a default role into system
async def executeAddRole():
    print()
    print("2. Add role table")
    print()
    print(f"-> Start adding role: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()

    try:
        stmt = select(PermissionModel)
        result_set = await async_session.execute(stmt)
        permisions = result_set.scalars().all()

        if len(permisions) == 0:
            raise Exception("No permissions!")

        # * Initialize superadmin role
        roleSuperadmin = RoleModel()
        roleSuperadmin.role = ERole.SUPERADMIN.value

        for permisson in permisions:
            roleSuperadmin.permissions.append(permisson)

        # * Initialize admin role
        roleAdmin = RoleModel()
        roleAdmin.role = ERole.ADMIN.value

        admin_allowed_permissions = [
            EPermission.USER_READ.value,
            EPermission.USER_WRITE.value,
            EPermission.USER_UPDATE.value,
        ]

        admin_permissions = [
            admin_p for admin_p in permisions if admin_p.action in admin_allowed_permissions
        ]


        if len(admin_permissions) == 0:
            raise Exception("Admin no permission added, please check!")

        for xp in admin_permissions:
            roleAdmin.permissions.append(xp)
        

        # * Apply commit change
        async_session.add_all([roleSuperadmin, roleAdmin])
        await async_session.commit()
        await async_session.flush()

        print("✅ Adding role [Superadmin, Admin] successfully.")

    except SQLAlchemyError as e:
        await async_session.rollback()
        print("Original error:", repr(e))

    except Exception as ee:
        await async_session.rollback()
        print(ee)

    finally:
        await async_session.close()


# Attach an role for the default user into system
async def excuteAddSuperAdminUser():
    print()
    print("2. Add user table")
    print()
    print(f"-> Start adding user: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()

    try:
        stmt = select(RoleModel).where(RoleModel.role == ERole.SUPERADMIN.value)
        result_set = await async_session.execute(stmt)

        role = result_set.scalar_one_or_none()

        if role is None:
            raise Exception("⚠️ Role not found!")

        user = UserModel()
        user.first_name = "SVI(AEC)"
        user.last_name = "Superadmin"
        user.email = "superadmin@sviaec.com"
        user.password = hashMyPassword("12345678")
        user.bio = "Full system control."
        user.roles.append(role)
        user.created_by = "System"
        user.code = "KH53419"
        user.status = EUserStatus.ACTIVE.value

        async_session.add(user)
        await async_session.commit()
        await async_session.flush()

        print("✅ Adding user successfully.")
        print("Login credentials:")
        print("Email: superadmin@sviaec.com")
        print("Password: 12345678")

    except SQLAlchemyError as e:
        await async_session.rollback()
        print("Original error:", repr(e))

    except Exception as ge:
        await async_session.rollback()
        print("Exception:", repr(ge))

    finally:
        await async_session.close()


# Execution entrypoint
async def contextExecuter():
    await executeRemvingPermission()
    print("waiting for the next process...")

    await sleep(1.5)
    await executeRemvingRole()
    print("waiting for the next process...")

    await sleep(1.5)
    await executeRemvingUsers()
    print("waiting for the next process...")

    await sleep(1.5)
    print("waiting for adding permissions process...")

    await sleep(1.5)
    await excuteAddAllPermission()
    print("waiting for adding role process ...")

    await sleep(1.5)
    await executeAddRole()
    print("waiting for adding user process ...")

    await sleep(1.5)
    await excuteAddSuperAdminUser()


if __name__ == "__main__":
    print("------------------------------------")
    print("     | System Boostrap |        ")
    print("------------------------------------")
    print()
    print("||||| System runs deletions step |||||")
    print()
    async_runner(contextExecuter())
