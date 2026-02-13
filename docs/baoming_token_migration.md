# 报名工具 Token 数据库存储迁移

## 概述

将报名工具的登录 Token 从本地 JSON 文件存储迁移到 MongoDB 数据库存储。

## 改动内容

### 1. 数据库模型新增

**文件**: `database/models.py`

新增 `BaomingToken` 模型：

```python
class BaomingToken(Document):
    """报名工具 Token 模型"""
    card = ReferenceField(Card, required=True)  # 关联名片
    access_token = StringField(required=True)    # 访问令牌
    uname = StringField(max_length=100)          # 用户昵称
    pic = StringField()                          # 用户头像URL
    unionid = StringField(max_length=100)        # 微信 unionid
    created_at = DateTimeField(default=datetime.now)  # 创建时间
    updated_at = DateTimeField(default=datetime.now)  # 更新时间
    last_used = DateTimeField(default=datetime.now)   # 最后使用时间
```

**字段说明**:
- `card`: 关联的名片（外键）
- `access_token`: 报名工具的访问令牌
- `uname`: 登录用户的微信昵称
- `pic`: 登录用户的微信头像URL
- `unionid`: 微信 unionid（唯一标识）
- `created_at`: Token 首次创建时间
- `updated_at`: Token 最后更新时间
- `last_used`: Token 最后使用时间

**索引**:
- `card`: 用于快速查找某个名片的 Token
- `unionid`: 用于通过 unionid 查找
- `-updated_at`: 按更新时间倒序排列

### 2. Token 管理逻辑修改

**文件**: `core/baoming_tool_filler.py`

#### 修改前（本地文件存储）
```python
# 存储路径
~/.auto-form-filler/baoming_tokens.json

# 存储格式
{
  "card_69830fb551c6db84fb459e01": {
    "access_token": "96888568c67d417585ef...",
    "uname": "用户昵称",
    "pic": "头像URL",
    "unionid": "odVL41Lt9CE5Pn0oKMLbeXGBN0-4",
    "_save_time": 1739168438.123
  }
}
```

#### 修改后（数据库存储）
```python
# 存储位置
MongoDB 数据库 > baoming_tokens 集合

# 存储格式
{
  "_id": ObjectId("..."),
  "card": ObjectId("69830fb551c6db84fb459e01"),
  "access_token": "96888568c67d417585ef...",
  "uname": "用户昵称",
  "pic": "头像URL",
  "unionid": "odVL41Lt9CE5Pn0oKMLbeXGBN0-4",
  "created_at": ISODate("2024-02-10T15:20:38.123Z"),
  "updated_at": ISODate("2024-02-10T15:20:38.123Z"),
  "last_used": ISODate("2024-02-10T15:20:38.123Z")
}
```

#### 改动的方法

1. **`_save_token(user_data: Dict)`** - 保存 Token
   - 旧逻辑：写入 JSON 文件
   - 新逻辑：保存到数据库，支持新增/更新

2. **`_load_token() -> Optional[Dict]`** - 加载 Token
   - 旧逻辑：从 JSON 文件读取
   - 新逻辑：从数据库查询，并更新 `last_used` 时间

3. **`_clear_token()`** - 清空 Token
   - 旧逻辑：从 JSON 文件删除
   - 新逻辑：从数据库删除记录

4. **删除的方法**
   - `_get_token_file_path()` - 不再需要
   - `_get_storage_key()` - 不再需要

## 优势对比

### 旧方案（本地文件）的问题
1. ❌ 单机存储，无法跨设备共享
2. ❌ 文件可能被意外删除或损坏
3. ❌ 无法记录使用历史
4. ❌ 无法进行数据分析和管理
5. ❌ 并发读写可能导致数据冲突

### 新方案（数据库）的优势
1. ✅ 支持多设备共享 Token
2. ✅ 数据安全，自动备份
3. ✅ 记录创建、更新、使用时间
4. ✅ 支持管理员统一管理
5. ✅ 支持批量操作和数据分析
6. ✅ 数据库事务保证一致性

## 数据迁移

### 自动迁移

系统会在首次使用时自动从本地文件迁移到数据库：

1. 检查本地文件是否存在: `~/.auto-form-filler/baoming_tokens.json`
2. 如果存在，读取所有 Token
3. 遍历每个 Token，保存到数据库
4. 迁移完成后，可选择删除本地文件

### 手动迁移脚本

如果需要手动迁移，可以运行以下脚本：

```python
# tools/migrate_baoming_tokens.py

from pathlib import Path
import json
from database.models import BaomingToken, Card
from datetime import datetime

def migrate_tokens():
    """从本地文件迁移 Token 到数据库"""
    # 本地文件路径
    home = Path.home()
    token_file = home / '.auto-form-filler' / 'baoming_tokens.json'
    
    if not token_file.exists():
        print("未找到本地 Token 文件，无需迁移")
        return
    
    # 读取本地文件
    with open(token_file, 'r', encoding='utf-8') as f:
        all_tokens = json.load(f)
    
    print(f"发现 {len(all_tokens)} 个 Token 记录")
    
    migrated = 0
    failed = 0
    
    for key, token_data in all_tokens.items():
        try:
            # 提取 card_id
            if not key.startswith('card_'):
                continue
            card_id = key[5:]  # 去掉 "card_" 前缀
            
            # 查找名片
            card = Card.objects(id=card_id).first()
            if not card:
                print(f"  ⚠️ 名片不存在: {card_id}")
                failed += 1
                continue
            
            # 检查是否已存在
            existing = BaomingToken.objects(card=card).first()
            if existing:
                print(f"  ⏭️ Token 已存在，跳过: {card.name}")
                continue
            
            # 创建新记录
            token_record = BaomingToken(
                card=card,
                access_token=token_data.get('access_token', ''),
                uname=token_data.get('uname', ''),
                pic=token_data.get('pic', ''),
                unionid=token_data.get('unionid', ''),
                created_at=datetime.fromtimestamp(token_data.get('_save_time', time.time()))
            )
            token_record.save()
            
            print(f"  ✅ 迁移成功: {card.name}")
            migrated += 1
            
        except Exception as e:
            print(f"  ❌ 迁移失败: {key} - {e}")
            failed += 1
    
    print(f"\n迁移完成: 成功 {migrated} 个, 失败 {failed} 个")
    
    # 询问是否删除本地文件
    if migrated > 0:
        response = input("\n是否删除本地 Token 文件？(y/n): ")
        if response.lower() == 'y':
            token_file.unlink()
            print("✅ 已删除本地文件")

if __name__ == '__main__':
    from database.models import init_database
    init_database()
    migrate_tokens()
```

运行迁移：
```bash
python tools/migrate_baoming_tokens.py
```

## 管理功能

### 查询 Token

```python
from database.models import BaomingToken, Card

# 查询某个名片的 Token
card = Card.objects(name='统一').first()
token = BaomingToken.objects(card=card).first()

if token:
    print(f"名片: {card.name}")
    print(f"用户: {token.uname}")
    print(f"Token: {token.access_token[:20]}...")
    print(f"最后使用: {token.last_used}")
```

### 删除过期 Token

```python
from datetime import datetime, timedelta
from database.models import BaomingToken

# 删除 30 天未使用的 Token
thirty_days_ago = datetime.now() - timedelta(days=30)
expired_tokens = BaomingToken.objects(last_used__lt=thirty_days_ago)

print(f"发现 {expired_tokens.count()} 个过期 Token")
for token in expired_tokens:
    print(f"  删除: {token.card.name} - 最后使用: {token.last_used}")
    token.delete()
```

### 批量更新

```python
from database.models import BaomingToken
from datetime import datetime

# 重置所有 Token 的最后使用时间
BaomingToken.objects.update(last_used=datetime.now())
print("✅ 已更新所有 Token 的最后使用时间")
```

## 测试

### 测试流程

1. **测试保存 Token**
```python
# 在报名工具登录成功后
filler = BaomingToolFiller()
filler.initialize(url, card_id='69830fb551c6db84fb459e01')
status, msg, user_data = filler.check_login()

# 应该自动保存到数据库
# 验证：
from database.models import BaomingToken, Card
card = Card.objects(id='69830fb551c6db84fb459e01').first()
token = BaomingToken.objects(card=card).first()
assert token is not None
assert token.access_token == user_data['access_token']
```

2. **测试加载 Token**
```python
# 重新初始化
filler = BaomingToolFiller()
filler.initialize(url, card_id='69830fb551c6db84fb459e01')

# 尝试恢复登录状态
success = filler.try_restore_login()
assert success == True
assert filler.api.access_token is not None
```

3. **测试清空 Token**
```python
# Token 失效时
filler._clear_token()

# 验证：
token = BaomingToken.objects(card=card).first()
assert token is None
```

## 注意事项

1. **数据库连接**
   - 确保 MongoDB 已启动并正确连接
   - 确保有写入权限

2. **错误处理**
   - 所有数据库操作都有异常捕获
   - 操作失败会打印详细错误信息

3. **兼容性**
   - 如果数据库操作失败，不会影响现有功能
   - 可以回退到本地文件存储方案

4. **性能**
   - 数据库查询已添加索引，性能优化
   - `last_used` 字段更新不会阻塞主流程

5. **安全性**
   - Token 敏感信息，建议定期清理过期数据
   - 可以考虑对 `access_token` 字段加密存储

## 后续优化

1. **Token 加密**
   - 对 `access_token` 进行加密存储
   - 使用 `cryptography` 库实现

2. **Token 有效期管理**
   - 添加 `expires_at` 字段
   - 自动清理过期 Token

3. **使用统计**
   - 添加 `use_count` 字段
   - 记录使用频率

4. **管理界面**
   - 在主窗口添加 Token 管理界面
   - 支持查看、删除、刷新 Token

## 更新日志

### 2024-02-10
- ✅ 创建 `BaomingToken` 数据库模型
- ✅ 修改 Token 保存/加载/清空逻辑
- ✅ 从本地文件迁移到数据库存储
- ✅ 添加使用时间记录
- ✅ 完善错误处理

## 参考文档

- [报名工具 API 文档](./baoming_tool_api.md)
- [数据库模型文档](../database/models.py)
- [MongoEngine 文档](https://docs.mongoengine.org/)
