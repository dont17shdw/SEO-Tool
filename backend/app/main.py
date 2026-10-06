from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router
from app.config.settings import get_settings
from app.db.session import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Release database connections at shutdown without connecting during startup.
    在关闭时释放数据库连接，不在启动时连接数据库。
    """
    try:
        yield
    finally:
        dispose_engine()


def create_app() -> FastAPI:
    """Assemble HTTP boundaries while leaving SEO processing in separate modules.
    组装 HTTP 边界，同时将 SEO 处理保留在独立模块中。
    """
    settings = get_settings()
    application = FastAPI(title="SEO Tool API", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
