import asyncio
import time

from fastapi import Request
from redis.asyncio import Redis


async def sseGenerator(*, topic: str, request: Request, redis_client: Redis):
    pubsub = redis_client.pubsub()

    client = request.client
    host = client.host if client else "unknown"
    port = client.port if client else "unknown"
    agent = request.headers.get("user-agent", "unknown")

    try:
        # subscribe to a specific channel
        await pubsub.subscribe(topic)

        print(f"[SSE connected: {agent} - {host}:{port}]")
        last_ping = time.monotonic()

        while True:
            # Check request connection
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message is not None:
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")

                # Ensure valid SSE formatting
                yield f"data: {data}\n\n"

                last_ping = time.monotonic()
                
            elif time.monotonic() - last_ping >= 10:
                yield ": ping\n\n"
                last_ping = time.monotonic()

    except asyncio.CancelledError:
        raise

    finally:
        print(f"[SSE disconnected: {agent} - {host}:{port}]")
        try:
            await pubsub.unsubscribe(topic)
        finally:
            await pubsub.aclose()
