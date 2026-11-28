from sqlalchemy.ext.asyncio import AsyncSession


class ProcessRepositoy:
    def __init__(self, asyn_session: AsyncSession):
        self.session = asyn_session
