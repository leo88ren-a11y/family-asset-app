"""
家庭资产管家 - 后端 API 服务
Family Asset Manager - Backend API
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.api.system import router as system_router
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

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
app.include_router(system_router, prefix="/api/v1/system")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "family-asset-manager"}
