from dataclasses import dataclass


@dataclass
class DeleteProcessCommand:
    user_id: int
    process_id: int