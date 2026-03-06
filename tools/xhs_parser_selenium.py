"""
小红书解析服务（Selenium 版，兼容 CentOS 7）
支持：
  1. 笔记链接 → 标题、点赞、收藏、评论
  2. 用户主页链接 → 昵称、简介、粉丝、获赞与收藏、笔记列表
"""
import re
import json
import time
import argparse
import logging
from dataclasses import dataclass, asdict, field
from typing import List

logger = logging.getLogger("xhs_parser")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ──────────────────────────── 数据模型 ────────────────────────────

@dataclass
class XhsNoteData:
    """小红书笔记数据"""
    url: str = ""
    title: str = ""
    author: str = ""
    likes: str = "0"
    collects: str = "0"
    comments: str = "0"
    content: str = ""
    note_id: str = ""
    publish_time: str = ""
    tags: list = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  小红书笔记数据",
            f"{'='*60}",
            f"  标题: {self.title}",
            f"  作者: {self.author}",
            f"  笔记ID: {self.note_id}",
            f"  发布时间: {self.publish_time}",
            f"{'─'*60}",
            f"  👍 点赞: {self.likes}",
            f"  ⭐ 收藏: {self.collects}",
            f"  💬 评论: {self.comments}",
            f"{'─'*60}",
            f"  链接: {self.url}",
        ]
        if self.content:
            preview = self.content[:200] + ("..." if len(self.content) > 200 else "")
            lines.append(f"  内容: {preview}")
        if self.tags:
            lines.append(f"  标签: {', '.join(self.tags)}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


@dataclass
class XhsProfileData:
    """小红书用户主页数据"""
    url: str = ""
    user_id: str = ""
    xhs_id: str = ""
    nickname: str = ""
    bio: str = ""
    following: str = "0"
    followers: str = "0"
    likes_and_collects: str = "0"
    avatar: str = ""
    notes: List[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  小红书用户主页",
            f"{'='*60}",
            f"  昵称: {self.nickname}",
            f"  小红书ID: {self.xhs_id}",
            f"  用户ID: {self.user_id}",
            f"  简介: {self.bio}",
            f"{'─'*60}",
            f"  📝 关注: {self.following}",
            f"  👥 粉丝: {self.followers}",
            f"  🔥 获赞与收藏: {self.likes_and_collects}",
            f"{'─'*60}",
            f"  链接: {self.url}",
        ]
        if self.notes:
            lines.append(f"  笔记列表 (共 {len(self.notes)} 条):")
            for i, note in enumerate(self.notes, 1):
                title = note.get("title", "")[:40]
                likes = note.get("likes", "0")
                lines.append(f"    {i}. {title}  👍{likes}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ──────────────────────────── 常量 ────────────────────────────

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

SHORT_LINK_RE = re.compile(r"(?:https?://)?xhslink\.com/\S+")
PROFILE_URL_RE = re.compile(r"xiaohongshu\.com/user/profile/([a-f0-9]+)")

# 笔记页面 JS 提取脚本
EXTRACT_NOTE_JS = r'''
return (() => {
    const result = {
        title: "", author: "", content: "",
        likes: "0", collects: "0", comments: "0",
        publishTime: "", tags: []
    };

    const titleEl = document.querySelector('.content-container .title')
        || document.querySelector('.note-title')
        || document.querySelector('h1');
    if (titleEl) result.title = titleEl.textContent.trim();
    if (!result.title) {
        const pt = document.title.replace(/ - (小红书|rednote)$/i, '').trim();
        if (pt && pt !== '小红书') result.title = pt;
    }

    const authorSels = [
        '.author-username', '.author-name', '.author-detail',
        '.note-author', '.user-name', '.nickname'
    ];
    for (const sel of authorSels) {
        const el = document.querySelector(sel);
        if (el) { const t = el.textContent.trim(); if (t) { result.author = t; break; } }
    }

    const contentEl = document.querySelector('.content-container .desc')
        || document.querySelector('.note-desc')
        || document.querySelector('.content-text');
    if (contentEl) result.content = contentEl.textContent.trim();
    if (!result.content) {
        const container = document.querySelector('.content-container');
        if (container) {
            const unfold = container.querySelector('.unfold-container');
            if (unfold) {
                result.content = unfold.textContent.trim();
                if (result.title && result.content.startsWith(result.title))
                    result.content = result.content.slice(result.title.length).trim();
                result.content = result.content.replace(/^展开全文/, '').trim();
            }
        }
    }

    const actionButtons = document.querySelectorAll('.action-buttons .action-button');
    if (actionButtons.length >= 3) {
        const getText = (el) => {
            const strong = el.querySelector('strong');
            if (strong) return strong.textContent.trim();
            const span = el.querySelector('span');
            if (span) return span.textContent.trim();
            return el.textContent.trim();
        };
        result.likes = getText(actionButtons[0]) || "0";
        result.collects = getText(actionButtons[1]) || "0";
        result.comments = getText(actionButtons[2]) || "0";
    }

    if (result.comments === "0") {
        const ccEl = document.querySelector('.comment-count');
        if (ccEl) { const m = ccEl.textContent.match(/(\d+)/); if (m) result.comments = m[1]; }
    }

    const dateSels = ['.note-date', '.publish-date', '.date', '[class*="date"]', '[class*="time"]'];
    for (const sel of dateSels) {
        const el = document.querySelector(sel);
        if (el) { const t = el.textContent.trim(); if (t && t.length < 50) { result.publishTime = t; break; } }
    }

    const tagEls = document.querySelectorAll('a.tag, [class*="tag"] a, a[href*="search_result"]');
    for (const el of tagEls) {
        const t = el.textContent.trim().replace(/^#/, '');
        if (t && !result.tags.includes(t)) result.tags.push(t);
    }

    return result;
})()
'''

# 主页 JS 提取脚本
EXTRACT_PROFILE_JS = r'''
return (() => {
    const result = {
        nickname: "",
        xhsId: "",
        bio: "",
        following: "0",
        followers: "0",
        likesAndCollects: "0",
        avatar: "",
        notes: []
    };

    // 昵称
    const nameEl = document.querySelector('.user-name');
    if (nameEl) result.nickname = nameEl.textContent.trim();
    if (!result.nickname) {
        const pt = document.title.replace(/@/, '').replace(/'s profile page/i, '').trim();
        if (pt) result.nickname = pt;
    }

    // 小红书 ID
    const nameBox = document.querySelector('.user-name-box, .user-card-center');
    if (nameBox) {
        const text = nameBox.textContent;
        const idMatch = text.match(/(?:rednote ID|小红书号)[:\s]*(\S+)/i);
        if (idMatch) result.xhsId = idMatch[1];
    }

    // 简介
    const descEl = document.querySelector('.desc-text');
    if (descEl) result.bio = descEl.textContent.trim();

    // 头像
    const avatarEl = document.querySelector('.user-avatar img, .avatar img, [class*="avatar"] img');
    if (avatarEl) result.avatar = avatarEl.src || "";

    // 关注 / 粉丝 / 获赞与收藏
    const followsNum = document.querySelector('.follows .num');
    if (followsNum) result.following = followsNum.textContent.trim();

    const fansNum = document.querySelector('.fans .num');
    if (fansNum) result.followers = fansNum.textContent.trim();

    const likedNum = document.querySelector('.liked .num');
    if (likedNum) result.likesAndCollects = likedNum.textContent.trim();

    // 笔记列表
    const noteCards = document.querySelectorAll('.reds-note-card, [class*="note-card"]');
    for (const card of noteCards) {
        const titleEl = card.querySelector('.reds-note-card-title, [class*="title"]');
        const likeEl = card.querySelector('.reds-note-like-text, [class*="like"] strong');
        const imgEl = card.querySelector('img');
        const userEl = card.querySelector('.reds-note-user');

        const title = titleEl ? titleEl.textContent.trim() : "";
        if (!title) continue;

        result.notes.push({
            title: title,
            likes: likeEl ? likeEl.textContent.trim() : "0",
            cover: imgEl ? imgEl.src : "",
            author: userEl ? userEl.textContent.trim() : ""
        });
    }

    return result;
})()
'''


# ──────────────────────────── 解析器 ────────────────────────────

class XhsParser:
    """小红书解析器（Selenium 版，兼容 CentOS 7）"""

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
        opts.add_argument("--window-size=390,844")

        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(self.timeout)
        driver.implicitly_wait(5)
        return driver

    def _resolve_url(self, driver, url: str) -> str:
        """加载 URL 并返回最终地址（处理短链接重定向）"""
        if not url.startswith("http"):
            url = "https://" + url
        driver.get(url)
        if SHORT_LINK_RE.match(url.replace("https://", "").replace("http://", "")):
            logger.info(f"解析短链接: {url}")
            time.sleep(4)
            final = driver.current_url
            logger.info(f"实际地址: {final}")
            return final
        return url

    def _is_profile_url(self, url: str) -> bool:
        return bool(PROFILE_URL_RE.search(url))

    def _extract_user_id(self, url: str) -> str:
        m = PROFILE_URL_RE.search(url)
        return m.group(1) if m else ""

    def _extract_note_id(self, url: str) -> str:
        for p in [r"/(?:explore|discovery/item)/([a-f0-9]{24})", r"note_id=([a-f0-9]{24})"]:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return ""

    # ── 笔记解析 ──

    def parse_note(self, url: str) -> XhsNoteData:
        """解析小红书笔记链接"""
        data = XhsNoteData(url=url)
        driver = None
        try:
            driver = self._create_driver()
            data.url = self._resolve_url(driver, url)
            time.sleep(5)
            data.note_id = self._extract_note_id(data.url)
            raw = driver.execute_script(EXTRACT_NOTE_JS)
            data.title = raw.get("title", "")
            data.author = raw.get("author", "")
            data.content = raw.get("content", "")
            data.likes = raw.get("likes", "0")
            data.collects = raw.get("collects", "0")
            data.comments = raw.get("comments", "0")
            data.publish_time = raw.get("publishTime", "")
            data.tags = raw.get("tags", [])
        except Exception as e:
            data.error = f"解析失败: {str(e)}"
            logger.error(f"笔记解析失败: {e}")
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
        return data

    # ── 主页解析 ──

    def parse_profile(self, url: str) -> XhsProfileData:
        """解析小红书用户主页链接"""
        data = XhsProfileData(url=url)
        driver = None
        try:
            driver = self._create_driver()
            data.url = self._resolve_url(driver, url)
            time.sleep(5)
            data.user_id = self._extract_user_id(data.url)
            raw = driver.execute_script(EXTRACT_PROFILE_JS)
            data.nickname = raw.get("nickname", "")
            data.xhs_id = raw.get("xhsId", "")
            data.bio = raw.get("bio", "")
            data.following = raw.get("following", "0")
            data.followers = raw.get("followers", "0")
            data.likes_and_collects = raw.get("likesAndCollects", "0")
            data.avatar = raw.get("avatar", "")
            data.notes = raw.get("notes", [])
        except Exception as e:
            data.error = f"解析失败: {str(e)}"
            logger.error(f"主页解析失败: {e}")
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
        return data

    # ── 自动识别 ──

    def parse(self, url: str):
        """自动识别链接类型并解析（笔记 or 主页）"""
        if not url.startswith("http"):
            url = "https://" + url

        # 先判断已知的完整链接
        if self._is_profile_url(url):
            return self.parse_profile(url)
        if self._extract_note_id(url):
            return self.parse_note(url)

        # 短链接需要先解析真实 URL 再判断
        if SHORT_LINK_RE.match(url.replace("https://", "").replace("http://", "")):
            driver = None
            try:
                driver = self._create_driver()
                real_url = self._resolve_url(driver, url)
            except Exception:
                real_url = url
            finally:
                if driver:
                    try: driver.quit()
                    except Exception: pass

            if self._is_profile_url(real_url):
                return self.parse_profile(real_url)
            return self.parse_note(real_url)

        return self.parse_note(url)


# ──────────────────────────── CLI ────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="小红书解析工具（笔记 + 主页）")
    ap.add_argument("url", help="小红书链接（笔记/主页，支持短链接）")
    ap.add_argument("--type", choices=["note", "profile", "auto"], default="auto",
                    help="指定解析类型，默认自动识别")
    ap.add_argument("--no-headless", action="store_true", help="显示浏览器窗口")
    ap.add_argument("--timeout", type=int, default=30, help="页面加载超时（秒）")
    ap.add_argument("--chrome-binary", default=None, help="Chrome 可执行文件路径")
    ap.add_argument("--json", action="store_true", help="JSON 格式输出")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = XhsParser(
        headless=not args.no_headless,
        timeout=args.timeout,
        chrome_binary=args.chrome_binary,
    )

    if args.type == "note":
        result = parser.parse_note(args.url)
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
