"""
Threads 解析服务（Selenium 版，通过 Clash 代理翻墙访问）
支持：
  用户主页链接 → 昵称、用户名、粉丝、帖子数、简介、头像、标签、最新帖子
  帖子链接     → 作者、正文、标签、浏览量、互动数据、评论、图片
"""
import re
import time
import argparse
import logging
from dataclasses import dataclass, asdict, field
from typing import List

logger = logging.getLogger("threads_parser")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ──────────────────────────── 数据模型 ────────────────────────────

@dataclass
class ThreadsProfileData:
    """Threads 用户主页数据"""
    url: str = ""
    username: str = ""
    full_name: str = ""
    bio: str = ""
    avatar: str = ""
    followers: str = "0"
    threads_count: str = "0"
    tags: List[str] = field(default_factory=list)
    website: str = ""
    instagram_url: str = ""
    recent_posts: List[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  Threads 用户主页",
            f"{'='*60}",
            f"  名称: {self.full_name}",
            f"  用户名: @{self.username}",
            f"{'─'*60}",
            f"  👥 粉丝: {self.followers}",
            f"  📝 帖子: {self.threads_count}",
        ]
        if self.bio:
            lines.append(f"  简介: {self.bio[:200]}")
        if self.tags:
            lines.append(f"  标签: {', '.join(self.tags)}")
        if self.website:
            lines.append(f"  网站: {self.website}")
        if self.instagram_url:
            lines.append(f"  IG: {self.instagram_url}")
        if self.recent_posts:
            lines.append(f"  最新帖子: {len(self.recent_posts)} 条")
        lines.append(f"  链接: {self.url}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


@dataclass
class ThreadsPostData:
    """Threads 帖子数据"""
    url: str = ""
    post_id: str = ""
    author_username: str = ""
    author_name: str = ""
    author_avatar: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    image: str = ""
    views: str = "0"
    likes: str = "0"
    replies: str = "0"
    reposts: str = "0"
    shares: str = "0"
    publish_time: str = ""
    comments: List[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  Threads 帖子",
            f"{'='*60}",
            f"  作者: {self.author_name} (@{self.author_username})",
        ]
        if self.content:
            lines.append(f"  内容: {self.content[:200]}")
        lines.append(f"{'─'*60}")
        lines.append(f"  👁 浏览: {self.views}")
        lines.append(f"  ❤️ 点赞: {self.likes}")
        lines.append(f"  💬 回复: {self.replies}")
        lines.append(f"  🔄 转发: {self.reposts}")
        if self.tags:
            lines.append(f"  标签: {', '.join(self.tags)}")
        if self.publish_time:
            lines.append(f"  时间: {self.publish_time}")
        if self.comments:
            lines.append(f"  评论: {len(self.comments)} 条")
        lines.append(f"  链接: {self.url}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ──────────────────────────── 常量 ────────────────────────────

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

THREADS_PROFILE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?threads\.(?:com|net)/@([A-Za-z0-9._]+)/?(?:\?.*)?$"
)

THREADS_POST_RE = re.compile(
    r"(?:https?://)?(?:www\.)?threads\.(?:com|net)/@([A-Za-z0-9._]+)/post/([A-Za-z0-9_-]+)"
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
    d.ogUrl = getMeta('property', 'og:url');
    d.description = getMeta('name', 'description');

    d.pageTitle = document.title || '';

    // h1 elements — Threads puts username and full name in h1
    d.h1Texts = [];
    document.querySelectorAll('h1').forEach(h => {
        const t = h.textContent.trim();
        if (t) d.h1Texts.push(t);
    });

    // Collect span texts
    const allSpans = document.querySelectorAll('span');
    const textItems = [];
    for (const span of allSpans) {
        const t = span.textContent.trim();
        if (t.length > 0 && t.length < 300) textItems.push(t);
    }

    // Followers — match "N followers"
    d.followers = '';
    for (const t of textItems) {
        const m = t.match(/^([\d,.]+[KkMm]?)\s+followers?/i);
        if (m) { d.followers = m[1]; break; }
    }

    // Bio — from span (usually span[4] area, the one with multi-line text)
    d.bio = '';
    for (const t of textItems) {
        if (t.length > 15 && t.includes('\n') && !t.includes('Log in')
            && !t.includes('Sorry') && !t.includes('Learn more')) {
            d.bio = t;
            break;
        }
    }

    // Tags from links
    d.tags = [];
    document.querySelectorAll('a[href*="serp_type=tags"]').forEach(a => {
        const t = a.textContent.trim();
        if (t && !d.tags.includes(t)) d.tags.push(t);
    });

    // External website
    d.website = '';
    d.instagramUrl = '';
    document.querySelectorAll('a[href*="l.threads.com"]').forEach(a => {
        const href = a.getAttribute('href') || '';
        const text = a.textContent.trim();
        const uMatch = href.match(/u=([^&]+)/);
        const decodedUrl = uMatch ? decodeURIComponent(uMatch[1]) : '';
        if (text === 'Instagram' && decodedUrl.includes('instagram.com')) {
            d.instagramUrl = decodedUrl;
        } else if (text.length > 3 && text.length < 100
            && !text.includes('Learn') && !text.includes('Policy')
            && !text.includes('Terms') && !text.includes('Cookies')
            && !decodedUrl.includes('facebook.com/help')
            && !decodedUrl.includes('help.instagram.com')) {
            if (!d.website) d.website = text;
        }
    });

    // Profile picture
    d.profileImg = '';
    const imgs = document.querySelectorAll('img[alt*="profile picture"]');
    if (imgs.length > 0) d.profileImg = imgs[0].src || '';

    // Recent posts from links
    d.recentPosts = [];
    const seenPosts = new Set();
    document.querySelectorAll('a[href*="/post/"]').forEach(a => {
        const href = a.getAttribute('href') || '';
        const postMatch = href.match(/\/@([^/]+)\/post\/([A-Za-z0-9_-]+)/);
        if (postMatch && !seenPosts.has(postMatch[2])) {
            seenPosts.add(postMatch[2]);
            d.recentPosts.push({
                url: 'https://www.threads.com' + href,
                id: postMatch[2],
                author: postMatch[1]
            });
        }
    });

    // Post content from spans — long text blocks after username mentions
    d.postTexts = [];
    let foundUsername = false;
    for (let i = 0; i < textItems.length; i++) {
        const t = textItems[i];
        // Skip profile header area
        if (t === 'Threads' && i > 10) foundUsername = true;
        if (foundUsername && t.length > 20 && t.length < 500
            && !t.includes('Log in') && !t.includes('Sorry')
            && !t.includes('Learn more') && !t.includes('followers')) {
            d.postTexts.push(t.substring(0, 300));
        }
    }

    return d;
})()
'''


EXTRACT_POST_JS = r'''
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
    d.ogUrl = getMeta('property', 'og:url');
    d.description = getMeta('name', 'description');
    d.pageTitle = document.title || '';

    // Collect spans
    const allSpans = document.querySelectorAll('span');
    const textItems = [];
    for (const span of allSpans) {
        const t = span.textContent.trim();
        if (t.length > 0 && t.length < 500) textItems.push(t);
    }

    // Author username from links
    d.authorUsername = '';
    const authorLink = document.querySelector('a[href*="/@"]');
    if (authorLink) {
        const m = authorLink.getAttribute('href').match(/\/@([A-Za-z0-9._]+)$/);
        if (m) d.authorUsername = m[1];
    }

    // Views
    d.views = '';
    for (const t of textItems) {
        const m = t.match(/^([\d,.]+[KkMm]?)\s+views?$/i);
        if (m) { d.views = m[1]; break; }
    }

    // Post content — long text blocks (the main post, not comments)
    d.contentParts = [];
    let foundAuthor = false;
    for (let i = 0; i < textItems.length; i++) {
        const t = textItems[i];
        if (t === d.authorUsername && !foundAuthor) { foundAuthor = true; continue; }
        if (foundAuthor && t.length > 10 && !t.includes('views')
            && !t.includes('Sorry') && !t.includes('Learn more')
            && !t.includes('Log in') && !t.includes('Translate')
            && t !== d.authorUsername) {
            d.contentParts.push(t);
            // Stop after getting the main content (before interaction numbers)
            if (d.contentParts.length >= 2) break;
        }
    }

    // Interaction numbers — deduplicated sequence after content
    // Threads renders each number twice; pattern: likes, replies, reposts, shares
    d.interactions = [];
    let seenContent = false;
    let lastNum = null;
    for (let i = 0; i < textItems.length; i++) {
        const t = textItems[i];
        if (t === 'Translate' || (t.length > 50 && seenContent === false)) {
            seenContent = true;
            continue;
        }
        if (seenContent && /^\d+$/.test(t) && parseInt(t) < 100000) {
            if (t === lastNum) { lastNum = null; continue; } // skip duplicate
            d.interactions.push(t);
            lastNum = t;
            if (d.interactions.length >= 4) break;
        }
        if (seenContent && t.length > 10 && !/^\d+$/.test(t)) {
            // Hit next comment/section, stop
            if (d.interactions.length >= 2) break;
        }
    }

    // Tags from links
    d.tags = [];
    document.querySelectorAll('a[href*="serp_type=tags"]').forEach(a => {
        const t = a.textContent.trim();
        if (t && !d.tags.includes(t)) d.tags.push(t);
    });

    // Publish time from <time> elements
    d.publishTime = '';
    const timeEl = document.querySelector('time[datetime]');
    if (timeEl) d.publishTime = timeEl.getAttribute('datetime') || '';

    // Author avatar
    d.authorAvatar = '';
    const avatarImg = document.querySelector('img[alt*="profile picture"]');
    if (avatarImg) d.authorAvatar = avatarImg.src || '';

    // Comments — find start of comment section (after main post interaction numbers)
    d.comments = [];
    const dateRe = /^\d{2}\/\d{2}\/\d{2}$/;
    const timeRe = /^\d+[dhm]$/;
    // Find comment section start: after 8+ consecutive number spans
    let commentStart = -1;
    let numRunLen = 0;
    for (let i = 0; i < textItems.length; i++) {
        if (/^\d+$/.test(textItems[i]) && parseInt(textItems[i]) < 100000) {
            numRunLen++;
            if (numRunLen >= 8) commentStart = i + 1;
        } else {
            numRunLen = 0;
        }
    }

    if (commentStart > 0) {
        // Gather post links to identify comment authors and their post IDs
        const postLinks = document.querySelectorAll('a[href*="/post/"]');
        const mainPostId = (d.ogUrl || '').match(/\/post\/([A-Za-z0-9_-]+)/);
        const mainId = mainPostId ? mainPostId[1] : '';
        const commentOrder = [];
        const seenIds = new Set();
        for (const a of postLinks) {
            const href = a.getAttribute('href') || '';
            const pm = href.match(/\/@([^/]+)\/post\/([A-Za-z0-9_-]+)/);
            if (!pm || pm[2] === mainId || seenIds.has(pm[2])) continue;
            seenIds.add(pm[2]);
            commentOrder.push(pm[1]); // author usernames in order
        }

        // Walk spans from commentStart, matching author→content pairs
        let ci = 0;
        for (let i = commentStart; i < textItems.length && ci < commentOrder.length; i++) {
            const t = textItems[i];
            if (t === commentOrder[ci]) {
                // Found the author, now search forward for content
                for (let j = i + 1; j < Math.min(i + 10, textItems.length); j++) {
                    const ct = textItems[j];
                    if (ct === commentOrder[ci] || dateRe.test(ct) || timeRe.test(ct)
                        || ct === '·' || ct === 'Author' || ct === 'Translate'
                        || /^\d+$/.test(ct)) continue;
                    if (ct.length >= 2 && !ct.startsWith('Log ')
                        && !ct.startsWith('See ') && !ct.startsWith('Continue')) {
                        const content = ct.replace(/\s*Translate$/, '').trim();
                        if (content) {
                            d.comments.push({ author: commentOrder[ci], content: content });
                        }
                        ci++;
                        i = j; // jump past this content
                        break;
                    }
                }
            }
        }
    }

    return d;
})()
'''


# ──────────────────────────── 解析器 ────────────────────────────

class ThreadsParser:
    """Threads 主页 & 帖子解析器"""

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

    def parse_profile(self, url: str) -> ThreadsProfileData:
        """解析 Threads 主页"""
        result = ThreadsProfileData(url=url)
        driver = None

        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url

            m = THREADS_PROFILE_RE.search(url)
            if m:
                result.username = m.group(1)

            logger.info(f"解析 Threads 主页: {url}")
            driver = self._create_driver()

            try:
                driver.get(url)
            except Exception as e:
                logger.warning(f"页面加载异常: {type(e).__name__}")

            time.sleep(12)

            final_url = driver.current_url
            if "chrome-error" in final_url:
                result.error = "无法通过代理访问 Threads（请检查代理配置）"
                return result

            raw = driver.execute_script(EXTRACT_PROFILE_JS)
            if not raw:
                result.error = "JavaScript 提取返回空"
                return result

            # Username — from h1 or URL
            h1_texts = raw.get("h1Texts", [])
            if h1_texts:
                result.username = h1_texts[0]

            # Full name — from og:title or second h1
            og_title = raw.get("ogTitle", "")
            if og_title:
                name_match = re.match(r'^(.+?)\s*\(@\w+\)', og_title)
                if name_match:
                    result.full_name = name_match.group(1).strip()
            if not result.full_name and len(h1_texts) > 1:
                result.full_name = h1_texts[1]

            # Avatar
            result.avatar = raw.get("profileImg") or raw.get("ogImage", "")

            # Followers & threads count — from og:description
            og_desc = raw.get("ogDesc") or raw.get("description", "")
            followers_match = re.search(r'([\d,.]+[KkMm]?)\s+Followers?', og_desc, re.IGNORECASE)
            if followers_match:
                result.followers = followers_match.group(1)
            if raw.get("followers"):
                result.followers = raw["followers"]

            threads_match = re.search(r'([\d,.]+)\s+Threads?', og_desc, re.IGNORECASE)
            if threads_match:
                result.threads_count = threads_match.group(1)

            # Bio — from description meta, strip header
            result.bio = self._extract_bio(og_desc)
            if raw.get("bio") and len(raw["bio"]) > len(result.bio):
                result.bio = raw["bio"]

            # Tags
            result.tags = raw.get("tags", [])

            # Website & Instagram
            result.website = raw.get("website", "")
            result.instagram_url = raw.get("instagramUrl", "")

            # Recent posts — merge link data with post texts
            posts = raw.get("recentPosts", [])
            post_texts = raw.get("postTexts", [])
            for i, post in enumerate(posts[:10]):
                if i < len(post_texts):
                    post["content"] = post_texts[i]
            result.recent_posts = posts[:10]

            result.url = final_url
            logger.info(f"Threads 解析完成: {result.full_name} (@{result.username})")

        except Exception as e:
            logger.error(f"Threads 解析异常: {e}")
            result.error = str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return result

    def parse_post(self, url: str) -> ThreadsPostData:
        """解析 Threads 帖子"""
        result = ThreadsPostData(url=url)
        driver = None

        try:
            url = url.strip()
            if not url.startswith("http"):
                url = "https://" + url
            # 去除查询参数，保持干净的 post URL
            url = re.sub(r'\?.*$', '', url)

            m = THREADS_POST_RE.search(url)
            if m:
                result.author_username = m.group(1)
                result.post_id = m.group(2)

            logger.info(f"解析 Threads 帖子: {url}")
            driver = self._create_driver()

            try:
                driver.get(url)
            except Exception as e:
                logger.warning(f"页面加载异常: {type(e).__name__}")

            time.sleep(12)

            final_url = driver.current_url
            if "chrome-error" in final_url:
                result.error = "无法通过代理访问 Threads（请检查代理配置）"
                return result

            raw = driver.execute_script(EXTRACT_POST_JS)
            if not raw:
                result.error = "JavaScript 提取返回空"
                return result

            # Author
            result.author_username = raw.get("authorUsername") or result.author_username
            og_title = raw.get("ogTitle", "")
            if og_title:
                name_match = re.match(r'^(.+?)\s*\(@\w+\)', og_title)
                if name_match:
                    result.author_name = name_match.group(1).strip()

            result.author_avatar = raw.get("authorAvatar", "")

            # Content — from og:description (most complete) or spans
            og_desc = raw.get("ogDesc") or raw.get("description", "")
            content_parts = raw.get("contentParts", [])
            result.content = og_desc if og_desc else "\n".join(content_parts)

            # Image
            result.image = raw.get("ogImage", "")

            # Views
            result.views = raw.get("views", "0") or "0"

            # Interactions: likes, replies, reposts, shares
            interactions = raw.get("interactions", [])
            if len(interactions) >= 1:
                result.likes = interactions[0]
            if len(interactions) >= 2:
                result.replies = interactions[1]
            if len(interactions) >= 3:
                result.reposts = interactions[2]
            if len(interactions) >= 4:
                result.shares = interactions[3]

            # Tags
            result.tags = raw.get("tags", [])

            # Publish time
            result.publish_time = raw.get("publishTime", "")

            # Comments
            result.comments = raw.get("comments", [])[:10]

            result.url = final_url
            logger.info(f"Threads 帖子解析完成: @{result.author_username} / {result.post_id}")

        except Exception as e:
            logger.error(f"Threads 帖子解析异常: {e}")
            result.error = str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return result

    def parse(self, url: str):
        """通用入口：自动识别主页 or 帖子"""
        if THREADS_POST_RE.search(url):
            return self.parse_post(url)
        return self.parse_profile(url)

    @staticmethod
    def _extract_bio(desc: str) -> str:
        """从 og:description 中提取 bio"""
        if not desc:
            return ""
        # Format: "88 Followers • 7 Threads • bio text. See the latest..."
        parts = desc.split("•")
        if len(parts) >= 3:
            bio_part = "•".join(parts[2:]).strip()
            bio_part = re.sub(r'\.\s*See the latest.*$', '', bio_part).strip()
            return bio_part
        # Fallback: remove "N Followers ... N Threads ... " prefix
        bio = re.sub(r'^[\d,.]+[KkMm]?\s+Followers?\s*•?\s*[\d,.]+\s+Threads?\s*•?\s*', '', desc, flags=re.IGNORECASE).strip()
        bio = re.sub(r'\.\s*See the latest.*$', '', bio).strip()
        return bio if bio != desc else ""


# ──────────────────────────── CLI ────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Threads 主页解析器")
    parser.add_argument("url", help="Threads 主页链接")
    parser.add_argument("--chrome", default="/usr/bin/chromium-browser", help="Chrome 路径")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890", help="代理地址")
    parser.add_argument("--no-proxy", action="store_true", help="不使用代理")
    args = parser.parse_args()

    proxy = None if args.no_proxy else args.proxy
    th = ThreadsParser(headless=True, timeout=45, chrome_binary=args.chrome, proxy=proxy)
    data = th.parse_profile(args.url)
    print(data.summary())
