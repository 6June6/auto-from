"""
Instagram 解析服务（Selenium 版，通过 Clash 代理翻墙访问）
支持：
  用户主页链接 → 昵称、用户名、粉丝、关注、帖子数、简介、头像、最新帖子
"""
import re
import time
import argparse
import logging
from dataclasses import dataclass, asdict, field
from typing import List

logger = logging.getLogger("instagram_parser")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ──────────────────────────── 数据模型 ────────────────────────────

@dataclass
class InstagramProfileData:
    """Instagram 用户主页数据"""
    url: str = ""
    username: str = ""
    full_name: str = ""
    bio: str = ""
    avatar: str = ""
    posts_count: str = "0"
    followers: str = "0"
    following: str = "0"
    external_url: str = ""
    is_verified: bool = False
    recent_posts: List[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  Instagram 用户主页",
            f"{'='*60}",
            f"  名称: {self.full_name}",
            f"  用户名: @{self.username}",
        ]
        if self.is_verified:
            lines.append(f"  认证: 已认证")
        lines.append(f"{'─'*60}")
        lines.append(f"  📸 帖子: {self.posts_count}")
        lines.append(f"  👥 粉丝: {self.followers}")
        lines.append(f"  📝 关注: {self.following}")
        if self.bio:
            lines.append(f"  简介: {self.bio[:200]}")
        if self.external_url:
            lines.append(f"  网站: {self.external_url}")
        if self.recent_posts:
            lines.append(f"  最新帖子: {len(self.recent_posts)} 条")
        lines.append(f"  链接: {self.url}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ──────────────────────────── 常量 ────────────────────────────

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

IG_PROFILE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9._]+)/?(?:\?.*)?$"
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
    d.ogUrl = getMeta('property', 'og:url');

    d.pageTitle = document.title || '';

    // Extract username from h2 (IG profile page puts username in h2)
    const h2 = document.querySelector('h2');
    d.h2Username = h2 ? h2.textContent.trim() : '';

    // Collect span texts
    const allSpans = document.querySelectorAll('span');
    const textItems = [];
    for (const span of allSpans) {
        const t = span.textContent.trim();
        if (t.length > 0 && t.length < 300) textItems.push(t);
    }

    // Full name — first span that looks like a display name
    d.fullName = '';
    for (const t of textItems) {
        if (t.length > 1 && t.length < 100 && t !== d.h2Username
            && !/^\d/.test(t) && !t.includes('post') && !t.includes('follow')
            && !t.includes('Log') && !t.includes('Sign')
            && !t.includes('more') && !t.includes('Instagram')) {
            d.fullName = t;
            break;
        }
    }

    // Posts / Followers / Following — match "N posts", "N followers", "N following"
    d.posts = '';
    d.followers = '';
    d.following = '';
    for (const t of textItems) {
        const m = t.match(/^([\d,.]+[KkMm]?)\s+(posts?|followers?|following)/i);
        if (m) {
            const val = m[1];
            const key = m[2].toLowerCase();
            if (key.startsWith('post') && !d.posts) d.posts = val;
            else if (key.startsWith('follower') && !d.followers) d.followers = val;
            else if (key === 'following' && !d.following) d.following = val;
        }
    }

    // Bio from description meta tag
    d.bio = '';
    const desc = d.description || '';
    const bioMatch = desc.match(/on Instagram:\s*"(.+)"$/s);
    if (bioMatch) {
        d.bio = bioMatch[1];
    }

    // Profile image — prefer header img or og:image
    d.profileImg = '';
    const headerImg = document.querySelector('header img[alt]');
    if (headerImg) {
        d.profileImg = headerImg.src || '';
    }

    // External URL from links
    d.externalUrl = '';
    const links = document.querySelectorAll('a[href]');
    for (const a of links) {
        const href = a.getAttribute('href') || '';
        if (href.includes('l.instagram.com') || href.includes('linktr.ee')
            || href.includes('bit.ly') || href.includes('pse.is')) {
            d.externalUrl = a.textContent.trim() || href;
            break;
        }
    }

    // Recent posts from links
    d.recentPosts = [];
    for (const a of links) {
        const href = a.getAttribute('href') || '';
        if (href.match(/\/p\/[A-Za-z0-9_-]+\/$/) || href.match(/\/reel\/[A-Za-z0-9_-]+\/$/)) {
            const alt = a.querySelector('img') ? (a.querySelector('img').alt || '') : '';
            const type = href.includes('/reel/') ? 'reel' : 'post';
            const postId = href.match(/\/(p|reel)\/([A-Za-z0-9_-]+)\//);
            d.recentPosts.push({
                url: 'https://www.instagram.com' + href,
                type: type,
                id: postId ? postId[2] : '',
                caption: alt.substring(0, 300)
            });
        }
    }

    // Post captions from h2 elements (IG renders post texts in h2)
    d.postCaptions = [];
    const h2s = document.querySelectorAll('h2');
    for (let i = 1; i < h2s.length && d.postCaptions.length < 10; i++) {
        const t = h2s[i].textContent.trim();
        if (t.length > 10 && t.length < 500) {
            d.postCaptions.push(t.substring(0, 300));
        }
    }

    return d;
})()
'''


# ──────────────────────────── 解析器 ────────────────────────────

class InstagramParser:
    """Instagram 主页解析器"""

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

    def parse_profile(self, url: str) -> InstagramProfileData:
        """解析 Instagram 主页"""
        result = InstagramProfileData(url=url)
        driver = None

        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url

            m = IG_PROFILE_RE.search(url)
            if m:
                result.username = m.group(1)

            logger.info(f"解析 Instagram 主页: {url}")
            driver = self._create_driver()

            try:
                driver.get(url)
            except Exception as e:
                logger.warning(f"页面加载异常: {type(e).__name__}")

            time.sleep(12)

            final_url = driver.current_url
            if "chrome-error" in final_url:
                result.error = "无法通过代理访问 Instagram（请检查代理配置）"
                return result

            if "/accounts/login" in final_url:
                result.error = "被重定向到登录页，可能需要登录"
                return result

            raw = driver.execute_script(EXTRACT_PROFILE_JS)
            if not raw:
                result.error = "JavaScript 提取返回空"
                return result

            # Username
            if raw.get("h2Username"):
                result.username = raw["h2Username"]

            # Full name — from og:title or first span
            og_title = raw.get("ogTitle", "")
            if og_title:
                name_match = re.match(r'^(.+?)\s*\(@\w+\)', og_title)
                if name_match:
                    result.full_name = name_match.group(1).strip()
                else:
                    result.full_name = og_title.split("•")[0].strip().split("(@")[0].strip()
            if not result.full_name and raw.get("fullName"):
                result.full_name = raw["fullName"]

            # Avatar
            result.avatar = raw.get("profileImg") or raw.get("ogImage", "")

            # Stats
            result.posts_count = raw.get("posts", "0") or "0"
            result.followers = raw.get("followers", "0") or "0"
            result.following = raw.get("following", "0") or "0"

            # Bio — from description meta
            if raw.get("bio"):
                result.bio = raw["bio"]
            else:
                desc = raw.get("description") or raw.get("ogDesc", "")
                result.bio = self._extract_bio(desc)

            # External URL
            result.external_url = raw.get("externalUrl", "")

            # Recent posts — merge link data with captions
            posts = raw.get("recentPosts", [])
            captions = raw.get("postCaptions", [])
            for i, post in enumerate(posts[:10]):
                if i < len(captions) and not post.get("caption"):
                    post["caption"] = captions[i]
            result.recent_posts = posts[:10]

            result.url = final_url
            logger.info(f"Instagram 解析完成: {result.full_name} (@{result.username})")

        except Exception as e:
            logger.error(f"Instagram 解析异常: {e}")
            result.error = str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return result

    def parse(self, url: str):
        """通用入口"""
        return self.parse_profile(url)

    @staticmethod
    def _extract_bio(desc: str) -> str:
        """从 meta description 中提取 bio"""
        if not desc:
            return ""
        # Format: "N Followers, N Following, N Posts - NAME on Instagram: "bio""
        bio_match = re.search(r'on Instagram:\s*["\u201c](.+?)["\u201d]\s*$', desc, re.DOTALL)
        if bio_match:
            return bio_match.group(1).strip()
        # Format: "N Followers, N Following, N Posts - See Instagram photos..."
        dash_match = re.search(r'Posts\s*-\s*(.+)$', desc)
        if dash_match:
            text = dash_match.group(1).strip()
            if text.startswith("See Instagram"):
                return ""
            return text
        return ""


# ──────────────────────────── CLI ────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Instagram 主页解析器")
    parser.add_argument("url", help="Instagram 主页链接")
    parser.add_argument("--chrome", default="/usr/bin/chromium-browser", help="Chrome 路径")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890", help="代理地址")
    parser.add_argument("--no-proxy", action="store_true", help="不使用代理")
    args = parser.parse_args()

    proxy = None if args.no_proxy else args.proxy
    ig = InstagramParser(headless=True, timeout=45, chrome_binary=args.chrome, proxy=proxy)
    data = ig.parse_profile(args.url)
    print(data.summary())
