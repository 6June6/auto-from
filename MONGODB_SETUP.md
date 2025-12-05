# MongoDB 数据库设置指南

## 🚨 当前问题

项目已成功迁移到 MongoDB，但遇到**权限不足**的问题：

```
❌ not authorized on auto_form_filler to execute command { count: "cards" }
```

## 问题分析

提供的 MongoDB 账号（`mp-97cf738a-ef6a-4a9a-a80c-53378cb9ada3`）**没有对 `auto_form_filler` 数据库的读写权限**。

当前账号可能只有：
- ✅ 连接权限（可以连接到数据库）
- ❌ 读取权限（无法执行 count、find 等操作）
- ❌ 写入权限（无法执行 insert、update 等操作）
- ❌ 索引权限（无法创建索引）

## 解决方案

### 方案 1：授予数据库权限（推荐）⭐

在 **阿里云 MongoDB 控制台**为当前用户授予权限：

1. 登录阿里云控制台
2. 进入 MongoDB 实例管理
3. 选择 "账号管理"
4. 为账号 `mp-97cf738a-ef6a-4a9a-a80c-53378cb9ada3` 授予以下权限：
   ```
   数据库: auto_form_filler
   权限: readWrite (读写权限)
   ```

### 方案 2：创建新账号

创建一个专门的应用账号：

```javascript
// 在 MongoDB 中执行（通过控制台或 mongo shell）
use admin
db.createUser({
  user: "auto_form_filler_app",
  pwd: "你的密码",
  roles: [
    {
      role: "readWrite",
      db: "auto_form_filler"
    }
  ]
})
```

然后更新 `config.py` 中的连接字符串：

```python
MONGODB_URI = "mongodb://auto_form_filler_app:你的密码@dds-bp17151e3fa0eca41972-pub.mongodb.rds.aliyuncs.com:3717,dds-bp17151e3fa0eca42468-pub.mongodb.rds.aliyuncs.com:3717/auto_form_filler?replicaSet=mgset-90193512&authSource=admin"
```

### 方案 3：使用 admin 数据库（不推荐）

临时方案，直接使用 admin 数据库：

```python
# config.py
MONGODB_URI = "mongodb://mp-97cf738a-ef6a-4a9a-a80c-53378cb9ada3:4b0c5b88d8caafb5e6cfe06f4ef088bf@dds-bp17151e3fa0eca41972-pub.mongodb.rds.aliyuncs.com:3717,dds-bp17151e3fa0eca42468-pub.mongodb.rds.aliyuncs.com:3717/admin?replicaSet=mgset-90193512&authSource=admin"
MONGODB_DB_NAME = "admin"
```

⚠️ **不推荐原因**：
- admin 数据库是系统数据库
- 混合应用数据和系统数据不是好的做法
- 可能会有命名冲突

## 所需权限清单

应用程序需要以下 MongoDB 权限：

| 操作 | 权限 | 说明 |
|------|------|------|
| 查询文档 | `find` | 读取数据 |
| 统计文档 | `count` | 统计数量 |
| 插入文档 | `insert` | 创建数据 |
| 更新文档 | `update` | 修改数据 |
| 删除文档 | `remove` | 删除数据 |
| 创建集合 | `createCollection` | 自动创建表 |

**推荐角色**：`readWrite`（包含以上所有权限）

**不需要的权限**：
- ❌ `dbAdmin`（数据库管理）
- ❌ `createIndex`（创建索引）- 已在代码中禁用自动创建

## 验证权限

授权完成后，运行测试脚本验证：

```bash
python test_mongodb_connection.py
```

预期输出：

```
============================================================
🧪 MongoDB 数据库连接测试
============================================================

1️⃣ 测试数据库连接...
✅ MongoDB 连接成功！数据库: auto_form_filler
✅ 数据库初始化完成

2️⃣ 测试统计信息...
  📊 统计数据:
     - 名片总数: 1
     - 链接总数: 2
     ...
✅ 统计信息获取成功

...

🎉 所有测试通过！数据库工作正常
```

## 数据库结构

迁移后的数据库包含 3 个集合（Collection）：

### 1. cards（名片）

```javascript
{
  "_id": ObjectId("..."),
  "name": "名片1",
  "description": "测试名片",
  "configs": [
    {
      "key": "手机号",
      "value": "13800138000",
      "order": 0
    }
  ],
  "created_at": ISODate("2025-10-21T..."),
  "updated_at": ISODate("2025-10-21T...")
}
```

### 2. links（链接）

```javascript
{
  "_id": ObjectId("..."),
  "name": "测试链接",
  "url": "https://example.com",
  "status": "active",
  "category": "测试",
  "description": "测试链接",
  "created_at": ISODate("2025-10-21T..."),
  "updated_at": ISODate("2025-10-21T...")
}
```

### 3. fill_records（填写记录）

```javascript
{
  "_id": ObjectId("..."),
  "card": ObjectId("..."),  // 引用 cards
  "link": ObjectId("..."),  // 引用 links
  "fill_count": 8,
  "total_count": 10,
  "success": true,
  "error_message": null,
  "created_at": ISODate("2025-10-21T...")
}
```

## 建议的索引（可选）

虽然代码中已禁用自动创建索引，但如果有权限，建议手动创建以下索引以提升性能：

```javascript
// cards 集合
db.cards.createIndex({ "name": 1 })
db.cards.createIndex({ "created_at": -1 })

// links 集合
db.links.createIndex({ "status": 1 })
db.links.createIndex({ "created_at": -1 })

// fill_records 集合
db.fill_records.createIndex({ "created_at": -1 })
db.fill_records.createIndex({ "card": 1 })
db.fill_records.createIndex({ "link": 1 })
```

## 连接字符串说明

```
mongodb://用户名:密码@主机1:端口1,主机2:端口2/数据库名?参数
```

参数说明：
- `replicaSet=mgset-90193512`：副本集名称
- `authSource=admin`：认证数据库（用户存储位置）

## 常见问题

### Q1: 为什么不能自动创建索引？

**A:** 权限限制。代码中已设置 `auto_create_index=False` 禁用自动创建。

### Q2: 数据会存储在哪里？

**A:** 存储在 `auto_form_filler` 数据库的 3 个集合中（cards、links、fill_records）。

### Q3: ObjectId 是什么？

**A:** MongoDB 的主键类型，类似 SQLite 的自增 ID，但是字符串格式。

### Q4: 如何从 SQLite 迁移数据？

**A:** 需要编写数据迁移脚本，读取 SQLite 数据并写入 MongoDB。

## 联系支持

如需帮助，请提供：
1. MongoDB 版本
2. 阿里云实例配置
3. 完整的错误信息
4. 用户权限列表

---

**更新时间**: 2025-10-21  
**MongoDB 版本**: v2.0.0

