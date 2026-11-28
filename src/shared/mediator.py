from typing import Any, Awaitable, Protocol, TypeVar

Message = TypeVar("Message")


class Handler(Protocol[Message]):
    async def handle(self, message: Message) -> Any:
        pass


class Mediator:
    def __init__(self) -> None:
        self.handlers: dict[type, Handler[Any]] = {}

    def register(
        self,
        message_type: type[Message],
        handler: Handler[Message],
    ) -> None:
        self.handlers[message_type] = handler

    async def send(self, message: Any) -> Any:
        handler = self.handlers.get(type(message))

        if handler is None:
            raise ValueError(f"No handler registered for {type(message).__name__}")

        return await handler.handle(message)
