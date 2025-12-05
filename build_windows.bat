@echo off
REM Windows 打包脚本 - 自动表单填写工具

echo ============================================================
echo   🚀 自动表单填写工具 - Windows 打包程序
echo ============================================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.9 或更高版本
    pause
    exit /b 1
)

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    echo ✅ 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  未找到虚拟环境，使用系统 Python
)

REM 安装 PyInstaller
echo.
echo 📦 检查 PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ⚠️  PyInstaller 未安装，正在安装...
    pip install pyinstaller
)

REM 清理旧文件
echo.
echo 🧹 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "自动表单填写工具.spec" del "自动表单填写工具.spec"

REM 打包应用
echo.
echo 🚀 开始打包应用...
echo.

pyinstaller ^
    --name="自动表单填写工具" ^
    --windowed ^
    --onedir ^
    --clean ^
    main.py

if errorlevel 1 (
    echo.
    echo ❌ 打包失败
    pause
    exit /b 1
)

REM 创建说明文档
echo.
echo 📄 创建使用说明...
(
echo 自动表单填写工具 - Windows 版
echo ================================
echo.
echo 使用方法：
echo 1. 双击运行 "自动表单填写工具.exe"
echo 2. 如果 Windows Defender 提示，点击"更多信息" ^> "仍要运行"
echo.
echo 数据库位置：
echo 程序会在当前用户目录下创建 data 文件夹
echo.
echo 问题反馈：
echo 如有问题请联系开发者
) > dist\README.txt

echo.
echo ============================================================
echo   ✅ 打包完成！
echo ============================================================
echo.
echo 📁 打包文件位置: dist\自动表单填写工具\
echo.
echo 📌 下一步:
echo   1. 测试运行 dist\自动表单填写工具\自动表单填写工具.exe
echo   2. 如需分发，压缩整个文件夹为 ZIP
echo   3. 可以使用 Inno Setup 制作安装包
echo.
pause

