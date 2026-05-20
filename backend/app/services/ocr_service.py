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
        logger.info(f"[OCR] 腾讯云返回原始数据: {resp_json[:800]}")
        
        items = _parse_ocr_response(resp_json)
        
        return OCRResponse(success=True, items=items, raw_text=resp.to_json_string())
    
    except Exception as e:
        logger.error(f"[OCR] 腾讯云调用失败: {type(e).__name__}: {e}", exc_info=True)
        return OCRResponse(success=False, error=str(e))


def _parse_ocr_response(ocr_json: str) -> list[OCRResultItem]:
    """
    解析腾讯云 OCR 返回的 JSON，提取资产信息
    
    核心思路：不再假设固定双行/三行格式，而是基于每行文本内容语义来识别：
    - 名称行：包含已知资产名 / 以序号开头+中文基金名
    - 数值行：包含「市值」关键字 + 金额 + 代码
    - 成本行：包含「成本」「可用数」等（跳过）
    
    支持的券商格式：富途牛牛、同花顺、雪球、东方财富等
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
    
    # 合并每行文本（按X坐标排序）
    lines = []
    for row_y in sorted(rows.keys()):
        row_items = sorted(rows[row_y], key=lambda t: t["x"])
        line_text = " ".join(t["text"] for t in row_items)
        lines.append(line_text)
    
    logger.info(f"[OCR] 解析文本，共 {len(lines)} 行")
    for i, line in enumerate(lines[:25]):
        logger.info(f"  [{i}] {line}")
    
    # ===== 新策略：基于语义识别每行类型，然后组合 =====
    parsed_items = _strategy_semantic(lines)
    
    # ===== 兜底：如果语义策略结果太少，尝试单行匹配 =====
    if len(parsed_items) < 1:
        single_items = _strategy_single_line(lines)
        parsed_items.extend(single_items)
    
    logger.info(f"[OCR] 最终解析结果: {len(parsed_items)} 条")
    for item in parsed_items:
        logger.info(f"  - {item.name} ({item.code}): {item.amount} {item.currency.value}")
    
    return parsed_items


def _strategy_semantic(lines: list[str]) -> list[OCRResultItem]:
    """
    语义解析策略：基于每行文本内容判断其类型，然后正确组合
    
    富途牛牛实际格式（3行/资产）：
      第1行: "1. 十年国债ETF"           → 名称行
      第2行: "512198  市值  50,335.42  +0.5%"  → 数值行（代码+市值+涨跌）
      第3行: "成本 119.428  可用数 1100"     → 成本行（跳过）
    
    策略：
    1. 分类每行：名称行 / 数值行 / 成本行 / 其他
    2. 将每个名称行与下方最近的数值行配对
    3. 从数值行提取代码和金额
    """
    # 已知资产映射（按优先级排序，长的放前面）
    known_assets = [
        ("小鹏集团", "小鹏集团-W", "09868.HK"),
        ("黄金ETF", "黄金ETF", "518880.SH"),
        ("沪深300ETF", "沪深300ETF", "510300.SH"),
        ("能源化工ETF", "能源化工ETF", "159981.SZ"),
        ("恒生ETF华夏", "恒生ETF华夏", "515080.SH"),
        ("恒生ETF", "恒生ETF", "159920.SZ"),
        ("科创50ETF", "科创50ETF", "588000.SH"),
        ("恒生科技ETF", "恒生科技ETF", "513180.SH"),
        ("十年国债ETF", "十年国债ETF", "512198.SH"),
        ("红利ETF易方达", "红利ETF易方达", "515530.SH"),
        ("红利ETF", "红利ETF", "515180.SH"),
        ("中证500ETF嘉实", "中证500ETF嘉实", "159922.SZ"),
        ("中证500ETF", "中证500ETF", "510500.SH"),
        ("纳指ETF", "纳指ETF", "513100.SH"),
        ("标普500ETF", "标普500ETF", "513500.SH"),
        ("货币基金A", "货币基金A", ""),
        ("银行理财", "银行理财", ""),
    ]
    
    def find_asset_name(text):
        """从文本中查找已知资产名"""
        for key, std_name, code in known_assets:
            if key in text:
                return std_name, code
        return None, None
    
    def is_name_line(line):
        """判断是否为名称行：含已知资产名，或以序号开头+中文"""
        line = line.strip()
        # 含已知资产名
        name, _ = find_asset_name(line)
        if name:
            return True
        # 序号开头 + 中文基金/股票名
        if re.match(r'^\d+[．.、]\s*[\u4e00-\u9fa5]', line):
            return True
        return False
    
    def is_value_line(line):
        """判断是否为数值行：包含「市值」或金额+代码"""
        line = line.strip()
        if '市值' in line:
            return True
        # 包含5-6位代码 + 大金额
        if re.search(r'\b\d{5,6}\b.*[\d,]{3,}\.?\d*\b', line) and re.search(r'[+-]?\d', line):
            return True
        return False
    
    def is_cost_line(line):
        """判断是否为成本/详情行（应跳过）"""
        skip_keywords = ['成本', '可用数', '持仓数', '今日盈亏', '总盈亏', '盈亏比例']
        return any(kw in line for kw in skip_keywords)
    
    # ===== 第1步：分类每一行 =====
    line_types = []  # [(type, index), ...]
    for i, line in enumerate(lines):
        lt = 'other'
        if is_cost_line(line):
            lt = 'cost'
        elif is_name_line(line):
            lt = 'name'
        elif is_value_line(line):
            lt = 'value'
        line_types.append((lt, i))
        logger.info(f"[OCR-语义] 行[{i}] 类型={lt}: {line[:60]}")
    
    # ===== 第2步：配对名称行和数值行 =====
    parsed_items = []
    used = set()
    
    for ti, (lt, idx) in enumerate(line_types):
        if idx in used or lt != 'name':
            continue
        
        name_line = lines[idx]
        name_clean = re.sub(r'^\d+[．.、]\s*', '', name_line).strip()
        stock_name, stock_code = find_asset_name(name_clean)
        
        # 找下方最近的 value 行
        best_value_idx = None
        for tj in range(ti + 1, len(line_types)):
            vlt, vidx = line_types[tj]
            if vidx in used:
                continue
            if vlt == 'value':
                best_value_idx = vidx
                break
            # 跨过 cost 行继续找，但遇到下一个 name 行就停
            if vlt == 'name':
                break
        
        if best_value_idx is None:
            logger.warning(f"[OCR-语义] 名称行[{idx}] '{name_line[:30]}' 未找到配对的数值行")
            continue
        
        value_line = lines[best_value_idx].strip()
        
        # 从数值行提取代码（5-6位数字）
        code_match = re.search(r'\b(\d{5,6})\b', value_line)
        code = code_match.group(1) if code_match else (stock_code.replace('.SH','').replace('.SZ','').replace('.HK','') if stock_code else '')
        
        # 从数值行提取金额（多种格式）
        amount = None
        currency = CurrencyEnum.CNY
        
        # 格式1: "市值  XX,XXX.XX" 或 "市值 港币 XX,XXX.XX"
        am = re.search(r'市值\s*(?:港[币汇]?\s*)?([\d,]+(?:\.\d+)?)\s*(?:元)?', value_line)
        if am:
            amount = float(am.group(1).replace(',', ''))
        
        # 格式2: 行首大数字（兜底）
        if amount is None:
            am = re.search(r'^\s*([\d,]+(?:\.\d{1,2})?)\s', value_line)
            if am:
                try:
                    val = float(am.group(1).replace(',', ''))
                    if abs(val) >= 10:
                        amount = val
                except ValueError:
                    pass
        
        # 格式3: 任意位置的大金额
        if amount is None:
            amounts = re.findall(r'([\d,]+(?:\.\d{1,2})?)(?!.*%)', value_line)
            for amt_str in reversed(amounts):  # 取最后一个（通常是市值）
                try:
                    val = float(amt_str.replace(',', ''))
                    if abs(val) >= 10:
                        amount = val
                        break
                except ValueError:
                    pass
        
        if amount is None or not code:
            logger.warning(f"[OCR-语义] 数值行[{best_value_idx}] 提取失败: code={code}, amount={amount}")
            continue
        
        # 判断币种
        combined = name_line + " " + value_line
        if any(x in combined for x in ["港币", "港汇", "HKD", "HK$", "港"]):
            currency = CurrencyEnum.HKD
        elif "$" in combined and "HK" not in combined:
            currency = CurrencyEnum.USD
        
        final_name = stock_name or name_clean
        parsed_items.append(OCRResultItem(
            name=final_name,
            code=code,
            category=AssetCategoryEnum.EQUITY,
            amount=abs(amount),
            currency=currency,
            cost=None,
            confidence=0.85 if stock_name else 0.70,
        ))
        used.add(idx)
        used.add(best_value_idx)
        logger.info(f"[OCR-语义] ✅ {final_name} | 代码:{code} | 金额:{amount:.2f} | {currency.value}")
    
    return parsed_items


def _strategy_single_line(lines: list[str]) -> list[OCRResultItem]:
    """
    单行匹配策略：适用于单行内包含名称和市值的格式
    如："中证500ETF嘉实 159922 基金 总亏盈 +45.12% +21794.87"
    """
    parsed_items = []
    
    # 匹配含金额的行（金额 > 100）
    amount_pattern = re.compile(r'([+-]?[\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)(?!.*%)')
    
    for i, line in enumerate(lines):
        # 跳过已被双行策略使用的行附近
        # 查找所有金额候选
        amounts = amount_pattern.findall(line)
        
        for amt_str in amounts:
            try:
                val = float(amt_str.replace(',', ''))
                if abs(val) >= 100:
                    # 提取行首的名称
                    name_match = re.match(r'^([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9\-\+\.W]+)', line)
                    if name_match and len(name_match.group(1)) >= 2:
                        name = name_match.group(1).strip()
                        
                        # 提取代码（6位数字.交易所 格式）
                        code_match = re.search(r'(\d{6}\.(?:SH|SZ|HK))', line)
                        code = code_match.group(1) if code_match else ""
                        
                        parsed_items.append(OCRResultItem(
                            name=name,
                            code=code,
                            category=AssetCategoryEnum.EQUITY,
                            amount=abs(val),
                            currency=CurrencyEnum.CNY,
                            cost=None,
                            confidence=0.65,
                        ))
                        logger.info(f"[OCR-单行] 匹配: {name} -> {val} (from line: {line[:40]})")
                        break  # 每行只取一个最大金额
            except ValueError:
                pass
    
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
