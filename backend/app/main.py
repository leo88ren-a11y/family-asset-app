"""
家庭资产管家 - 后端 API 服务
Family Asset Manager - Backend API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.config import settings

app = FastAPI(
    title="家庭资产管家 API",
    description="Family Asset Manager Backend API",
    version="1.0.0",
)

# CORS - 允许 H5 前端和 Android WebView 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "family-asset-manager"}
