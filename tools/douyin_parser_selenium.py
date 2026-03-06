"""
抖音解析服务（Selenium 版，兼容 CentOS 7）
通过 _ROUTER_DATA SSR 数据提取精确的统计信息
支持：
  1. 视频链接 → 标题、作者、点赞、评论、转发、收藏
  2. 用户主页链接 → 昵称、粉丝、获赞、作品数、简介
"""
import re
import json
import time
import argparse
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional

logger = logging.getLogger("douyin_parser")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ──────────────────────────── 数据模型 ────────────────────────────

@dataclass
class DouyinVideoData:
    """抖音视频数据"""
    url: str = ""
    video_id: str = ""
    title: str = ""
    author: str = ""
    description: str = ""
    likes: str = "0"
    comments: str = "0"
    shares: str = "0"
    collects: str = "0"
    plays: str = "0"
    music: str = ""
    tags: list = field(default_factory=list)
    cover: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  抖音视频数据",
            f"{'='*60}",
            f"  标题: {self.title}",
            f"  作者: {self.author}",
            f"  视频ID: {self.video_id}",
            f"{'─'*60}",
            f"  👍 点赞: {self.likes}",
            f"  💬 评论: {self.comments}",
            f"  ⭐ 收藏: {self.collects}",
            f"  🔗 转发: {self.shares}",
        ]
        if self.description:
            lines.append(f"  描述: {self.description[:150]}")
        if self.music:
            lines.append(f"  音乐: {self.music}")
        if self.tags:
            lines.append(f"  标签: {', '.join(self.tags)}")
        lines.append(f"  链接: {self.url}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


@dataclass
class DouyinProfileData:
    """抖音用户主页数据"""
    url: str = ""
    sec_uid: str = ""
    douyin_id: str = ""
    nickname: str = ""
    signature: str = ""
    followers: str = "0"
    following: str = "0"
    likes_received: str = "0"
    works_count: str = "0"
    avatar: str = ""
    videos: List[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  抖音用户主页",
            f"{'='*60}",
            f"  昵称: {self.nickname}",
            f"  抖音号: {self.douyin_id}",
            f"  简介: {self.signature[:100]}",
            f"{'─'*60}",
            f"  🔥 获赞: {self.likes_received}",
            f"  📝 关注: {self.following}",
            f"  👥 粉丝: {self.followers}",
            f"  🎬 作品: {self.works_count}",
            f"{'─'*60}",
            f"  链接: {self.url}",
        ]
        if self.videos:
            lines.append(f"  视频列表 (共 {len(self.videos)} 条):")
            for i, v in enumerate(self.videos, 1):
                title = v.get("title", "")[:35]
                likes = v.get("likes", "")
                lines.append(f"    {i}. {title}  👍{likes}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ──────────────────────────── 常量 ────────────────────────────

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

DOUYIN_SHORT_RE = re.compile(r"(?:https?://)?v\.douyin\.com/\S+")
DOUYIN_VIDEO_RE = re.compile(r"(?:iesdouyin|douyin)\.com/(?:share/)?video/(\d+)")
DOUYIN_USER_RE = re.compile(r"iesdouyin\.com/share/user/([\w=]+)")
ROUTER_DATA_RE = re.compile(r'_ROUTER_DATA\s*=\s*(\{.+?\})\s*</script>', re.DOTALL)


def _format_count(n) -> str:
    """把数字格式化为可读字符串"""
    if isinstance(n, str):
        try:
            n = int(n)
        except (ValueError, TypeError):
            return n
    if n >= 100000000:
        return f"{n / 100000000:.1f}亿"
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


# ──────────────────────────── 解析器 ────────────────────────────

class DouyinParser:
    """抖音解析器"""

    def __init__(self, headless: bool = True, timeout: int = 30,
                 chrome_binary: str = None):
        self.headless = headless
        self.timeout = timeout
        self.chrome_binary = chrome_binary

    def _create_driver(self):
        if not HAS_SELENIUM:
            raise RuntimeError("Selenium 未安装: pip install selenium")

        opts = Options()
        if self.chrome_binary:
            opts.binary_location = self.chrome_binary

        mobile_emulation = {
            "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
            "userAgent": MOBILE_UA,
        }
        opts.add_experimental_option("mobileEmulation", mobile_emulation)

        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--lang=zh-CN")

        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(self.timeout)
        driver.implicitly_wait(5)
        return driver

    def _load_and_get_ssr(self, driver, url: str) -> tuple:
        """加载页面并提取 _ROUTER_DATA SSR 数据，返回 (final_url, ssr_dict)"""
        if not url.startswith("http"):
            url = "https://" + url
        driver.get(url)
        if DOUYIN_SHORT_RE.match(url.replace("https://", "").replace("http://", "")):
            logger.info(f"解析短链接: {url}")
            time.sleep(4)
        else:
            time.sleep(3)

        final_url = driver.current_url
        logger.info(f"最终地址: {final_url[:120]}")

        html = driver.page_source
        match = ROUTER_DATA_RE.search(html)
        if match:
            try:
                return final_url, json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return final_url, {}

    def _is_profile_url(self, url: str) -> bool:
        return bool(DOUYIN_USER_RE.search(url))

    def _extract_video_id(self, url: str) -> str:
        m = DOUYIN_VIDEO_RE.search(url)
        return m.group(1) if m else ""

    # ── 视频解析 ──

    def parse_video(self, url: str) -> DouyinVideoData:
        data = DouyinVideoData(url=url)
        driver = None
        try:
            driver = self._create_driver()
            final_url, ssr = self._load_and_get_ssr(driver, url)
            data.url = final_url
            data.video_id = self._extract_video_id(final_url)

            if ssr:
                self._fill_video_from_ssr(data, ssr)

            # 如果 SSR 没拿到评论数，从 DOM 补充
            if data.comments == "0":
                data.comments = self._get_comment_count_from_dom(driver)

            # 如果 SSR 完全没数据，回退到 DOM
            if not data.title:
                self._fill_video_from_dom(data, driver)

        except Exception as e:
            data.error = f"解析失败: {str(e)}"
            logger.error(f"视频解析失败: {e}")
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
        return data

    def _fill_video_from_ssr(self, data: DouyinVideoData, ssr: dict):
        """从 _ROUTER_DATA 提取视频数据"""
        loader = ssr.get("loaderData", {})

        # 找到包含 aweme 数据的 page
        aweme_detail = None
        for key, val in loader.items():
            if not isinstance(val, dict):
                continue
            if "aweme_detail" in val:
                aweme_detail = val["aweme_detail"]
                break
            # 也检查 itemInfo
            if "itemInfo" in val:
                aweme_detail = val["itemInfo"]
                break

        # 尝试从 HTML 中搜索 statistics
        if not aweme_detail:
            for key, val in loader.items():
                if isinstance(val, dict):
                    val_str = json.dumps(val)
                    if "digg_count" in val_str:
                        # 递归查找包含 statistics 的对象
                        aweme_detail = self._find_aweme_in_dict(val)
                        if aweme_detail:
                            break

        if not aweme_detail:
            return

        data.title = aweme_detail.get("desc", "")
        data.description = data.title

        author_info = aweme_detail.get("author", {})
        data.author = author_info.get("nickname", "")

        stats = aweme_detail.get("statistics", {})
        data.likes = _format_count(stats.get("digg_count", 0))
        data.comments = _format_count(stats.get("comment_count", 0))
        data.shares = _format_count(stats.get("share_count", 0))
        data.collects = _format_count(stats.get("collect_count", 0))
        data.plays = _format_count(stats.get("play_count", 0))

        music_info = aweme_detail.get("music", {})
        if music_info:
            data.music = music_info.get("title", "")

        cover_info = aweme_detail.get("video", {}).get("cover", {})
        if cover_info:
            urls = cover_info.get("url_list", [])
            if urls:
                data.cover = urls[0]

        # 提取标签
        text_extra = aweme_detail.get("text_extra", [])
        for item in text_extra:
            name = item.get("hashtag_name", "")
            if name and name not in data.tags:
                data.tags.append(name)

    def _find_aweme_in_dict(self, d: dict) -> Optional[dict]:
        """递归查找包含 statistics.digg_count 的字典"""
        if not isinstance(d, dict):
            return None
        if "statistics" in d and isinstance(d["statistics"], dict):
            if "digg_count" in d["statistics"]:
                return d
        for v in d.values():
            if isinstance(v, dict):
                result = self._find_aweme_in_dict(v)
                if result:
                    return result
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        result = self._find_aweme_in_dict(item)
                        if result:
                            return result
        return None

    def _get_comment_count_from_dom(self, driver) -> str:
        try:
            return driver.execute_script(r'''
                const el = document.querySelector("[class*='commentTotalCount']");
                if (el) {
                    const m = el.textContent.match(/(\d[\d.]*万?\+?)/);
                    return m ? m[1] : "0";
                }
                return "0";
            ''') or "0"
        except Exception:
            return "0"

    def _fill_video_from_dom(self, data: DouyinVideoData, driver):
        """回退：从 DOM 提取基本数据"""
        try:
            raw = driver.execute_script(r'''
                return {
                    title: document.title.replace(/ - 抖音$/, '').trim(),
                    author: (document.querySelector('.author-name') || {}).textContent || "",
                    desc: (document.querySelector('.desc') || {}).textContent || ""
                };
            ''')
            if raw:
                if not data.title:
                    data.title = raw.get("title", "")
                if not data.author:
                    data.author = (raw.get("author", "") or "").replace("@", "").strip()
                if not data.description:
                    data.description = raw.get("desc", "")
        except Exception:
            pass

    # ── 主页解析 ──

    def parse_profile(self, url: str) -> DouyinProfileData:
        data = DouyinProfileData(url=url)
        driver = None
        try:
            driver = self._create_driver()
            final_url, ssr = self._load_and_get_ssr(driver, url)
            data.url = final_url

            if ssr:
                self._fill_profile_from_ssr(data, ssr)

            # SSR 没数据则从 DOM 提取
            if not data.nickname:
                self._fill_profile_from_dom(data, driver)

        except Exception as e:
            data.error = f"解析失败: {str(e)}"
            logger.error(f"主页解析失败: {e}")
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
        return data

    def _fill_profile_from_ssr(self, data: DouyinProfileData, ssr: dict):
        """从 _ROUTER_DATA 提取用户主页数据"""
        loader = ssr.get("loaderData", {})

        user_info = None
        for key, val in loader.items():
            if not isinstance(val, dict):
                continue
            res = val.get("userInfoRes", {})
            if res:
                user_info = res.get("user_info", {})
                break

        if not user_info:
            return

        data.nickname = user_info.get("nickname", "")
        data.signature = user_info.get("signature", "")
        data.douyin_id = user_info.get("unique_id", "") or user_info.get("short_id", "")
        data.sec_uid = user_info.get("sec_uid", "")
        data.following = _format_count(user_info.get("following_count", 0))
        data.followers = _format_count(user_info.get("mplatform_followers_count", 0))
        data.likes_received = _format_count(user_info.get("total_favorited", 0))
        data.works_count = str(user_info.get("aweme_count", 0))

        avatar = user_info.get("avatar_medium", {})
        if isinstance(avatar, dict):
            urls = avatar.get("url_list", [])
            if urls:
                data.avatar = urls[0]

    def _fill_profile_from_dom(self, data: DouyinProfileData, driver):
        """回退：从 DOM 提取主页数据"""
        try:
            raw = driver.execute_script(r'''
                const r = { nickname: "", followers: "0", following: "0", likesReceived: "0", worksCount: "0", videos: [] };
                const nameEl = document.querySelector('.name');
                if (nameEl) r.nickname = nameEl.textContent.trim();
                const dataDivs = document.querySelectorAll('.user-data');
                for (const div of dataDivs) {
                    const t = (div.querySelector('.title') || {}).textContent || '';
                    const n = (div.querySelector('.num') || {}).textContent || '0';
                    if (/获赞/.test(t)) r.likesReceived = n.trim();
                    else if (/关注/.test(t)) r.following = n.trim();
                    else if (/粉丝/.test(t)) r.followers = n.trim();
                }
                const tabNum = document.querySelector('.select-tab-number');
                if (tabNum) r.worksCount = tabNum.textContent.trim();
                const covers = document.querySelectorAll('.user-post-cover');
                for (const c of covers) {
                    const likeEl = c.querySelector('.count-number');
                    r.videos.push({ likes: likeEl ? likeEl.textContent.trim() : "" });
                }
                return r;
            ''')
            if raw:
                if not data.nickname:
                    data.nickname = raw.get("nickname", "")
                if data.followers == "0":
                    data.followers = raw.get("followers", "0")
                if data.following == "0":
                    data.following = raw.get("following", "0")
                if data.likes_received == "0":
                    data.likes_received = raw.get("likesReceived", "0")
                if data.works_count == "0":
                    data.works_count = raw.get("worksCount", "0")
                if not data.videos and raw.get("videos"):
                    data.videos = raw["videos"]
        except Exception:
            pass

    # ── 自动识别 ──

    def parse(self, url: str):
        if not url.startswith("http"):
            url = "https://" + url

        if self._is_profile_url(url):
            return self.parse_profile(url)
        vid = self._extract_video_id(url)
        if vid:
            return self.parse_video(url)

        # 短链接先解析
        if DOUYIN_SHORT_RE.match(url.replace("https://", "").replace("http://", "")):
            driver = None
            try:
                driver = self._create_driver()
                final_url, ssr = self._load_and_get_ssr(driver, url)

                if self._is_profile_url(final_url):
                    data = DouyinProfileData(url=final_url)
                    if ssr:
                        self._fill_profile_from_ssr(data, ssr)
                    if not data.nickname:
                        self._fill_profile_from_dom(data, driver)
                    return data
                else:
                    data = DouyinVideoData(url=final_url)
                    data.video_id = self._extract_video_id(final_url)
                    if ssr:
                        self._fill_video_from_ssr(data, ssr)
                    if data.comments == "0":
                        data.comments = self._get_comment_count_from_dom(driver)
                    if not data.title:
                        self._fill_video_from_dom(data, driver)
                    return data
            except Exception as e:
                return DouyinVideoData(url=url, error=f"解析失败: {str(e)}")
            finally:
                if driver:
                    try: driver.quit()
                    except Exception: pass

        return self.parse_video(url)


# ──────────────────────────── CLI ────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="抖音解析工具（视频 + 主页）")
    ap.add_argument("url", help="抖音链接（视频/主页，支持短链接）")
    ap.add_argument("--type", choices=["video", "profile", "auto"], default="auto")
    ap.add_argument("--no-headless", action="store_true")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--chrome-binary", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = DouyinParser(
        headless=not args.no_headless,
        timeout=args.timeout,
        chrome_binary=args.chrome_binary,
    )

    if args.type == "video":
        result = parser.parse_video(args.url)
    elif args.type == "profile":
        result = parser.parse_profile(args.url)
    else:
        result = parser.parse(args.url)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.summary())

    if result.error:
        print(f"\n⚠️  警告: {result.error}")


if __name__ == "__main__":
    main()
