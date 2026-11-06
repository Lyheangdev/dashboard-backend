from contextlib import asynccontextmanager
from datetime import datetime as dt
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteException

#! SYSTEM MAIN CONFIGURATION
from src.config.database import PostGresConnector
from src.config.logging import get_logger, setup_logging, shut_down_logging
from src.config.redis import RedisClient, RedisConnector
from src.dependencies import GlobalRateLimiter
from src.generators.sse_event_generator import seeEventGenerator

#! SYSTEMR RESPONSE FORMAT
from src.lib.api_enum import ApiTagEnum
from src.lib.api_response import ApiError, ApiSingletonResponse

#! DONT' REMOVE THIS IMPORT EVEN THOUGH IT DOESN'T USE
from src.models.asset_model import AssetModel
from src.models.auditing_model import AuditingModel
from src.models.line_model import LineModel
from src.models.permission_model import PermissionModel
from src.models.role_model import RoleModel
from src.models.role_permission_model import role_permission_model
from src.models.user_model import UserModel
from src.models.user_role_model import user_role_model
from src.models.user_view_model import user_view_model
from src.models.view_model import ViewModel

#! SYSTEM ROUTE REGISTRATION
from src.router.asset_route import router as assetsRouter
from src.router.auth_route import router as authRouter
from src.router.line_route import router as lineRouter
from src.router.permission_route import router as permissionRouter
from src.router.role_route import router as roleRouter
from src.router.system_access_route import router as systemAccessRouter
from src.router.third_party_route import router as thirdPartyRouter
from src.router.user_route import router as userRouter
from src.router.view_route import router as viewRouter

SERVE_PATH = Path(__file__).resolve().parent.parent / "assets"
SERVE_PATH.mkdir(parents=True, exist_ok=True)

logger = get_logger("Main")


@asynccontextmanager
async def preConfiguration(app: FastAPI):
    # *-- initialize log
    setup_logging(mode="development")

    # *-- initialize database
    alchemy_instance = PostGresConnector()
    await alchemy_instance.initilizeConnection()
    app.state.alchemy_instance = alchemy_instance

    # *-- initialize redis
    redis_instance = RedisConnector()
    app.state.redis_instance = redis_instance
    await redis_instance.initRedisConnection()

    logger.info(msg="🏁 Production Dashboard System Up and Running.")

    yield
    #! REALEASE RESOURCE & CLEAN UP
    await alchemy_instance.releaseAlchemyInstance()
    await redis_instance.releaseRedisClient()

    logger.info("🔚 Application Stop.")
    shut_down_logging()


# *-- OPEN API DESCRIPTION
description = """
Smart dashboard API integration. 🚀

### Contact Information

-----

**Site:**   &nbsp;&nbsp;SVI (AEC) Company Limited

**Department:**   &nbsp;&nbsp;Management Information System (MIS)

**Person In Charge:**   &nbsp;&nbsp;lyheang.pic@svi-aec.com

**Position:**   &nbsp;&nbsp; IT Web Developer

----
"""

app = FastAPI(
    lifespan=preConfiguration,
    dependencies=[GlobalRateLimiter],
    title="SVI(AEC) 面板API接口集成文档",
    version="1.0.0",
    description=description,
    contact={
        "Site": "SVI (AEC) Company Limited",
        "Department": "Management Information System (MIS)",
        "PIC": "lyheang.pic@svi-aec.com",
        "Pos": "IT Web Developer",
    },
)

app.mount(path="/assets", app=StaticFiles(directory=SERVE_PATH), name="assets")


@app.exception_handler(SQLAlchemyError)
async def handlePostGresSQLServerException(__: Request, exc: SQLAlchemyError):
    logger.exception("🔥 Database error, please check!")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiSingletonResponse(
            status="failed",
            message="Opps, something went wrong with database !",
            error=ApiError(
                code=exc.code,
                message="The operation with database causes an error, global exception_handler !",
                details=exc._message(),
            ),
            data=None,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def handleRequestValidationException(__: Request, exc: RequestValidationError):
    logger.error("💥 Validation error!")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ApiSingletonResponse(
            status="failed",
            message="Validation error!",
            error=ApiError(
                code="ERROR VALIDATION",
                message="Your data is validated failed!",
                details=exc.errors(),
            ),
            data=None,
        ).model_dump(),
    )


@app.exception_handler(StarletteException)
async def handleHttpException(__: Request, exc: StarletteException):
    if_server_error = f"{exc.status_code}".startswith("5")

    if if_server_error:
        logger.exception(exc.detail)
    else:
        logger.error(exc.detail)

    if "duplicate" in f"{exc.detail}":
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiSingletonResponse(
                status="failed",
                message="Something went wrong!",
                error=ApiError(code=str(exc.status_code), message=exc.detail, details=None),
                data=None,
            ).model_dump(),
        )

    else:
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiSingletonResponse(
                status="failed",
                message="Http error exception!",
                error=ApiError(code=str(exc.status_code), message=str(exc.detail), details=None),
                data=None,
            ).model_dump(),
        )


#! CORS CONFIGURATION
allowed_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#! ATTACHE ROUTE TO APP
root_path_prefix_v1 = "/api/v1"
app.include_router(router=userRouter, prefix=root_path_prefix_v1)
app.include_router(router=authRouter, prefix=root_path_prefix_v1)
app.include_router(router=permissionRouter, prefix=root_path_prefix_v1)
app.include_router(router=roleRouter, prefix=root_path_prefix_v1)
app.include_router(router=lineRouter, prefix=root_path_prefix_v1)
app.include_router(router=systemAccessRouter, prefix=root_path_prefix_v1)
app.include_router(router=assetsRouter, prefix=root_path_prefix_v1)
app.include_router(router=viewRouter, prefix=root_path_prefix_v1)
app.include_router(router=thirdPartyRouter, prefix=root_path_prefix_v1)


#! SEVER SEND EVENT (SSE) REGISTRATION
@app.get(
    f"{root_path_prefix_v1}/sse/stream",
    tags=[ApiTagEnum.SSE],
    name="Realtime endpoint",
)
async def streamSSE(request: Request, redis_client: RedisClient):

    print("-------------   | SSE CONNECTION STUB | ----------------")
    print()
    print(f"| Established at: {dt.now()}")
    print(f"| Connection Stub : {request.url}")
    print()
    print("--------------------------------------------------------")

    return StreamingResponse(
        seeEventGenerator(topic="LINE_POST", request=request, redis_client=redis_client),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
