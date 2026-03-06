#!/bin/bash
set -e

APP_DIR="/opt/xhs-api"
SERVICE_NAME="xhs-api"

echo "=========================================="
echo "  小红书解析 API 部署脚本"
echo "=========================================="

# 系统依赖
echo "[1/6] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv > /dev/null 2>&1
echo "  ✓ 系统依赖安装完成"

# 创建目录
echo "[2/6] 创建应用目录..."
mkdir -p $APP_DIR
cp xhs_parser.py $APP_DIR/
cp xhs_api.py $APP_DIR/
cp xhs_requirements.txt $APP_DIR/requirements.txt
echo "  ✓ 文件复制完成"

# Python 虚拟环境
echo "[3/6] 创建 Python 虚拟环境..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✓ Python 依赖安装完成"

# Playwright 浏览器
echo "[4/6] 安装 Playwright Chromium..."
playwright install chromium
playwright install-deps chromium 2>/dev/null || echo "  ⚠ install-deps 需要手动处理（见下方提示）"
echo "  ✓ Playwright 安装完成"

# systemd 服务
echo "[5/6] 配置 systemd 服务..."
cat > /etc/systemd/system/${SERVICE_NAME}.service << 'UNIT'
[Unit]
Description=XHS Parser API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/xhs-api
ExecStart=/opt/xhs-api/venv/bin/python -m uvicorn xhs_api:app --host 0.0.0.0 --port 8900 --workers 2
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}
echo "  ✓ 服务已启动"

# 验证
echo "[6/6] 验证服务状态..."
sleep 3
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "  ✓ 服务运行正常"
else
    echo "  ✗ 服务启动失败，查看日志: journalctl -u ${SERVICE_NAME} -n 50"
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "  API 地址: http://$(hostname -I | awk '{print $1}'):8900"
echo "  健康检查: curl http://localhost:8900/"
echo "  解析示例: curl 'http://localhost:8900/parse?url=http://xhslink.com/o/5f5TMLuhpDf'"
echo ""
echo "  管理命令:"
echo "    查看状态: systemctl status ${SERVICE_NAME}"
echo "    查看日志: journalctl -u ${SERVICE_NAME} -f"
echo "    重启服务: systemctl restart ${SERVICE_NAME}"
echo ""
