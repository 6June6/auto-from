"""
配置加密模块
用于加密和解密敏感配置信息
"""
import base64
import hashlib
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

# 使用 cryptography 库进行 AES 加密
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ cryptography 库未安装，使用基础加密")


class ConfigCrypto:
    """配置加密解密器"""
    
    # 固定的盐值（混淆后难以提取）
    _SALT_PARTS = [b'\x8f', b'\x2a', b'\x91', b'\xc5', b'\x3d', b'\xe7', b'\x6b', b'\xf4',
                   b'\x18', b'\x73', b'\xd9', b'\x5e', b'\xa2', b'\x0f', b'\xcc', b'\x47']
    
    def __init__(self, key_source: Optional[str] = None):
        """
        初始化加密器
        
        Args:
            key_source: 密钥来源，默认使用机器特征
        """
        self._key = self._derive_key(key_source)
        if CRYPTO_AVAILABLE:
            self._fernet = Fernet(self._key)
        else:
            self._fernet = None
    
    @classmethod
    def _get_salt(cls) -> bytes:
        """获取盐值"""
        return b''.join(cls._SALT_PARTS)
    
    def _derive_key(self, key_source: Optional[str] = None) -> bytes:
        """
        从来源派生密钥
        
        Args:
            key_source: 密钥来源字符串
        
        Returns:
            32字节密钥
        """
        if key_source is None:
            # 使用机器特征作为密钥来源
            key_source = self._get_machine_id()
        
        if CRYPTO_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._get_salt(),
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key_source.encode()))
        else:
            # 简单的密钥派生
            key = hashlib.pbkdf2_hmac(
                'sha256',
                key_source.encode(),
                self._get_salt(),
                100000,
                dklen=32
            )
            key = base64.urlsafe_b64encode(key)
        
        return key
    
    def _get_machine_id(self) -> str:
        """
        获取机器唯一标识
        
        Returns:
            机器ID字符串
        """
        import platform
        import uuid
        
        # 组合多个机器特征
        features = [
            platform.node(),  # 主机名
            platform.machine(),  # 架构
            str(uuid.getnode()),  # MAC 地址
        ]
        
        # 添加固定的应用标识
        features.append("auto-form-filler-v2")
        
        return "|".join(features)
    
    def encrypt(self, data: str) -> str:
        """
        加密字符串
        
        Args:
            data: 明文字符串
        
        Returns:
            加密后的 base64 字符串
        """
        if CRYPTO_AVAILABLE and self._fernet:
            encrypted = self._fernet.encrypt(data.encode())
            return encrypted.decode()
        else:
            # 基础混淆（不是真正的加密，仅用于简单保护）
            return self._simple_encode(data)
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密字符串
        
        Args:
            encrypted_data: 加密的 base64 字符串
        
        Returns:
            解密后的明文
        """
        try:
            if CRYPTO_AVAILABLE and self._fernet:
                decrypted = self._fernet.decrypt(encrypted_data.encode())
                return decrypted.decode()
            else:
                return self._simple_decode(encrypted_data)
        except Exception as e:
            print(f"⚠️ 解密失败: {e}")
            return encrypted_data
    
    def _simple_encode(self, data: str) -> str:
        """简单编码（当 cryptography 不可用时使用）"""
        # XOR 混淆 + base64
        key_bytes = self._key[:len(data.encode())]
        if len(key_bytes) < len(data.encode()):
            key_bytes = (key_bytes * (len(data.encode()) // len(key_bytes) + 1))[:len(data.encode())]
        
        encoded = bytes([a ^ b for a, b in zip(data.encode(), key_bytes)])
        return base64.b64encode(encoded).decode()
    
    def _simple_decode(self, data: str) -> str:
        """简单解码"""
        try:
            decoded_bytes = base64.b64decode(data.encode())
            key_bytes = self._key[:len(decoded_bytes)]
            if len(key_bytes) < len(decoded_bytes):
                key_bytes = (key_bytes * (len(decoded_bytes) // len(key_bytes) + 1))[:len(decoded_bytes)]
            
            return bytes([a ^ b for a, b in zip(decoded_bytes, key_bytes)]).decode()
        except:
            return data
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """加密字典为字符串"""
        json_str = json.dumps(data, ensure_ascii=False)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """解密字符串为字典"""
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)


class SecureConfig:
    """安全配置管理器"""
    
    # 加密配置文件名
    CONFIG_FILE = ".secure_config"
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化安全配置管理器
        
        Args:
            base_dir: 配置文件所在目录
        """
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self.config_path = self.base_dir / self.CONFIG_FILE
        self.crypto = ConfigCrypto()
        self._config_cache: Optional[Dict[str, Any]] = None
    
    def _load_raw_config(self) -> Dict[str, Any]:
        """加载原始加密配置"""
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                encrypted = f.read().strip()
                if encrypted:
                    return self.crypto.decrypt_dict(encrypted)
        except Exception as e:
            print(f"⚠️ 加载配置失败: {e}")
        
        return {}
    
    def _save_raw_config(self, config: Dict[str, Any]) -> bool:
        """保存加密配置"""
        try:
            encrypted = self.crypto.encrypt_dict(config)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            self._config_cache = config
            return True
        except Exception as e:
            print(f"⚠️ 保存配置失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        if self._config_cache is None:
            self._config_cache = self._load_raw_config()
        return self._config_cache.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        if self._config_cache is None:
            self._config_cache = self._load_raw_config()
        self._config_cache[key] = value
        return self._save_raw_config(self._config_cache)
    
    def set_multiple(self, items: Dict[str, Any]) -> bool:
        """批量设置配置项"""
        if self._config_cache is None:
            self._config_cache = self._load_raw_config()
        self._config_cache.update(items)
        return self._save_raw_config(self._config_cache)
    
    def has_config(self) -> bool:
        """检查是否已有加密配置"""
        return self.config_path.exists()
    
    def clear(self) -> bool:
        """清除配置"""
        try:
            if self.config_path.exists():
                self.config_path.unlink()
            self._config_cache = None
            return True
        except:
            return False


def generate_encrypted_config():
    """
    从当前 config.py 生成加密配置文件
    这是一个工具函数，用于首次加密配置
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    
    # 导入当前配置（明文）
    try:
        from config import MONGODB_URI, MONGODB_DB_NAME, JWT_SECRET_KEY, DEEPSEEK_CONFIG
        
        # 创建安全配置管理器
        secure = SecureConfig()
        
        # 加密保存敏感配置
        secure.set_multiple({
            'MONGODB_URI': MONGODB_URI,
            'MONGODB_DB_NAME': MONGODB_DB_NAME,
            'JWT_SECRET_KEY': JWT_SECRET_KEY,
            'DEEPSEEK_CONFIG': DEEPSEEK_CONFIG,
        })
        
        print("✅ 加密配置已生成到 .secure_config 文件")
        print("⚠️ 请修改 config.py，移除明文敏感信息")
        return True
        
    except ImportError as e:
        print(f"❌ 导入配置失败: {e}")
        return False


def get_secure_config() -> SecureConfig:
    """获取安全配置管理器单例"""
    if not hasattr(get_secure_config, '_instance'):
        get_secure_config._instance = SecureConfig()
    return get_secure_config._instance


if __name__ == '__main__':
    # 运行此文件生成加密配置
    generate_encrypted_config()
