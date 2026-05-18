"""
认证 API - 登录/注册/验证码
"""
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer

from app.core.database import get_db
from app.core.auth import create_access_token, decode_access_token
from app.models.models import User, Family, SMSCode, UserRole
from app.models.schemas import (
    SMSRequest, LoginRequest, TokenResponse, UserResponse,
    CreateFamilyRequest, JoinFamilyRequest, UpdateNicknameRequest,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def generate_code() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(6)])


def generate_invite_code() -> str:
    import string
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """从 JWT 提取当前用户"""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return payload


@router.post("/sms/send")
async def send_sms(req: SMSRequest, db: AsyncSession = Depends(get_db)):
    """发送验证码（开发阶段直接返回，生产环境对接腾讯云SMS）"""
    code = generate_code()
    
    result = await db.execute(select(SMSCode).where(SMSCode.phone == req.phone))
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.code = code
        existing.used = False
    else:
        sms_record = SMSCode(phone=req.phone, code=code)
        db.add(sms_record)
    
    await db.commit()
    
    print(f"📱 [开发模式] 验证码: {code} → 手机号: {req.phone}")
    
    return {"success": True, "message": "验证码已发送", "dev_code": code}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """验证码登录/注册（开发模式：接受任意验证码）"""
    # 开发阶段：直接接受123456
    if req.code != "123456":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误")
    
    # 标记该手机号的验证码为已用（如果存在）
    result = await db.execute(
        select(SMSCode).where(SMSCode.phone == req.phone, SMSCode.used == False)
    )
    sms = result.scalar_one_or_none()
    if sms:
        sms.used = True
        await db.commit()
    
    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(phone=req.phone, nickname=f"用户{req.phone[-4:]}")
        db.add(user)
        await db.flush()
        await db.refresh(user)
    
    token_data = {"sub": str(user.id), "phone": user.phone}
    access_token = create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/family/create", response_model=dict)
async def create_family(
    req: CreateFamilyRequest,
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建家庭（新用户首次使用时调用）"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    if user.family_id:
        raise HTTPException(status_code=400, detail="您已加入家庭，无需重复创���")
    
    family = Family(name=req.name, invite_code=generate_invite_code())
    db.add(family)
    await db.flush()
    
    user.family_id = family.id
    user.role = UserRole.OWNER
    await db.commit()
    
    return {
        "id": family.id,
        "name": family.name,
        "invite_code": family.invite_code,
        "message": "家庭创建成功",
    }


@router.post("/family/join", response_model=dict)
async def join_family(
    req: JoinFamilyRequest,
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通过邀请码加入家庭"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    if user.family_id:
        raise HTTPException(status_code=400, detail="您已加入家庭")
    
    result = await db.execute(select(Family).where(Family.invite_code == req.invite_code))
    family = result.scalar_one_or_none()
    
    if not family:
        raise HTTPException(status_code=404, detail="邀请码无效")
    
    user.family_id = family.id
    user.role = UserRole.MEMBER
    await db.commit()
    
    return {"message": f"成功加入「{family.name}」"}


@router.get("/me", response_model=UserResponse)
async def get_me(token_data: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前用户信息"""
    user_id = int(token_data["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    return UserResponse.model_validate(user)


@router.put("/me/nickname")
async def update_nickname(
    req: UpdateNicknameRequest,
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改昵称"""
    user_id = int(token_data["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.nickname = req.nickname
    await db.commit()
    return {"message": "昵称更新成功"}