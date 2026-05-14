"""
家庭 API - 成员管理、家庭信息
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Family
from app.models.schemas import UserResponse, FamilyDetailResponse

router = APIRouter()


@router.get("/detail", response_model=FamilyDetailResponse)
async def get_family_detail(
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取家庭详情（成员列表等）"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    if not user.family_id:
        raise HTTPException(status_code=404, detail="您尚未加入任何家庭")
    
    result = await db.execute(select(Family).where(Family.id == user.family_id))
    family = result.scalar_one()
    
    return FamilyDetailResponse.model_validate(family)


@router.get("/members", response_model=list[UserResponse])
async def get_family_members(
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取家庭成员列表"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    if not user.family_id:
        raise HTTPException(status_code=404, detail="您尚未加入任何家庭")
    
    result = await db.execute(
        select(User).where(User.family_id == user.family_id).order_by(User.created_at)
    )
    members = result.scalars().all()
    
    return [UserResponse.model_validate(m) for m in members]
