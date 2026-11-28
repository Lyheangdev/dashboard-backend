from dataclasses import dataclass, field

from src.domain.entities.permission_entity import PermissionEntity


@dataclass
class RoleEntity:
    id: int
    role: str
    permissions: list[PermissionEntity] = field(default_factory=list)
