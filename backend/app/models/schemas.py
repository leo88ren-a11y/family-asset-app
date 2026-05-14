"""
Pydantic 请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ===== 枚举 =====

class UserRoleEnum(str, Enum):
    OWNER = "owner"
    MEMBER = "member"


class AssetCategoryEnum(str, Enum):
    EQUITY = "equity"
    BOND = "bond"
    COMMODITY = "commodity"
    CASH = "cash"
    OTHER = "other"


class CurrencyEnum(str, Enum):
    CNY = "CNY"
    USD = "USD"
    HKD = "HKD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    SGD = "SGD"


# ===== 认证 =====

class SMSRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class CreateFamilyRequest(BaseModel):
    name: str = Field(default="我的家庭", max_length=100)


class JoinFamilyRequest(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=20)


class UpdateNicknameRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)


# ===== 用户响应 =====

class UserResponse(BaseModel):
    id: int
    phone: str
    nickname: str
    avatar: str
    role: UserRoleEnum
    family_id: Optional[int] = None

    class Config:
        from_attributes = True


class FamilyMemberResponse(UserResponse):
    pass


class FamilyDetailResponse(BaseModel):
    id: int
    name: str
    invite_code: str
    members: list[FamilyMemberResponse]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== 资产 =====

class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = ""
    category: AssetCategoryEnum
    amount: float = Field(..., gt=0)
    currency: CurrencyEnum = CurrencyEnum.CNY
    cost: Optional[float] = None
    profit: Optional[float] = None
    platform: str = ""
    source_image: str = ""


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[AssetCategoryEnum] = None
    amount: Optional[float] = None
    currency: Optional[CurrencyEnum] = None
    cost: Optional[float] = None
    profit: Optional[float] = None
    platform: Optional[str] = None


class AssetConfirmUpdate(BaseModel):
    """用户确认/编辑 AI 识别结果后提交"""
    name: str
    code: str = ""
    category: AssetCategoryEnum
    amount: float
    currency: CurrencyEnum = CurrencyEnum.CNY
    cost: Optional[float] = None
    platform: str = ""


class AssetResponse(BaseModel):
    id: int
    name: str
    code: str
    category: AssetCategoryEnum
    amount: float
    currency: CurrencyEnum
    amount_cny: float
    cost: Optional[float] = None
    profit: Optional[float] = None
    profit_rate: Optional[float] = None
    platform: str
    owner_id: int
    owner_nickname: str
    is_confirmed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AssetSummaryResponse(BaseModel):
    """资产汇总（用于首页饼图）"""
    total_cny: float
    total_count: int
    categories: list[dict]


class OCRResultItem(BaseModel):
    """OCR 识别出的单条资产"""
    name: str = ""
    code: str = ""
    category: Optional[AssetCategoryEnum] = None
    amount: Optional[float] = None
    currency: Optional[CurrencyEnum] = None
    cost: Optional[float] = None
    confidence: float = 0.0  # 置信度 0-1


class OCRResponse(BaseModel):
    """OCR 识别结果"""
    success: bool
    items: list[OCRResultItem] = []
    raw_text: str = ""  # 原始识别文本（供用户参考）
    error: str = ""


# ===== 汇率 =====

class ExchangeRateResponse(BaseModel):
    base: str
    rates: dict[str, float]
