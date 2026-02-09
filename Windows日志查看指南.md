# Windows 环境日志查看指南 🪟

## 📍 日志文件位置

Windows 系统下,日志文件存储在:

```
C:\Users\你的用户名\.auto-form-filler\logs\
```

**示例:**
```
C:\Users\Administrator\.auto-form-filler\logs\
C:\Users\张三\.auto-form-filler\logs\
```

## 🚀 快速查看日志的方法

### 方法1: 使用批处理脚本(最简单)

双击运行或在命令行执行:

```cmd
check_crash_logs.bat
```

这会自动显示所有日志内容。

### 方法2: 使用 PowerShell 查看

打开 PowerShell,执行:

```powershell
# 切换到日志目录
cd $env:USERPROFILE\.auto-form-filler\logs

# 列出所有日志文件
dir

# 查看崩溃日志
Get-Content crash.log

# 查看错误日志(最后50行)
Get-Content error.log -Tail 50

# 查看应用日志(最后100行)
Get-Content app.log -Tail 100

# 实时监控日志
Get-Content error.log -Wait -Tail 20
```

### 方法3: 使用命令提示符(CMD)

```cmd
cd %USERPROFILE%\.auto-form-filler\logs

REM 列出文件
dir

REM 查看崩溃日志
type crash.log

REM 查看错误日志
type error.log | more

REM 查看应用日志
type app.log | more
```

### 方法4: 使用记事本打开

1. 按 `Win + R` 打开运行对话框
2. 输入: `%USERPROFILE%\.auto-form-filler\logs`
3. 按回车,会打开日志目录
4. 双击 `.log` 文件用记事本查看

### 方法5: 使用图形界面日志查看器

```cmd
python tools\log_viewer.py
```

或双击运行:
```cmd
view_logs.bat
```

## 🔍 针对"登录后闪退"的快速排查

### 步骤1: 运行检查脚本

```cmd
check_crash_logs.bat
```

### 步骤2: 查找关键信息

在输出中查找:

```
[User: 用户名] ✅ 用户登录成功
[User: 用户名] 📝 启动表单填写界面...
[User: 用户名] ❌ 创建主窗口失败: 错误信息
```

### 步骤3: 查看崩溃详情

查找 `crash_20260209_143022.json` 类似的文件:

```powershell
# PowerShell 查看最新的崩溃详情
Get-ChildItem "$env:USERPROFILE\.auto-form-filler\logs\crash_*.json" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1 | 
    Get-Content | 
    ConvertFrom-Json | 
    ConvertTo-Json -Depth 10
```

或直接用记事本打开查看。

## 📊 PowerShell 高级查询

### 搜索特定用户的日志

```powershell
# 搜索特定用户的错误
Select-String -Path "$env:USERPROFILE\.auto-form-filler\logs\error.log" -Pattern "用户名" -Context 5

# 搜索特定错误类型
Select-String -Path "$env:USERPROFILE\.auto-form-filler\logs\error.log" -Pattern "AttributeError|KeyError" -Context 3

# 统计错误数量
(Select-String -Path "$env:USERPROFILE\.auto-form-filler\logs\error.log" -Pattern "ERROR").Count
```

### 查看今天的日志

```powershell
$Today = Get-Date -Format "yyyy-MM-dd"
Select-String -Path "$env:USERPROFILE\.auto-form-filler\logs\error.log" -Pattern $Today
```

### 导出用户的所有日志

```powershell
# 导出特定用户的日志
$Username = "test_user"
Get-Content "$env:USERPROFILE\.auto-form-filler\logs\*.log" | 
    Select-String $Username | 
    Out-File "user_${Username}_logs.txt"
```

## 🗂️ 打包日志发送给开发者

### 方法1: 使用 PowerShell 压缩

```powershell
# 压缩所有日志
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
Compress-Archive -Path "$env:USERPROFILE\.auto-form-filler\logs\*" -DestinationPath "crash_logs_$Date.zip"
```

### 方法2: 使用命令行

```cmd
REM 切换到日志目录
cd %USERPROFILE%\.auto-form-filler\logs

REM 复制所有日志到桌面
xcopy *.* %USERPROFILE%\Desktop\crash_logs\ /Y

REM 然后手动压缩桌面上的 crash_logs 文件夹
```

## 🛠️ 常用命令速查

| 操作 | PowerShell 命令 | CMD 命令 |
|------|----------------|----------|
| 打开日志目录 | `explorer $env:USERPROFILE\.auto-form-filler\logs` | `explorer %USERPROFILE%\.auto-form-filler\logs` |
| 查看崩溃日志 | `Get-Content crash.log` | `type crash.log` |
| 查看最后50行 | `Get-Content error.log -Tail 50` | `powershell Get-Content error.log -Tail 50` |
| 实时监控 | `Get-Content error.log -Wait -Tail 20` | 不支持,需要用 PowerShell |
| 搜索关键词 | `Select-String -Path error.log -Pattern "用户名"` | `findstr "用户名" error.log` |
| 统计行数 | `(Get-Content error.log).Count` | `find /c /v "" error.log` |

## 🐛 Windows 特有问题排查

### 问题1: 找不到日志目录

**检查:**
```cmd
echo %USERPROFILE%\.auto-form-filler\logs
```

**手动创建:**
```cmd
mkdir %USERPROFILE%\.auto-form-filler\logs
```

### 问题2: 日志文件乱码

**原因:** Windows 默认编码问题

**解决:**
```cmd
REM 在批处理文件开头添加
chcp 65001
```

或使用支持 UTF-8 的编辑器查看(如 VS Code, Notepad++)。

### 问题3: 权限不足

**以管理员身份运行:**
1. 右键点击 `check_crash_logs.bat`
2. 选择"以管理员身份运行"

### 问题4: Python 找不到

**检查 Python 安装:**
```cmd
python --version
python3 --version
```

**如果没有输出,需要:**
1. 安装 Python 3.x
2. 安装时勾选 "Add Python to PATH"
3. 或手动添加到环境变量

## 📱 实时监控(开发/测试用)

### 使用 PowerShell 实时监控

**终端1 - 监控错误日志:**
```powershell
Get-Content "$env:USERPROFILE\.auto-form-filler\logs\error.log" -Wait -Tail 20
```

**终端2 - 运行程序:**
```cmd
python main.py
```

### 使用 Windows Terminal(推荐)

如果安装了 Windows Terminal:
1. 分屏打开两个终端
2. 一个运行监控命令
3. 一个运行应用程序

## 🎯 快速排查流程(Windows 版)

### 1. 用户报告闪退后立即执行:

```cmd
check_crash_logs.bat
```

### 2. 复制崩溃日志:

```cmd
REM 打开日志目录
explorer %USERPROFILE%\.auto-form-filler\logs

REM 复制 crash.log 内容
```

### 3. 查看具体错误:

在 `crash.log` 中查找:
- 用户名
- 异常类型
- 堆栈跟踪

### 4. 分析原因:

根据错误类型:
- `AttributeError` → 对象属性问题
- `FileNotFoundError` → 文件缺失
- `ImportError` → 模块导入失败
- `KeyError` → 字典键不存在

## 💡 Windows 环境特别注意

### 1. 路径分隔符

Windows 使用反斜杠 `\`:
```
C:\Users\用户名\.auto-form-filler\logs\
```

### 2. 文件编码

日志文件使用 UTF-8 编码,建议使用:
- Notepad++ (推荐)
- VS Code
- Sublime Text

不建议使用记事本(可能乱码)。

### 3. 权限问题

某些 Windows 版本可能需要管理员权限访问日志目录。

### 4. 防病毒软件

防病毒软件可能阻止日志写入,需要添加例外:
```
%USERPROFILE%\.auto-form-filler\
```

## 📚 相关脚本文件

| 脚本 | 功能 | 使用方法 |
|------|------|---------|
| `check_crash_logs.bat` | 查看所有日志 | 双击运行 |
| `view_logs.bat` | 启动图形界面查看器 | 双击运行 |
| `test_logger.bat` | 测试日志系统 | 双击运行 |

## 🆘 获取帮助

如果遇到问题:

1. 查看完整文档:
   - `日志监控使用指南.md`
   - `用户闪退排查手册.md`

2. 导出日志:
   ```cmd
   check_crash_logs.bat > log_output.txt
   ```

3. 将 `log_output.txt` 发送给技术支持

## ✅ 快速命令备忘

```cmd
REM 一键查看所有日志
check_crash_logs.bat

REM 打开日志目录
explorer %USERPROFILE%\.auto-form-filler\logs

REM 查看崩溃日志
type %USERPROFILE%\.auto-form-filler\logs\crash.log

REM 启动图形界面查看器
view_logs.bat

REM 测试日志系统
test_logger.bat
```

---

💡 **提示:** Windows 用户建议使用 PowerShell 而不是 CMD,功能更强大!
