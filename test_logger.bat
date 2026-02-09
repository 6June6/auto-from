@echo off
REM Windows 测试日志系统脚本
chcp 65001 >nul

echo 🧪 测试日志系统...

REM 尝试使用 python 或 python3
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python tools\test_logger.py
    goto :show_logs
)

where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python3 tools\test_logger.py
    goto :show_logs
)

echo ❌ 错误: 未找到 Python 解释器
echo 请安装 Python 3.x 并添加到 PATH
pause
exit /b 1

:show_logs
echo.
echo 📋 查看生成的日志文件...
dir /A-D /O-D "%USERPROFILE%\.auto-form-filler\logs"
echo.
echo 💡 运行 view_logs.bat 可以使用图形界面查看日志
pause
