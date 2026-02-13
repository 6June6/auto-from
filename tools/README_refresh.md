# Token 自动刷新工具

## 快速开始

### 运行一次
```bash
python tools/refresh_baoming_tokens.py
```

### 定时运行（Cron）
```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每 6 小时）
0 */6 * * * cd /path/to/auto-form-filler-py && python tools/refresh_baoming_tokens.py >> /var/log/baoming_refresh.log 2>&1
```

### 内置定时器
```bash
# 安装依赖
pip install schedule

# 启动定时器（每 6 小时）
python tools/refresh_baoming_tokens.py --scheduler --interval 6 --run-immediately
```

## 常用命令

```bash
# 只刷新 7 天内使用过的 Token
python tools/refresh_baoming_tokens.py --max-age-days 7

# 刷新并清理 30 天未使用的 Token
python tools/refresh_baoming_tokens.py --cleanup-days 30

# 保存日志
python tools/refresh_baoming_tokens.py --log-file /var/log/baoming_refresh.log

# 详细输出
python tools/refresh_baoming_tokens.py --verbose

# 查看帮助
python tools/refresh_baoming_tokens.py --help
```

## 工作原理

1. 从数据库读取所有 Token
2. 调用 `/enroll/v3/detail` 接口验证 Token
3. 更新 `last_used` 时间
4. 删除失效的 Token

## 推荐配置

### Cron 方式（推荐）
```cron
# 每 6 小时刷新活跃 Token
0 */6 * * * cd /opt/auto-form-filler-py && python tools/refresh_baoming_tokens.py --max-age-days 7 >> /var/log/baoming_refresh.log 2>&1

# 每天凌晨刷新全部
0 2 * * * cd /opt/auto-form-filler-py && python tools/refresh_baoming_tokens.py >> /var/log/baoming_refresh.log 2>&1

# 每周清理过期
0 3 * * 0 cd /opt/auto-form-filler-py && python tools/refresh_baoming_tokens.py --cleanup-days 30 >> /var/log/baoming_refresh.log 2>&1
```

## 日志查看

```bash
# 实时查看
tail -f /var/log/baoming_refresh.log

# 查看最近 100 行
tail -n 100 /var/log/baoming_refresh.log

# 搜索错误
grep "ERROR" /var/log/baoming_refresh.log

# 查看统计
grep "刷新统计" /var/log/baoming_refresh.log
```

## 详细文档

- [完整部署指南](../docs/refresh_tokens_deployment.md)
- [Token 数据库存储](../docs/baoming_token_migration.md)
- [报名工具 API](../docs/baoming_tool_api.md)
