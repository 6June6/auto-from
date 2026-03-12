"""
通告管理 API 模块
提供通告的创建和查询接口，以 APIRouter 形式挂载到主服务。

可独立运行：python tools/notice_api.py（端口 8901）
也可被 xhs_api 挂载到 /notice 路径下共用 8900 端口。
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from database.models import init_database
from database.db_manager import DatabaseManager
from tools.link_utils import is_supported_platform, extract_urls

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("notice_api")

API_KEY = getattr(config, "NOTICE_API_KEY", "notice-api-key-2025-change-in-production")
API_PORT = getattr(config, "NOTICE_API_PORT", 8901)

# ──────────────────── Pydantic Models ────────────────────

class NoticeCreateRequest(BaseModel):
    platform: str = Field(..., description="平台名称，需为 /platforms 返回的有效平台名")
    category: List[str] = Field(default_factory=list, description="类目列表，可从 /categories 获取")
    content: str = Field(..., min_length=1, description="通告完整内容")
    status: str = Field(default="active", pattern="^(active|expired|closed)$")

class NoticeResponse(BaseModel):
    id: str
    platform: str
    category: List[str]
    content: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class DuplicateWarning(BaseModel):
    count: int
    previews: List[str]

class NoticeCreateResponse(BaseModel):
    success: bool
    notice: Optional[NoticeResponse] = None
    duplicate_warning: Optional[DuplicateWarning] = None
    message: str

class PlatformItem(BaseModel):
    id: str
    name: str

class CategoryItem(BaseModel):
    id: str
    name: str

# ──────────────────── Auth ────────────────────

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

# ──────────────────── Router ────────────────────

def _init_db():
    """确保数据库已初始化（幂等）"""
    try:
        from mongoengine.connection import get_connection
        get_connection()
    except Exception:
        logger.info("正在初始化数据库连接...")
        init_database()

_init_db()
db = DatabaseManager()

def _notice_to_response(n) -> NoticeResponse:
    return NoticeResponse(
        id=str(n.id),
        platform=n.platform,
        category=n.category or [],
        content=n.content,
        status=n.status,
        created_at=n.created_at.isoformat() if n.created_at else None,
        updated_at=n.updated_at.isoformat() if n.updated_at else None,
    )

router = APIRouter(tags=["通告管理"])

@router.get("/platforms", response_model=List[PlatformItem], summary="获取可用平台列表")
def list_platforms(api_key: str = Header(..., alias="X-API-Key")):
    verify_api_key(api_key)
    platforms = db.get_all_platforms()
    return [PlatformItem(id=str(p.id), name=p.name) for p in platforms]


@router.get("/categories", response_model=List[CategoryItem], summary="获取可用类目列表")
def list_categories(api_key: str = Header(..., alias="X-API-Key")):
    verify_api_key(api_key)
    categories = db.get_all_notice_categories()
    return [CategoryItem(id=str(c.id), name=c.name) for c in categories]


@router.post("/notices", response_model=NoticeCreateResponse, summary="创建通告")
def create_notice(req: NoticeCreateRequest, api_key: str = Header(..., alias="X-API-Key")):
    verify_api_key(api_key)

    valid_platforms = [p.name for p in db.get_all_platforms()]
    if req.platform not in valid_platforms:
        raise HTTPException(status_code=422, detail=f"无效平台 '{req.platform}'，可选: {valid_platforms}")

    urls = extract_urls(req.content)
    if not urls:
        raise HTTPException(status_code=422, detail="通告内容中未检测到任何链接，请添加链接后再发布")
    unsupported = [u for u in urls if not is_supported_platform(u)]
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail=f"通告内容中包含 {len(unsupported)} 个不支持的链接: {unsupported[:5]}。"
                   f"支持的平台: 腾讯文档、腾讯问卷、石墨文档、问卷星、金数据、飞书、"
                   f"金山文档/WPS、问卷网、报名工具、番茄表单、见数、麦客表单"
        )

    duplicate_warning = None
    duplicates = db.check_notice_duplicate(req.platform, req.content)
    if duplicates:
        previews = []
        for d in duplicates[:3]:
            preview = (d.content or "")[:80].replace("\n", " ")
            previews.append(f"[{d.platform}] {preview}...")
        duplicate_warning = DuplicateWarning(count=len(duplicates), previews=previews)

    try:
        notice = db.create_notice(
            platform=req.platform,
            category=req.category,
            content=req.content,
            status=req.status,
            publish_date=datetime.now(),
        )
        msg = "通告创建成功"
        if duplicate_warning:
            msg += f"（注意：检测到 {duplicate_warning.count} 条含相同链接的通告）"
        return NoticeCreateResponse(
            success=True,
            notice=_notice_to_response(notice),
            duplicate_warning=duplicate_warning,
            message=msg,
        )
    except Exception as e:
        logger.error(f"创建通告失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("/notices", response_model=List[NoticeResponse], summary="查询通告列表")
def list_notices(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    platform: Optional[str] = Query(None, description="按平台筛选"),
    status: Optional[str] = Query(None, description="按状态筛选: active / expired / closed"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    api_key: str = Header(..., alias="X-API-Key"),
):
    verify_api_key(api_key)
    notices = db.get_all_notices(
        keyword=keyword,
        platform=platform,
        status=status,
        limit=limit,
    )
    return [_notice_to_response(n) for n in notices]


@router.get("/notices/{notice_id}", response_model=NoticeResponse, summary="查询单条通告")
def get_notice(notice_id: str, api_key: str = Header(..., alias="X-API-Key")):
    verify_api_key(api_key)
    notice = db.get_notice_by_id(notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="通告不存在")
    return _notice_to_response(notice)


# ──────────────────── Standalone Entry ────────────────────

def create_standalone_app() -> FastAPI:
    """独立运行时创建完整 FastAPI 应用"""
    standalone = FastAPI(title="通告管理 API", version="1.0.0", description="通告广场 CRUD 接口")
    standalone.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    standalone.include_router(router)
    return standalone

app = create_standalone_app()

if __name__ == "__main__":
    import uvicorn
    logger.info(f"通告 API 独立启动，端口 {API_PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
