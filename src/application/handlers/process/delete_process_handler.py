from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.process.delete_process_command import DeleteProcessCommand
from src.infrastructure.repositories.process.process_repository import ProcessRepositoy


class DeleteProcessHandler:
    def __init__(self, async_session: AsyncSession, repository: ProcessRepositoy):
        self.async_session = async_session
        self.repository = repository

    async def handle(self, command: DeleteProcessCommand): ...
