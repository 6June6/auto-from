# 报名工具 Token 自动刷新部署指南

## 概述

`refresh_baoming_tokens.py` 是一个定时刷新报名工具 Token 的脚本，可以保持 Token 活跃状态，防止过期。

## 功能特性

- ✅ 自动刷新所有 Token
- ✅ 检测并删除失效 Token
- ✅ 清理长期未使用的 Token
- ✅ 支持多种部署方式
- ✅ 完善的日志记录
- ✅ 错误处理和重试

## 快速开始

### 运行一次

```bash
cd /Users/chenchen/Desktop/开发项目/auto-form-filler-py
python tools/refresh_baoming_tokens.py
```

### 查看帮助

```bash
python tools/refresh_baoming_tokens.py --help
```

## 使用方式

### 1. 单次运行模式

**基础用法**
```bash
python tools/refresh_baoming_tokens.py
```

**只刷新最近使用的 Token**
```bash
# 只刷新 7 天内使用过的 Token
python tools/refresh_baoming_tokens.py --max-age-days 7
```

**刷新并清理过期 Token**
```bash
# 刷新 Token 并清理 30 天未使用的
python tools/refresh_baoming_tokens.py --cleanup-days 30
```

**保存日志到文件**
```bash
python tools/refresh_baoming_tokens.py --log-file /var/log/baoming_refresh.log
```

**详细输出（调试）**
```bash
python tools/refresh_baoming_tokens.py --verbose
```

### 2. 内置定时器模式

需要先安装 `schedule` 库：
```bash
pip install schedule
```

**启动定时器**
```bash
# 每 6 小时刷新一次
python tools/refresh_baoming_tokens.py --scheduler --interval 6

# 启动时立即执行一次
python tools/refresh_baoming_tokens.py --scheduler --interval 6 --run-immediately

# 后台运行
nohup python tools/refresh_baoming_tokens.py --scheduler --interval 6 \
  --log-file /var/log/baoming_refresh.log > /dev/null 2>&1 &
```

## 部署方式

### 方式 1: Cron 定时任务（推荐）

Cron 是最简单可靠的定时任务方案。

#### 1.1 编辑 Crontab

```bash
crontab -e
```

#### 1.2 添加定时任务

```cron
# 每 6 小时刷新一次 Token
0 */6 * * * /usr/bin/python3 /path/to/auto-form-filler-py/tools/refresh_baoming_tokens.py >> /var/log/baoming_refresh.log 2>&1

# 每天凌晨 2 点刷新并清理 30 天未使用的 Token
0 2 * * * /usr/bin/python3 /path/to/auto-form-filler-py/tools/refresh_baoming_tokens.py --cleanup-days 30 >> /var/log/baoming_refresh.log 2>&1

# 每 4 小时刷新最近 7 天使用过的 Token
0 */4 * * * /usr/bin/python3 /path/to/auto-form-filler-py/tools/refresh_baoming_tokens.py --max-age-days 7 >> /var/log/baoming_refresh.log 2>&1
```

#### 1.3 Cron 时间表达式说明

```
*  *  *  *  *
│  │  │  │  │
│  │  │  │  └─ 星期几 (0-7, 0 和 7 都表示周日)
│  │  │  └──── 月份 (1-12)
│  │  └─────── 日期 (1-31)
│  └────────── 小时 (0-23)
└───────────── 分钟 (0-59)
```

常用示例：
- `0 */6 * * *` - 每 6 小时执行一次（0:00, 6:00, 12:00, 18:00）
- `0 2 * * *` - 每天凌晨 2 点执行
- `*/30 * * * *` - 每 30 分钟执行一次
- `0 0 * * 0` - 每周日凌晨执行

#### 1.4 查看 Cron 日志

```bash
# 查看最近的日志
tail -f /var/log/baoming_refresh.log

# 查看完整日志
cat /var/log/baoming_refresh.log

# 只看错误
grep "ERROR" /var/log/baoming_refresh.log
```

### 方式 2: systemd Timer（推荐用于生产环境）

systemd timer 提供更强大的定时任务管理。

#### 2.1 创建服务文件

创建 `/etc/systemd/system/baoming-refresh.service`：

```ini
[Unit]
Description=Refresh Baoming Tool Tokens
After=network.target mongod.service

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/auto-form-filler-py
ExecStart=/usr/bin/python3 /path/to/auto-form-filler-py/tools/refresh_baoming_tokens.py --max-age-days 7
StandardOutput=append:/var/log/baoming_refresh.log
StandardError=append:/var/log/baoming_refresh.log

[Install]
WantedBy=multi-user.target
```

#### 2.2 创建定时器文件

创建 `/etc/systemd/system/baoming-refresh.timer`：

```ini
[Unit]
Description=Refresh Baoming Tool Tokens Timer
Requires=baoming-refresh.service

[Timer]
# 每 6 小时执行一次
OnCalendar=*-*-* 00,06,12,18:00:00
# 系统启动 5 分钟后首次执行
OnBootSec=5min
# 如果错过了执行时间，启动后立即执行
Persistent=true

[Install]
WantedBy=timers.target
```

#### 2.3 启用并启动

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用定时器（开机自启）
sudo systemctl enable baoming-refresh.timer

# 启动定时器
sudo systemctl start baoming-refresh.timer

# 查看定时器状态
sudo systemctl status baoming-refresh.timer

# 查看下次执行时间
sudo systemctl list-timers baoming-refresh.timer

# 立即执行一次（测试）
sudo systemctl start baoming-refresh.service
```

#### 2.4 查看日志

```bash
# 查看服务日志
sudo journalctl -u baoming-refresh.service

# 实时查看日志
sudo journalctl -u baoming-refresh.service -f

# 查看最近 50 条日志
sudo journalctl -u baoming-refresh.service -n 50

# 查看今天的日志
sudo journalctl -u baoming-refresh.service --since today
```

### 方式 3: Docker 部署

#### 3.1 创建 Dockerfile

创建 `Dockerfile.refresh`：

```dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建日志目录
RUN mkdir -p /var/log

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 默认命令
CMD ["python", "tools/refresh_baoming_tokens.py", "--scheduler", "--interval", "6", "--run-immediately"]
```

#### 3.2 构建镜像

```bash
docker build -f Dockerfile.refresh -t baoming-token-refresh .
```

#### 3.3 运行容器

```bash
# 单次运行
docker run --rm \
  -v $(pwd)/logs:/var/log \
  --network=host \
  baoming-token-refresh \
  python tools/refresh_baoming_tokens.py

# 定时运行（后台）
docker run -d \
  --name baoming-refresh \
  --restart=unless-stopped \
  -v $(pwd)/logs:/var/log \
  --network=host \
  baoming-token-refresh

# 查看日志
docker logs -f baoming-refresh
```

#### 3.4 Docker Compose

创建 `docker-compose.refresh.yml`：

```yaml
version: '3.8'

services:
  token-refresh:
    build:
      context: .
      dockerfile: Dockerfile.refresh
    container_name: baoming-token-refresh
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./logs:/var/log
    environment:
      - PYTHONUNBUFFERED=1
    command: >
      python tools/refresh_baoming_tokens.py
      --scheduler
      --interval 6
      --run-immediately
      --log-file /var/log/baoming_refresh.log
```

运行：
```bash
docker-compose -f docker-compose.refresh.yml up -d
```

## 日志管理

### 日志格式

```
2024-02-10 15:30:00 [INFO] ============================================================
2024-02-10 15:30:00 [INFO] 🚀 开始刷新报名工具 Token
2024-02-10 15:30:00 [INFO] ============================================================
2024-02-10 15:30:00 [INFO] 📊 找到 5 个 Token 需要刷新
2024-02-10 15:30:00 [INFO] ------------------------------------------------------------
2024-02-10 15:30:00 [INFO] 
2024-02-10 15:30:00 [INFO] [1/5] 名片: 统一
2024-02-10 15:30:00 [INFO]   用户: 张三
2024-02-10 15:30:00 [INFO]   最后使用: 2024-02-09 10:30:00
2024-02-10 15:30:00 [INFO] 🔄 刷新 Token: 名片 '统一' (ID: 69830fb551c6db84fb459e01)
2024-02-10 15:30:01 [INFO]   ✅ Token 有效，已更新使用时间
```

### 日志轮转

创建 `/etc/logrotate.d/baoming-refresh`：

```
/var/log/baoming_refresh.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 your_user your_group
}
```

手动轮转：
```bash
sudo logrotate -f /etc/logrotate.d/baoming-refresh
```

### 日志查看命令

```bash
# 查看最新日志
tail -f /var/log/baoming_refresh.log

# 查看最近 100 行
tail -n 100 /var/log/baoming_refresh.log

# 搜索错误
grep "ERROR" /var/log/baoming_refresh.log

# 搜索失败的 Token
grep "失效" /var/log/baoming_refresh.log

# 统计刷新成功率
grep "刷新统计" /var/log/baoming_refresh.log | tail -n 1
```

## 监控和告警

### 基础监控脚本

创建 `monitor_token_refresh.sh`：

```bash
#!/bin/bash

LOG_FILE="/var/log/baoming_refresh.log"
ALERT_EMAIL="admin@example.com"

# 检查日志是否有最近更新（1小时内）
LAST_UPDATE=$(stat -f %m "$LOG_FILE")
NOW=$(date +%s)
DIFF=$((NOW - LAST_UPDATE))

if [ $DIFF -gt 3600 ]; then
    echo "⚠️ 警告: Token 刷新脚本超过 1 小时未运行" | mail -s "Token刷新异常" "$ALERT_EMAIL"
fi

# 检查是否有错误
ERROR_COUNT=$(grep -c "ERROR" "$LOG_FILE" | tail -n 100)
if [ $ERROR_COUNT -gt 5 ]; then
    echo "⚠️ 警告: 发现 $ERROR_COUNT 个错误" | mail -s "Token刷新错误" "$ALERT_EMAIL"
fi
```

定时检查（Cron）：
```cron
*/30 * * * * /path/to/monitor_token_refresh.sh
```

### Prometheus 监控

导出指标示例：

```python
# 在脚本中添加 Prometheus 指标导出
from prometheus_client import Counter, Gauge, push_to_gateway

refresh_success = Counter('baoming_token_refresh_success', 'Successful token refreshes')
refresh_failed = Counter('baoming_token_refresh_failed', 'Failed token refreshes')
token_count = Gauge('baoming_token_count', 'Total number of tokens')

# 在刷新完成后推送指标
push_to_gateway('localhost:9091', job='baoming_token_refresh', registry=registry)
```

## 故障排查

### 常见问题

#### 1. 数据库连接失败

**错误信息**:
```
❌ MongoDB 连接失败: ServerSelectionTimeoutError
```

**解决方法**:
```bash
# 检查 MongoDB 是否运行
sudo systemctl status mongod

# 检查配置文件
cat config.py

# 测试连接
python -c "from database.models import init_database; init_database()"
```

#### 2. Token 刷新失败

**错误信息**:
```
⚠️ Token 已失效: invalid access_token
```

**解决方法**:
- Token 确实已失效，需要用户重新登录
- 脚本会自动删除失效的 Token

#### 3. 权限问题

**错误信息**:
```
Permission denied: /var/log/baoming_refresh.log
```

**解决方法**:
```bash
# 创建日志文件并设置权限
sudo touch /var/log/baoming_refresh.log
sudo chown your_user:your_group /var/log/baoming_refresh.log
sudo chmod 644 /var/log/baoming_refresh.log
```

#### 4. Cron 不执行

**排查步骤**:
```bash
# 1. 检查 Cron 服务
sudo systemctl status cron

# 2. 检查 Cron 日志
sudo tail -f /var/log/syslog | grep CRON

# 3. 测试脚本
/usr/bin/python3 /path/to/refresh_baoming_tokens.py --verbose

# 4. 检查 Python 路径
which python3

# 5. 使用绝对路径
0 */6 * * * cd /path/to/project && /usr/bin/python3 tools/refresh_baoming_tokens.py
```

### 调试模式

启用详细日志：
```bash
python tools/refresh_baoming_tokens.py --verbose --log-file debug.log
```

## 性能优化

### 1. 批量刷新

如果 Token 数量很多，可以分批刷新：

```python
# 修改脚本，添加批量处理
BATCH_SIZE = 10  # 每批处理 10 个

for i in range(0, total, BATCH_SIZE):
    batch = tokens[i:i+BATCH_SIZE]
    # 处理这一批
    time.sleep(5)  # 批次间休息 5 秒
```

### 2. 并发刷新

使用多线程加速（谨慎使用，避免请求过快）：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(refresh_single_token, token): token for token in tokens}
    for future in as_completed(futures):
        result = future.result()
```

### 3. 智能刷新

只刷新即将过期的 Token：

```bash
# 只刷新 3 天内使用过的
python tools/refresh_baoming_tokens.py --max-age-days 3

# 配合 Cron，不同频率刷新
# 每 4 小时刷新活跃 Token
0 */4 * * * python tools/refresh_baoming_tokens.py --max-age-days 3

# 每天刷新全部 Token
0 3 * * * python tools/refresh_baoming_tokens.py
```

## 最佳实践

1. **合理设置刷新频率**
   - 建议每 4-8 小时刷新一次
   - 高峰期可以适当增加频率

2. **定期清理过期 Token**
   - 建议每周清理一次 30 天未使用的 Token
   - 避免数据库膨胀

3. **日志管理**
   - 启用日志轮转
   - 保留最近 7-30 天的日志
   - 定期归档重要日志

4. **监控和告警**
   - 设置监控检查脚本是否正常运行
   - 失败率超过阈值时发送告警
   - 监控数据库连接状态

5. **容错处理**
   - 单个 Token 失败不影响其他 Token
   - 网络异常时自动重试
   - 记录详细错误信息

## 附录

### A. 完整的 Crontab 示例

```cron
# 报名工具 Token 自动刷新
# 项目路径: /opt/auto-form-filler-py
# 日志路径: /var/log/baoming_refresh.log

# 每 6 小时刷新活跃 Token（7 天内使用过的）
0 */6 * * * cd /opt/auto-form-filler-py && /usr/bin/python3 tools/refresh_baoming_tokens.py --max-age-days 7 >> /var/log/baoming_refresh.log 2>&1

# 每天凌晨 2 点刷新全部 Token
0 2 * * * cd /opt/auto-form-filler-py && /usr/bin/python3 tools/refresh_baoming_tokens.py >> /var/log/baoming_refresh.log 2>&1

# 每周日凌晨 3 点清理 30 天未使用的 Token
0 3 * * 0 cd /opt/auto-form-filler-py && /usr/bin/python3 tools/refresh_baoming_tokens.py --cleanup-days 30 >> /var/log/baoming_refresh.log 2>&1
```

### B. systemd 完整配置

**服务文件** (`/etc/systemd/system/baoming-refresh.service`):
```ini
[Unit]
Description=Refresh Baoming Tool Tokens
After=network.target mongod.service
Wants=mongod.service

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/opt/auto-form-filler-py
Environment="PYTHONPATH=/opt/auto-form-filler-py"
ExecStart=/usr/bin/python3 /opt/auto-form-filler-py/tools/refresh_baoming_tokens.py --max-age-days 7
StandardOutput=append:/var/log/baoming_refresh.log
StandardError=append:/var/log/baoming_refresh.log
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

**定时器文件** (`/etc/systemd/system/baoming-refresh.timer`):
```ini
[Unit]
Description=Refresh Baoming Tool Tokens Every 6 Hours
Requires=baoming-refresh.service

[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
OnBootSec=5min
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
```

### C. 监控脚本

**Bash 监控脚本** (`monitor_refresh.sh`):
```bash
#!/bin/bash

LOG_FILE="/var/log/baoming_refresh.log"
ALERT_EMAIL="admin@example.com"
MAX_AGE_HOURS=8

# 检查日志文件是否存在
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ 日志文件不存在: $LOG_FILE"
    exit 1
fi

# 检查最后更新时间
LAST_UPDATE=$(stat -f %m "$LOG_FILE" 2>/dev/null || stat -c %Y "$LOG_FILE")
NOW=$(date +%s)
HOURS_SINCE_UPDATE=$(( (NOW - LAST_UPDATE) / 3600 ))

if [ $HOURS_SINCE_UPDATE -gt $MAX_AGE_HOURS ]; then
    MESSAGE="⚠️ Token 刷新脚本已 $HOURS_SINCE_UPDATE 小时未运行"
    echo "$MESSAGE"
    echo "$MESSAGE" | mail -s "Token刷新异常告警" "$ALERT_EMAIL"
fi

# 检查最近的错误
RECENT_ERRORS=$(tail -n 200 "$LOG_FILE" | grep -c "ERROR")
if [ $RECENT_ERRORS -gt 10 ]; then
    MESSAGE="⚠️ 最近 200 行日志中发现 $RECENT_ERRORS 个错误"
    echo "$MESSAGE"
    echo "$MESSAGE" | mail -s "Token刷新错误告警" "$ALERT_EMAIL"
fi

# 检查 Token 失效数量
EXPIRED_COUNT=$(tail -n 200 "$LOG_FILE" | grep -c "已失效")
if [ $EXPIRED_COUNT -gt 5 ]; then
    MESSAGE="⚠️ 发现 $EXPIRED_COUNT 个失效 Token"
    echo "$MESSAGE"
fi

echo "✅ 监控检查完成"
```

## 更新日志

### 2024-02-10
- ✅ 创建 Token 自动刷新脚本
- ✅ 支持单次运行和定时运行
- ✅ 支持多种部署方式
- ✅ 完善的日志和监控
- ✅ 自动清理失效 Token
