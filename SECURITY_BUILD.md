# 代码混淆加固指南

本文档说明如何对项目进行代码混淆和敏感信息加密保护。

## 安全加固方案概览

1. **敏感配置加密** - 数据库连接、API Key 等敏感信息加密存储
2. **代码混淆** - 使用 PyArmor 混淆 Python 代码
3. **打包保护** - 结合 PyInstaller 打包成可执行文件

## 快速开始

### 1. 安装依赖

```bash
pip install cryptography pyarmor pyinstaller
```

### 2. 生成加密配置

```bash
# 从当前 config.py 生成加密配置文件
python -m core.crypto
```

这会在项目根目录生成 `.secure_config` 文件，包含加密后的敏感信息。

### 3. 混淆并打包

```bash
# 完整混淆 + 打包
python obfuscate.py --mode full

# 仅混淆，不打包
python obfuscate.py --mode full --no-pack

# 简单混淆（编译为 .pyc）
python obfuscate.py --mode simple

# 仅加密配置，不混淆
python obfuscate.py --mode encrypt-only
```

## 配置加密详解

### 工作原理

- 敏感配置使用 AES-256 (Fernet) 加密
- 密钥基于机器特征（主机名、MAC 地址等）自动派生
- 加密配置存储在 `.secure_config` 文件中
- 程序启动时自动解密读取

### 手动操作

```python
# 加密新配置
from core.crypto import get_secure_config

secure = get_secure_config()
secure.set('MONGODB_URI', 'mongodb://...')
secure.set('JWT_SECRET_KEY', 'your-secret')

# 读取配置
uri = secure.get('MONGODB_URI')
```

### 重要提示

1. `.secure_config` 文件已添加到 `.gitignore`，**不会提交到 Git**
2. 打包时需要将 `.secure_config` 一起打包
3. 加密配置基于机器特征，换机器需要重新生成

## 代码混淆详解

### PyArmor 混淆

PyArmor 提供强力的代码保护：

- 代码加密，无法直接反编译
- 运行时解密执行
- 支持绑定硬件

```bash
# 使用 PyArmor 混淆
pyarmor gen --output dist_obfuscated --recursive main.py
```

### 简单混淆

如果不想使用 PyArmor，可以使用简单的 .pyc 编译：

```bash
python obfuscate.py --mode simple
```

这种方式保护较弱，但不依赖第三方工具。

## 部署流程

### 开发环境

```bash
# 1. 克隆项目
git clone <repo>

# 2. 创建 .secure_config（首次）
python -m core.crypto
```

### 生产环境打包

```bash
# 1. 确保 .secure_config 存在
# 2. 混淆并打包
python obfuscate.py --mode full

# 3. 产物在 dist_obfuscated/dist/ 目录
```

## 文件说明

| 文件               | 说明                           |
| ------------------ | ------------------------------ |
| `core/crypto.py`   | 加密解密模块                   |
| `config.py`        | 配置文件（自动从加密配置读取） |
| `config_secure.py` | 纯安全配置模板                 |
| `obfuscate.py`     | 混淆打包脚本                   |
| `.secure_config`   | 加密配置文件（不提交 Git）     |

## 安全建议

1. **永远不要**将 `.secure_config` 提交到 Git
2. **定期更换** JWT 密钥和 API Key
3. 生产环境使用 `--mode full` 完整混淆
4. 考虑使用 PyArmor 付费版获得更强保护
5. 数据库密码定期轮换

## 故障排除

### 加密配置无法读取

```bash
# 重新生成加密配置
rm .secure_config
python -m core.crypto
```

### PyArmor 混淆失败

```bash
# 检查版本
pyarmor --version

# 试用版有文件大小限制，考虑：
# 1. 购买付费版
# 2. 使用简单混淆模式
python obfuscate.py --mode simple
```

### 打包后程序无法运行

确保 `.secure_config` 文件被正确打包：

```bash
# PyInstaller 添加数据文件
--add-data ".secure_config:."
```
