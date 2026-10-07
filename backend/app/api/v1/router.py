from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.imports import router as imports_router
from app.api.v1.pages import router as pages_router

router = APIRouter()
router.include_router(health_router)
router.include_router(imports_router)
router.include_router(pages_router)
