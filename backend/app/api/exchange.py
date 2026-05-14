"""
汇率 API
"""
from fastapi import APIRouter, Depends
from app.services.exchange_service import get_exchange_rates

router = APIRouter()


@router.get("/rates")
async def get_rates(base: str = "CNY"):
    """获取实时汇率"""
    return await get_exchange_rates(base)
