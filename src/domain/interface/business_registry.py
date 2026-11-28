from typing import Protocol, TypeVar

# -- CR mean C=Command, R=Query
CR = TypeVar("CR")


# Just define the structure=type of object of the class would be
class HandlerStruct(Protocol[CR]):
    async def handle(self, cr: CR): ...
