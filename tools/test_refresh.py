#!/usr/bin/env python3
"""
测试 Token 刷新功能

运行前确保：
1. MongoDB 已启动
2. 数据库中有至少一个 Token
3. Token 是有效的
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import init_database, BaomingToken, Card
from core.baoming_tool_filler import BaomingToolAPI
from datetime import datetime


def test_database_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试 1: 数据库连接")
    print("-" * 60)
    
    if not init_database():
        print("❌ 数据库连接失败")
        return False
    
    print("✅ 数据库连接成功")
    return True


def test_token_exists():
    """测试是否有 Token"""
    print("\n" + "=" * 60)
    print("测试 2: 检查 Token")
    print("-" * 60)
    
    count = BaomingToken.objects.count()
    print(f"📊 数据库中有 {count} 个 Token")
    
    if count == 0:
        print("⚠️ 没有 Token，请先登录报名工具")
        return False
    
    print("\n最近的 Token:")
    for token in BaomingToken.objects.order_by('-updated_at').limit(3):
        card = token.card
        print(f"  - 名片: {card.name}")
        print(f"    用户: {token.uname}")
        print(f"    最后使用: {token.last_used.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    print("✅ 找到 Token")
    return True


def test_refresh_single_token():
    """测试刷新单个 Token"""
    print("=" * 60)
    print("测试 3: 刷新单个 Token")
    print("-" * 60)
    
    # 获取第一个 Token
    token = BaomingToken.objects.order_by('-updated_at').first()
    if not token:
        print("❌ 没有可测试的 Token")
        return False
    
    card = token.card
    old_last_used = token.last_used
    
    print(f"测试 Token: 名片 '{card.name}'")
    print(f"旧的最后使用时间: {old_last_used.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建 API 实例
    api = BaomingToolAPI()
    api.access_token = token.access_token
    api.eid = "69844bcf8eaa2449c7a37fae"  # 测试用的 eid
    
    print("\n调用 get_enroll_detail 接口...")
    success, msg, info_id = api.get_enroll_detail()
    
    if success or '未找到已有报名记录' in msg:
        print("✅ Token 有效")
        
        # 更新最后使用时间
        token.last_used = datetime.now()
        token.save()
        
        new_last_used = token.last_used
        print(f"新的最后使用时间: {new_last_used.strftime('%Y-%m-%d %H:%M:%S')}")
        print("✅ 刷新成功")
        return True
    else:
        print(f"❌ Token 无效: {msg}")
        return False


def test_cleanup():
    """测试清理功能"""
    print("\n" + "=" * 60)
    print("测试 4: 清理功能（不执行真实删除）")
    print("-" * 60)
    
    from datetime import timedelta
    
    # 查找 30 天未使用的 Token
    cutoff_date = datetime.now() - timedelta(days=30)
    old_tokens = BaomingToken.objects(last_used__lt=cutoff_date)
    count = old_tokens.count()
    
    print(f"📊 发现 {count} 个 30 天未使用的 Token")
    
    if count > 0:
        print("Token 列表:")
        for token in old_tokens.limit(5):
            card = token.card
            days_ago = (datetime.now() - token.last_used).days
            print(f"  - {card.name}: {days_ago} 天前")
        
        print("\n⚠️ 这些 Token 会被清理")
        print("（本测试不会真实删除）")
    else:
        print("✅ 没有需要清理的 Token")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print(" " * 20 + "Token 刷新功能测试")
    print("=" * 70 + "\n")
    
    tests = [
        ("数据库连接", test_database_connection),
        ("Token 存在性", test_token_exists),
        ("单个 Token 刷新", test_refresh_single_token),
        ("清理功能", test_cleanup)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 显示测试结果
    print("\n" + "=" * 70)
    print("测试结果总结")
    print("=" * 70)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("-" * 70)
    print(f"总计: {passed}/{total} 个测试通过")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 所有测试通过！可以开始使用刷新功能")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查配置")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
