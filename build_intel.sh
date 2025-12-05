#!/bin/bash
# 打包 Intel (x86_64) 版本的应用
# 需要在 Apple Silicon Mac 上使用 Rosetta 2 运行

echo "============================================================"
echo "  🚀 自动表单填写工具 - Intel (x86_64) 打包程序"
echo "============================================================"
echo ""

# 检查 Rosetta 2 是否安装
if ! /usr/bin/pgrep -q oahd; then
    echo "⚠️  需要安装 Rosetta 2..."
    /usr/sbin/softwareupdate --install-rosetta --agree-to-license
fi

# 清理旧文件
echo "🧹 清理旧的构建文件..."
rm -rf build dist *.spec
echo "✅ 清理完成"
echo ""

# 创建 x86_64 虚拟环境
INTEL_VENV="venv_x86"
if [ ! -d "$INTEL_VENV" ]; then
    echo "🔧 创建 Intel (x86_64) 虚拟环境..."
    # 使用 Rosetta 运行 Python 创建虚拟环境
    arch -x86_64 /usr/bin/python3 -m venv $INTEL_VENV
    echo "✅ 虚拟环境创建完成"
    echo ""
    
    echo "📦 安装依赖..."
    arch -x86_64 $INTEL_VENV/bin/pip install --upgrade pip
    arch -x86_64 $INTEL_VENV/bin/pip install -r requirements.txt
    # 修复 Qt 版本兼容性问题
    arch -x86_64 $INTEL_VENV/bin/pip install "PyQt6-Qt6==6.6.1" "PyQt6-WebEngine-Qt6==6.6.0" --force-reinstall
    arch -x86_64 $INTEL_VENV/bin/pip install pyinstaller
    echo "✅ 依赖安装完成"
    echo ""
fi

# 打包
echo "🚀 开始打包 Intel 版本..."
arch -x86_64 $INTEL_VENV/bin/pyinstaller \
    --name="自动表单填写工具-Intel" \
    --windowed \
    --onedir \
    --clean \
    --osx-bundle-identifier=com.autofill.app \
    main.py

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "  ✅ Intel 版本打包完成！"
    echo "============================================================"
    echo ""
    echo "📁 打包文件位置: dist/自动表单填写工具-Intel.app"
    echo ""
    echo "📌 此版本适用于 Intel 芯片的 Mac"
else
    echo ""
    echo "❌ 打包失败！"
fi

