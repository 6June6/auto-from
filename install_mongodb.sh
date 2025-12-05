#!/bin/bash
# MongoDB 版本快速安装脚本

echo "======================================================"
echo "🚀 自动表单填写工具 - MongoDB 版本安装"
echo "======================================================"
echo ""

# 检查 Python 版本
echo "1️⃣ 检查 Python 版本..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "   ✅ Python 版本: $(python3 --version)"
else
    echo "   ❌ Python 版本过低，需要 3.10 或更高"
    echo "   当前版本: $(python3 --version)"
    exit 1
fi

echo ""

# 检查虚拟环境
echo "2️⃣ 检查虚拟环境..."
if [ -d "venv" ]; then
    echo "   ✅ 虚拟环境已存在"
else
    echo "   🔧 创建虚拟环境..."
    python3 -m venv venv
    echo "   ✅ 虚拟环境创建成功"
fi

echo ""

# 激活虚拟环境
echo "3️⃣ 激活虚拟环境..."
source venv/bin/activate
echo "   ✅ 虚拟环境已激活"

echo ""

# 升级 pip
echo "4️⃣ 升级 pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "   ✅ pip 已升级到最新版本"

echo ""

# 安装依赖
echo "5️⃣ 安装 MongoDB 依赖..."
pip install mongoengine pymongo --quiet
echo "   ✅ mongoengine 安装成功"
echo "   ✅ pymongo 安装成功"

echo ""

# 安装其他依赖
echo "6️⃣ 安装其他依赖..."
pip install -r requirements.txt --quiet
echo "   ✅ 所有依赖安装完成"

echo ""

# 测试数据库连接
echo "7️⃣ 测试数据库连接..."
python test_mongodb_connection.py

echo ""
echo "======================================================"
echo "✅ 安装完成！"
echo "======================================================"
echo ""
echo "📝 使用说明："
echo "   1. 启动应用: python main.py"
echo "   2. 测试连接: python test_mongodb_connection.py"
echo ""
echo "📚 相关文档："
echo "   - MONGODB_MIGRATION_README.md  - 迁移说明"
echo "   - MONGODB_SETUP.md             - 配置指南"
echo "   - 项目完整文档.md              - 使用文档"
echo ""
echo "🎉 祝使用愉快！"
echo ""

