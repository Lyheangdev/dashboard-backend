from dataclasses import dataclass


@dataclass
class CreateProcessCommand:
    user_id: int
    process: str