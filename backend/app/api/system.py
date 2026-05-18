from fastapi import APIRouter, Query
from pathlib import Path

router = APIRouter()

LOG_FILE = Path("/home/ubuntu/family-asset-app/backend/backend.log")

@router.get("/logs")
async def get_logs(lines: int = Query(50, ge=1, le=1000)):
    """获取后端最近 N 行日志"""
    if not LOG_FILE.exists():
        return {"error": "Log file not found", "path": str(LOG_FILE)}
    
    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        content = f.readlines()
    
    last_lines = content[-lines:]
    return {
        "total_lines": len(content),
        "requested_lines": lines,
        "content": "".join(last_lines)
    }
