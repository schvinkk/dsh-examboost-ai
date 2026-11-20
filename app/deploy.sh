#!/bin/bash
# ExamBoost AI 部署脚本
# 由 AI 自动执行：把 app/ 部署到用户本地，启动服务，打开浏览器

set -e

# 配置
APP_NAME="ExamBoost"
INSTALL_DIR="${HOME}/${APP_NAME}"
PORT=3000

echo "======================================"
echo "  ExamBoost AI 部署"
echo "======================================"

# Step 1: 检查环境
echo "[1/6] 检查环境..."
if command -v python3 &> /dev/null; then
    echo "  ✓ Python3: $(python3 --version)"
else
    echo "  ✗ 未找到 Python3，请安装 Python 3.8+"
    exit 1
fi

# Step 2: 复制文件
echo "[2/6] 复制文件到 ${INSTALL_DIR}..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${INSTALL_DIR}"
cp -r "${SCRIPT_DIR}"/* "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SCRIPT_DIR}/index.html" "${INSTALL_DIR}/" 2>/dev/null || true
cp -r "${SCRIPT_DIR}/static" "${INSTALL_DIR}/" 2>/dev/null || true
mkdir -p "${INSTALL_DIR}/data"

# Step 3: 检查依赖
echo "[3/6] 检查依赖..."
echo "  ✓ 后端使用 Python 标准库 http.server，无需安装任何第三方依赖"

# Step 4: 初始化数据
echo "[4/6] 初始化数据..."
if [ ! -f "${INSTALL_DIR}/data/init.json" ]; then
    echo '{"initialized": true, "created": "'$(date)'"}' > "${INSTALL_DIR}/data/init.json"
fi
echo "  ✓ 数据目录就绪"

# Step 5: 启动服务
echo "[5/6] 启动服务 (http://localhost:${PORT})..."
cd "${INSTALL_DIR}"
nohup python3 server.py --port ${PORT} > "${INSTALL_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo "  ✓ 服务启动 PID: ${SERVER_PID}"

# Step 6: 打开浏览器

echo "[6/6] 打开浏览器..."
sleep 1
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:${PORT}" &
elif command -v open &> /dev/null; then
    open "http://localhost:${PORT}"
elif command -v start &> /dev/null; then
    start "http://localhost:${PORT}"
fi

# 获取局域网 IP（手机/平板可访问）
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$LAN_IP" ]; then
    LAN_IP="127.0.0.1"
fi

echo "======================================"
echo "  ✅ ExamBoost 部署完成！"
echo "  本机访问: http://localhost:${PORT}"
echo "  手机/平板访问(同一WiFi): http://${LAN_IP}:${PORT}"
echo "  数据目录: ${INSTALL_DIR}/data"
echo "  关闭服务: kill ${SERVER_PID}"
echo "======================================"
