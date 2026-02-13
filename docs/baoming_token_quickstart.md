# 报名工具 Token 数据库存储 - 快速指南

## 概述

报名工具的登录 Token 现在保存在 MongoDB 数据库中，而不是本地文件。

## 主要变化

### 之前（本地文件）
```
~/.auto-form-filler/baoming_tokens.json
```

### 现在（数据库）
```
MongoDB > baoming_tokens 集合
```

## 自动迁移

系统会在首次使用时自动迁移本地 Token 到数据库，无需手动操作。

## 手动迁移（可选）

如果需要手动迁移，运行以下命令：

```bash
cd /Users/chenchen/Desktop/开发项目/auto-form-filler-py
python tools/migrate_baoming_tokens.py
```

迁移脚本会：
1. 读取本地 Token 文件
2. 显示所有 Token 列表
3. 询问是否继续迁移
4. 迁移到数据库
5. 询问是否删除本地文件（会先备份）

## 优势

| 特性 | 本地文件 | 数据库 |
|------|---------|--------|
| 多设备共享 | ❌ | ✅ |
| 数据安全 | ❌ | ✅ |
| 历史记录 | ❌ | ✅ |
| 统一管理 | ❌ | ✅ |
| 并发安全 | ❌ | ✅ |

## 数据结构

```javascript
{
  "_id": ObjectId("..."),
  "card": ObjectId("名片ID"),        // 关联的名片
  "access_token": "token字符串",     // 访问令牌
  "uname": "微信昵称",               // 用户昵称
  "pic": "头像URL",                  // 用户头像
  "unionid": "微信unionid",          // 微信唯一标识
  "created_at": ISODate("..."),      // 创建时间
  "updated_at": ISODate("..."),      // 更新时间
  "last_used": ISODate("...")        // 最后使用时间
}
```

## 查询 Token

### Python 代码
```python
from database.models import BaomingToken, Card

# 查询某个名片的 Token
card = Card.objects(name='统一').first()
token = BaomingToken.objects(card=card).first()

if token:
    print(f"名片: {card.name}")
    print(f"用户: {token.uname}")
    print(f"最后使用: {token.last_used}")
```

### MongoDB Shell
```javascript
// 查看所有 Token
db.baoming_tokens.find().pretty()

// 查询某个名片的 Token
db.baoming_tokens.find({
  "card": ObjectId("69830fb551c6db84fb459e01")
})

// 统计 Token 数量
db.baoming_tokens.count()

// 查找最近使用的 Token
db.baoming_tokens.find().sort({"last_used": -1}).limit(5)
```

## 清理过期 Token

### Python 脚本
```python
from datetime import datetime, timedelta
from database.models import BaomingToken

# 删除 30 天未使用的 Token
thirty_days_ago = datetime.now() - timedelta(days=30)
expired_tokens = BaomingToken.objects(last_used__lt=thirty_days_ago)

print(f"发现 {expired_tokens.count()} 个过期 Token")
expired_tokens.delete()
print("✅ 清理完成")
```

### MongoDB Shell
```javascript
// 删除 30 天未使用的 Token
var thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

db.baoming_tokens.deleteMany({
  "last_used": { $lt: thirtyDaysAgo }
})
```

## 常见问题

### Q1: 本地文件还在用吗？
A: 不再使用。新系统只使用数据库存储。

### Q2: 需要手动迁移吗？
A: 不需要。系统会自动迁移。如果想手动迁移，可以运行迁移脚本。

### Q3: 本地文件可以删除吗？
A: 可以。迁移后可以安全删除 `~/.auto-form-filler/baoming_tokens.json`。

### Q4: Token 会过期吗？
A: 报名工具的 Token 有效期由服务器决定。如果失效，系统会自动删除并要求重新登录。

### Q5: 多个设备可以共享 Token 吗？
A: 可以。只要使用同一个 MongoDB 数据库，所有设备都可以共享 Token。

### Q6: 如何备份 Token？
A: 备份 MongoDB 数据库即可。也可以导出 `baoming_tokens` 集合：
```bash
mongoexport --db=auto-form-db --collection=baoming_tokens --out=baoming_tokens_backup.json
```

### Q7: 如何恢复 Token？
A: 导入备份的数据：
```bash
mongoimport --db=auto-form-db --collection=baoming_tokens --file=baoming_tokens_backup.json
```

## 技术支持

如有问题，请查看详细文档：
- [完整迁移文档](./baoming_token_migration.md)
- [报名工具 API 文档](./baoming_tool_api.md)
- [数据库模型](../database/models.py)
