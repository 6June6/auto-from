"""
配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 数据库配置 - MongoDB
# 连接字符串 - 使用 auto-form-db 数据库，admin 作为认证源
MONGODB_URI = "mongodb://mp-97cf738a-ef6a-4a9a-a80c-53378cb9ada3:4b0c5b88d8caafb5e6cfe06f4ef088bf@dds-bp17151e3fa0eca41972-pub.mongodb.rds.aliyuncs.com:3717,dds-bp17151e3fa0eca42468-pub.mongodb.rds.aliyuncs.com:3717/auto-form-db?replicaSet=mgset-90193512&authSource=admin"
MONGODB_DB_NAME = "auto-form-db"  # 使用的数据库名称

# 应用配置
APP_NAME = "自动表单填写工具"
APP_VERSION = "2.0.0"  # MongoDB 版本
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

# 自动填写配置
AUTO_FILL_DELAY = 1000  # 毫秒，页面加载后延迟执行时间（优化后1秒即可）
MATCH_THRESHOLD = 0.6   # 字段匹配相似度阈值

# JWT 认证配置
JWT_SECRET_KEY = "auto-form-filler-secret-key-2025-change-in-production"  # 生产环境请修改
JWT_EXPIRATION_DAYS = 30  # Token 过期时间（天）
MAX_DEVICES_PER_USER = 2  # 每个用户最多绑定设备数

# 调试模式
DEBUG = True

# DeepSeek AI 配置
DEEPSEEK_CONFIG = {
    "apiKey": "sk-090fcb34e8704302a2ca9920f24bd530",
    "apiUrl": "https://api.deepseek.com/chat/completions",
    "model": "deepseek-chat",
    "maxTokens": 2000,
    "temperature": 0.8
}

