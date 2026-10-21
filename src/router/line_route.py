from fastapi import APIRouter

from src.lib.api_enum import ApiTagEnum

# from ..config.redis import redisClientDepend
# import json

router = APIRouter(
    prefix="/lines",
    tags=[ApiTagEnum.PRODUCTION_LINE],
    responses={404: {"Description": "Resource not found."}},
)

# # Create line
# @router.post("/")
# async def create_line(name: Annotated[str, Query()], redis_client: redisClientDepend):
#     await redis_client.set(f"aec_{name}",name)
#     await redis_client.publish("LINE_POST",json.dumps({"data":name}))
#     return {"data": "okay"}

# # Get a line
# @router.get("/{name}")
# async def get_line(name: str, redis_client: redisClientDepend):
#     data = await redis_client.get(f"aec_{name}")
#     return {"data": data}

# # Get all lines
# @router.get('/')
# async def get_lines():
#     pass

# # Update line
# @router.put('/{line_id}')
# async def update_line(line_id: int):
#     pass

# # Delete a line
# @router.delete('/{line_id}')
# async def delete_line(line_id: int):
#     pass

# # Delete all lines
# @router.delete('/')
# async def delete_lines():
#     pass
