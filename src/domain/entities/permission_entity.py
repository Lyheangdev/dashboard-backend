from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionEntity:
    id: int
    resource: str
    action: str
