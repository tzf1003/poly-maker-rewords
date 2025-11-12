#!/bin/bash

# 启动脚本 - 使用 screen 运行两个 Python 程序
# Screen 会话名称: poly-main, poly-update

set -e  # 遇到错误立即退出

SCREEN_MAIN="poly-main"
SCREEN_UPDATE="poly-update"
VENV_PATH=".venv/bin/activate"

echo "======================================"
echo "启动 poly-maker-rewords 服务"
echo "======================================"

# 检查虚拟环境是否存在
if [ ! -f "$VENV_PATH" ]; then
    echo "❌ 错误: 虚拟环境不存在"
    echo "请先运行: ./build.sh"
    exit 1
fi

# 检查 screen 是否安装
if ! command -v screen &> /dev/null; then
    echo "❌ 错误: screen 未安装"
    echo "请安装 screen: sudo apt-get install screen  # Ubuntu/Debian"
    echo "              或 sudo yum install screen     # CentOS/RHEL"
    exit 1
fi

echo "🛑 停止旧的 screen 会话..."

# 杀掉旧的 screen 会话（如果存在）
if screen -list | grep -q "$SCREEN_MAIN"; then
    echo "  - 停止 $SCREEN_MAIN"
    screen -S "$SCREEN_MAIN" -X quit 2>/dev/null || true
fi

if screen -list | grep -q "$SCREEN_UPDATE"; then
    echo "  - 停止 $SCREEN_UPDATE"
    screen -S "$SCREEN_UPDATE" -X quit 2>/dev/null || true
fi

sleep 1

echo ""
echo "🚀 启动新的 screen 会话..."

# 启动 main.py
echo "  - 启动 $SCREEN_MAIN (main.py)"
screen -dmS "$SCREEN_MAIN" bash -c "source $VENV_PATH && python main.py"

# 启动 update_markets.py
echo "  - 启动 $SCREEN_UPDATE (update_markets.py)"
screen -dmS "$SCREEN_UPDATE" bash -c "source $VENV_PATH && python update_markets.py"

sleep 1

echo ""
echo "======================================"
echo "✅ 服务启动成功！"
echo "======================================"
echo ""
echo "Screen 会话列表："
screen -list | grep -E "$SCREEN_MAIN|$SCREEN_UPDATE" || echo "  (无活动会话)"
echo ""
echo "查看日志："
echo "  screen -r $SCREEN_MAIN    # 查看 main.py"
echo "  screen -r $SCREEN_UPDATE  # 查看 update_markets.py"
echo ""
echo "退出 screen: Ctrl+A 然后按 D"
echo "停止服务: ./stop.sh"
echo ""
