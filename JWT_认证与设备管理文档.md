# JWT Token 认证与设备管理系统文档

## 📋 目录

1. [功能概述](#功能概述)
2. [技术架构](#技术架构)
3. [数据库模型](#数据库模型)
4. [核心功能](#核心功能)
5. [使用说明](#使用说明)
6. [API 文档](#api文档)
7. [配置说明](#配置说明)
8. [安全机制](#安全机制)

---

## 🎯 功能概述

本系统实现了基于 JWT Token 的认证机制和设备绑定管理功能，主要特性包括：

- ✅ JWT Token 自动登录
- ✅ 设备数量限制（每用户最多 2 台设备）
- ✅ 设备信息记录和管理
- ✅ Token 过期自动重新登录
- ✅ 管理员设备管理后台

---

## 🏗️ 技术架构

### 技术栈

- **认证框架**: PyJWT 2.10.1
- **数据库**: MongoDB (MongoEngine ORM)
- **GUI 框架**: PyQt6
- **加密算法**: HS256 (HMAC-SHA256)

### 架构设计

```
┌─────────────────┐
│   客户端启动     │
└────────┬────────┘
         │
         ├─→ 检查本地Token
         │
         ├─→ Token存在且有效
         │   └─→ 自动登录
         │
         └─→ Token不存在/无效
             └─→ 显示登录窗口
                 └─→ 用户名密码登录
                     ├─→ 检查设备限制
                     ├─→ 生成Token
                     └─→ 绑定设备
```

---

## 💾 数据库模型

### Device 设备模型

```python
class Device(Document):
    """设备模型 - 用于设备管理和限制"""
    user = ReferenceField(User, required=True)          # 所属用户
    device_id = StringField(required=True, max_length=200)  # 设备唯一标识
    device_name = StringField(required=True, max_length=100) # 设备名称
    device_type = StringField(max_length=50)            # 设备类型 (macOS/Windows/Linux)
    last_ip = StringField(max_length=50)                # 最后登录IP
    last_login = DateTimeField(default=datetime.now)    # 最后登录时间
    created_at = DateTimeField(default=datetime.now)    # 首次绑定时间
    is_active = BooleanField(default=True)              # 是否激活
```

**字段说明**:

- `device_id`: 基于 MAC 地址生成的唯一标识，格式如 `Darwin_0x1a2b3c4d5e6f`
- `device_name`: 计算机名称，如 `MacBook-Pro`
- `device_type`: 操作系统类型 (Darwin/Windows/Linux)
- `is_active`: 设备是否激活，解绑后为 False

---

## ⚙️ 核心功能

### 1. JWT Token 生成

**位置**: `core/auth.py` - `generate_token()`

**流程**:

```python
Token Payload = {
    'user_id': 用户ID,
    'username': 用户名,
    'role': 用户角色,
    'device_id': 设备ID,
    'exp': 过期时间 (30天后),
    'iat': 签发时间
}
```

**特点**:

- Token 包含设备信息，确保绑定设备才能使用
- 30 天有效期
- 使用 HS256 算法签名

### 2. 设备标识生成

**位置**: `core/auth.py` - `get_device_id()`

**算法**:

```python
device_id = f"{platform.system()}_{hex(uuid.getnode())}"
# 示例: Darwin_0x1a2b3c4d5e6f
```

**特点**:

- 基于网卡 MAC 地址生成
- 同一台设备 ID 始终一致
- 跨平台兼容

### 3. 设备限制检查

**位置**: `core/auth.py` - `check_device_limit()`

**逻辑**:

```
1. 查询用户的所有激活设备
2. 检查当前设备是否已绑定
   - 已绑定 → 允许登录
   - 未绑定 → 检查设备数量
3. 未绑定且设备数 >= 2 → 拒绝登录
4. 未绑定且设备数 < 2 → 允许登录并绑定
```

**限制规则**:

- 每个用户最多绑定 2 台设备
- 超过限制时提示："该账号已达到最大设备数量限制（2 台），请在后台解绑其他设备后重试"

### 4. 自动登录

**位置**: `main.py` - `try_auto_login()`

**流程**:

```
1. 读取本地Token文件 (~/.auto-form-filler/.token)
2. 验证Token有效性
   - 检查签名
   - 检查过期时间
   - 检查设备是否仍然绑定
3. Token有效 → 自动登录成功
4. Token无效 → 删除Token，显示登录窗口
```

### 5. 设备管理后台

**位置**: `gui/admin_main_window.py`

**功能**:

- 📋 查看所有用户的设备列表
- 🔍 显示设备详细信息
- 🔓 解绑设备功能
- 🔄 刷新设备列表

**显示信息**:
| 字段 | 说明 | 示例 |
|------|------|------|
| 用户 | 设备所属用户 | admin |
| 设备名称 | 计算机名称 | MacBook-Pro |
| 设备类型 | 操作系统 | 🍎 macOS |
| 设备 ID | 唯一标识（缩短显示）| Darwin_0x1a2b3c... |
| 最后登录 | 最后活跃时间 | 2025-10-21 15:36 |
| 状态 | 激活/已解绑 | ✅ 激活 |
| 操作 | 解绑按钮 | [解绑] |

---

## 📖 使用说明

### 用户端使用

#### 首次登录

1. 启动程序，显示登录窗口
2. 输入用户名和密码
3. 系统自动绑定当前设备
4. 登录成功，Token 保存到本地

#### 自动登录

1. 再次启动程序
2. 系统自动读取本地 Token
3. 验证通过，直接进入主界面
4. 无需输入用户名密码

#### 设备限制提示

当尝试在第 3 台设备登录时：

```
登录失败
该账号已达到最大设备数量限制（2台）
请在后台解绑其他设备后重试
```

### 管理员使用

#### 查看设备列表

1. 登录管理后台
2. 点击左侧菜单"📱 设备管理"
3. 查看所有用户的设备绑定情况

#### 解绑设备

1. 在设备列表中找到要解绑的设备
2. 点击"解绑"按钮
3. 确认解绑操作
4. 设备状态变为"已解绑"
5. 该设备的 Token 将失效，需要重新登录

---

## 🔌 API 文档

### 认证相关 API

#### 1. 用户名密码登录

```python
from core.auth import login_with_password

success, message, token, user = login_with_password(username, password)

# 返回值:
# success: bool - 是否成功
# message: str - 提示消息
# token: str - JWT Token (成功时)
# user: User - 用户对象 (成功时)
```

**示例**:

```python
success, message, token, user = login_with_password('admin', 'admin123')
if success:
    print(f"登录成功，Token: {token}")
    # 保存Token到本地
else:
    print(f"登录失败: {message}")
```

#### 2. Token 自动登录

```python
from core.auth import login_with_token

success, message, user = login_with_token(token)

# 返回值:
# success: bool - 是否成功
# message: str - 提示消息
# user: User - 用户对象 (成功时)
```

**示例**:

```python
token = read_token_from_local()
success, message, user = login_with_token(token)
if success:
    print(f"自动登录成功: {user.username}")
else:
    print(f"自动登录失败: {message}")
```

#### 3. Token 生成

```python
from core.auth import generate_token, get_device_info

device_info = get_device_info()
token = generate_token(user, device_info)
```

#### 4. Token 验证

```python
from core.auth import verify_token

payload = verify_token(token)
if payload:
    print(f"Token有效，用户: {payload['username']}")
else:
    print("Token无效或已过期")
```

### 设备管理 API

#### 1. 检查设备限制

```python
from core.auth import check_device_limit

can_login, message = check_device_limit(user, device_id)
if can_login:
    print("允许登录")
else:
    print(f"拒绝登录: {message}")
```

#### 2. 绑定设备

```python
from core.auth import bind_device, get_device_info

device_info = get_device_info()
device = bind_device(user, device_info, ip_address='192.168.1.1')
print(f"设备已绑定: {device.device_name}")
```

#### 3. 解绑设备

```python
from core.auth import unbind_device

success = unbind_device(device_id)
if success:
    print("设备已解绑")
```

#### 4. 获取用户设备列表

```python
from core.auth import get_user_devices

devices = get_user_devices(user)
for device in devices:
    print(f"{device['device_name']} - {device['device_type']}")
```

---

## ⚙️ 配置说明

### 配置文件: `config.py`

```python
# JWT 认证配置
JWT_SECRET_KEY = "auto-form-filler-secret-key-2025-change-in-production"
JWT_EXPIRATION_DAYS = 30  # Token 过期时间（天）
MAX_DEVICES_PER_USER = 2  # 每个用户最多绑定设备数
```

### 配置项说明

| 配置项               | 类型 | 默认值                                                | 说明                             |
| -------------------- | ---- | ----------------------------------------------------- | -------------------------------- |
| JWT_SECRET_KEY       | str  | auto-form-filler-secret-key-2025-change-in-production | JWT 签名密钥（生产环境必须修改） |
| JWT_EXPIRATION_DAYS  | int  | 30                                                    | Token 有效期（天）               |
| MAX_DEVICES_PER_USER | int  | 2                                                     | 每用户最大设备数                 |

### Token 存储位置

- **路径**: `~/.auto-form-filler/.token`
- **格式**: 纯文本文件，存储 JWT Token 字符串
- **权限**: 用户私有文件

---

## 🔒 安全机制

### 1. Token 安全

**加密算法**: HS256 (HMAC-SHA256)

- 签名验证，防止 Token 篡改
- 包含过期时间，自动失效
- 设备绑定，防止 Token 跨设备使用

**存储安全**:

- Token 存储在用户主目录
- 仅当前用户可访问
- 不暴露在项目目录

### 2. 设备验证

**多重验证**:

1. Token 签名验证
2. Token 过期时间验证
3. 用户状态检查（是否被禁用）
4. 设备绑定状态检查（是否已解绑）

**防御措施**:

- 设备 ID 基于硬件信息生成，难以伪造
- 设备数量限制，防止无限制绑定
- 管理员可随时解绑设备

### 3. 密码安全

- 密码使用 SHA256 加密存储
- 不存储明文密码
- 登录失败不泄露具体原因

### 4. 会话管理

**Token 失效场景**:

1. Token 过期（30 天后）
2. 用户被禁用
3. 设备被解绑
4. Token 签名验证失败

**失效处理**:

- 自动删除本地 Token
- 跳转到登录窗口
- 提示用户重新登录

---

## 📊 数据流图

### 登录流程

```
用户输入用户名密码
    ↓
验证用户名和密码
    ↓
检查用户是否被禁用
    ↓
获取设备信息
    ↓
检查设备数量限制
    ↓
绑定/更新设备信息
    ↓
生成JWT Token
    ↓
保存Token到本地
    ↓
登录成功
```

### 自动登录流程

```
启动应用
    ↓
读取本地Token
    ↓
验证Token签名
    ↓
检查Token是否过期
    ↓
验证用户状态
    ↓
验证设备绑定状态
    ↓
更新最后登录时间
    ↓
自动登录成功
```

### 设备解绑流程

```
管理员选择设备
    ↓
点击解绑按钮
    ↓
确认解绑操作
    ↓
设置设备为非激活状态
    ↓
保存到数据库
    ↓
设备Token失效
    ↓
该设备需要重新登录
```

---

## 🔍 故障排查

### 常见问题

#### 1. 自动登录失败

**问题**: 启动程序时提示"自动登录失败"

**可能原因**:

- Token 已过期（30 天）
- 设备已被管理员解绑
- 用户被禁用
- Token 文件损坏

**解决方法**:

1. 检查 `~/.auto-form-filler/.token` 文件是否存在
2. 尝试手动删除 Token 文件重新登录
3. 检查用户账号状态
4. 检查设备管理后台的绑定状态

#### 2. 设备数量限制

**问题**: 提示"该账号已达到最大设备数量限制"

**解决方法**:

1. 登录管理后台
2. 进入"设备管理"页面
3. 找到要解绑的设备
4. 点击"解绑"按钮
5. 重新在新设备上登录

#### 3. Token 验证失败

**问题**: 日志显示"Token 无效"

**可能原因**:

- JWT_SECRET_KEY 被修改
- Token 格式错误
- Token 被篡改

**解决方法**:

- 删除本地 Token 文件重新登录
- 检查 config.py 中的 JWT_SECRET_KEY 是否一致

---

## 📝 日志说明

### 日志示例

```bash
# 首次登录
🔧 初始化 MongoDB 数据库...
✅ MongoDB 连接成功！数据库: auto-form-db
ℹ️ 未找到保存的登录信息，需要手动登录
✅ Token 已保存
✅ 用户登录成功: admin (admin)
📊 启动管理后台界面...

# 自动登录
🔧 初始化 MongoDB 数据库...
✅ MongoDB 连接成功！数据库: auto-form-db
🔐 尝试自动登录...
✅ 自动登录成功: admin
📊 启动管理后台界面...

# 登录失败
❌ 自动登录失败: Token 已过期
ℹ️ 需要手动登录
```

---

## 🎓 开发建议

### 生产环境部署

1. **修改 JWT 密钥**

   ```python
   # config.py
   JWT_SECRET_KEY = "your-production-secret-key-very-long-and-complex"
   ```

2. **调整 Token 过期时间**

   ```python
   JWT_EXPIRATION_DAYS = 7  # 改为7天，更安全
   ```

3. **设置设备数量限制**
   ```python
   MAX_DEVICES_PER_USER = 3  # 根据实际需求调整
   ```

### 扩展功能建议

1. **添加 IP 白名单**

   - 限制只能从特定 IP 登录
   - 记录异常登录尝试

2. **设备审批机制**

   - 新设备需要管理员审批
   - 发送通知邮件

3. **Token 刷新机制**

   - 实现 refresh token
   - 延长活跃用户的会话时间

4. **登录日志**
   - 记录每次登录时间和 IP
   - 异常登录告警

---

## 📄 文件清单

### 核心文件

```
auto-form-filler-py/
├── core/
│   └── auth.py                 # JWT认证核心模块
├── database/
│   ├── models.py               # 数据库模型（含Device模型）
│   └── __init__.py            # 导出Device模型
├── gui/
│   ├── login_window.py        # 登录窗口（集成Token保存）
│   └── admin_main_window.py   # 管理后台（设备管理界面）
├── config.py                   # JWT配置
├── main.py                     # 主程序（自动登录逻辑）
└── requirements.txt            # 依赖（含PyJWT）
```

### 本地数据

```
~/.auto-form-filler/
└── .token                      # JWT Token存储文件
```

---

## 📚 参考资料

- [PyJWT 官方文档](https://pyjwt.readthedocs.io/)
- [JWT 标准规范](https://datatracker.ietf.org/doc/html/rfc7519)
- [MongoEngine 文档](http://docs.mongoengine.org/)

---

## 📅 更新日志

### v2.0.0 (2025-10-21)

- ✅ 实现 JWT Token 认证机制
- ✅ 添加设备绑定和限制功能
- ✅ 实现自动登录
- ✅ 添加设备管理后台界面
- ✅ Token 本地存储和自动清理

---

## 👥 维护说明

**负责人**: 开发团队  
**最后更新**: 2025-10-21  
**版本**: v2.0.0

如有问题，请联系开发团队或查看项目文档。
