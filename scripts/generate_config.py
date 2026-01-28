#!/usr/bin/env python3
"""
CI 环境生成加密配置脚本
从环境变量读取敏感信息并生成加密配置
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.crypto import SecureConfig


def main():
    # 从环境变量读取
    mongodb_uri = os.environ.get('MONGODB_URI', '')
    jwt_secret_key = os.environ.get('JWT_SECRET_KEY', '')
    deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    
    if not mongodb_uri:
        print("❌ 错误: MONGODB_URI 环境变量未设置")
        sys.exit(1)
    
    if not jwt_secret_key:
        print("❌ 错误: JWT_SECRET_KEY 环境变量未设置")
        sys.exit(1)
    
    # 生成加密配置
    secure = SecureConfig()
    secure.set_multiple({
        'MONGODB_URI': mongodb_uri,
        'MONGODB_DB_NAME': 'auto-form-db',
        'JWT_SECRET_KEY': jwt_secret_key,
        'DEEPSEEK_CONFIG': {
            'apiKey': deepseek_api_key,
            'apiUrl': 'https://api.deepseek.com/chat/completions',
            'model': 'deepseek-chat',
            'maxTokens': 2000,
            'temperature': 0.8
        },
    })
    
    print("✅ Secure config generated successfully")


if __name__ == '__main__':
    main()
