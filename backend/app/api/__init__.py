"""
API 路由总入口
"""
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.family import router as family_router
from app.api.assets import router as assets_router
from app.api.exchange import router as exchange_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(family_router, prefix="/family", tags=["家庭"])
router.include_router(assets_router, prefix="/assets", tags=["资产"])
router.include_router(exchange_router, prefix="/exchange", tags=["汇率"])
