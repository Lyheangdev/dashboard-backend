from asyncio import run as async_runner
from asyncio import sleep
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from src.domain.enums.api_entities.api_user_entity_enum import EUserStatus
from src.domain.enums.authorities_enum import EMenu, EPermission, ERole
from src.domain.enums.system_credentials_enum import ESystemCredentials
from src.domain.utils.security.password_security_helper import hashMyPassword
from src.infrastructure.cache.connection import RedisConnector
from src.infrastructure.database.connection import PostGresConnector
from src.infrastructure.models.asset.asset_model import AssetModel
from src.infrastructure.models.junctions.role_permission_model import role_permission_model
from src.infrastructure.models.junctions.role_view_model import role_view_model
from src.infrastructure.models.junctions.user_role_model import user_role_model
from src.infrastructure.models.line.line_model import LineModel
from src.infrastructure.models.permission.permission_model import PermissionModel
from src.infrastructure.models.role.role_model import RoleModel
from src.infrastructure.models.user.user_model import UserModel
from src.infrastructure.models.view.view_model import ViewModel

alchemy_session = PostGresConnector()
redisClient = RedisConnector()

"""
Caution: PLEASE DO NOT RUN THIS FILE WIOUT UNDERSTANDING, IT WILL COMPROMISE ALL THE SYTEM DATA
Owner: lyheang.pic@svi-aec.com
Created date: October, 21 2026
"""


async def initalizeSession():
    async with alchemy_session.session_factory() as async_session:
        return async_session


async def cleanUpRedisCache():
    try:
        await redisClient.redis_client.flushall()
        print("✅ All redis cache data has been wiped out successfully.")

    except Exception as error:
        print("🔚 Redis error.")
        raise error


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
async def executeRemvingMenu():
    print()
    print("2. clean all menu table")
    print()
    print(f"-> Start removing menus: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()

    try:
        stmt = delete(ViewModel)

        await async_session.execute(stmt)
        await async_session.commit()

        print()
        print("✅ Delete all menus successfully.")
        print()
        print(f"-> End removing menus: [{datetime.now()}]")

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
            resource = base.split(":")[0]

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


# Insert all menu into system
async def excuteAddAllMenu():
    print()
    print("2. Add menu table")
    print()
    print(f"-> Start adding menu: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()
    views: list[ViewModel] = []

    try:
        for view in EMenu:
            viewModel = ViewModel()
            viewModel.menu = view.value
            viewModel.note = "Main menu"
            views.append(viewModel)

        async_session.add_all(views)
        await async_session.commit()
        await async_session.flush()

        print("✅ Adding views successfully.")

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
            EPermission.CUSTOMER_WRITE.value,
            EPermission.CUSTOMER_DELETE.value,
            EPermission.CUSTOMER_READ.value,
            EPermission.CUSTOMER_UPDATE.value,
            EPermission.LINE_WRITE.value,
            EPermission.LINE_DELETE.value,
            EPermission.LINE_DELETE.value,
            EPermission.LINE_READ.value,
            EPermission.PROCESS_DELETE.value,
            EPermission.PROCESS_READ.value,
            EPermission.PROCESS_WRITE.value,
            EPermission.PROCESS_UPDATE.value,
            EPermission.PROJECT_DELETE.value,
            EPermission.PROJECT_READ.value,
            EPermission.PROJECT_WRITE.value,
            EPermission.PROJECT_UPDATE.value,
            EPermission.PROJECT_LINE_DELETE.value,
            EPermission.PROJECT_LINE_READ.value,
            EPermission.PROJECT_LINE_UPDATE.value,
            EPermission.PROJECT_LINE_WRITE.value,
            EPermission.JOBORDER_UPDATE.value,
            EPermission.JOBORDER_DELETE.value,
            EPermission.JOBORDER_READ.value,
            EPermission.JOBORDER_WRITE.value,
            EPermission.WORKORDER_DELETE.value,
            EPermission.WORKORDER_READ.value,
            EPermission.WORKORDER_UPDATE.value,
            EPermission.WORKORDER_WRITE.value,
            EPermission.LINE_OWNER_DELETE.value,
            EPermission.LINE_OWNER_READ.value,
            EPermission.LINE_OWNER_WRITE.value,
            EPermission.LINE_OWNER_UPDATE.value,
            EPermission.YIELD_READ.value,
            EPermission.YIELD_WRITE.value,
            EPermission.YIELD_DELETE.value,
            EPermission.YIELD_UPDATE.value,
            EPermission.DASHBOARD_DELETE.value,
            EPermission.DASHBOARD_READ.value,
            EPermission.DASHBOARD_UPDATE.value,
            EPermission.DASHBOARD_WRITE.value,
            EPermission.ACCOUNT_WRITE.value,
            EPermission.ACCOUNT_UPDATE.value,
            EPermission.ACCOUNT_READ.value,
            EPermission.ACCOUNT_DELETE.value,
        ]

        admin_permissions = [
            admin_p for admin_p in permisions if admin_p.action in admin_allowed_permissions
        ]

        if len(admin_permissions) == 0:
            raise Exception("Admin no permission added, please check!")

        for xp in admin_permissions:
            roleAdmin.permissions.append(xp)

        # * Create editor role
        roleEditor = RoleModel()
        roleEditor.role = ERole.EDITOR.value

        # *editor_allowed_permissions
        editor_allowed_permissions = [
            EPermission.CUSTOMER_WRITE.value,
            EPermission.CUSTOMER_DELETE.value,
            EPermission.CUSTOMER_READ.value,
            EPermission.CUSTOMER_UPDATE.value,
            EPermission.LINE_WRITE.value,
            EPermission.LINE_DELETE.value,
            EPermission.LINE_DELETE.value,
            EPermission.LINE_READ.value,
            EPermission.PROCESS_DELETE.value,
            EPermission.PROCESS_READ.value,
            EPermission.PROCESS_WRITE.value,
            EPermission.PROCESS_UPDATE.value,
            EPermission.PROJECT_DELETE.value,
            EPermission.PROJECT_READ.value,
            EPermission.PROJECT_WRITE.value,
            EPermission.PROJECT_UPDATE.value,
            EPermission.PROJECT_LINE_DELETE.value,
            EPermission.PROJECT_LINE_READ.value,
            EPermission.PROJECT_LINE_UPDATE.value,
            EPermission.PROJECT_LINE_WRITE.value,
            EPermission.JOBORDER_UPDATE.value,
            EPermission.JOBORDER_DELETE.value,
            EPermission.JOBORDER_READ.value,
            EPermission.JOBORDER_WRITE.value,
            EPermission.WORKORDER_DELETE.value,
            EPermission.WORKORDER_READ.value,
            EPermission.WORKORDER_UPDATE.value,
            EPermission.WORKORDER_WRITE.value,
            EPermission.YIELD_READ.value,
            EPermission.YIELD_WRITE.value,
            EPermission.YIELD_DELETE.value,
            EPermission.YIELD_UPDATE.value,
            EPermission.DASHBOARD_DELETE.value,
            EPermission.DASHBOARD_READ.value,
            EPermission.DASHBOARD_UPDATE.value,
            EPermission.DASHBOARD_WRITE.value,
            EPermission.ACCOUNT_WRITE.value,
            EPermission.ACCOUNT_UPDATE.value,
            EPermission.ACCOUNT_READ.value,
            EPermission.ACCOUNT_DELETE.value,
        ]

        editor_permissions = [
            editor_p for editor_p in permisions if editor_p.action in editor_allowed_permissions
        ]

        if len(editor_permissions) == 0:
            raise Exception("Editor no permission added, please check!")

        for ep in editor_permissions:
            roleEditor.permissions.append(ep)

        # * Create author role
        roleAuthor = RoleModel()
        roleAuthor.role = ERole.AUTHOR.value

        # *author_allowed_permissions
        author_allowed_permissions = [
            EPermission.DASHBOARD_DELETE.value,
            EPermission.DASHBOARD_READ.value,
            EPermission.DASHBOARD_UPDATE.value,
            EPermission.DASHBOARD_WRITE.value,
            EPermission.YIELD_READ.value,
            EPermission.YIELD_WRITE.value,
            EPermission.YIELD_DELETE.value,
            EPermission.YIELD_UPDATE.value,
            EPermission.ACCOUNT_WRITE.value,
            EPermission.ACCOUNT_UPDATE.value,
            EPermission.ACCOUNT_READ.value,
            EPermission.ACCOUNT_DELETE.value,
        ]

        author_permissions = [
            author_p for author_p in permisions if author_p.action in author_allowed_permissions
        ]

        if len(author_permissions) == 0:
            raise Exception("Author no permission added, please check!")

        for ap in author_permissions:
            roleAuthor.permissions.append(ap)

        # * Apply commit change
        async_session.add_all([roleSuperadmin, roleAdmin, roleEditor, roleAuthor])
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


# Attach menus for the default role into system
async def executeAddMenuToEachDefaultRole():
    print()
    print("2. Add role view table")
    print()
    print(f"-> Start adding menu to the each role: [{datetime.now()}]")
    print()

    async_session = await initalizeSession()

    try:
        async with async_session.begin():
            role_stmt = select(RoleModel).options(selectinload(RoleModel.views))
            roles_result = await async_session.execute(role_stmt)
            roles = roles_result.scalars().all()

            menu_stmt = select(ViewModel)
            menus_result = await async_session.execute(menu_stmt)
            menus = menus_result.scalars().all()

            # --- superadmin menu
            superadminMenus = menus

            # --- admin menu
            adminAndEditorMenus = [m for m in menus if m.menu not in [EMenu.VIEW_LOG_MENU.value]]

            # --- editor menu
            authorMenus = [
                m
                for m in menus
                if m.menu not in [EMenu.VIEW_LOG_MENU.value, EMenu.VIEW_MICELLANEOUS_MENU.value]
            ]

            superadmin = ERole.SUPERADMIN.value
            admin = ERole.ADMIN.value
            editor = ERole.EDITOR.value
            author = ERole.AUTHOR.value

            for role in roles:
                if role.role == superadmin:
                    role.views.extend(superadminMenus)
                elif role.role == admin or role.role == editor:
                    role.views.extend(adminAndEditorMenus)
                elif role.role == author:
                    role.views.extend(authorMenus)

            print("complete menu attachment")

    except SQLAlchemyError as e:
        print("Original error:", repr(e))

    except Exception as ge:
        print("Exception:", repr(ge))


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
        user.first_name = "super"
        user.last_name = "admin"
        user.email = ESystemCredentials.EMAIL.value
        user.password = hashMyPassword(ESystemCredentials.PASSWORD.value)
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
        print(f"Email: {ESystemCredentials.EMAIL.value}")
        print(f"Password: {ESystemCredentials.PASSWORD.value}")

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
    await cleanUpRedisCache()
    print("waiting for the removing process...")

    await sleep(1.5)
    await executeRemvingPermission()
    print("waiting for the removing roles process...")

    await sleep(1.5)
    await executeRemvingRole()
    print("waiting for the removing menus process...")

    await sleep(1.5)
    await executeRemvingMenu()
    print("waiting for the removing users process...")

    await sleep(1.5)
    await executeRemvingUsers()
    print("waiting for the adding process...")

    await sleep(1.5)
    print("waiting for adding permissions process...")

    await sleep(1.5)
    await excuteAddAllPermission()
    print("waiting for adding role process ...")

    await sleep(1.5)
    await excuteAddAllMenu()
    print("waiting for adding menu process ...")

    await sleep(1.5)
    await executeAddRole()
    print("waiting for attach menu to role process ...")

    await sleep(1.5)
    await executeAddMenuToEachDefaultRole()
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
