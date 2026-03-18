"""
社交媒体解析 API 服务
基于 FastAPI，支持小红书、抖音、Facebook、Instagram、Threads、TikTok 链接解析
内置缓存：相同 URL 在 TTL 内直接返回缓存结果（默认 2 小时）
对于本地受地域限制的平台（如 TikTok、Instagram），自动转发到远端 API 节点解析
"""
import asyncio
import hashlib
import json
import logging
import os
import re
import time
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

import requests as http_requests

from xhs_parser_selenium import XhsParser, XhsNoteData, XhsProfileData
from douyin_parser_selenium import DouyinParser, DouyinVideoData, DouyinProfileData
from facebook_parser_selenium import FacebookParser, FacebookProfileData
from instagram_parser_selenium import InstagramParser, InstagramProfileData
from threads_parser_selenium import ThreadsParser, ThreadsProfileData, ThreadsPostData
from tiktok_parser_selenium import TikTokParser, TikTokProfileData, TikTokVideoData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("social_api")

CHROME_BIN = "/usr/bin/chromium-browser"
CLASH_PROXY = "http://127.0.0.1:7890"
CACHE_DIR = Path("/opt/xhs-api/cache")
CACHE_TTL = 7200  # 默认缓存 2 小时

# 远端 API 节点：用于转发本地受地域限制的平台请求
# 设为空字符串则禁用转发，所有请求均本地解析
REMOTE_API = os.environ.get("REMOTE_API", "")
# 需要转发到远端的平台列表（本地受限的平台）
REMOTE_PLATFORMS = set(
    p.strip() for p in os.environ.get("REMOTE_PLATFORMS", "").split(",") if p.strip()
)
NOTICE_API_BASE = os.environ.get("NOTICE_API_BASE", "http://127.0.0.1:8901")

xhs_parser = XhsParser(headless=True, timeout=30, chrome_binary=CHROME_BIN)
douyin_parser = DouyinParser(headless=True, timeout=30, chrome_binary=CHROME_BIN)
facebook_parser = FacebookParser(headless=True, timeout=45, chrome_binary=CHROME_BIN, proxy=CLASH_PROXY)
instagram_parser = InstagramParser(headless=True, timeout=45, chrome_binary=CHROME_BIN, proxy=CLASH_PROXY)
threads_parser = ThreadsParser(headless=True, timeout=45, chrome_binary=CHROME_BIN, proxy=CLASH_PROXY)
tiktok_parser = TikTokParser(headless=True, timeout=45, chrome_binary=CHROME_BIN, proxy=CLASH_PROXY)


# ──────────────────────────── 缓存层 ────────────────────────────

class ParseCache:
    """双层缓存：内存 + 磁盘 JSON 持久化"""

    def __init__(self, cache_dir: Path, default_ttl: int = 7200):
        self._mem: dict = {}  # {cache_key: {"data": ..., "ts": ...}}
        self._lock = threading.Lock()
        self._dir = cache_dir
        self._ttl = default_ttl
        self._dir.mkdir(parents=True, exist_ok=True)
        self._load_disk()

    @staticmethod
    def _make_key(url: str) -> str:
        normalized = re.sub(r'[?#].*$', '', url.strip().rstrip('/').lower())
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, url: str) -> Optional[dict]:
        key = self._make_key(url)
        with self._lock:
            entry = self._mem.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > self._ttl:
            self._evict(key)
            return None
        return entry["data"]

    def put(self, url: str, data: dict):
        key = self._make_key(url)
        entry = {"data": data, "ts": time.time(), "url": url}
        with self._lock:
            self._mem[key] = entry
        self._save_disk(key, entry)

    def _evict(self, key: str):
        with self._lock:
            self._mem.pop(key, None)
        fpath = self._dir / f"{key}.json"
        fpath.unlink(missing_ok=True)

    def _save_disk(self, key: str, entry: dict):
        try:
            fpath = self._dir / f"{key}.json"
            fpath.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"缓存写盘失败: {e}")

    def _load_disk(self):
        loaded = 0
        now = time.time()
        for fpath in self._dir.glob("*.json"):
            try:
                entry = json.loads(fpath.read_text(encoding="utf-8"))
                if now - entry.get("ts", 0) <= self._ttl:
                    self._mem[fpath.stem] = entry
                    loaded += 1
                else:
                    fpath.unlink(missing_ok=True)
            except Exception:
                fpath.unlink(missing_ok=True)
        if loaded:
            logger.info(f"从磁盘加载 {loaded} 条缓存")

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            valid = sum(1 for e in self._mem.values() if now - e["ts"] <= self._ttl)
        return {"total": len(self._mem), "valid": valid, "ttl_seconds": self._ttl}

    def clear(self) -> int:
        with self._lock:
            count = len(self._mem)
            self._mem.clear()
        for fpath in self._dir.glob("*.json"):
            fpath.unlink(missing_ok=True)
        return count


_cache = ParseCache(CACHE_DIR, CACHE_TTL)


def _forward_to_remote(path: str, url: str, refresh: bool = False) -> Optional[dict]:
    """将请求转发到远端 API 节点，返回 JSON 响应或 None（失败时）"""
    if not REMOTE_API:
        return None
    try:
        remote_url = f"{REMOTE_API.rstrip('/')}/{path.lstrip('/')}"
        params = {"url": url}
        if refresh:
            params["refresh"] = "true"
        logger.info(f"转发到远端: {remote_url} url={url[:80]}")
        resp = http_requests.get(remote_url, params=params, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"远端转发失败: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"社交媒体解析 API 启动 (端口 8900, 缓存 TTL={CACHE_TTL}s)")
    yield
    logger.info("社交媒体解析 API 关闭")


app = FastAPI(
    title="社交媒体解析 API",
    description="解析小红书、抖音、Facebook、Instagram、Threads、TikTok 链接，获取笔记/视频/帖子/用户主页数据（带缓存）",
    version="7.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ParseRequest(BaseModel):
    url: str = Field(..., description="链接（小红书/抖音/Facebook/Instagram/Threads/TikTok，支持短链接）")
    refresh: bool = Field(False, description="是否强制刷新缓存")


class ApiResponse(BaseModel):
    success: bool
    platform: str = ""
    type: str = ""
    data: Optional[dict] = None
    error: Optional[str] = None
    cached: bool = False


def _proxy_notice_request(method: str, path: str, *, headers: Optional[dict] = None,
                          params: Optional[dict] = None, payload: Optional[dict] = None) -> JSONResponse:
    """将 /notice 请求转发到本机 8901 独立服务。"""
    url = f"{NOTICE_API_BASE.rstrip('/')}/{path.lstrip('/')}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    try:
        resp = http_requests.request(
            method=method,
            url=url,
            headers=headers or {},
            params=clean_params,
            json=payload,
            timeout=30,
        )
    except Exception as e:
        logger.error(f"通告接口转发失败: {e}")
        return JSONResponse(
            status_code=502,
            content={"detail": f"notice service unavailable: {str(e)}"},
        )

    try:
        content = resp.json()
    except Exception:
        content = {"detail": resp.text or "notice service returned non-json response"}
    return JSONResponse(status_code=resp.status_code, content=content)


# ── 通用入口：自动识别平台 + 类型 ──

def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "xhslink.com" in url_lower or "xiaohongshu.com" in url_lower:
        return "xhs"
    if "douyin.com" in url_lower or "iesdouyin.com" in url_lower:
        return "douyin"
    if "facebook.com" in url_lower or "fb.com" in url_lower:
        return "facebook"
    if "instagram.com" in url_lower or "instagr.am" in url_lower:
        return "instagram"
    if "threads.com" in url_lower or "threads.net" in url_lower:
        return "threads"
    if "tiktok.com" in url_lower:
        return "tiktok"
    return "unknown"


@app.get("/", summary="健康检查")
async def health():
    info = {"status": "ok", "service": "social-media-parser-api", "version": "7.3.0",
            "platforms": ["xiaohongshu", "douyin", "facebook", "instagram", "threads", "tiktok"],
            "cache": _cache.stats()}
    if REMOTE_API:
        info["remote"] = {"api": REMOTE_API, "platforms": sorted(REMOTE_PLATFORMS)}
    return info


# ── 缓存管理 ──

@app.get("/cache/stats", summary="缓存状态")
async def cache_stats():
    return _cache.stats()


@app.delete("/cache/clear", summary="清空缓存")
async def cache_clear():
    count = _cache.clear()
    return {"cleared": count}


# ── 通告管理代理 ──

@app.get("/notice/platforms", summary="获取通告平台列表")
async def notice_platforms(x_api_key: str = Header(..., alias="X-API-Key")):
    return _proxy_notice_request("GET", "/platforms", headers={"X-API-Key": x_api_key})


@app.get("/notice/categories", summary="获取通告类目列表")
async def notice_categories(x_api_key: str = Header(..., alias="X-API-Key")):
    return _proxy_notice_request("GET", "/categories", headers={"X-API-Key": x_api_key})


@app.post("/notice/notices", summary="创建通告")
async def notice_create(
    payload: dict = Body(...),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    return _proxy_notice_request("POST", "/notices", headers={"X-API-Key": x_api_key}, payload=payload)


@app.get("/notice/notices", summary="查询通告列表")
async def notice_list(
    keyword: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    return _proxy_notice_request(
        "GET",
        "/notices",
        headers={"X-API-Key": x_api_key},
        params={"keyword": keyword, "platform": platform, "status": status, "limit": limit},
    )


@app.get("/notice/notices/{notice_id}", summary="查询单条通告")
async def notice_detail(notice_id: str, x_api_key: str = Header(..., alias="X-API-Key")):
    return _proxy_notice_request("GET", f"/notices/{notice_id}", headers={"X-API-Key": x_api_key})


# ── 通用解析 ──

@app.get("/parse", summary="自动识别并解析（GET）", response_model=ApiResponse)
async def parse_get(
    url: str = Query(..., description="小红书、抖音、Facebook、Instagram、Threads或TikTok链接"),
    refresh: bool = Query(False, description="是否强制刷新（忽略缓存）"),
):
    return await _auto_parse(url, refresh)


@app.post("/parse", summary="自动识别并解析（POST）", response_model=ApiResponse)
async def parse_post(req: ParseRequest):
    return await _auto_parse(req.url, req.refresh)


# ── 小红书专用 ──

@app.get("/xhs/note", summary="解析小红书笔记", response_model=ApiResponse)
async def xhs_note(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(xhs_parser.parse_note, url, "xhs", "note", refresh=refresh)


@app.get("/xhs/profile", summary="解析小红书主页", response_model=ApiResponse)
async def xhs_profile(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(xhs_parser.parse_profile, url, "xhs", "profile", refresh=refresh)


# ── 抖音专用 ──

@app.get("/douyin/video", summary="解析抖音视频", response_model=ApiResponse)
async def douyin_video(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(douyin_parser.parse_video, url, "douyin", "video", refresh=refresh)


@app.get("/douyin/profile", summary="解析抖音主页", response_model=ApiResponse)
async def douyin_profile(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(douyin_parser.parse_profile, url, "douyin", "profile", refresh=refresh)


# ── Facebook 专用 ──

@app.get("/facebook/profile", summary="解析Facebook主页", response_model=ApiResponse)
async def fb_profile(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(facebook_parser.parse_profile, url, "facebook", "profile", refresh=refresh)


# ── Instagram 专用 ──

@app.get("/instagram/profile", summary="解析Instagram主页", response_model=ApiResponse)
async def ig_profile(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(instagram_parser.parse_profile, url, "instagram", "profile",
                      refresh=refresh, remote_path="instagram/profile")


# ── Threads 专用 ──

@app.get("/threads/profile", summary="解析Threads主页", response_model=ApiResponse)
async def threads_profile(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(threads_parser.parse_profile, url, "threads", "profile", refresh=refresh)


@app.get("/threads/post", summary="解析Threads帖子", response_model=ApiResponse)
async def threads_post(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(threads_parser.parse_post, url, "threads", "post", refresh=refresh)


# ── TikTok 专用 ──

@app.get("/tiktok/profile", summary="解析TikTok主页", response_model=ApiResponse)
async def tiktok_profile(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(tiktok_parser.parse_profile, url, "tiktok", "profile",
                      refresh=refresh, remote_path="tiktok/profile")


@app.get("/tiktok/video", summary="解析TikTok视频", response_model=ApiResponse)
async def tiktok_video(url: str = Query(...), refresh: bool = Query(False)):
    return await _run(tiktok_parser.parse_video, url, "tiktok", "video",
                      refresh=refresh, remote_path="tiktok/video")


# ── 内部逻辑 ──

async def _auto_parse(url: str, refresh: bool = False) -> dict:
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url 不能为空")

    platform = _detect_platform(url)
    logger.info(f"收到解析请求 [{platform}]: {url[:100]}")

    dispatch = {
        "xhs": (xhs_parser.parse, "xhs"),
        "douyin": (douyin_parser.parse, "douyin"),
        "facebook": (facebook_parser.parse, "facebook"),
        "instagram": (instagram_parser.parse, "instagram"),
        "threads": (threads_parser.parse, "threads"),
        "tiktok": (tiktok_parser.parse, "tiktok"),
    }

    if platform not in dispatch:
        raise HTTPException(status_code=400,
            detail="无法识别链接平台，支持: 小红书、抖音、Facebook、Instagram、Threads、TikTok")

    func, pf = dispatch[platform]
    return await _run(func, url, pf, refresh=refresh)


async def _run(func, url: str, platform: str, force_type: str = None,
               refresh: bool = False, remote_path: str = None) -> dict:
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url 不能为空")

    # 1) 查缓存
    if not refresh:
        cached = _cache.get(url)
        if cached:
            logger.info(f"缓存命中 [{platform}]: {url[:80]}")
            cached["cached"] = True
            return cached

    # 2) 如果该平台需要远端转发
    if platform in REMOTE_PLATFORMS and REMOTE_API:
        path = remote_path or f"parse"
        t0 = time.time()
        remote_resp = _forward_to_remote(path, url, refresh)
        elapsed = round(time.time() - t0, 1)
        if remote_resp and remote_resp.get("success"):
            remote_resp["cached"] = False
            _cache.put(url, remote_resp)
            logger.info(f"远端解析成功 [{platform}] ({elapsed}s, 已缓存)")
            return remote_resp
        if remote_resp:
            logger.warning(f"远端解析失败 ({elapsed}s): {remote_resp.get('error')}")
            return remote_resp
        logger.warning(f"远端不可达，回退本地解析 [{platform}]")

    # 3) 本地解析
    t0 = time.time()
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, func, url)
    except Exception as e:
        logger.error(f"解析异常: {e}")
        return {"success": False, "platform": platform, "type": force_type or "unknown",
                "data": None, "error": str(e), "cached": False}

    elapsed = round(time.time() - t0, 1)
    result_type = force_type or _detect_type(result)

    if result.error:
        logger.warning(f"解析警告 ({elapsed}s): {result.error}")
        return {"success": False, "platform": platform, "type": result_type,
                "data": result.to_dict(), "error": result.error, "cached": False}

    # 4) 写缓存（只缓存成功结果）
    resp = {"success": True, "platform": platform, "type": result_type,
            "data": result.to_dict(), "error": None, "cached": False}
    _cache.put(url, resp)

    logger.info(f"解析成功 [{platform}/{result_type}] ({elapsed}s, 已缓存)")
    return resp


def _detect_type(result) -> str:
    if isinstance(result, (XhsNoteData, DouyinVideoData, TikTokVideoData)):
        if isinstance(result, XhsNoteData):
            return "note"
        return "video"
    if isinstance(result, ThreadsPostData):
        return "post"
    if isinstance(result, (XhsProfileData, DouyinProfileData, FacebookProfileData,
                           InstagramProfileData, ThreadsProfileData, TikTokProfileData)):
        return "profile"
    return "unknown"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)
