#!/bin/bash

# 停止脚本 - 关闭所有 screen 会话

SCREEN_MAIN="poly-main"
SCREEN_UPDATE="poly-update"

echo "======================================"
echo "停止 poly-maker-rewords 服务"
echo "======================================"

# 检查 screen 是否安装
if ! command -v screen &> /dev/null; then
    echo "❌ 错误: screen 未安装"
    exit 1
fi

echo "🛑 停止 screen 会话..."

STOPPED=0

# 停止 main.py 的 screen
if screen -list | grep -q "$SCREEN_MAIN"; then
    echo "  - 停止 $SCREEN_MAIN"
    screen -S "$SCREEN_MAIN" -X quit 2>/dev/null || true
    STOPPED=$((STOPPED + 1))
else
    echo "  - $SCREEN_MAIN 未运行"
fi

# 停止 update_markets.py 的 screen
if screen -list | grep -q "$SCREEN_UPDATE"; then
    echo "  - 停止 $SCREEN_UPDATE"
    screen -S "$SCREEN_UPDATE" -X quit 2>/dev/null || true
    STOPPED=$((STOPPED + 1))
else
    echo "  - $SCREEN_UPDATE 未运行"
fi

echo ""
echo "======================================"
if [ $STOPPED -gt 0 ]; then
    echo "✅ 已停止 $STOPPED 个服务"
else
    echo "ℹ️  没有运行中的服务"
fi
echo "======================================"
echo ""

