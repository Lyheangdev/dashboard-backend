# import time
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send

from src.infrastructure.logging.config import print_capture_log
from src.infrastructure.logging.log_context import actor_id, request_id


class LogContextMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_token = request_id.set(str(uuid4()))
        actor_token = actor_id.set(None)

        # start = time.perf_counter()

        try:
            await self.app(scope, receive, send)

        finally:
            # execution_time = (time.perf_counter() - start) * 1000
            try:
                print_capture_log(
                    name="HTTP Request",
                    type="info",
                    msg=(
                        f"method: {scope['method']} | "
                        f"path: {scope['path']} | "
                        f"user_id: {actor_id.get() or 'Unknown'} | "
                        f"request_id: {request_id.get()} | "
                        # f"total_exec: {execution_time:.2f} ms"
                    ),
                )
            finally:
                actor_id.reset(actor_token)
                request_id.reset(request_token)
