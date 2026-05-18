"""
OCR 识别服务 - 腾讯云 OCR
"""
import asyncio
import base64
import json
import logging
import re

from app.core.config import settings

logger = logging.getLogger(__name__)
from app.models.schemas import OCRResponse, OCRResultItem, AssetCategoryEnum, CurrencyEnum


async def ocr_screenshot(image_bytes: bytes) -> OCRResponse:
    """
    对截图进行 OCR 识别，提取资产信息
    
    优先使用腾讯云 OCR，未配置时返回模拟数据（开发模式）
    """
    logger.info(f"[OCR] 开始识别，图片大小: {len(image_bytes)} bytes")
    logger.info(f"[OCR] SECRET_ID: {settings.TENCENT_OCR_SECRET_ID[:10] if settings.TENCENT_OCR_SECRET_ID else 'None'}...")
    logger.info(f"[OCR] SECRET_KEY: {settings.TENCENT_OCR_SECRET_KEY[:10] if settings.TENCENT_OCR_SECRET_KEY else 'None'}...")
    
    if settings.TENCENT_OCR_SECRET_ID and settings.TENCENT_OCR_SECRET_KEY:
        logger.info("[OCR] 走腾讯云 OCR 分支")
        return await _call_tencent_ocr(image_bytes)
    
    # 开发模式：返回模拟识别结果
    logger.info("[OCR] 走模拟数据分支")
    return _mock_ocr_result()


async def _call_tencent_ocr(image_bytes: bytes) -> OCRResponse:
    """调用腾讯云通用 OCR API"""
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.ocr.v20181119 import ocr_client, models
        
        cred = credential.Credential(
            settings.TENCENT_OCR_SECRET_ID,
            settings.TENCENT_OCR_SECRET_KEY,
        )
        httpProfile = HttpProfile(endpoint="ocr.tencentcloudapi.com")
        clientProfile = ClientProfile(httpProfile=httpProfile)
        
        client = ocr_client.OcrClient(cred, "ap-shanghai", clientProfile)
        
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        req = models.GeneralAccurateOCRRequest()
        req.from_json_string(json.dumps({"ImageBase64": image_base64}))
        
        resp = await asyncio.to_thread(client.GeneralAccurateOCR, req)
        
        resp_json = resp.to_json_string()
        logger.info(f"[OCR] 腾讯云返回原始数据: {resp_json[:500]}")
        
        items = _parse_ocr_response(resp_json)
        
        return OCRResponse(success=True, items=items, raw_text=resp.to_json_string())
    
    except Exception as e:
        logger.error(f"[OCR] 腾讯云调用失败: {type(e).__name__}: {e}", exc_info=True)
        return OCRResponse(success=False, error=str(e))


def _parse_ocr_response(ocr_json: str) -> list[OCRResultItem]:
    """
    解析腾讯云 OCR 返回的 JSON，提取资产信息
    
    富途牛牛格式（从日志分析）：
    [5] 小鹏集团-W -2,041.48 100 HK$61.200 -13
    [6] 5,335.42沪港通 -27.67% 100 HK$84.617 -2
    [7] 黄金ETF华安 +34,305.24 4,400 9.727 +21
    [8] 42,798.80 +403.89% 4,400 1.930 +0
    
    规律：
    - 奇数行：股票名 + 盈亏 + 持仓量 + 现价 + 涨跌幅
    - 偶数行：市值 + 涨跌幅% + 其他信息
    """
    data = json.loads(ocr_json)
    
    # 提取所有文本区域并按Y坐标分组
    text_areas = []
    if "TextDetections" in data:
        for td in data["TextDetections"]:
            text_areas.append({
                "text": td.get("DetectedText", "").strip(),
                "y": td.get("Polygon", [{}])[0].get("Y", 0) if td.get("Polygon") else 0,
                "x": td.get("Polygon", [{}])[0].get("X", 0) if td.get("Polygon") else 0,
            })
    
    # 按Y坐标分组成行（容差15像素）
    y_tolerance = 15
    rows = {}
    for ta in text_areas:
        y = ta["y"]
        matched_row = None
        for row_y in rows:
            if abs(row_y - y) < y_tolerance:
                matched_row = row_y
                break
        if matched_row:
            rows[matched_row].append(ta)
        else:
            rows[y] = [ta]
    
    # 合并每行文本
    lines = []
    for row_y in sorted(rows.keys()):
        row_items = sorted(rows[row_y], key=lambda t: t["x"])
        line_text = " ".join(t["text"] for t in row_items)
        lines.append(line_text)
    
    logger.info(f"[OCR] 解析文本，共 {len(lines)} 行")
    for i, line in enumerate(lines[:15]):
        logger.info(f"  [{i}] {line}")
    
    # 已知股票/ETF名称
    known_assets = {
        "小鹏集团": ("小鹏集团-W", "09868.HK"),
        "黄金ETF": ("黄金ETF华安", "518880.SH"),
        "沪深300ETF": ("沪深300ETF", "510300.SH"),
        "中证500ETF": ("中证500ETF", "510500.SH"),
        "能源化工ETF": ("能源化工ETF", "159981.SZ"),
        "恒生ETF": ("恒生ETF华夏", "159920.SZ"),
        "科创50ETF": ("科创50ETF", "588000.SH"),
        "恒生科技ETF": ("恒生科技ETF", "513180.SH"),
    }
    
    stock_keywords = ["集团", "控股", "科技", "银行", "股份", "证券", "保险", "汽车"]
    
    parsed_items = []
    
    # 双行匹配策略
    for i in range(len(lines) - 1):
        line = lines[i]
        next_line = lines[i + 1]
        
        # 查找股票名
        stock_name = None
        stock_code = None
        
        for key, (name, code) in known_assets.items():
            if key in line:
                stock_name = name
                stock_code = code
                break
        
        if not stock_name:
            for kw in stock_keywords:
                if kw in line:
                    match = re.match(r'^([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9\-\+\.]+)', line)
                    if match:
                        stock_name = match.group(1).strip()
                        break
        
        if not stock_name:
            continue
        
        # 在下一行提取市值（格式：5,335.42沪港通 或 42,798.80）
        # 修复：匹配行首金额，忽略后面的文字
        amount_match = re.match(r'^([+-]?[\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', next_line.strip())
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                if abs(amount) >= 100:
                    # 判断货币：检查当前行和下一行
                    combined_text = line + " " + next_line
                    if "HK$" in combined_text or "港币" in combined_text or "沪港通" in combined_text:
                        currency = CurrencyEnum.HKD
                    elif "$" in combined_text and "HK" not in combined_text:
                        currency = CurrencyEnum.USD
                    else:
                        currency = CurrencyEnum.CNY
                    
                    parsed_items.append(OCRResultItem(
                        name=stock_name,
                        code=stock_code,
                        category=AssetCategoryEnum.EQUITY,
                        amount=abs(amount),
                        currency=currency,
                        cost=None,
                        confidence=0.85 if stock_code else 0.70,
                    ))
                    logger.info(f"[OCR] 匹配成功: {stock_name} -> 市值 {amount} {currency.value}")
            except ValueError as e:
                logger.warning(f"[OCR] 金额解析失败: {amount_str} -> {e}")
    
    logger.info(f"[OCR] 解析结果: {len(parsed_items)} 条")
    for item in parsed_items:
        logger.info(f"  - {item.name}: {item.amount} {item.currency.value}")
    
    return parsed_items


def _mock_ocr_result() -> OCRResponse:
    """开发模式：返回模拟的 OCR 识别结果"""
    return OCRResponse(
        success=True,
        items=[
            OCRResultItem(
                name="腾讯控股",
                code="00700.HK",
                category=AssetCategoryEnum.EQUITY,
                amount=423850.0,
                currency=CurrencyEnum.HKD,
                cost=None,
                confidence=0.92,
            ),
            OCRResultItem(
                name="贵州茅台",
                code="600519.SH",
                category=AssetCategoryEnum.EQUITY,
                amount=187200.0,
                currency=CurrencyEnum.CNY,
                cost=None,
                confidence=0.89,
            ),
        ],
        raw_text="模拟识别结果（开发模式）",
    )
