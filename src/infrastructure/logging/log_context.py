from contextvars import ContextVar

actor_id: ContextVar[int | None] = ContextVar("actor_id", default=None)
request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def setActorContext(*, user_id: int | None):
    return actor_id.set(user_id)
