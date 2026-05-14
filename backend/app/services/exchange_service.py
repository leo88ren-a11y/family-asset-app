"""
汇率服务 - 实时汇率查询 + 货币转换
"""
import httpx
from typing import Optional

from app.core.config import settings
from app.models.schemas import ExchangeRateResponse

# 汇率缓存（简单内存缓存，生产环境应使用 Redis）
_rate_cache: dict = {}
_cache_timestamp: float = 0
_CACHE_TTL: int = 3600  # 缓存1小时


async def get_exchange_rates(base: str = "CNY") -> ExchangeRateResponse:
    """获取实时汇率"""
    import time
    
    now = time.time()
    if base in _rate_cache and (now - _cache_timestamp) < _CACHE_TTL:
        return ExchangeRateResponse(base=base, rates=_rate_cache[base])
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{settings.EXCHANGE_RATE_API}{base}"
            resp = await client.get(url)
            data = resp.json()
            
            rates = data.get("rates", {})
            # 确保常用币种存在
            target_currencies = ["USD", "HKD", "EUR", "GBP", "JPY", "SGD"]
            filtered_rates = {k: v for k, v in rates.items() if k in target_currencies}
            
            # 如果 base 不是 CNY，需要计算对 CNY 的汇率
            if base != "CNY" and "CNY" in rates:
                cny_rate = rates["CNY"]
                for curr in target_currencies:
                    if curr in rates and curr != "CNY":
                        filtered_rates[curr] = round(rates[curr] / cny_rate, 6)
                filtered_rates["CNY"] = round(1 / cny_rate, 6)
            
            _rate_cache[base] = filtered_rates
            _cache_timestamp = now
            
            return ExchangeRateResponse(base=base, rates=filtered_rates)
    
    except Exception as e:
        print(f"汇率获取失败: {e}")
        # 返回备用固定汇率（仅供参考）
        return ExchangeRateResponse(
            base=base,
            rates={
                "USD": 7.2456,
                "HKD": 0.9285,
                "EUR": 7.8234,
                "GBP": 9.1567,
                "JPY": 0.0483,
                "SGD": 5.3821,
            },
        )


async def convert_to_cny(amount: float, from_currency: str) -> float:
    """
    将指定金额从原币种转换为人民币
    
    Args:
        amount: 原始金额
        from_currency: 原币种代码 (USD, HKD, CNY 等)
    
    Returns:
        折合人民币金额
    """
    if from_currency == "CNY":
        return round(amount, 2)
    
    rate_data = await get_exchange_rates(from_currency)
    
    # exchangerate-api.com 的 rates 是 1 单位 from_currency = ? CNY
    # 如果我们请求的是 USD 为 base，rates["CNY"] 就是 1 USD = ? CNY
    if from_currency != "CNY" and "CNY" in rate_data.rates:
        rate = rate_data.rates["CNY"]
    else:
        # 反向：1 CNY = ? from_currency，所以 amount CNY = amount / rate
        rate = rate_data.rates.get(from_currency, 1.0)
        if from_currency in ("USD", "HKD", "EUR"):
            # 这些是 1 外币 = ? CNY 的常见映射
            fallback_rates = {"USD": 7.2456, "HKD": 0.9285, "EUR": 7.8234}
            rate = fallback_rates.get(from_currency, rate)
    
    return round(amount * rate, 2)
