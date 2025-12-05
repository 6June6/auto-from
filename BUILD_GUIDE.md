# 📦 打包指南

## 快速打包

### macOS 打包：

```bash
cd /Users/chenchen/Desktop/开发项目/auto-form-filler-py
source venv/bin/activate
python build.py
```

### Windows 打包：

```cmd
cd C:\path\to\auto-form-filler-py
venv\Scripts\activate
python build.py
```

## 手动打包（高级）

### 1. 安装 PyInstaller

```bash
pip install pyinstaller
```

### 2. macOS 打包命令

```bash
pyinstaller --name="自动表单填写工具" \
    --windowed \
    --onedir \
    --clean \
    --osx-bundle-identifier=com.autofill.app \
    main.py
```

### 3. Windows 打包命令

```cmd
pyinstaller --name="自动表单填写工具" ^
    --windowed ^
    --onedir ^
    --clean ^
    main.py
```

## 打包选项说明

| 选项         | 说明                             |
| ------------ | -------------------------------- |
| `--name`     | 应用名称                         |
| `--windowed` | GUI 模式，不显示控制台           |
| `--onedir`   | 打包成文件夹（推荐，启动快）     |
| `--onefile`  | 打包成单个 exe（体积大，启动慢） |
| `--clean`    | 清理缓存                         |
| `--icon`     | 指定图标文件                     |

## 添加图标

### macOS (.icns):

```bash
pyinstaller --icon=icon.icns ...
```

### Windows (.ico):

```cmd
pyinstaller --icon=icon.ico ...
```

## 打包后文件结构

```
dist/
└── 自动表单填写工具/
    ├── 自动表单填写工具          # macOS 可执行文件
    ├── 自动表单填写工具.exe      # Windows 可执行文件
    ├── _internal/                # 依赖库（自动生成）
    └── data/                     # 数据库（首次运行自动创建）
```

## 分发说明

### macOS:

1. 压缩 `dist/自动表单填写工具` 文件夹
2. 用户解压后直接运行
3. 如需签名和公证，需要 Apple Developer 账号

### Windows:

1. 压缩 `dist/自动表单填写工具` 文件夹
2. 用户解压后运行 .exe 文件
3. 建议使用 Inno Setup 或 NSIS 制作安装包

## 常见问题

### Q1: macOS 提示"无法打开，因为它来自身份不明的开发者"

**解决方案：**

```bash
# 方法1：临时允许
右键点击应用 > 打开 > 在弹窗中点击"打开"

# 方法2：系统设置
系统偏好设置 > 安全性与隐私 > 允许从以下位置下载的App > 仍要打开
```

### Q2: Windows Defender 提示病毒

**解决方案：**

- 点击"更多信息" > "仍要运行"
- PyInstaller 打包的应用可能被误报，这是正常现象

### Q3: 打包后体积太大

**解决方案：**

```bash
# 使用虚拟环境，只安装必要的包
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir

# 使用 UPX 压缩
pip install upx-pyinstaller
pyinstaller --upx-dir=/path/to/upx ...
```

### Q4: 程序无法启动

**解决方案：**

1. 在终端中运行，查看错误信息
2. 检查是否缺少依赖
3. 使用 `--debug all` 选项重新打包

## 代码签名（可选）

### macOS 签名：

```bash
# 需要 Apple Developer 账号
codesign --deep --force --verify --verbose \
    --sign "Developer ID Application: Your Name" \
    dist/自动表单填写工具.app
```

### Windows 签名：

需要购买代码签名证书，使用 SignTool 进行签名。

## 优化建议

1. **减小体积**

   - 使用虚拟环境
   - 移除不需要的包
   - 使用 `--onedir` 而非 `--onefile`

2. **提高启动速度**

   - 使用 `--onedir` 模式
   - 减少导入的模块
   - 使用懒加载

3. **提升安全性**
   - 代码签名
   - 使用 PyArmor 加密代码
   - 不在代码中硬编码敏感信息

## 自动化打包脚本

已创建 `build.py`，支持：

- ✅ 自动清理旧文件
- ✅ 检查并安装 PyInstaller
- ✅ 根据平台自动选择配置
- ✅ 生成使用说明

直接运行：

```bash
python build.py
```




