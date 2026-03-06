"""
Facebook 解析服务（Selenium 版，通过 Clash 代理翻墙访问）
支持：
  用户主页链接 → 昵称、粉丝、关注、简介、头像、最新帖子
"""
import re
import json
import time
import argparse
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional

logger = logging.getLogger("facebook_parser")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ──────────────────────────── 数据模型 ────────────────────────────

@dataclass
class FacebookProfileData:
    """Facebook 用户主页数据"""
    url: str = ""
    fb_id: str = ""
    name: str = ""
    alt_name: str = ""
    bio: str = ""
    category: str = ""
    followers: str = "0"
    following: str = "0"
    likes: str = "0"
    talking_about: str = "0"
    website: str = ""
    avatar: str = ""
    cover: str = ""
    intro_items: List[str] = field(default_factory=list)
    recent_posts: List[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  Facebook 用户主页",
            f"{'='*60}",
            f"  名称: {self.name}",
        ]
        if self.alt_name:
            lines.append(f"  别名: {self.alt_name}")
        if self.category:
            lines.append(f"  类型: {self.category}")
        lines.append(f"{'─'*60}")
        lines.append(f"  👥 粉丝: {self.followers}")
        lines.append(f"  📝 关注: {self.following}")
        if self.likes != "0":
            lines.append(f"  ❤️ 获赞: {self.likes}")
        if self.talking_about != "0":
            lines.append(f"  💬 讨论: {self.talking_about}")
        if self.bio:
            lines.append(f"  简介: {self.bio[:150]}")
        if self.website:
            lines.append(f"  网站: {self.website}")
        if self.intro_items:
            lines.append(f"  信息:")
            for item in self.intro_items[:5]:
                lines.append(f"    · {item}")
        lines.append(f"  链接: {self.url}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ──────────────────────────── 常量 ────────────────────────────

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

FB_PROFILE_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?facebook\.com/([A-Za-z0-9._-]+)(?:/|\?|$)"
)

EXTRACT_PROFILE_JS = r'''
return (() => {
    const d = {};

    // 1) Meta tags — most reliable source
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
    const iosUrl = getMeta('property', 'al:ios:url');
    d.fbId = iosUrl ? iosUrl.replace('fb://profile/', '') : '';

    // 2) Page title
    d.pageTitle = document.title || '';

    // 3) Walk all visible text nodes for profile data
    const allSpans = document.querySelectorAll('span');
    const textItems = [];
    for (const span of allSpans) {
        const t = span.textContent.trim();
        if (t.length > 0 && t.length < 200) textItems.push(t);
    }

    // Find name from first h1
    const h1 = document.querySelector('h1');
    d.h1Name = h1 ? h1.textContent.trim() : '';

    // Find followers/following
    d.followers = '';
    d.following = '';
    d.likes = '';
    d.talkingAbout = '';
    for (let i = 0; i < textItems.length; i++) {
        const t = textItems[i];
        const tl = t.toLowerCase();
        // Match "902 followers", "541 following", "902 likes"
        const numMatch = t.match(/^([\d,.]+[KkMm]?)\s*(followers?|following|likes?|talking about this)/i);
        if (numMatch) {
            const val = numMatch[1];
            const key = numMatch[2].toLowerCase();
            if (key.startsWith('follower') && !d.followers) d.followers = val;
            else if (key === 'following' && !d.following) d.following = val;
            else if (key.startsWith('like') && !d.likes) d.likes = val;
            else if (key.includes('talking') && !d.talkingAbout) d.talkingAbout = val;
            continue;
        }
        // Match split format: "902" then "followers" as separate spans
        if (/^[\d,.]+[KkMm]?$/.test(t) && i < textItems.length - 1) {
            const next = textItems[i + 1].toLowerCase().trim();
            if ((next === 'followers' || next === 'follower') && !d.followers) d.followers = t;
            else if (next === 'following' && !d.following) d.following = t;
            else if ((next === 'likes' || next === 'like') && !d.likes) d.likes = t;
        }
    }

    // Alt name (in parentheses after main name)
    d.altName = '';
    for (const t of textItems) {
        if (/^\(.+\)$/.test(t) && t.length < 60) {
            d.altName = t.replace(/^\(/, '').replace(/\)$/, '');
            break;
        }
    }

    // Category (e.g. "Digital creator", "Public figure")
    d.category = '';
    const categoryKeywords = ['creator', 'figure', 'artist', 'musician', 'brand', 'company',
        'restaurant', 'organization', 'community', 'blogger', 'gamer', 'coach', 'writer'];
    for (const t of textItems) {
        const tl = t.toLowerCase();
        if (t.length < 60 && t.length > 3 && !t.includes('http') && !t.includes('.com')
            && categoryKeywords.some(kw => tl.includes(kw))) {
            const clean = t.replace(/^Profile\s*·?\s*/i, '').trim();
            if (clean && !clean.toLowerCase().includes('profile') && !clean.toLowerCase().includes('page')) {
                d.category = clean;
                break;
            }
        }
    }

    // Intro items
    d.introItems = [];
    let inIntro = false;
    for (const t of textItems) {
        if (t === 'Intro') { inIntro = true; continue; }
        if (inIntro) {
            if (['Photos', 'Friends', 'Videos', 'Reels', 'See all photos', 'Posts'].includes(t)) break;
            if (t.length > 2 && t.length < 200 && !t.startsWith('{')) {
                d.introItems.push(t);
            }
        }
    }

    // Websites from links
    d.websites = [];
    const links = document.querySelectorAll('a[href]');
    for (const a of links) {
        const href = a.getAttribute('href') || '';
        const text = a.textContent.trim();
        if (href.includes('l.facebook.com/l.php') || 
            (text.length > 5 && text.length < 100 && /^https?:\/\//.test(text) && !text.includes('facebook.com'))) {
            d.websites.push(text);
        }
    }

    // Recent posts
    d.posts = [];
    const postElements = document.querySelectorAll('[data-ad-rendering-role="story_message"], [data-ad-comet-preview="message"]');
    for (const el of postElements) {
        const text = el.textContent.trim();
        if (text.length > 5) d.posts.push(text.substring(0, 300));
    }
    // Fallback: look for "See more" pattern
    if (d.posts.length === 0) {
        const seeMore = textItems.filter(t => t === 'See more');
        for (let i = 0; i < textItems.length && d.posts.length < 3; i++) {
            const t = textItems[i];
            if (t.length > 30 && t.length < 500 && !t.startsWith('{') && !t.startsWith('//')) {
                d.posts.push(t.substring(0, 300));
            }
        }
    }

    // Parse og:description for likes count
    if (d.ogDesc) {
        const likeMatch = d.ogDesc.match(/([\d,.]+)\s*likes?/i);
        if (likeMatch && !d.likes) d.likes = likeMatch[1];
        const talkMatch = d.ogDesc.match(/([\d,.]+)\s*talking\s+about\s+this/i);
        if (talkMatch && !d.talkingAbout) d.talkingAbout = talkMatch[1];
    }

    return d;
})()
'''


# ──────────────────────────── 解析器 ────────────────────────────

class FacebookParser:
    """Facebook 主页解析器"""

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

    def parse_profile(self, url: str) -> FacebookProfileData:
        """解析 Facebook 主页"""
        result = FacebookProfileData(url=url)
        driver = None

        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url

            # Extract profile ID from URL
            m = FB_PROFILE_RE.search(url)
            if m:
                result.fb_id = m.group(1)

            logger.info(f"解析 Facebook 主页: {url}")
            driver = self._create_driver()

            try:
                driver.get(url)
            except Exception as e:
                logger.warning(f"页面加载异常: {type(e).__name__}")

            time.sleep(10)

            final_url = driver.current_url
            if "chrome-error" in final_url:
                result.error = "无法通过代理访问 Facebook（请检查代理配置）"
                return result

            # Close login popup if present
            try:
                driver.execute_script("""
                    const btn = document.querySelector('[aria-label="Close"]')
                        || document.querySelector('[data-testid="royal_close_button"]');
                    if (btn) btn.click();
                """)
                time.sleep(1)
            except Exception:
                pass

            # Extract data via JS
            raw = driver.execute_script(EXTRACT_PROFILE_JS)
            if not raw:
                result.error = "JavaScript 提取返回空"
                return result

            # Fill result
            result.name = raw.get("h1Name") or raw.get("ogTitle", "").replace(" | Facebook", "")
            result.alt_name = raw.get("altName", "")
            result.category = raw.get("category", "")
            result.avatar = raw.get("ogImage", "")

            # Parse description for bio
            desc = raw.get("ogDesc") or raw.get("description", "")
            result.bio = self._extract_bio(desc, result.name)

            # Followers / following / likes
            result.followers = raw.get("followers", "0") or "0"
            result.following = raw.get("following", "0") or "0"
            result.likes = raw.get("likes", "0") or "0"
            result.talking_about = raw.get("talkingAbout", "0") or "0"

            # FB ID
            if raw.get("fbId"):
                result.fb_id = raw["fbId"]

            # Intro items
            result.intro_items = raw.get("introItems", [])

            # Website
            websites = raw.get("websites", [])
            if websites:
                result.website = websites[0]

            # Posts
            posts = raw.get("posts", [])
            result.recent_posts = [{"content": p} for p in posts[:5]]

            result.url = final_url
            logger.info(f"Facebook 解析完成: {result.name}")

        except Exception as e:
            logger.error(f"Facebook 解析异常: {e}")
            result.error = str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return result

    def parse(self, url: str):
        """通用入口（目前只支持主页）"""
        return self.parse_profile(url)

    @staticmethod
    def _extract_bio(desc: str, name: str) -> str:
        """从 og:description 中提取简介（去掉 likes/talking about 前缀）"""
        if not desc:
            return ""
        bio = desc
        # Remove "Name. 902 likes · 14 talking about this. " prefix
        # Handle various name formats (with non-breaking spaces, alt names)
        clean_name = re.escape(name.split("(")[0].strip().replace("\xa0", " "))
        pattern = re.compile(
            rf'^.{{0,5}}{clean_name}\.?\s*'
            r'[\d,.]+[KkMm]?\s*likes?\s*·?\s*'
            r'(?:[\d,.]+[KkMm]?\s*talking\s+about\s+this\.?\s*)?',
            re.IGNORECASE
        )
        bio = pattern.sub('', bio).strip()
        if not bio:
            bio = desc
        return bio


# ──────────────────────────── CLI ────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Facebook 主页解析器")
    parser.add_argument("url", help="Facebook 主页链接")
    parser.add_argument("--chrome", default="/usr/bin/chromium-browser", help="Chrome 路径")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890", help="代理地址")
    parser.add_argument("--no-proxy", action="store_true", help="不使用代理")
    args = parser.parse_args()

    proxy = None if args.no_proxy else args.proxy
    fb = FacebookParser(headless=True, timeout=45, chrome_binary=args.chrome, proxy=proxy)
    data = fb.parse_profile(args.url)
    print(data.summary())
