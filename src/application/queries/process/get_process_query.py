from dataclasses import dataclass


@dataclass
class GetProcessQuery:
    page: int
    page_size: int
