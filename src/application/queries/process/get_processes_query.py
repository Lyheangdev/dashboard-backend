from dataclasses import dataclass


@dataclass
class GetProcessesQuery:
    user_id: int
    process_id: int