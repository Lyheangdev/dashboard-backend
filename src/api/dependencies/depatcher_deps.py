from typing import Annotated

from fastapi import Depends

from src.api.dependencies.database_deps import AlchemySessionDeps
from src.domain.registry.bunsiness_registry import Dispatcher


# Share alchemy session dependency
async def get_dispatcher(async_session: AlchemySessionDeps):
    dispatcher = Dispatcher(async_session)
    return dispatcher


DispatcherDeps = Annotated[Dispatcher, Depends(get_dispatcher)]
