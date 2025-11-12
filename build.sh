#!/bin/bash

# 构建脚本 - 创建虚拟环境并安装依赖
# 使用 uv 包管理器

set -e  # 遇到错误立即退出

echo "======================================"
echo "开始构建 poly-maker-rewords 项目"
echo "======================================"

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: uv 未安装"
    echo "请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv 已安装"

# 删除旧的虚拟环境（如果存在）
if [ -d ".venv" ]; then
    echo "🗑️  删除旧的虚拟环境..."
    rm -rf .venv
fi

# 创建新的虚拟环境
echo "📦 创建虚拟环境..."
uv venv

# 同步依赖（从 uv.lock）
echo "📥 安装依赖包..."
uv sync

echo ""
echo "======================================"
echo "✅ 构建完成！"
echo "======================================"
echo ""
echo "下一步："
echo "  运行: ./start.sh  # 启动服务"
echo "  停止: ./stop.sh   # 停止服务"
echo ""

