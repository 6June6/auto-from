"""
TikTok 解析服务（Selenium 版，通过 Clash 代理翻墙访问）
支持：
  用户主页链接 → 昵称、用户名、粉丝、关注、获赞、简介、头像
  视频链接     → 标题、描述、点赞、评论、分享、音乐、作者信息
"""
import re
import time
import argparse
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional

logger = logging.getLogger("tiktok_parser")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ──────────────────────────── 数据模型 ────────────────────────────

@dataclass
class TikTokProfileData:
    """TikTok 用户主页数据"""
    url: str = ""
    username: str = ""
    nickname: str = ""
    bio: str = ""
    avatar: str = ""
    following: str = "0"
    followers: str = "0"
    likes: str = "0"
    website: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  TikTok 用户主页",
            f"{'='*60}",
            f"  昵称: {self.nickname}",
            f"  用户名: @{self.username}",
            f"{'─'*60}",
            f"  👥 粉丝: {self.followers}",
            f"  📝 关注: {self.following}",
            f"  ❤️ 获赞: {self.likes}",
        ]
        if self.bio:
            lines.append(f"  简介: {self.bio[:200]}")
        if self.website:
            lines.append(f"  网站: {self.website}")
        lines.append(f"  链接: {self.url}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


@dataclass
class TikTokVideoData:
    """TikTok 视频数据"""
    url: str = ""
    video_id: str = ""
    author_username: str = ""
    author_nickname: str = ""
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    likes: str = "0"
    comments: str = "0"
    shares: str = "0"
    bookmarks: str = "0"
    music: str = ""
    publish_date: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  TikTok 视频",
            f"{'='*60}",
            f"  作者: {self.author_nickname} (@{self.author_username})",
        ]
        if self.title:
            lines.append(f"  标题: {self.title[:150]}")
        if self.description:
            lines.append(f"  描述: {self.description[:200]}")
        lines.append(f"{'─'*60}")
        lines.append(f"  ❤️ 点赞: {self.likes}")
        lines.append(f"  💬 评论: {self.comments}")
        lines.append(f"  🔄 分享: {self.shares}")
        if self.bookmarks != "0":
            lines.append(f"  🔖 收藏: {self.bookmarks}")
        if self.music:
            lines.append(f"  🎵 音乐: {self.music}")
        if self.tags:
            lines.append(f"  标签: {' '.join(self.tags)}")
        if self.publish_date:
            lines.append(f"  日期: {self.publish_date}")
        lines.append(f"  链接: {self.url}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ──────────────────────────── 常量 ────────────────────────────

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TT_PROFILE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?tiktok\.com/@([A-Za-z0-9._]+)/?(?:\?.*)?$"
)

TT_VIDEO_RE = re.compile(
    r"(?:https?://)?(?:www\.)?tiktok\.com/@([A-Za-z0-9._]+)/video/(\d+)"
)

EXTRACT_PROFILE_JS = r'''
return (() => {
    const d = {};

    const getMeta = (attr, val) => {
        try {
            const el = document.querySelector('meta[' + attr + '="' + val + '"]');
            return el ? (el.getAttribute('content') || '') : '';
        } catch(e) { return ''; }
    };

    d.ogTitle = getMeta('property', 'og:title');
    d.ogDesc = getMeta('property', 'og:description');
    d.ogImage = getMeta('property', 'og:image');
    d.description = getMeta('name', 'description');

    d.pageTitle = document.title || '';

    // data-e2e elements — TikTok's primary data source
    const getE2e = (attr) => {
        const el = document.querySelector('[data-e2e="' + attr + '"]');
        return el ? el.textContent.trim() : '';
    };

    d.userTitle = getE2e('user-title');
    d.userSubtitle = getE2e('user-subtitle');
    d.followingCount = getE2e('following-count');
    d.followersCount = getE2e('followers-count');
    d.likesCount = getE2e('likes-count');

    // Bio from h2 (second h2 is bio)
    d.bio = '';
    const h2s = document.querySelectorAll('h2');
    if (h2s.length >= 2) {
        d.bio = h2s[1].textContent.trim();
    }

    // Website from links
    d.website = '';
    const spans = document.querySelectorAll('span');
    for (const s of spans) {
        const t = s.textContent.trim();
        if (t.match(/^[a-zA-Z0-9].*\.(com|net|org|io|co|me|tw|cn|jp)\/?$/i)) {
            d.website = t;
            break;
        }
    }

    // Avatar
    d.avatar = '';
    const userPage = document.querySelector('[data-e2e="user-page"]');
    if (userPage) {
        const img = userPage.querySelector('img');
        if (img) d.avatar = img.src || '';
    }

    return d;
})()
'''

EXTRACT_VIDEO_JS = r'''
return (() => {
    const d = {};

    const getMeta = (attr, val) => {
        try {
            const el = document.querySelector('meta[' + attr + '="' + val + '"]');
            return el ? (el.getAttribute('content') || '') : '';
        } catch(e) { return ''; }
    };

    d.ogTitle = getMeta('property', 'og:title');
    d.ogDesc = getMeta('property', 'og:description');
    d.description = getMeta('name', 'description');
    d.ogUrl = getMeta('property', 'og:url');

    d.pageTitle = document.title || '';

    const getE2e = (attr) => {
        const el = document.querySelector('[data-e2e="' + attr + '"]');
        return el ? el.textContent.trim() : '';
    };

    // First video container (the target video, not recommendations)
    const firstItem = document.querySelector('[data-e2e="recommend-list-item-container"]');
    const getE2eIn = (parent, attr) => {
        if (!parent) return '';
        const el = parent.querySelector('[data-e2e="' + attr + '"]');
        return el ? el.textContent.trim() : '';
    };

    // Video stats from first container
    d.likeCount = getE2eIn(firstItem, 'like-count') || getE2e('like-count');
    d.commentCount = getE2eIn(firstItem, 'comment-count') || getE2e('comment-count');
    d.bookmarkCount = getE2eIn(firstItem, 'undefined-count') || getE2e('undefined-count');

    // Share count — filter out non-numeric "Share" text
    const rawShare = getE2eIn(firstItem, 'share-count') || getE2e('share-count');
    d.shareCount = /^\d/.test(rawShare) ? rawShare : '0';

    // Video description from first container
    d.videoDesc = getE2eIn(firstItem, 'video-desc') || getE2e('video-desc');

    // Author
    d.authorUsername = '';
    const authorLink = document.querySelector('[data-e2e="video-author-avatar"]');
    if (authorLink) {
        const href = authorLink.closest('a') ? authorLink.closest('a').getAttribute('href') : '';
        const m = href ? href.match(/@([A-Za-z0-9._]+)/) : null;
        if (m) d.authorUsername = m[1];
    }
    // Fallback: from link
    if (!d.authorUsername) {
        const links = document.querySelectorAll('a[href*="/@"]');
        for (const a of links) {
            const href = a.getAttribute('href') || '';
            const m = href.match(/\/@([A-Za-z0-9._]+)$/);
            if (m) { d.authorUsername = m[1]; break; }
        }
    }

    // Tags from links
    d.tags = [];
    document.querySelectorAll('a[href*="/tag/"]').forEach(a => {
        const text = a.textContent.trim();
        if (text.startsWith('#')) d.tags.push(text);
    });

    // Music
    d.music = '';
    const musicEl = document.querySelector('[data-e2e="video-music"]');
    if (musicEl) d.music = musicEl.textContent.trim();

    // Publish date from spans
    d.publishDate = '';
    const spans = document.querySelectorAll('span');
    for (const s of spans) {
        const t = s.textContent.trim();
        if (t.match(/^\d{4}-\d{1,2}-\d{1,2}$/)) {
            d.publishDate = t;
            break;
        }
    }

    return d;
})()
'''


# ──────────────────────────── 解析器 ────────────────────────────

class TikTokParser:
    """TikTok 主页 & 视频解析器"""

    def __init__(self, headless: bool = True, timeout: int = 45,
                 chrome_binary: str = None, proxy: str = "http://127.0.0.1:7890"):
        self.headless = headless
        self.timeout = timeout
        self.chrome_binary = chrome_binary
        self.proxy = proxy

    def _create_driver(self):
        if not HAS_SELENIUM:
            raise RuntimeError("Selenium 未安装: pip install selenium")

        opts = Options()
        if self.chrome_binary:
            opts.binary_location = self.chrome_binary

        opts.add_argument(f"--user-agent={DESKTOP_UA}")
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--window-size=1440,900")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])

        if self.proxy:
            opts.add_argument(f"--proxy-server={self.proxy}")
            opts.add_argument("--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1")

        driver = webdriver.Chrome(options=opts)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        })
        driver.set_page_load_timeout(self.timeout)
        driver.implicitly_wait(5)
        return driver

    def _load_page(self, driver, url: str) -> Optional[str]:
        """加载页面并返回最终 URL，失败返回 None"""
        try:
            driver.get(url)
        except Exception as e:
            logger.warning(f"页面加载异常: {type(e).__name__}")

        time.sleep(15)

        final_url = driver.current_url
        if "chrome-error" in final_url:
            return None
        return final_url

    # ── 主页解析 ──

    def parse_profile(self, url: str) -> TikTokProfileData:
        result = TikTokProfileData(url=url)
        driver = None

        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url

            m = TT_PROFILE_RE.search(url)
            if m:
                result.username = m.group(1)

            logger.info(f"解析 TikTok 主页: {url}")
            driver = self._create_driver()

            final_url = self._load_page(driver, url)
            if not final_url:
                result.error = "无法通过代理访问 TikTok（请检查代理配置）"
                return result

            raw = driver.execute_script(EXTRACT_PROFILE_JS)
            if not raw:
                result.error = "JavaScript 提取返回空"
                return result

            # Username & Nickname
            result.username = raw.get("userTitle") or result.username
            result.nickname = raw.get("userSubtitle", "")

            if not result.nickname:
                og_title = raw.get("ogTitle", "")
                name_match = re.match(r'^(.+?)\s*\(@\w+\)', og_title)
                if name_match:
                    result.nickname = name_match.group(1).strip()

            # Avatar
            result.avatar = raw.get("avatar") or raw.get("ogImage", "")

            # Stats
            result.following = raw.get("followingCount", "0") or "0"
            result.followers = raw.get("followersCount", "0") or "0"
            result.likes = raw.get("likesCount", "0") or "0"

            # Fallback: parse from og:description
            if result.followers == "0":
                desc = raw.get("ogDesc") or raw.get("description", "")
                fm = re.search(r'([\d,.]+[KkMm]?)\s+Followers?', desc, re.IGNORECASE)
                if fm:
                    result.followers = fm.group(1)
                lm = re.search(r'([\d,.]+[KkMm]?)\s+Likes?', desc, re.IGNORECASE)
                if lm:
                    result.likes = lm.group(1)

            # Bio
            result.bio = raw.get("bio", "")
            if not result.bio:
                desc = raw.get("description") or raw.get("ogDesc", "")
                result.bio = self._extract_profile_bio(desc, result.nickname)

            # Website
            result.website = raw.get("website", "")

            result.url = final_url
            logger.info(f"TikTok 主页解析完成: {result.nickname} (@{result.username})")

        except Exception as e:
            logger.error(f"TikTok 主页解析异常: {e}")
            result.error = str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return result

    # ── 视频解析 ──

    def parse_video(self, url: str) -> TikTokVideoData:
        result = TikTokVideoData(url=url)
        driver = None

        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url

            m = TT_VIDEO_RE.search(url)
            if m:
                result.author_username = m.group(1)
                result.video_id = m.group(2)

            logger.info(f"解析 TikTok 视频: {url}")
            driver = self._create_driver()

            final_url = self._load_page(driver, url)
            if not final_url:
                result.error = "无法通过代理访问 TikTok（请检查代理配置）"
                return result

            raw = driver.execute_script(EXTRACT_VIDEO_JS)
            if not raw:
                result.error = "JavaScript 提取返回空"
                return result

            # Author
            result.author_username = raw.get("authorUsername") or result.author_username

            # Author nickname from og:title
            og_title = raw.get("ogTitle", "")
            if og_title:
                result.author_nickname = og_title.replace(" on TikTok", "").strip()

            # Title from page title
            page_title = raw.get("pageTitle", "")
            if page_title:
                result.title = page_title.replace(" | TikTok", "").strip()

            # Description — og:description is most accurate for the target video
            result.description = raw.get("ogDesc") or raw.get("videoDesc", "")

            # Stats
            result.likes = raw.get("likeCount", "0") or "0"
            result.comments = raw.get("commentCount", "0") or "0"
            result.shares = raw.get("shareCount", "0") or "0"
            result.bookmarks = raw.get("bookmarkCount", "0") or "0"

            # Fallback: parse likes from description meta
            if result.likes == "0":
                desc = raw.get("description", "")
                lm = re.search(r'(\d+)\s+Likes?', desc, re.IGNORECASE)
                if lm:
                    result.likes = lm.group(1)

            # Tags
            result.tags = raw.get("tags", [])
            if not result.tags and result.description:
                result.tags = re.findall(r'#\w+', result.description)

            # Music
            result.music = raw.get("music", "")

            # Publish date
            result.publish_date = raw.get("publishDate", "")

            result.url = final_url
            logger.info(f"TikTok 视频解析完成: {result.title[:50]}")

        except Exception as e:
            logger.error(f"TikTok 视频解析异常: {e}")
            result.error = str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return result

    # ── 通用入口 ──

    def parse(self, url: str):
        """自动识别并解析主页或视频"""
        if TT_VIDEO_RE.search(url):
            return self.parse_video(url)
        return self.parse_profile(url)

    @staticmethod
    def _extract_profile_bio(desc: str, nickname: str) -> str:
        """从 meta description 中提取 bio"""
        if not desc:
            return ""
        # Format: "NAME (@user) on TikTok | N Likes. N Followers. BIO.Watch..."
        parts = desc.split(".")
        bio_parts = []
        skip_next = True
        for p in parts:
            pt = p.strip()
            if skip_next:
                if re.search(r'\d+\s+Followers?', pt, re.IGNORECASE):
                    skip_next = False
                continue
            if pt.lower().startswith("watch"):
                break
            if pt:
                bio_parts.append(pt)
        return ". ".join(bio_parts).strip() if bio_parts else ""


# ──────────────────────────── CLI ────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="TikTok 主页/视频解析器")
    parser.add_argument("url", help="TikTok 链接")
    parser.add_argument("--chrome", default="/usr/bin/chromium-browser", help="Chrome 路径")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890", help="代理地址")
    parser.add_argument("--no-proxy", action="store_true", help="不使用代理")
    args = parser.parse_args()

    proxy = None if args.no_proxy else args.proxy
    tt = TikTokParser(headless=True, timeout=45, chrome_binary=args.chrome, proxy=proxy)
    data = tt.parse(args.url)
    print(data.summary())
