from fastapi import APIRouter

# Merge endpoints to the root prefix
from src.api.v1.endpoints import auth_endpoint, cache_endpoint

router = APIRouter(prefix="/api/v1")
router.include_router(router=auth_endpoint.router)
router.include_router(router=cache_endpoint.router)
