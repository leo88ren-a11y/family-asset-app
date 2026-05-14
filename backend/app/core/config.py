"""
应用配置 - 从环境变量读取
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "家庭资产管家"
    DEBUG: bool = True
    
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/family_asset"
    
    # JWT 认证
    SECRET_KEY: str = "family-asset-manager-dev-secret-key-change-in-production-2024"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天
    
    # 短信验证码（腾讯云 SMS）
    TENCENT_SMS_SECRET_ID: Optional[str] = None
    TENCENT_SMS_SECRET_KEY: Optional[str] = None
    TENCENT_SMS_SDK_APP_ID: Optional[str] = None
    TENCENT_SMS_SIGN_NAME: Optional[str] = None
    TENCENT_SMS_TEMPLATE_ID: Optional[str] = None
    
    # OCR 识别（腾讯云 OCR）
    TENCENT_OCR_SECRET_ID: Optional[str] = None
    TENCENT_OCR_SECRET_KEY: Optional[str] = None
    
    # 对象存储（腾讯云 COS）
    COS_SECRET_ID: Optional[str] = None
    COS_SECRET_KEY: Optional[str] = None
    COS_BUCKET: Optional[str] = None
    COS_REGION: Optional[str] = "ap-shanghai"
    
    # 汇率接口（免费接口）
    EXCHANGE_RATE_API: str = "https://api.exchangerate-api.com/v4/latest/"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
