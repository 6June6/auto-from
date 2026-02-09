#!/bin/bash
# 日志查看器启动脚本

cd "$(dirname "$0")"

echo "🔍 启动日志查看器..."

# 尝试使用 python3 或 python
if command -v python3 &> /dev/null; then
    python3 tools/log_viewer.py
elif command -v python &> /dev/null; then
    python tools/log_viewer.py
else
    echo "❌ 错误: 未找到 Python 解释器"
    echo "请安装 Python 3.x"
    exit 1
fi
