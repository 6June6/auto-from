@echo off
REM Windows 日志查看器启动脚本
chcp 65001 >nul

echo 🔍 启动日志查看器...

REM 尝试使用 python 或 python3
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python tools\log_viewer.py
    exit /b
)

where python3 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python3 tools\log_viewer.py
    exit /b
)

echo ❌ 错误: 未找到 Python 解释器
echo 请安装 Python 3.x 并添加到 PATH
pause
exit /b 1
