"""
OCR 识别服务 - 腾讯云 OCR
"""
import base64
import json

from app.core.config import settings
from app.models.schemas import OCRResponse, OCRResultItem, AssetCategoryEnum, CurrencyEnum


async def ocr_screenshot(image_bytes: bytes) -> OCRResponse:
    """
    对截图进行 OCR 识别，提取资产信息
    
    优先使用腾讯云 OCR，未配置时返回模拟数据（开发模式）
    """
    if settings.TENCENT_OCR_SECRET_ID and settings.TENCENT_OCR_SECRET_KEY:
        return await _call_tencent_ocr(image_bytes)
    
    # 开发模式：返回模拟识别结果
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
        clientProfile = ClientProfile()
        client = ocr_client.OcrClient(cred, "ap-shanghai", clientProfile, httpProfile)
        
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        req = models.GeneralAccurateOCRRequest()
        req.from_json_string(json.dumps({"ImageBase64": image_base64}))
        
        resp = await client.GeneralAccurateOCR(req)
        
        # 解析 OCR 结果为结构化资产数据
        items = _parse_ocr_response(resp.to_json_string())
        
        return OCRResponse(success=True, items=items, raw_text=resp.to_json_string())
    
    except Exception as e:
        return OCRResponse(success=False, error=str(e))


def _parse_ocr_response(ocr_json: str) -> list[OCRResultItem]:
    """
    解析腾讯云 OCR 返回的 JSON，尝试提取资产信息
    
    券商截图通常包含表格，格式如：
      持仓名称   代码       持仓数量/金额   市值/盈亏
      腾讯控股   00700.HK   500股           ¥185,000
    """
    import re
    
    data = json.loads(ocr_json)
    items = []
    
    # 提取所有文本区域
    text_areas = []
    if "TextDetections" in data:
        for td in data["TextDetections"]:
            text_areas.append({
                "text": td.get("DetectedText", "").strip(),
                "confidence": td.get("Confidence", 0),
            })
    
    # 尝试解析表格行（简化版 - 生产环境需要更复杂的解析逻辑）
    # 这里做基本的模式匹配
    full_text = "\n".join([t["text"] for t in text_areas])
    
    # 匹配类似 "名称 代码 金额" 的行
    lines = [t["text"] for t in text_areas]
    
    # TODO: 根据实际券商截图格式优化解析逻辑
    # 当前先返回原始文本让前端展示
    
    for line in lines:
        item = OCRResultItem(
            name=line,
            confidence=0.3,
        )
        items.append(item)
    
    return items


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
            OCRResultItem(
                name="招商银行",
                code="600036.SH",
                category=AssetCategoryEnum.EQUITY,
                amount=156800.0,
                currency=CurrencyEnum.CNY,
                cost=None,
                confidence=0.91,
            ),
        ],
        raw_text="模拟识别结果（开发模式）- 配置腾讯云 OCR 后将使用真实识别",
    )
