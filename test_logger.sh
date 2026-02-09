#!/bin/bash
# 测试日志系统

cd "$(dirname "$0")"

echo "🧪 测试日志系统..."

# 尝试使用 python3 或 python
if command -v python3 &> /dev/null; then
    python3 tools/test_logger.py
elif command -v python &> /dev/null; then
    python tools/test_logger.py
else
    echo "❌ 错误: 未找到 Python 解释器"
    echo "请安装 Python 3.x"
    exit 1
fi

echo ""
echo "📋 查看生成的日志文件..."
ls -lh ~/.auto-form-filler/logs/

echo ""
echo "💡 运行 './view_logs.sh' 可以使用图形界面查看日志"
