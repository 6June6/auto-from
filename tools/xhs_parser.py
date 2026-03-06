"""
小红书笔记数据解析服务
支持解析小红书链接中的：标题、点赞数、收藏数、评论数等
使用 Playwright 模拟移动端浏览器渲染页面后提取数据
"""
import sys
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


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


class XhsParser:
    """小红书笔记解析器（移动端模式）"""

    MOBILE_UA = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    )

    SHORT_LINK_PATTERN = re.compile(r"(?:https?://)?xhslink\.com/\S+")

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout

    def _ensure_playwright(self):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError(
                "Playwright 未安装，请运行:\n"
                "  pip install playwright && playwright install chromium"
            )

    def _create_mobile_context(self, browser):
        return browser.new_context(
            user_agent=self.MOBILE_UA,
            viewport={"width": 390, "height": 844},
            locale="zh-CN",
            is_mobile=True,
        )

    def _resolve_short_link_via_browser(self, page, short_url: str) -> str:
        """通过浏览器跟随重定向解析短链接"""
        if not short_url.startswith("http"):
            short_url = "https://" + short_url
        try:
            page.goto(short_url, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(3000)
            return page.url
        except Exception:
            return short_url

    def _extract_note_id(self, url: str) -> str:
        patterns = [
            r"/(?:explore|discovery/item)/([a-f0-9]{24})",
            r"note_id=([a-f0-9]{24})",
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return ""

    def _extract_data_from_mobile_page(self, page) -> dict:
        """从移动端渲染页面的 DOM 中提取笔记数据"""
        return page.evaluate(r'''() => {
            const result = {
                title: "",
                author: "",
                content: "",
                likes: "0",
                collects: "0",
                comments: "0",
                publishTime: "",
                tags: []
            };

            // --- 标题 ---
            const titleEl = document.querySelector('.content-container .title')
                || document.querySelector('.note-title')
                || document.querySelector('h1');
            if (titleEl) {
                result.title = titleEl.textContent.trim();
            }
            if (!result.title) {
                const pt = document.title.replace(/ - 小红书$/, '').trim();
                if (pt && pt !== '小红书') result.title = pt;
            }

            // --- 作者 ---
            const authorSelectors = [
                '.author-username', '.author-name', '.author-detail',
                '.note-author', '.user-name', '.nickname'
            ];
            for (const sel of authorSelectors) {
                const el = document.querySelector(sel);
                if (el) {
                    const t = el.textContent.trim();
                    if (t) { result.author = t; break; }
                }
            }

            // --- 内容 ---
            const contentEl = document.querySelector('.content-container .desc')
                || document.querySelector('.note-desc')
                || document.querySelector('.content-text');
            if (contentEl) {
                result.content = contentEl.textContent.trim();
            }
            if (!result.content) {
                const container = document.querySelector('.content-container');
                if (container) {
                    const unfold = container.querySelector('.unfold-container');
                    if (unfold) {
                        result.content = unfold.textContent.trim();
                        if (result.title && result.content.startsWith(result.title)) {
                            result.content = result.content.slice(result.title.length).trim();
                        }
                        // 去掉 "展开全文" 前缀
                        result.content = result.content.replace(/^展开全文/, '').trim();
                    }
                }
            }

            // --- 互动数据（底部 action bar）---
            const actionButtons = document.querySelectorAll(
                '.action-buttons .action-button'
            );
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

            // 如果 action bar 没拿到，尝试从评论区头部获取评论数
            if (result.comments === "0") {
                const commentCountEl = document.querySelector('.comment-count');
                if (commentCountEl) {
                    const m = commentCountEl.textContent.match(/(\d+)/);
                    if (m) result.comments = m[1];
                }
            }

            // --- 发布时间 ---
            const dateSelectors = [
                '.note-date', '.publish-date', '.date',
                '[class*="date"]', '[class*="time"]'
            ];
            for (const sel of dateSelectors) {
                const el = document.querySelector(sel);
                if (el) {
                    const t = el.textContent.trim();
                    if (t && t.length < 50) { result.publishTime = t; break; }
                }
            }

            // --- 标签 ---
            const tagEls = document.querySelectorAll(
                'a.tag, [class*="tag"] a, a[href*="search_result"]'
            );
            for (const el of tagEls) {
                const t = el.textContent.trim().replace(/^#/, '');
                if (t && !result.tags.includes(t)) result.tags.push(t);
            }

            return result;
        }''')

    def parse(self, url: str) -> XhsNoteData:
        """解析小红书链接，返回笔记数据"""
        self._ensure_playwright()

        data = XhsNoteData(url=url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = self._create_mobile_context(browser)
            page = context.new_page()

            try:
                if self.SHORT_LINK_PATTERN.match(url.replace("https://", "").replace("http://", "")):
                    print(f"[*] 解析短链接: {url}")
                    actual_url = self._resolve_short_link_via_browser(page, url)
                    print(f"[*] 实际地址: {actual_url}")
                    data.url = actual_url
                else:
                    if not url.startswith("http"):
                        url = "https://" + url
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                    data.url = url

                page.wait_for_timeout(5000)

                data.note_id = self._extract_note_id(data.url)

                raw = self._extract_data_from_mobile_page(page)

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
            finally:
                browser.close()

        return data


def main():
    ap = argparse.ArgumentParser(description="小红书笔记数据解析工具")
    ap.add_argument("url", help="小红书笔记链接（支持短链接）")
    ap.add_argument("--no-headless", action="store_true", help="显示浏览器窗口（调试用）")
    ap.add_argument("--timeout", type=int, default=30000, help="页面加载超时（毫秒）")
    ap.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = ap.parse_args()

    parser = XhsParser(headless=not args.no_headless, timeout=args.timeout)
    result = parser.parse(args.url)

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(result.summary())

    if result.error:
        print(f"\n⚠️  警告: {result.error}")


if __name__ == "__main__":
    main()
