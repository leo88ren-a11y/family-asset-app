"""
资产 API - CRUD + 汇总
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Asset, User, AssetCategory
from app.models.schemas import (
    AssetCreate, AssetUpdate, AssetResponse,
    AssetSummaryResponse, OCRResultItem, OCRResponse, AssetConfirmUpdate,
)
from app.services.ocr_service import ocr_screenshot
from app.services.exchange_service import convert_to_cny

router = APIRouter()


# ===== 资产汇总（首页） =====

@router.get("/summary", response_model=AssetSummaryResponse)
async def get_asset_summary(
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取家庭资产汇总（首页饼图数据）"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    if not user.family_id:
        return AssetSummaryResponse(total_cny=0, total_count=0, categories=[])
    
    # 查询家庭所有资产
    result = await db.execute(
        select(Asset).where(Asset.owner_id.in_(
            select(User.id).where(User.family_id == user.family_id)
        ))
    )
    assets = result.scalars().all()
    
    total_cny = sum(float(a.amount_cny or 0) for a in assets)
    
    # 按分类聚合
    category_map = {
        AssetCategory.EQUITY: {"name": "权益类", "amount": 0, "color": "#3B82F6"},
        AssetCategory.BOND: {"name": "债券类", "amount": 0, "color": "#8B5CF6"},
        AssetCategory.COMMODITY: {"name": "大宗商品", "amount": 0, "color": "#F59E0B"},
        AssetCategory.CASH: {"name": "现金类", "amount": 0, "color": "#10B981"},
        AssetCategory.OTHER: {"name": "其他", "amount": 0, "color": "#94A3B8"},
    }
    
    for a in assets:
        cat = a.category
        if cat in category_map:
            category_map[cat]["amount"] += float(a.amount_cny or 0)
    
    categories = []
    for cat_key, info in category_map.items():
        amount = round(info["amount"], 2)
        pct = round(amount / total_cny * 100, 1) if total_cny > 0 else 0
        categories.append({
            "category": cat_key.value,
            "name": info["name"],
            "amount": amount,
            "percentage": pct,
            "color": info["color"],
        })
    
    # 按金额降序
    categories.sort(key=lambda x: x["amount"], reverse=True)
    
    return AssetSummaryResponse(
        total_cny=round(total_cny, 2),
        total_count=len(assets),
        categories=categories,
    )


# ===== 资产列表（详情页） =====

@router.get("/list")
async def get_asset_list(
    sort_by: str = "pct",  # pct / amount / name
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取资产详情列表（配置详情页）"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    
    if not user.family_id:
        return {"items": [], "total": 0}
    
    result = await db.execute(
        select(Asset).join(Asset.owner).where(
            Asset.owner_id.in_(select(User.id).where(User.family_id == user.family_id))
        )
    )
    assets = result.scalars().all()
    
    items = []
    for a in assets:
        owner_result = await db.execute(select(User).where(User.id == a.owner_id))
        owner = owner_result.scalar_one()
        
        amount_val = float(a.amount or 0)
        cny_val = float(a.amount_cny or 0)
        cost_val = float(a.cost) if a.cost else None
        
        profit_val = None
        profit_rate_val = None
        if cost_val and cost_val > 0:
            profit_val = cny_val - cost_val
            profit_rate_val = round(profit_val / cost_val * 100, 2)
        
        items.append({
            "id": a.id,
            "name": a.name,
            "code": a.code or "",
            "category": a.category.value,
            "amount": cny_val,
            "original_amount": amount_val,
            "currency": a.currency.value,
            "cost": cost_val,
            "profit": round(profit_val, 2) if profit_val else None,
            "profit_rate": profit_rate_val,
            "platform": a.platform or "",
            "owner_id": a.owner_id,
            "owner_nickname": owner.nickname,
            "is_confirmed": a.is_confirmed,
        })
    
    # 排序
    total_cny = sum(i["amount"] for i in items) if items else 0
    
    if sort_by == "pct":
        items.sort(key=lambda x: (x["amount"] / total_cny * 100) if total_cny > 0 else 0, reverse=True)
    elif sort_by == "amount":
        items.sort(key=lambda x: x["amount"], reverse=True)
    elif sort_by == "name":
        items.sort(key=lambda x: x["name"])
    
    # 计算占比
    for item in items:
        item["percentage"] = round(item["amount"] / total_cny * 100, 1) if total_cny > 0 else 0
    
    return {"items": items, "total": len(items), "total_cny": round(total_cny, 2)}


# ===== 手动录入资产 =====

@router.post("", response_model=AssetResponse)
async def create_asset(
    req: AssetCreate,
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动创建资产"""
    user_id = int(token_data["sub"])
    
    # 折合人民币
    amount_cny = await convert_to_cny(req.amount, req.currency.value)
    
    asset = Asset(
        name=req.name,
        code=req.code,
        category=req.category,
        amount=req.amount,
        currency=req.currency,
        amount_cny=amount_cny,
        cost=req.cost,
        platform=req.platform,
        owner_id=user_id,
        is_confirmed=True,  # 手动录入默认已确认
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    # 补充 owner_nickname
    owner_result = await db.execute(select(User).where(User.id == user_id))
    owner = owner_result.scalar_one()
    
    response = AssetResponse.model_validate(asset)
    response.owner_nickname = owner.nickname
    return response


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    req: AssetUpdate,
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新资产"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.owner_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作此资产")
    
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    # 如果金额或币种变了，重新计算 CNY
    if "amount" in update_data or "currency" in update_data:
        asset.amount_cny = await convert_to_cny(asset.amount, asset.currency.value)
    
    await db.commit()
    await db.refresh(asset)
    
    owner_result = await db.execute(select(User).where(User.id == user_id))
    owner = owner_result.scalar_one()
    
    response = AssetResponse.model_validate(asset)
    response.owner_nickname = owner.nickname
    return response


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: int,
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除资产"""
    user_id = int(token_data["sub"])
    
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.owner_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作此资产")
    
    await db.delete(asset)
    await db.commit()
    
    return {"message": "删除成功"}


# ===== 截图识别流程 =====

@router.post("/ocr/upload")
async def upload_for_ocr(
    file: UploadFile = File(...),
    token_data: dict = Depends(get_current_user),
):
    """上传截图进行 AI/OCR 识别"""
    # 验证文件类型
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail="图片大小不能超过10MB")
    
    # 调用 OCR 服务识别
    ocr_result = await ocr_screenshot(contents)
    
    return ocr_result


@router.post("/ocr/confirm")
async def confirm_ocr_result(
    req: AssetConfirmUpdate,
    token_data: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户确认/编辑 OCR 识别结果后保存为资产"""
    user_id = int(token_data["sub"])
    
    amount_cny = await convert_to_cny(req.amount, req.currency.value)
    
    asset = Asset(
        name=req.name,
        code=req.code,
        category=req.category,
        amount=req.amount,
        currency=req.currency,
        amount_cny=amount_cny,
        cost=req.cost,
        platform=req.platform,
        owner_id=user_id,
        is_confirmed=True,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    owner_result = await db.execute(select(User).where(User.id == user_id))
    owner = owner_result.scalar_one()
    
    response = AssetResponse.model_validate(asset)
    response.owner_nickname = owner.nickname
    return response
