"""
链接工具函数
从 gui/link_manager.py 提取的纯工具函数，无 GUI 依赖，可安全在服务端使用。
"""
import re

SUPPORTED_DOMAINS = [
    "docs.qq.com",       # 腾讯文档
    "wj.qq.com",         # 腾讯问卷
    "shimo.im",          # 石墨文档
    "wjx.cn",            # 问卷星
    "wjx.top",           # 问卷星
    "jsj.top",           # 金数据
    "jinshuju.net",      # 金数据
    "feishu.cn",         # 飞书
    "kdocs.cn",          # 金山文档/WPS
    "wps.cn",            # 金山文档/WPS
    "wps.com",           # 金山文档/WPS
    "wenjuan.com",       # 问卷网
    "baominggongju.com", # 报名工具
    "fanqier.cn",        # 番茄表单
    "credamo.com",       # 见数
    "mikecrm.com",       # 麦客表单
    "mike-x.com",        # 麦客企业版
]


def is_supported_platform(url: str) -> bool:
    """检查链接是否为支持的平台"""
    return any(domain in url for domain in SUPPORTED_DOMAINS)


def extract_urls(text: str) -> list:
    """从文本中提取所有 URL（去重）"""
    url_pattern = r'https?://[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=%]+'
    seen = set()
    urls = []
    for m in re.finditer(url_pattern, text):
        url = m.group()
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls
