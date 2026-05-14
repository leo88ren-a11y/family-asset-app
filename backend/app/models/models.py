"""
数据模型定义
"""
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum
from datetime import datetime, timezone

from app.core.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"       # 家庭创建者
    MEMBER = "member"     # 普通成员


class AssetCategory(str, enum.Enum):
    EQUITY = "equity"           # 权益类（股票/基金/REITs）
    BOND = "bond"               # 债券类
    COMMODITY = "commodity"     # 大宗商品（黄金/原油）
    CASH = "cash"               # 现金类（银行/货币基金）
    OTHER = "other"             # 其他


class Currency(str, enum.Enum):
    CNY = "CNY"
    USD = "USD"
    HKD = "HKD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    SGD = "SGD"


# ===== 用户 & 家庭 =====

class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), default="我的家庭")
    invite_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    members: Mapped[list["User"]] = relationship(back_populates="family", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(50), default="用户")
    avatar: Mapped[str] = mapped_column(String(500), default="")
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.MEMBER)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    family: Mapped["Family"] = relationship(back_populates="members")
    assets: Mapped[list["Asset"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


# ===== 资产 =====

class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))          # 资产名称：腾讯控股、黄金ETF等
    code: Mapped[str] = mapped_column(String(30), default="")  # 代码：00700.HK / 518880.SH
    category: Mapped[AssetCategory] = mapped_column(SAEnum(AssetCategory))
    amount: Mapped[float] = mapped_column(Numeric(14, 2))   # 原始币种金额
    currency: Mapped[Currency] = mapped_column(SAEnum(Currency), default=Currency.CNY)
    amount_cny: Mapped[float] = mapped_column(Numeric(14, 2))  # 折合人民币
    cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)  # 成本（可选）
    profit: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)  # 盈亏（可选）
    profit_rate: Mapped[float] = mapped_column(Numeric(8, 4), nullable=True)  # 盈亏比例
    platform: Mapped[str] = mapped_column(String(100), default="")  # 来源平台（用户填写/OCR识别）
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    source_image: Mapped[str] = mapped_column(String(500), default="")  # 截图URL
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已确认
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner: Mapped["User"] = relationship(back_populates="assets")


# ===== 验证码 =====

class SMSCode(Base):
    __tablename__ = "sms_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
