#!/usr/bin/env bash
# ExamBoost AI 一键部署（Linux / macOS / Android proot / WSL）
# 用法：bash deploy.sh [--port 3000] [--data-dir 路径] [--no-open]
set -u

APP_NAME="ExamBoost"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=3000
DATA_DIR=""
OPEN_BROWSER=1

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:-3000}"; shift 2 ;;
    --data-dir) DATA_DIR="${2:-}"; shift 2 ;;
    --no-open) OPEN_BROWSER=0; shift ;;
    -h|--help) sed -n '1,8p' "$0"; exit 0 ;;
    *) echo "未知参数：$1（可用：--port --data-dir --no-open）"; exit 1 ;;
  esac
done

echo "======================================"
echo "  ExamBoost AI 部署"
echo "======================================"

# [1/5] 环境检查
echo "[1/5] 检查运行环境…"
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' 2>/dev/null; then
      PY="$c"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "  ✗ 需要 Python 3.8 及以上。"
  echo "    Debian/Ubuntu : sudo apt-get install -y python3"
  echo "    macOS         : brew install python3"
  echo "    Windows       : 用 start.bat，或到 python.org 下载安装"
  exit 1
fi
echo "  ✓ $("$PY" --version 2>&1)（纯标准库，无需 pip 安装任何依赖）"

# [2/5] 选择安装目录
echo "[2/5] 准备程序目录…"
INSTALL_DIR="${HOME}/${APP_NAME}"
if [ "$SCRIPT_DIR" = "$INSTALL_DIR" ]; then
  echo "  · 已在目标目录中，跳过复制"
else
  mkdir -p "$INSTALL_DIR" || { echo "  ✗ 无法创建 $INSTALL_DIR"; exit 1; }
  for item in server.py edata.py ellm.py eqbank.py eqiz.py index.html sw.js \
              manifest.json sources.json pan_search.json static data_bank; do
    if [ -e "$SCRIPT_DIR/$item" ]; then
      rm -rf "$INSTALL_DIR/$item"
      cp -R "$SCRIPT_DIR/$item" "$INSTALL_DIR/" || { echo "  ✗ 复制 $item 失败"; exit 1; }
    fi
  done
  echo "  ✓ 已复制到 $INSTALL_DIR"
fi

# 数据目录：默认放在程序目录内；可用 --data-dir 指到别处（避免升级覆盖）
if [ -n "$DATA_DIR" ]; then
  DATA_ARG=(--data-dir "$DATA_DIR")
  mkdir -p "$DATA_DIR"
else
  DATA_ARG=()
  DATA_DIR="$INSTALL_DIR/data"
fi
mkdir -p "$DATA_DIR"
echo "  · 学习数据目录：$DATA_DIR"

# [3/5] 端口检查
echo "[3/5] 检查端口 $PORT…"
if command -v "$PY" >/dev/null 2>&1; then
  IN_USE=$("$PY" -c "
import socket,sys
s=socket.socket();s.settimeout(0.6)
print('1' if s.connect_ex(('127.0.0.1',$PORT))==0 else '0')
s.close()")
  if [ "$IN_USE" = "1" ]; then
    echo "  ⚠ 端口 $PORT 已被占用，server.py 会自动改用邻近端口"
  else
    echo "  ✓ 端口可用"
  fi
fi

# [4/5] 启动服务
echo "[4/5] 启动服务…"
cd "$INSTALL_DIR"
PID_FILE="$INSTALL_DIR/server.pid"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "  · 已有实例在运行（PID $(cat "$PID_FILE")），先停止它"
  kill "$(cat "$PID_FILE")" 2>/dev/null; sleep 1
fi
setsid "$PY" server.py --port "$PORT" "${DATA_ARG[@]}" > "$INSTALL_DIR/server.log" 2>&1 < /dev/null &
echo $! > "$PID_FILE"
sleep 2
if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "  ✗ 启动失败，日志如下："
  tail -20 "$INSTALL_DIR/server.log"
  exit 1
fi
ACTUAL_PORT=$(grep -oE 'http://localhost:[0-9]+' "$INSTALL_DIR/server.log" | head -1 | grep -oE '[0-9]+$')
ACTUAL_PORT=${ACTUAL_PORT:-$PORT}
echo "  ✓ 已启动（PID $(cat "$PID_FILE")，端口 $ACTUAL_PORT）"

# [5/5] 访问信息
echo "[5/5] 访问地址…"
LAN_IP=$("$PY" -c "
import socket
try:
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(1.5)
    s.connect(('8.8.8.8',80));print(s.getsockname()[0]);s.close()
except Exception:
    print('127.0.0.1')" 2>/dev/null || echo "127.0.0.1")

if [ "$OPEN_BROWSER" = "1" ]; then
  for opener in xdg-open open termux-open-url; do
    if command -v "$opener" >/dev/null 2>&1; then
      "$opener" "http://localhost:$ACTUAL_PORT" >/dev/null 2>&1 &
      echo "  ✓ 已调用浏览器（$opener）"
      break
    fi
  done
fi

echo "======================================"
echo "  ✅ 部署完成"
echo "  本机     : http://localhost:$ACTUAL_PORT"
echo "  手机/平板: http://$LAN_IP:$ACTUAL_PORT  （需同一 WiFi）"
echo "  日志     : $INSTALL_DIR/server.log"
echo "  数据     : $DATA_DIR"
echo "  停止服务 : kill \$(cat $PID_FILE)"
echo "  重启服务 : bash $SCRIPT_DIR/deploy.sh --port $PORT"
echo ""
echo "  提示：浏览器菜单里选「添加到主屏」，就能当独立 App 用。"
echo "======================================"
