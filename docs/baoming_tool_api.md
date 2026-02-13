# 报名工具 API 接口文档

> 基础域名：`https://api-xcx-qunsou.weiyoubot.cn/xcx`
> 
> 报名工具官网：`https://p.baominggongju.com`

## 目录

- [1. 登录相关](#1-登录相关)
  - [1.1 获取登录二维码](#11-获取登录二维码)
  - [1.2 轮询登录状态](#12-轮询登录状态)
- [2. 表单查询](#2-表单查询)
  - [2.1 获取表单简要信息](#21-获取表单简要信息)
  - [2.2 获取报名详情](#22-获取报名详情)
  - [2.3 获取表单字段](#23-获取表单字段)
- [3. 表单提交](#3-表单提交)
  - [3.1 新增报名](#31-新增报名)
  - [3.2 更新报名](#32-更新报名-已废弃)

---

## 1. 登录相关

### 1.1 获取登录二维码

**接口地址**
```
GET /enroll_web/v1/pc_code
```

**请求参数**
- 无

**响应示例**
```json
{
  "sta": 0,
  "msg": "ok",
  "data": {
    "qrcode": "https://qr-code-url...",
    "code": "登录凭证code"
  }
}
```

**字段说明**
- `qrcode`: 二维码图片 URL
- `code`: 登录凭证，用于轮询登录状态

**使用场景**
- 用户首次登录时获取二维码
- 每个名片只需登录一次，token 可跨活动复用

---

### 1.2 轮询登录状态

**接口地址**
```
GET /enroll_web/v1/pc_login
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 登录凭证（从获取二维码接口获取） |
| source | string | 是 | 固定值：`h5` |

**响应示例**

等待扫码：
```json
{
  "sta": -1,
  "msg": "等待扫码..."
}
```

登录成功：
```json
{
  "sta": 0,
  "msg": "ok",
  "data": {
    "access_token": "用户访问令牌",
    "uname": "用户昵称",
    "pic": "用户头像URL",
    "unionid": "微信 unionid"
  }
}
```

**字段说明**
- `sta`: 状态码
  - `0`: 登录成功
  - `-1`: 等待扫码
  - 其他: 登录失败
- `access_token`: 访问令牌，用于后续所有需要授权的接口

**使用场景**
- 展示二维码后，每隔 2 秒轮询一次
- 登录成功后保存 `access_token` 到本地，跨活动复用

---

## 2. 表单查询

### 2.1 获取表单简要信息

**接口地址**
```
GET /enroll/v1/short_detail
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| eid | string | 是 | 活动ID（从URL中提取） |

**响应示例**
```json
{
  "msg": "ok",
  "sta": 0,
  "data": {
    "eid": "69844bcf8eaa2449c7a37fae",
    "title": "测试活动",
    "sign_name": "组织者名称",
    "count": 5,
    "limit": 100,
    "start_time": 1770253200,
    "end_time": 1770825540,
    "status": 1,
    "views": 66
  }
}
```

**字段说明**
- `title`: 活动标题
- `sign_name`: 组织者名称
- `count`: 已报名人数
- `limit`: 报名人数限制
- `status`: 活动状态（1: 进行中）

**使用场景**
- 获取活动标题和基本信息
- 不需要 token，可以未登录访问

---

### 2.2 获取报名详情

**接口地址**
```
GET /enroll/v3/detail
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| eid | string | 是 | 活动ID |
| access_token | string | 是 | 用户访问令牌 |
| referer | string | 否 | 来源（可为空） |
| spider | string | 否 | 固定值：`h5` |

**响应示例**

首次报名（未报名过）：
```json
{
  "sta": 0,
  "msg": "ok",
  "data": {
    "eid": "69844bcf8eaa2449c7a37fae",
    "title": "测试活动",
    "info_id": "",  // 空字符串，表示未报名过
    "status": 1
  }
}
```

已报名过：
```json
{
  "sta": 0,
  "msg": "ok",
  "data": {
    "eid": "69844bcf8eaa2449c7a37fae",
    "title": "测试活动",
    "info_id": "6984xxxxx",  // 已有的报名记录ID
    "status": 1
  }
}
```

**字段说明**
- `info_id`: 报名记录ID
  - 为空：首次报名
  - 有值：已报名过，可用于更新记录

**使用场景**
- 判断用户是否已报名过
- 获取 `info_id` 用于更新报名信息

---

### 2.3 获取表单字段

**接口地址**
```
GET /enroll/v1/req_detail
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| eid | string | 是 | 活动ID |
| access_token | string | 是 | 用户访问令牌 |

**响应示例**
```json
{
  "sta": 0,
  "msg": "ok",
  "data": {
    "eid": "69844bcf8eaa2449c7a37fae",
    "req_info": [
      {
        "field_key": 1,
        "field_name": "姓名",
        "field_type": 0,
        "type_text": "单行文本",
        "require": 1,
        "ignore": 0,
        "field_len": 50,
        "status": 1
      },
      {
        "field_key": "ff13e6fe-45fb-4173-3423-b680c9a3e21c",
        "field_name": "选择哈哈",
        "field_type": 4,
        "type_text": "单项选择",
        "require": 1,
        "new_options": [
          {
            "key": "0ffcd",
            "value": "哈哈"
          },
          {
            "key": "128d4",
            "value": "嘿嘿"
          }
        ],
        "radio_style": 0
      },
      {
        "field_key": "00f79094-21cb-3933-c874-cfa692221b6c",
        "field_name": "选择哈哈哈",
        "field_type": 5,
        "type_text": "多项选择",
        "require": 1,
        "new_options": [
          {
            "key": "0f0b8",
            "value": "哈哈哈"
          },
          {
            "key": "1942a",
            "value": "哼哼哼"
          },
          {
            "key": "28ddf",
            "value": "嘿嘿嘿",
            "radio_custom": 1
          }
        ],
        "field_desc": "备注"
      }
    ],
    "req_logic": []
  }
}
```

**字段类型说明**
| field_type | type_text | 说明 |
|------------|-----------|------|
| 0 | 单行文本 | 普通文本输入 |
| 1 | 多行文本 | 长文本输入 |
| 4 | 单项选择 | 单选/下拉 |
| 5 | 多项选择 | 多选框 |

**字段说明**
- `field_key`: 字段唯一标识
  - 数字：系统字段（如姓名、手机号）
  - UUID：自定义字段
- `field_name`: 字段名称
- `require`: 是否必填（1: 必填，0: 非必填）
- `new_options`: 选择题的选项列表
  - `key`: 选项的唯一标识（提交时需要）
  - `value`: 选项显示文本
  - `radio_custom`: 是否允许自定义输入（"其他"选项）

**使用场景**
- 获取表单结构，用于渲染表单界面
- 获取字段类型和选项，用于智能匹配

---

## 3. 表单提交

### 3.1 新增报名

**接口地址**
```
POST /enroll/v5/enroll
```

**请求头**
```
Content-Type: application/json
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| eid | string | 是 | 活动ID |
| access_token | string | 是 | 用户访问令牌 |
| info | array | 是 | 表单数据 |
| on_behalf | number | 是 | 固定值：`1` |
| items | array | 是 | 固定值：`[]` |
| referer | string | 否 | 来源（可为空） |
| from | string | 是 | 固定值：`h5` |
| _a | string | 是 | RSA 签名（必须） |

**info 字段结构**

单行文本：
```json
{
  "field_key": 1,
  "field_name": "姓名",
  "field_value": "张三",
  "ignore": 0
}
```

单项选择：
```json
{
  "field_key": "ff13e6fe-45fb-4173-3423-b680c9a3e21c",
  "field_name": "选择哈哈",
  "field_value": "哈哈",
  "new_field_value": "0ffcd",  // 选项的 key（必须）
  "ignore": 0
}
```

多项选择：
```json
{
  "field_key": "00f79094-21cb-3933-c874-cfa692221b6c",
  "field_name": "选择哈哈哈",
  "field_value": ["哈哈哈", "哼哼哼"],
  "new_field_value": ["0f0b8", "1942a"],  // 选项的 key 数组（必须）
  "ignore": 0
}
```

**签名生成算法**

```python
import time
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

# 1. 公钥
public_key_pem = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCjI8E8LT0fwFekelMMuTWuaIfo
fK69lyNIo+Vz0CGdfE3rLSIH94S2A3Q+bg+9/VnImvfXzcDVmqwHwC4hHPHs6hc6
ufq0gfivTPms3kwX74F5qLMr70j4iZLt/PCkU+uyQ56KmRW4foCV4RPX8o8QZVss
6eifHaeUeJxKM556ewIDAQAB
-----END PUBLIC KEY-----"""

# 2. 生成签名
timestamp = round(time.time())  # 秒级时间戳
plain_text = f"{eid}{timestamp}"  # eid + 时间戳

public_key = RSA.import_key(public_key_pem)
cipher = PKCS1_v1_5.new(public_key)
encrypted = cipher.encrypt(plain_text.encode('utf-8'))
signature = base64.b64encode(encrypted).decode('utf-8')  # Base64 编码
```

**完整请求示例**
```json
{
  "eid": "69844bcf8eaa2449c7a37fae",
  "access_token": "96888568c67d417585ef...",
  "info": [
    {
      "field_key": 1,
      "field_name": "姓名",
      "field_value": "张三",
      "ignore": 0
    },
    {
      "field_key": "ff13e6fe-45fb-4173-3423-b680c9a3e21c",
      "field_name": "选择哈哈",
      "field_value": "哈哈",
      "new_field_value": "0ffcd",
      "ignore": 0
    }
  ],
  "on_behalf": 1,
  "items": [],
  "referer": "",
  "from": "h5",
  "_a": "FpqL8wlkhY9p8aYrDs1P1H3lLT8H2AqbWAI7Fr8mL/BAL2q07z..."
}
```

**响应示例**

提交成功：
```json
{
  "sta": 0,
  "msg": "ok",
  "data": {
    "info_id": "6984xxxxx"
  }
}
```

提交失败：
```json
{
  "sta": -1,
  "msg": "请输入姓名"
}
```

```json
{
  "sta": -1,
  "msg": "活动期间，只允许提交1次"
}
```

**常见错误码**
| sta | msg | 说明 |
|-----|-----|------|
| -1 | 请输入姓名 | 必填字段为空 |
| -1 | 活动期间，只允许提交1次 | 已报名过，不允许重复提交 |
| -1 | 签名验证失败 | `_a` 签名错误或过期 |
| -1 | invalid access_token | token 失效，需重新登录 |

**使用场景**
- 首次报名时使用
- 提交失败时直接返回错误信息

**重要说明**
- ⚠️ **签名必须正确**：`_a` 参数使用 RSA 加密 + Base64 编码
- ⚠️ **选择题必须提供 key**：单选/多选题必须同时提供 `field_value` 和 `new_field_value`
- ⚠️ **不支持重复提交**：如果已报名过，接口会返回 "只允许提交1次" 错误
- ⚠️ **时间戳敏感**：签名中的时间戳必须与当前时间接近，过期会被拒绝

---

### 3.2 更新报名（已废弃）

**接口地址**
```
POST /enroll/v1/user_update
```

**状态**
⚠️ **已废弃**：新版本中，如果活动不允许重复提交，直接返回错误信息，不再尝试更新。

**原设计用途**
- 用于更新已有的报名记录
- 需要先通过 `get_enroll_detail` 获取 `info_id`

**废弃原因**
- 大多数活动设置了"只允许提交1次"
- 新增接口报错后尝试更新会导致用户困惑
- 简化流程，直接提示真实错误信息

---

## 流程图

### 首次报名流程

```
1. 获取登录二维码 (pc_code)
   ↓
2. 轮询登录状态 (pc_login)
   ↓ 登录成功，保存 access_token
3. 获取表单简要信息 (short_detail)
   ↓
4. 获取表单字段 (req_detail)
   ↓ 智能匹配名片数据
5. 提交新增报名 (v5/enroll)
   ↓
   成功 → 提示成功
   失败 → 显示错误信息
```

### Token 复用流程

```
第一个活动登录成功后，保存 token
   ↓
其他活动直接使用已保存的 token
   ↓
如果 token 失效 → 重新登录
```

---

## 技术细节

### URL 格式

活动链接格式：
```
https://p.baominggongju.com/share?eid=69844bcf8eaa2449c7a37fae
```

提取 eid：
- 从 URL 查询参数中提取：`?eid=xxxx`
- eid 是 24 位十六进制字符串

### Token 存储

存储位置：
```
~/.auto-form-filler/baoming_tokens.json
```

存储格式：
```json
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

Key 规则：
- 格式：`card_{名片ID}`
- 同一名片的所有活动共享同一个 token

### 字段匹配算法

使用共享匹配算法（与腾讯文档、金山文档一致）：
1. **精确匹配**：字段名完全相同，分数 100
2. **别名匹配**：包含在别名列表中，分数 90
3. **模糊匹配**：使用 SequenceMatcher 计算相似度
4. **阈值过滤**：分数 >= 50 才认为匹配

示例：
```python
表单字段: "姓名"
名片配置: "你的姓名、姓名、请填写你的姓名"
匹配结果: ✅ 选中（分数: 100）

表单字段: "选择哈哈"
名片配置: 无匹配项
匹配结果: ❌ 未匹配（最高分: 0）
```

### 选择题处理

单选题/多选题需要特殊处理：

1. 获取选项列表：
```python
options = field.get('new_options', [])
# [{"key": "0ffcd", "value": "哈哈"}, ...]
```

2. 匹配选项值：
```python
# 精确匹配
if opt['value'] == matched_value:
    use_key = opt['key']
    
# 模糊匹配
if matched_value in opt['value']:
    use_key = opt['key']
```

3. 提交时同时提供文本和 key：
```python
{
  "field_value": "哈哈",      # 显示文本
  "new_field_value": "0ffcd"  # 选项 key
}
```

---

## 常见问题

### Q1: 签名生成失败怎么办？

**错误信息**
```
⚠️ [报名工具] 缺少 pycryptodome 库，无法生成签名
```

**解决方法**
```bash
pip install pycryptodome
```

---

### Q2: 为什么提示"只允许提交1次"？

**原因**
活动设置了报名次数限制，用户已经提交过。

**解决方法**
- 新版本：直接提示错误，不支持更新
- 旧版本：可以尝试使用更新接口（已废弃）

---

### Q3: Token 什么时候会失效？

**失效场景**
- 长时间未使用（具体时长未知）
- 用户在其他设备登录
- 服务端主动清除

**检测方法**
```python
if '登录' in error_msg or 'token' in error_msg:
    # Token 失效，需要重新登录
```

---

### Q4: 为什么选择题填充失败？

**原因**
- 没有提供 `new_field_value`（选项 key）
- 选项值不匹配

**解决方法**
1. 确保获取了 `new_options` 列表
2. 精确匹配或模糊匹配选项值
3. 同时提供 `field_value` 和 `new_field_value`

---

## 更新日志

### 2024-02-10
- ✅ 简化提交流程：新增接口报错时直接返回错误
- ❌ 废弃更新接口：不再尝试更新已有报名记录
- ✅ 优化错误提示：直接显示 API 返回的真实错误信息

### 2024-01-XX
- ✅ 实现 Token 跨活动复用
- ✅ 实现智能字段匹配
- ✅ 支持单选/多选题自动映射

---

## 参考链接

- 报名工具官网：https://p.baominggongju.com
- API 基础地址：https://api-xcx-qunsou.weiyoubot.cn/xcx
