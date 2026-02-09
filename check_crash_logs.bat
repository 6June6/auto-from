@echo off
REM Windows 闪退日志检查脚本
chcp 65001 >nul
echo 🔍 检查闪退日志...
echo ================================
echo.

set LOG_DIR=%USERPROFILE%\.auto-form-filler\logs

REM 检查日志目录是否存在
if not exist "%LOG_DIR%" (
    echo ❌ 日志目录不存在: %LOG_DIR%
    echo 程序可能还没有运行过,或者日志系统未初始化
    pause
    exit /b 1
)

echo 📂 日志目录: %LOG_DIR%
echo.

echo 📄 日志文件列表:
dir /A-D /O-D "%LOG_DIR%"
echo.

REM 查看崩溃日志
if exist "%LOG_DIR%\crash.log" (
    echo 🔴 崩溃日志内容:
    echo ================================
    type "%LOG_DIR%\crash.log"
    echo ================================
    echo.
) else (
    echo ⚠️  crash.log 不存在
    echo.
)

REM 查看错误日志的最后50行
if exist "%LOG_DIR%\error.log" (
    echo ⚠️  错误日志(最后50行):
    echo ================================
    powershell -Command "Get-Content '%LOG_DIR%\error.log' -Tail 50"
    echo ================================
    echo.
) else (
    echo ⚠️  error.log 不存在
    echo.
)

REM 查看应用日志的最后30行
if exist "%LOG_DIR%\app.log" (
    echo 📝 应用日志(最后30行):
    echo ================================
    powershell -Command "Get-Content '%LOG_DIR%\app.log' -Tail 30"
    echo ================================
    echo.
) else (
    echo ⚠️  app.log 不存在
    echo.
)

REM 查看最新的崩溃详情JSON
for /f "delims=" %%i in ('dir /B /O-D "%LOG_DIR%\crash_*.json" 2^>nul') do (
    set LATEST_JSON=%%i
    goto :found_json
)
:found_json
if defined LATEST_JSON (
    echo 📋 最新的崩溃详情: %LATEST_JSON%
    echo ================================
    type "%LOG_DIR%\%LATEST_JSON%"
    echo ================================
    echo.
)

echo.
echo 💡 排查建议:
echo 1. 查看上面的崩溃日志和错误日志
echo 2. 特别关注 "创建主窗口失败" 或类似的错误
echo 3. 检查堆栈跟踪中的文件和行号
echo 4. 使用图形界面查看器: python tools\log_viewer.py
echo.
echo 📚 详细文档:
echo - 日志监控使用指南.md
echo - 用户闪退排查手册.md
echo - Windows日志查看指南.md
echo.
pause
