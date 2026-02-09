#!/bin/bash
# 快速查看闪退日志脚本

echo "🔍 检查闪退日志..."
echo "================================"
echo ""

LOG_DIR=~/.auto-form-filler/logs

# 检查日志目录是否存在
if [ ! -d "$LOG_DIR" ]; then
    echo "❌ 日志目录不存在: $LOG_DIR"
    echo "程序可能还没有运行过,或者日志系统未初始化"
    exit 1
fi

echo "📂 日志目录: $LOG_DIR"
echo ""

# 列出所有日志文件
echo "📄 日志文件列表:"
ls -lh "$LOG_DIR"
echo ""

# 检查是否有崩溃日志
if [ -f "$LOG_DIR/crash.log" ]; then
    CRASH_COUNT=$(wc -l < "$LOG_DIR/crash.log")
    if [ "$CRASH_COUNT" -gt 0 ]; then
        echo "🔴 发现崩溃日志! (共 $CRASH_COUNT 行)"
        echo "================================"
        cat "$LOG_DIR/crash.log"
        echo "================================"
        echo ""
    else
        echo "✅ 没有崩溃记录"
    fi
else
    echo "⚠️  crash.log 不存在"
fi

# 查看最后的错误
if [ -f "$LOG_DIR/error.log" ]; then
    ERROR_COUNT=$(grep -c "ERROR\|CRITICAL" "$LOG_DIR/error.log" || echo "0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "⚠️  发现 $ERROR_COUNT 个错误!"
        echo "================================"
        echo "最后20条错误:"
        grep "ERROR\|CRITICAL" "$LOG_DIR/error.log" | tail -20
        echo "================================"
        echo ""
    else
        echo "✅ 没有错误记录"
    fi
else
    echo "⚠️  error.log 不存在"
fi

# 查看应用日志的最后几行
if [ -f "$LOG_DIR/app.log" ]; then
    echo "📝 应用日志(最后20行):"
    echo "================================"
    tail -20 "$LOG_DIR/app.log"
    echo "================================"
    echo ""
else
    echo "⚠️  app.log 不存在"
fi

# 查看崩溃详情JSON
JSON_FILES=$(ls -t "$LOG_DIR"/crash_*.json 2>/dev/null | head -1)
if [ -n "$JSON_FILES" ]; then
    echo "📋 最新的崩溃详情:"
    echo "================================"
    cat "$JSON_FILES" | python3 -m json.tool 2>/dev/null || cat "$JSON_FILES"
    echo "================================"
    echo ""
fi

# 总结
echo ""
echo "💡 排查建议:"
echo "1. 查看上面的崩溃日志和错误日志"
echo "2. 特别关注 '创建主窗口失败' 或类似的错误"
echo "3. 检查堆栈跟踪中的文件和行号"
echo "4. 如需详细分析,运行: ./view_logs.sh"
echo ""
echo "📚 详细文档:"
echo "- 日志监控使用指南.md"
echo "- 用户闪退排查手册.md"
echo ""
