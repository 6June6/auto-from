#!/usr/bin/env python3
"""
报名工具 Token 迁移脚本
将本地 JSON 文件中的 Token 迁移到 MongoDB 数据库
"""

import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import init_database, BaomingToken, Card


def migrate_tokens():
    """从本地文件迁移 Token 到数据库"""
    print("=" * 60)
    print("🔄 报名工具 Token 迁移工具")
    print("=" * 60)
    
    # 本地文件路径
    home = Path.home()
    token_file = home / '.auto-form-filler' / 'baoming_tokens.json'
    
    if not token_file.exists():
        print("\n❌ 未找到本地 Token 文件")
        print(f"   路径: {token_file}")
        print("   无需迁移")
        return
    
    print(f"\n📂 找到本地 Token 文件: {token_file}")
    
    # 读取本地文件
    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            all_tokens = json.load(f)
    except Exception as e:
        print(f"\n❌ 读取文件失败: {e}")
        return
    
    print(f"📊 发现 {len(all_tokens)} 个 Token 记录\n")
    
    if len(all_tokens) == 0:
        print("✅ 文件为空，无需迁移")
        return
    
    # 显示 Token 列表
    print("Token 列表:")
    print("-" * 60)
    for i, (key, token_data) in enumerate(all_tokens.items(), 1):
        card_id = key[5:] if key.startswith('card_') else key
        uname = token_data.get('uname', '未知')
        save_time = token_data.get('_save_time', 0)
        save_date = datetime.fromtimestamp(save_time).strftime('%Y-%m-%d %H:%M:%S') if save_time else '未知'
        print(f"  {i}. Card ID: {card_id[:8]}... | 用户: {uname} | 保存: {save_date}")
    print("-" * 60)
    
    # 询问是否继续
    response = input("\n是否开始迁移？(y/n): ")
    if response.lower() != 'y':
        print("❌ 取消迁移")
        return
    
    print("\n开始迁移...")
    print("-" * 60)
    
    migrated = 0
    skipped = 0
    failed = 0
    
    for key, token_data in all_tokens.items():
        try:
            # 提取 card_id
            if not key.startswith('card_'):
                print(f"  ⚠️ 跳过无效的 Key: {key}")
                skipped += 1
                continue
                
            card_id = key[5:]  # 去掉 "card_" 前缀
            
            # 查找名片
            try:
                card = Card.objects(id=card_id).first()
            except Exception as e:
                print(f"  ❌ 查询名片失败 [{card_id[:8]}...]: {e}")
                failed += 1
                continue
            
            if not card:
                print(f"  ⚠️ 名片不存在，跳过: {card_id[:8]}...")
                skipped += 1
                continue
            
            # 检查是否已存在
            existing = BaomingToken.objects(card=card).first()
            if existing:
                print(f"  ⏭️ Token 已存在，跳过: {card.name}")
                skipped += 1
                continue
            
            # 创建新记录
            save_time = token_data.get('_save_time', time.time())
            token_record = BaomingToken(
                card=card,
                access_token=token_data.get('access_token', ''),
                uname=token_data.get('uname', ''),
                pic=token_data.get('pic', ''),
                unionid=token_data.get('unionid', ''),
                created_at=datetime.fromtimestamp(save_time)
            )
            token_record.save()
            
            print(f"  ✅ 迁移成功: {card.name} (用户: {token_data.get('uname', '未知')})")
            migrated += 1
            
        except Exception as e:
            print(f"  ❌ 迁移失败: {key} - {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("-" * 60)
    print(f"\n📊 迁移统计:")
    print(f"   ✅ 成功: {migrated} 个")
    print(f"   ⏭️ 跳过: {skipped} 个")
    print(f"   ❌ 失败: {failed} 个")
    print(f"   📝 总计: {len(all_tokens)} 个")
    
    # 询问是否删除本地文件
    if migrated > 0:
        print("\n" + "=" * 60)
        response = input("是否删除本地 Token 文件？(y/n): ")
        if response.lower() == 'y':
            try:
                # 先备份
                backup_file = token_file.with_suffix('.json.bak')
                token_file.rename(backup_file)
                print(f"✅ 已备份到: {backup_file}")
                print(f"✅ 迁移完成！")
            except Exception as e:
                print(f"⚠️ 备份失败: {e}")
                print(f"💡 请手动删除: {token_file}")
        else:
            print("✅ 保留本地文件")
            print(f"💡 如需删除，请手动删除: {token_file}")
    
    print("\n" + "=" * 60)
    print("🎉 迁移流程完成！")
    print("=" * 60)


def verify_migration():
    """验证迁移结果"""
    print("\n" + "=" * 60)
    print("🔍 验证迁移结果")
    print("=" * 60)
    
    try:
        total_tokens = BaomingToken.objects.count()
        print(f"\n📊 数据库中共有 {total_tokens} 个 Token 记录")
        
        if total_tokens > 0:
            print("\n最近的 Token 记录:")
            print("-" * 60)
            recent_tokens = BaomingToken.objects.order_by('-updated_at').limit(5)
            for i, token in enumerate(recent_tokens, 1):
                print(f"  {i}. 名片: {token.card.name}")
                print(f"     用户: {token.uname}")
                print(f"     Token: {token.access_token[:20]}...")
                print(f"     更新时间: {token.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            print("-" * 60)
        
        print("\n✅ 验证完成")
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    # 初始化数据库
    print("🔧 正在连接数据库...")
    if not init_database():
        print("❌ 数据库连接失败，无法继续")
        return 1
    
    print("✅ 数据库连接成功\n")
    
    # 执行迁移
    migrate_tokens()
    
    # 验证结果
    verify_migration()
    
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
