#!/bin/bash
# 自动表单填写工具 - 安装脚本 (macOS/Linux)

echo "🚀 自动表单填写工具 - 安装程序"
echo "================================"
echo ""

# 检查 Python 版本
echo "📌 检查 Python 版本..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ 未找到 Python 3，请先安装 Python 3.10 或更高版本"
    exit 1
fi

# 创建虚拟环境
echo ""
echo "📦 创建虚拟环境..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ 创建虚拟环境失败"
    exit 1
fi

# 激活虚拟环境
echo "✅ 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo ""
echo "⬆️  升级 pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "📥 安装依赖包..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 安装依赖失败"
    exit 1
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "运行以下命令启动程序："
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "或者直接运行："
echo "  ./run.sh"

