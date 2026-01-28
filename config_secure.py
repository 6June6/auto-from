"""
安全配置文件
敏感信息从加密文件中读取
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 尝试从加密配置中读取敏感信息
def _load_secure_config():
    """加载加密配置"""
    try:
        from core.crypto import get_secure_config
        secure = get_secure_config()
        
        if secure.has_config():
            return {
                'MONGODB_URI': secure.get('MONGODB_URI'),
                'MONGODB_DB_NAME': secure.get('MONGODB_DB_NAME'),
                'JWT_SECRET_KEY': secure.get('JWT_SECRET_KEY'),
                'DEEPSEEK_CONFIG': secure.get('DEEPSEEK_CONFIG'),
            }
    except Exception as e:
        print(f"⚠️ 加载加密配置失败: {e}")
    
    return None


# 加载配置
_secure = _load_secure_config()

if _secure:
    # 从加密配置读取
    MONGODB_URI = _secure['MONGODB_URI']
    MONGODB_DB_NAME = _secure['MONGODB_DB_NAME']
    JWT_SECRET_KEY = _secure['JWT_SECRET_KEY']
    DEEPSEEK_CONFIG = _secure['DEEPSEEK_CONFIG']
else:
    # 配置未加密时的占位符（生产环境不应出现）
    print("⚠️ 未找到加密配置，请运行 python -m core.crypto 生成")
    MONGODB_URI = os.environ.get('MONGODB_URI', '')
    MONGODB_DB_NAME = os.environ.get('MONGODB_DB_NAME', 'auto-form-db')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', '')
    DEEPSEEK_CONFIG = {
        "apiKey": os.environ.get('DEEPSEEK_API_KEY', ''),
        "apiUrl": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "maxTokens": 2000,
        "temperature": 0.8
    }

# 应用配置（非敏感）
APP_NAME = "自动表单填写工具"
APP_VERSION = "2.0.0"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900

# 自动填写配置
AUTO_FILL_DELAY = 1000
MATCH_THRESHOLD = 0.6

# JWT 配置（非敏感部分）
JWT_EXPIRATION_DAYS = 30
MAX_DEVICES_PER_USER = 2

# 调试模式
DEBUG = False  # 生产环境关闭调试
