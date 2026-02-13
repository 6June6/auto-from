#!/usr/bin/env python3
"""
清理数据库中的无效引用
当名片、用户等文档被删除后，相关的引用可能会失效，导致访问时抛出 DoesNotExist 异常
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import init_database, CardEditRequest, Card, User
from mongoengine.errors import DoesNotExist


def check_and_fix_card_edit_requests():
    """检查并修复 CardEditRequest 中的无效引用"""
    print("=" * 60)
    print("检查 CardEditRequest 中的无效引用")
    print("=" * 60)
    
    all_requests = CardEditRequest.objects.all()
    total = all_requests.count()
    print(f"\n📊 总计 {total} 条审核记录")
    
    invalid_card_refs = []
    invalid_user_refs = []
    invalid_admin_refs = []
    
    print("\n🔍 正在检查...")
    for i, req in enumerate(all_requests, 1):
        if i % 10 == 0:
            print(f"  进度: {i}/{total}")
        
        # 检查 card 引用
        try:
            if req.card:
                _ = req.card.name  # 尝试访问属性
        except DoesNotExist:
            invalid_card_refs.append(str(req.id))
        
        # 检查 user 引用
        try:
            if req.user:
                _ = req.user.username
        except DoesNotExist:
            invalid_user_refs.append(str(req.id))
        
        # 检查 admin 引用
        try:
            if req.admin:
                _ = req.admin.username
        except DoesNotExist:
            invalid_admin_refs.append(str(req.id))
    
    print("\n" + "-" * 60)
    print("📊 检查结果:")
    print(f"  ❌ 无效的 card 引用: {len(invalid_card_refs)} 个")
    print(f"  ❌ 无效的 user 引用: {len(invalid_user_refs)} 个")
    print(f"  ❌ 无效的 admin 引用: {len(invalid_admin_refs)} 个")
    
    if invalid_card_refs:
        print("\n无效 card 引用的记录 ID:")
        for req_id in invalid_card_refs[:10]:  # 只显示前10个
            print(f"  - {req_id}")
        if len(invalid_card_refs) > 10:
            print(f"  ... 还有 {len(invalid_card_refs) - 10} 个")
    
    # 询问是否删除
    if invalid_card_refs or invalid_user_refs or invalid_admin_refs:
        print("\n" + "=" * 60)
        print("⚠️ 建议处理方式:")
        print("1. 保留这些记录（已添加异常处理，不会影响使用）")
        print("2. 删除这些记录（彻底清理）")
        print("-" * 60)
        
        choice = input("\n是否删除包含无效引用的记录？(y/n): ").strip().lower()
        
        if choice == 'y':
            delete_count = 0
            
            # 删除无效引用的记录
            all_invalid = set(invalid_card_refs + invalid_user_refs + invalid_admin_refs)
            for req_id in all_invalid:
                try:
                    req = CardEditRequest.objects.get(id=req_id)
                    req.delete()
                    delete_count += 1
                except Exception as e:
                    print(f"  ❌ 删除 {req_id} 失败: {e}")
            
            print(f"\n✅ 已删除 {delete_count} 条无效记录")
        else:
            print("\n✅ 已跳过删除，记录已保留")
    else:
        print("\n✅ 所有引用都有效，无需清理")
    
    return len(invalid_card_refs), len(invalid_user_refs), len(invalid_admin_refs)


def check_database_integrity():
    """检查数据库完整性"""
    print("\n" + "=" * 60)
    print("数据库完整性检查")
    print("=" * 60)
    
    card_count = Card.objects.count()
    user_count = User.objects.count()
    request_count = CardEditRequest.objects.count()
    
    print(f"\n📊 数据统计:")
    print(f"  名片总数: {card_count}")
    print(f"  用户总数: {user_count}")
    print(f"  审核记录总数: {request_count}")


def main():
    """主函数"""
    print("🔧 正在连接数据库...")
    if not init_database():
        print("❌ 数据库连接失败")
        return 1
    print("✅ 数据库连接成功\n")
    
    # 检查数据库完整性
    check_database_integrity()
    
    # 检查并修复无效引用
    invalid_cards, invalid_users, invalid_admins = check_and_fix_card_edit_requests()
    
    print("\n" + "=" * 60)
    print("🎉 检查完成")
    print("=" * 60)
    
    if invalid_cards + invalid_users + invalid_admins == 0:
        print("\n✅ 数据库状态良好，无需修复")
        return 0
    else:
        print("\n💡 提示: 已为所有引用访问添加异常处理，不会影响系统使用")
        return 0


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
