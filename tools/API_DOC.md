# 社交媒体解析 API 接口文档

**版本**: v7.2.0  
**基础地址**: `http://118.178.254.11:8900`  
**支持平台**: 小红书、抖音、Facebook、Instagram、Threads、TikTok

---

## 目录

- [通用说明](#通用说明)
- [1. 健康检查](#1-健康检查)
- [2. 缓存管理](#2-缓存管理)
- [3. 通用解析（自动识别平台）](#3-通用解析自动识别平台)
- [4. 小红书](#4-小红书)
- [5. 抖音](#5-抖音)
- [6. Facebook](#6-facebook)
- [7. Instagram](#7-instagram)
- [8. Threads](#8-threads)
- [9. TikTok](#9-tiktok)
- [返回值结构说明](#返回值结构说明)

---

## 通用说明

### 请求方式

所有接口支持 **GET** 请求，通用解析接口额外支持 **POST**。

### 统一响应格式

```json
{
  "success": true,
  "platform": "平台标识",
  "type": "profile / note / video / post",
  "data": { ... },
  "error": null,
  "cached": false
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `platform` | string | 平台标识：`xhs` / `douyin` / `facebook` / `instagram` / `threads` / `tiktok` |
| `type` | string | 数据类型：`profile`（主页）/ `note`（笔记）/ `video`（视频）/ `post`（帖子） |
| `data` | object | 解析后的数据（见各平台字段说明） |
| `error` | string | 错误信息，成功时为 `null` |
| `cached` | bool | 是否命中缓存。`true` = 缓存命中（毫秒级返回），`false` = 实时解析 |

### 缓存机制

- **默认 TTL**: 2 小时（7200 秒），相同 URL 在 TTL 内直接返回缓存，响应时间从 ~15s 降至 **< 100ms**
- **双层缓存**: 内存 + 磁盘 JSON 持久化，服务重启后自动恢复未过期的缓存
- **强制刷新**: 所有解析接口均支持 `refresh=true` 参数跳过缓存
- **仅缓存成功结果**: 解析失败的请求不会被缓存

### 通用参数

所有解析接口均支持以下参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `url` | string | 是 | - | 目标链接 |
| `refresh` | bool | 否 | `false` | 是否强制刷新（忽略缓存，重新解析） |

### 链接识别规则

| 平台 | 识别关键词 |
|------|-----------|
| 小红书 | `xhslink.com`、`xiaohongshu.com` |
| 抖音 | `douyin.com`、`iesdouyin.com` |
| Facebook | `facebook.com`、`fb.com` |
| Instagram | `instagram.com`、`instagr.am` |
| Threads | `threads.com`、`threads.net` |
| TikTok | `tiktok.com` |

### 需翻墙平台

Facebook、Instagram、Threads、TikTok 通过服务端 Clash 代理（`http://127.0.0.1:7890`）访问，响应时间约 15~25 秒。小红书、抖音无需代理，约 10~15 秒。

---

## 1. 健康检查

```
GET /
```

**响应示例**:

```json
{
  "status": "ok",
  "service": "social-media-parser-api",
  "version": "7.1.0",
  "platforms": ["xiaohongshu", "douyin", "facebook", "instagram", "threads", "tiktok"],
  "cache": {
    "total": 5,
    "valid": 4,
    "ttl_seconds": 7200
  }
}
```

---

## 2. 缓存管理

### 2.1 查看缓存状态

```
GET /cache/stats
```

**响应示例**:

```json
{
  "total": 5,
  "valid": 4,
  "ttl_seconds": 7200
}
```

| 字段 | 说明 |
|------|------|
| `total` | 缓存条目总数 |
| `valid` | 未过期的有效条目数 |
| `ttl_seconds` | 缓存过期时间（秒） |

### 2.2 清空缓存

```
DELETE /cache/clear
```

**响应示例**:

```json
{
  "cleared": 5
}
```

---

## 3. 通用解析（自动识别平台）

自动识别链接所属平台和类型（主页/笔记/视频），调用对应解析器。

### GET

```
GET /parse?url={链接}&refresh={true|false}
```

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 任意平台链接（支持短链接） |
| `refresh` | bool | 否 | 是否强制刷新缓存（默认 `false`） |

**示例**:

```bash
# 正常请求（自动使用缓存）
curl "http://118.178.254.11:8900/parse?url=https://www.tiktok.com/@entervan"

# 强制刷新
curl "http://118.178.254.11:8900/parse?url=https://www.tiktok.com/@entervan&refresh=true"
```

### POST

```
POST /parse
Content-Type: application/json
```

**请求体**:

```json
{
  "url": "https://www.instagram.com/enterbabyboss/",
  "refresh": false
}
```

---

## 4. 小红书

### 4.1 解析笔记

```
GET /xhs/note?url={笔记链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/xhs/note?url=https://www.xiaohongshu.com/explore/xxx"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `title` | string | 笔记标题 |
| `author` | string | 作者昵称 |
| `likes` | string | 点赞数 |
| `collects` | string | 收藏数 |
| `comments` | string | 评论数 |
| `content` | string | 笔记正文 |
| `note_id` | string | 笔记 ID |
| `publish_time` | string | 发布时间 |
| `tags` | string[] | 标签列表 |

### 4.2 解析主页

```
GET /xhs/profile?url={主页链接}
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `user_id` | string | 用户 ID |
| `xhs_id` | string | 小红书号 |
| `nickname` | string | 昵称 |
| `bio` | string | 个人简介 |
| `following` | string | 关注数 |
| `followers` | string | 粉丝数 |
| `likes_and_collects` | string | 获赞与收藏 |
| `avatar` | string | 头像 URL |
| `notes` | object[] | 近期笔记列表 |

---

## 5. 抖音

### 5.1 解析视频

```
GET /douyin/video?url={视频链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/douyin/video?url=https://www.douyin.com/video/xxx"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `video_id` | string | 视频 ID |
| `title` | string | 标题 |
| `author` | string | 作者昵称 |
| `description` | string | 视频描述 |
| `likes` | string | 点赞数 |
| `comments` | string | 评论数 |
| `shares` | string | 分享数 |
| `collects` | string | 收藏数 |
| `plays` | string | 播放量 |
| `music` | string | 背景音乐 |
| `tags` | string[] | 标签列表 |
| `cover` | string | 封面图 URL |

### 5.2 解析主页

```
GET /douyin/profile?url={主页链接}
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `sec_uid` | string | sec_uid |
| `douyin_id` | string | 抖音号 |
| `nickname` | string | 昵称 |
| `signature` | string | 个性签名 |
| `followers` | string | 粉丝数 |
| `following` | string | 关注数 |
| `likes_received` | string | 获赞数 |
| `works_count` | string | 作品数 |
| `avatar` | string | 头像 URL |
| `videos` | object[] | 近期视频列表 |

---

## 6. Facebook

### 6.1 解析主页

```
GET /facebook/profile?url={主页链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/facebook/profile?url=https://www.facebook.com/van.zhang.448341"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `fb_id` | string | Facebook 用户 ID |
| `name` | string | 显示名称 |
| `alt_name` | string | 别名（括号内的名字） |
| `bio` | string | 简介 |
| `category` | string | 类型（如 Digital creator） |
| `followers` | string | 粉丝数 |
| `following` | string | 关注数 |
| `likes` | string | 获赞数 |
| `talking_about` | string | 讨论人数 |
| `website` | string | 外部网站 |
| `avatar` | string | 头像 URL |
| `cover` | string | 封面图 URL |
| `intro_items` | string[] | 简介信息列表 |
| `recent_posts` | object[] | 最新帖子 `[{content}]` |

---

## 7. Instagram

### 7.1 解析主页

```
GET /instagram/profile?url={主页链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/instagram/profile?url=https://www.instagram.com/enterbabyboss/"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `username` | string | 用户名 |
| `full_name` | string | 显示名称 |
| `bio` | string | 个人简介 |
| `avatar` | string | 头像 URL |
| `posts_count` | string | 帖子数 |
| `followers` | string | 粉丝数 |
| `following` | string | 关注数 |
| `external_url` | string | 外部链接 |
| `is_verified` | bool | 是否认证 |
| `recent_posts` | object[] | 最新帖子 `[{url, type, id, caption}]` |

---

## 8. Threads

### 8.1 解析主页

```
GET /threads/profile?url={主页链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/threads/profile?url=https://www.threads.com/@enterbabyboss"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `username` | string | 用户名 |
| `full_name` | string | 显示名称 |
| `bio` | string | 个人简介 |
| `avatar` | string | 头像 URL |
| `followers` | string | 粉丝数 |
| `threads_count` | string | 帖子数 |
| `tags` | string[] | 兴趣标签 |
| `website` | string | 外部网站 |
| `instagram_url` | string | 关联 Instagram 链接 |
| `recent_posts` | object[] | 最新帖子 `[{url, id, author, content}]` |

### 8.2 解析帖子

```
GET /threads/post?url={帖子链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/threads/post?url=https://www.threads.com/@enterbabyboss/post/DVBcK9TDhA4"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `post_id` | string | 帖子 ID |
| `author_username` | string | 作者用户名 |
| `author_name` | string | 作者显示名称 |
| `author_avatar` | string | 作者头像 URL |
| `content` | string | 帖子正文 |
| `tags` | string[] | 标签列表 |
| `image` | string | 配图 URL |
| `views` | string | 浏览量 |
| `likes` | string | 点赞数 |
| `replies` | string | 回复数 |
| `reposts` | string | 转发数 |
| `shares` | string | 分享数 |
| `publish_time` | string | 发布时间（ISO 8601） |
| `comments` | object[] | 评论列表 `[{author, content}]` |

---

## 9. TikTok

### 9.1 解析主页

```
GET /tiktok/profile?url={主页链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/tiktok/profile?url=https://www.tiktok.com/@entervan"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `username` | string | 用户名 |
| `nickname` | string | 昵称 |
| `bio` | string | 个人简介 |
| `avatar` | string | 头像 URL |
| `following` | string | 关注数 |
| `followers` | string | 粉丝数 |
| `likes` | string | 获赞总数 |
| `website` | string | 外部网站 |

### 9.2 解析视频

```
GET /tiktok/video?url={视频链接}
```

**示例**:

```bash
curl "http://118.178.254.11:8900/tiktok/video?url=https://www.tiktok.com/@entervan/video/7263063850134686977"
```

**`data` 字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 最终链接 |
| `video_id` | string | 视频 ID |
| `author_username` | string | 作者用户名 |
| `author_nickname` | string | 作者昵称 |
| `title` | string | 视频标题 |
| `description` | string | 视频描述 |
| `tags` | string[] | 标签列表（如 `#生活`） |
| `likes` | string | 点赞数 |
| `comments` | string | 评论数 |
| `shares` | string | 分享数 |
| `bookmarks` | string | 收藏数 |
| `music` | string | 背景音乐 |
| `publish_date` | string | 发布日期 |

---

## 返回值结构说明

### 成功（实时解析）

```json
{
  "success": true,
  "platform": "tiktok",
  "type": "profile",
  "data": {
    "username": "entervan",
    "nickname": "張恩慈@確認鍵",
    "followers": "1162",
    "following": "62",
    "likes": "13.8K",
    "bio": "確認鍵網路行銷創辦人since2019...",
    "avatar": "https://...",
    "website": "enterimc.com/",
    "url": "https://www.tiktok.com/@entervan",
    "error": ""
  },
  "error": null,
  "cached": false
}
```

### 成功（命中缓存，< 100ms 返回）

```json
{
  "success": true,
  "platform": "tiktok",
  "type": "profile",
  "data": { ... },
  "error": null,
  "cached": true
}
```

### 失败

```json
{
  "success": false,
  "platform": "unknown",
  "type": "unknown",
  "data": null,
  "error": "无法识别链接平台，支持: 小红书、抖音、Facebook、Instagram、Threads、TikTok",
  "cached": false
}
```

### 错误码

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 请求成功（`success` 字段可能为 `false`） |
| 400 | 参数错误（url 为空、无法识别平台） |
| 500 | 服务器内部错误 |

---

## 接口一览表

| 方法 | 路径 | 说明 | 需翻墙 |
|------|------|------|--------|
| GET | `/` | 健康检查（含缓存状态） | - |
| GET | `/cache/stats` | 查看缓存状态 | - |
| DELETE | `/cache/clear` | 清空所有缓存 | - |
| GET/POST | `/parse` | 自动识别平台并解析 | 视平台 |
| GET | `/xhs/note` | 小红书笔记解析 | 否 |
| GET | `/xhs/profile` | 小红书主页解析 | 否 |
| GET | `/douyin/video` | 抖音视频解析 | 否 |
| GET | `/douyin/profile` | 抖音主页解析 | 否 |
| GET | `/facebook/profile` | Facebook 主页解析 | 是 |
| GET | `/instagram/profile` | Instagram 主页解析 | 是 |
| GET | `/threads/profile` | Threads 主页解析 | 是 |
| GET | `/threads/post` | Threads 帖子解析 | 是 |
| GET | `/tiktok/profile` | TikTok 主页解析 | 是 |
| GET | `/tiktok/video` | TikTok 视频解析 | 是 |

共 **14 个接口**，覆盖 **6 个平台**，支持 **主页 / 笔记 / 视频 / 帖子** 四种内容类型。

所有解析接口均支持 `refresh=true` 参数强制刷新缓存。

## 性能参考

| 场景 | 响应时间 |
|------|---------|
| 缓存命中 | **< 100ms** |
| 小红书 / 抖音（无缓存） | ~10-15s |
| Facebook / Instagram / Threads / TikTok（无缓存） | ~15-25s |
| 缓存 TTL | 2 小时（7200 秒） |
