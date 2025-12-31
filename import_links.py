#!/usr/bin/env python3
"""
批量导入问卷链接到数据库
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import init_database, Link, User
from database.db_manager import DatabaseManager

# 要导入的链接列表
LINKS_TO_IMPORT = [
    {
        "name": "问卷星表单",
        "url": "https://v.wjx.cn/vm/ru9AZMK.aspx#",
        "category": "问卷星",
        "description": "问卷星平台问卷"
    },
    {
        "name": "麦克CRM表单",
        "url": "http://bhoecbx1g5buqxtr.mikecrm.com/rcPL6KH",
        "category": "麦客CRM",
        "description": "麦客CRM平台表单"
    },
    {
        "name": "金数据表单",
        "url": "https://jsj.top/f/BON1ss",
        "category": "金数据",
        "description": "金数据平台表单"
    },
    {
        "name": "石墨文档表单",
        "url": "https://shimo.im/forms/m5kvddaoOBUK703X/fill",
        "category": "石墨文档",
        "description": "石墨文档平台表单"
    },
    {
        "name": "见数问卷",
        "url": "https://www.credamo.com/s/FvyUNzano/",
        "category": "见数",
        "description": "见数平台问卷"
    },
    {
        "name": "问卷网表单",
        "url": "https://www.wenjuan.com/s/UZBZJv4upY0/#",
        "category": "问卷网",
        "description": "问卷网平台问卷"
    },
    {
        "name": "番茄表单",
        "url": "https://gb0yca.fanqier.cn/f/k8rrb4we",
        "category": "番茄表单",
        "description": "番茄表单平台"
    },
    {
        "name": "飞书问卷",
        "url": "https://fcnf7djnyx0n.feishu.cn/share/base/form/shrcnDZXAGx2j3R8tJd94Y5CXKE",
        "category": "飞书",
        "description": "飞书问卷平台"
    },
    {
        "name": "WPS表单",
        "url": "https://f.kdocs.cn/g/yFivJzz4/",
        "category": "WPS",
        "description": "WPS金山文档表单"
    },
    {
        "name": "报名工具表单",
        "url": "https://p.baominggongju.com/share?eid=6927663044ba23c204b48c55",
        "category": "报名工具",
        "description": "报名工具平台"
    },
    {
        "name": "腾讯文档表单",
        "url": "https://docs.qq.com/form/page/DRkV4aE92THRhaWhs",
        "category": "腾讯文档",
        "description": "腾讯文档平台表单"
    },
    {
        "name": "腾讯问卷",
        "url": "https://wj.qq.com/s2/25017966/e30d/",
        "category": "腾讯问卷",
        "description": "腾讯问卷平台"
    },
]


def import_links():
    """导入链接到数据库"""
    print("=" * 50)
    print("🚀 开始导入问卷链接...")
    print("=" * 50)
    
    # 初始化数据库连接
    if not init_database():
        print("❌ 数据库连接失败，无法导入")
        return False
    
    # 获取 user 用户（如果不存在则使用 admin）
    user = User.objects(username='user').first()
    if not user:
        print("⚠️ 未找到 'user' 用户，尝试使用 admin 用户")
        user = User.objects(username='admin').first()
        if not user:
            print("❌ 未找到任何用户，无法导入")
            return False
    
    print(f"📌 将链接关联到用户: {user.username}")
    print("-" * 50)
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for link_data in LINKS_TO_IMPORT:
        try:
            # 检查是否已存在相同URL的链接
            existing_link = Link.objects(url=link_data['url']).first()
            if existing_link:
                print(f"⏭️  跳过（已存在）: {link_data['name']}")
                skip_count += 1
                continue
            
            # 创建新链接
            link = DatabaseManager.create_link(
                name=link_data['name'],
                url=link_data['url'],
                status='active',
                category=link_data.get('category', '其他'),
                description=link_data.get('description', '')
            )
            
            print(f"✅ 导入成功: {link_data['name']} [{link_data['category']}]")
            success_count += 1
            
        except Exception as e:
            print(f"❌ 导入失败: {link_data['name']} - {e}")
            error_count += 1
    
    print("-" * 50)
    print(f"📊 导入统计:")
    print(f"   ✅ 成功: {success_count}")
    print(f"   ⏭️  跳过: {skip_count}")
    print(f"   ❌ 失败: {error_count}")
    print("=" * 50)
    
    return success_count > 0


if __name__ == "__main__":
    import_links()















