@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ======================================
echo 开始构建 poly-maker-rewords 项目
echo ======================================
echo.

REM 检查 uv 是否安装
echo 检查 uv 是否安装...
uv --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: uv 未安装
    echo.
    echo 请先安装 uv:
    echo   方法1: 使用 pip 安装
    echo     pip install uv
    echo.
    echo   方法2: 使用官方安装脚本
    echo     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    pause
    exit /b 1
)

echo ✓ uv 已安装
echo.

REM 删除旧的虚拟环境（如果存在）
if exist ".venv" (
    echo 🗑️  删除旧的虚拟环境...
    rmdir /s /q .venv
    echo ✓ 旧环境已删除
    echo.
)

REM 创建新的虚拟环境
echo 📦 创建虚拟环境...
uv venv
if errorlevel 1 (
    echo ❌ 错误: 虚拟环境创建失败
    pause
    exit /b 1
)
echo ✓ 虚拟环境创建成功
echo.

REM 同步依赖（从 uv.lock）
echo 📥 安装 Python 依赖包...
uv sync
if errorlevel 1 (
    echo ❌ 错误: 依赖安装失败
    pause
    exit /b 1
)
echo ✓ Python 依赖安装成功
echo.

REM 检查 Node.js 是否安装
echo 检查 Node.js 是否安装...
node --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  警告: Node.js 未安装，跳过 poly_merger 依赖安装
    echo.
    echo 如需使用 poly_merger 功能，请安装 Node.js:
    echo   https://nodejs.org/
    echo.
    goto :skip_npm
)

echo ✓ Node.js 已安装
echo.

REM 安装 poly_merger 的 npm 依赖
if exist "poly_merger\package.json" (
    echo 📥 安装 poly_merger 的 npm 依赖...
    cd poly_merger
    call npm install
    if errorlevel 1 (
        echo ❌ 错误: npm 依赖安装失败
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo ✓ npm 依赖安装成功
    echo.
) else (
    echo ⚠️  警告: 未找到 poly_merger\package.json
    echo.
)

:skip_npm

echo.
echo ======================================
echo ✅ 构建完成！
echo ======================================
echo.
echo 下一步：
echo   1. 确保 .env 文件已配置
echo   2. 确保 credentials.json 文件已配置（Google Sheets 凭证）
echo   3. 运行: start.bat  # 启动服务
echo.
echo 提示：
echo   - 查看日志: logs\ 目录
echo   - 停止服务: 关闭启动的窗口或按 Ctrl+C
echo.

pause

