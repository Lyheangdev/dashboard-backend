from dataclasses import dataclass
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# -- commands
from src.application.commands.process.create_process_command import CreateProcessCommand
from src.application.commands.process.delete_process_command import DeleteProcessCommand
from src.application.commands.process.update_process_command import UpdateProcessCommand

# -- handlers
from src.application.handlers.process.create_process_handler import CreateProcessHandler
from src.application.handlers.process.delete_process_handler import DeleteProcessHandler
from src.application.handlers.process.get_process_handler import GetProcessHandler
from src.application.handlers.process.get_processes_handler import GetProcessesHandler
from src.application.handlers.process.update_process_handler import UpdateProcessHandler

# -- query
from src.application.queries.process.get_process_query import GetProcessQuery
from src.application.queries.process.get_processes_query import GetProcessesQuery

# -- interface
from src.domain.interface.business_registry import HandlerStruct

# -- repositories
from src.infrastructure.repositories.process.process_repository import ProcessRepositoy
from src.infrastructure.repositories.user.user_repository import UserRepositoy

CR = TypeVar("CR")
H = TypeVar("H")
R = TypeVar("R")


@dataclass(frozen=True)
class Registration:
    handler: type[CR]
    repository: type[R]


registration_map = {
    CreateProcessCommand: Registration(CreateProcessHandler, ProcessRepositoy),
    UpdateProcessCommand: Registration(UpdateProcessHandler, ProcessRepositoy),
    DeleteProcessCommand: Registration(DeleteProcessHandler, ProcessRepositoy),
    GetProcessQuery: Registration(GetProcessHandler, ProcessRepositoy),
    GetProcessesQuery: Registration(GetProcessesHandler, ProcessRepositoy),
}


class Dispatcher:
    def __init__(self, async_session: AsyncSession):
        self.async_session = async_session

    async def handle(self, cr: CR):
        if self.async_session is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Alchemy session is not supplied.",
            )

        registration = registration_map.get(type(cr))

        if registration is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Missing command restration: {type(cr)}, please register!",
            )

        repository = registration.repository(self.async_session)
        handler: HandlerStruct = registration.handler(self.async_session, repository)
        return await handler.handle(cr)

    def ping_test(self) -> str:
        return "It's good to see you bro!"
