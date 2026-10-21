from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger
from src.lib.authority_enum import EAction, EAuditingAction
from src.models.auditing_model import AuditingModel

logger = get_logger(__file__)

# Don't have to run in try,catch mode, let outer scope handle it
async def commitOperation(
        async_session: AsyncSession,
        user: str,
        resource: str,
        action: EAction,
        role: str,
        status: EAuditingAction
):
        auditModel = AuditingModel()
        auditModel.resource = resource
        auditModel.action = action.value
        auditModel.status = status.value
        auditModel.user = user
        auditModel.role = role

        await async_session.add(auditModel)
        await async_session.commit()
        await async_session.flush()

        logger.info(f"✅ {action} - {resource} by {user}:{role} successfully.")
