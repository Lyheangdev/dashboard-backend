from src.domain.entities.user_entity import UserEntity
from src.infrastructure.models.user.user_model import UserModel


def user_model_entity_adapter(user: UserModel):
    if user is None:
        return UserEntity(id=None, email="")

    role_obj = next(iter(user.roles or []), None)
    permissions_resouces_dict = {p.action: p.resource for p in (role_obj.permissions or [])}
    views = [v.menu for v in (role_obj.views or [])]

    return UserEntity(
        id=user.id,
        email=user.email,
        code=user.code,
        full_name=f"{user.first_name} {user.last_name}",
        bio=user.bio,
        profile_url=user.asset_identifier,
        isBanned=user.isBanned,
        status=user.status,
        role=role_obj.role,
        permissions=list(permissions_resouces_dict.keys()),
        resources=list(set(permissions_resouces_dict.values())),
        views=views,
        # extra fields
        first_name=user.first_name,
        last_name=user.last_name,
        password=user.password,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
