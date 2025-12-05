#!/usr/bin/env python3
"""
MongoDB 数据库连接测试脚本
"""
import sys
from database import init_database, DatabaseManager, Card, Link, FillRecord


def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("🧪 MongoDB 数据库连接测试")
    print("=" * 60)
    
    # 1. 测试连接
    print("\n1️⃣ 测试数据库连接...")
    if not init_database():
        print("❌ 数据库连接失败！")
        return False
    print("✅ 数据库连接成功")
    
    # 2. 测试统计信息
    print("\n2️⃣ 测试统计信息...")
    try:
        stats = DatabaseManager.get_statistics()
        print(f"  📊 统计数据:")
        print(f"     - 名片总数: {stats['total_cards']}")
        print(f"     - 链接总数: {stats['total_links']}")
        print(f"     - 填写记录: {stats['total_records']}")
        print(f"     - 成功次数: {stats['success_records']}")
        print(f"     - 激活链接: {stats['active_links']}")
        print("✅ 统计信息获取成功")
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")
        return False
    
    # 3. 测试名片查询
    print("\n3️⃣ 测试名片查询...")
    try:
        cards = DatabaseManager.get_all_cards()
        print(f"  📇 找到 {len(cards)} 个名片")
        if cards:
            for i, card in enumerate(cards, 1):
                print(f"     {i}. {card.name} - {len(card.configs)} 个配置项")
        print("✅ 名片查询成功")
    except Exception as e:
        print(f"❌ 名片查询失败: {e}")
        return False
    
    # 4. 测试链接查询
    print("\n4️⃣ 测试链接查询...")
    try:
        links = DatabaseManager.get_all_links()
        print(f"  🔗 找到 {len(links)} 个链接")
        if links:
            for i, link in enumerate(links, 1):
                print(f"     {i}. {link.name} - {link.status}")
        print("✅ 链接查询成功")
    except Exception as e:
        print(f"❌ 链接查询失败: {e}")
        return False
    
    # 5. 测试创建名片
    print("\n5️⃣ 测试创建名片...")
    try:
        test_card = DatabaseManager.create_card(
            name="测试名片",
            configs=[
                {'key': '测试字段1', 'value': '测试值1'},
                {'key': '测试字段2', 'value': '测试值2'}
            ],
            description="这是一个测试名片"
        )
        print(f"  ✅ 创建成功: {test_card.name} (ID: {test_card.id})")
        
        # 删除测试数据
        DatabaseManager.delete_card(str(test_card.id))
        print(f"  🗑️  测试数据已清理")
        
    except Exception as e:
        print(f"❌ 创建名片失败: {e}")
        return False
    
    # 6. 测试创建链接
    print("\n6️⃣ 测试创建链接...")
    try:
        test_link = DatabaseManager.create_link(
            name="测试链接",
            url="https://test.example.com",
            status="active",
            category="测试"
        )
        print(f"  ✅ 创建成功: {test_link.name} (ID: {test_link.id})")
        
        # 删除测试数据
        DatabaseManager.delete_link(str(test_link.id))
        print(f"  🗑️  测试数据已清理")
        
    except Exception as e:
        print(f"❌ 创建链接失败: {e}")
        return False
    
    # 7. 测试填写记录
    print("\n7️⃣ 测试填写记录查询...")
    try:
        records = DatabaseManager.get_fill_records(limit=5)
        print(f"  📝 找到 {len(records)} 条填写记录")
        if records:
            for i, record in enumerate(records, 1):
                print(f"     {i}. {record.card.name} → {record.link.name} "
                      f"({record.fill_count}/{record.total_count})")
        print("✅ 填写记录查询成功")
    except Exception as e:
        print(f"❌ 填写记录查询失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！数据库工作正常")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

