#!/bin/bash

echo "========================================"
echo "  Polymarket Market Making Bot"
echo "========================================"
echo ""
echo "正在启动 Polymarket 做市机器人..."
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python，请先安装 Python 3.9.10 或更高版本"
    exit 1
fi

# 检查 UV 是否安装
if ! python3 -m uv --version &> /dev/null; then
    echo "[警告] UV 未安装，正在安装..."
    python3 -m pip install uv
    if [ $? -ne 0 ]; then
        echo "[错误] UV 安装失败"
        exit 1
    fi
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "[错误] 未找到 .env 文件，请先配置环境变量"
    echo "请复制 .env.example 为 .env 并填写配置"
    exit 1
fi

# 检查依赖是否安装
if [ ! -d ".venv" ]; then
    echo "[提示] 首次运行，正在安装依赖..."
    python3 -m uv sync
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

echo ""
echo "[启动] 正在启动做市机器人..."
echo "[提示] 按 Ctrl+C 可以停止程序"
echo ""
echo "========================================"
echo ""

# 启动程序
python3 -m uv run python main.py

# 如果程序异常退出
if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序异常退出"
    read -p "按任意键退出..."
fi

