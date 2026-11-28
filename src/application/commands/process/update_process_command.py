from dataclasses import dataclass


@dataclass
class UpdateProcessCommand:
    user_id: int
    process_id: int
    process: str