@echo off
chcp 65001 >nul
echo ========================================
echo   Polymarket Market Making Bot
echo ========================================
echo.
echo 正在启动 Polymarket 做市机器人...
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9.10 或更高版本
    pause
    exit /b 1
)

REM 检查 UV 是否安装
python -m uv --version >nul 2>&1
if errorlevel 1 (
    echo [警告] UV 未安装，正在安装...
    python -m pip install uv
    if errorlevel 1 (
        echo [错误] UV 安装失败
        pause
        exit /b 1
    )
)

REM 检查 .env 文件
if not exist ".env" (
    echo [错误] 未找到 .env 文件，请先配置环境变量
    echo 请复制 .env.example 为 .env 并填写配置
    pause
    exit /b 1
)

REM 检查依赖是否安装
if not exist ".venv" (
    echo [提示] 首次运行，正在安装依赖...
    python -m uv sync
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo.
echo [启动] 正在启动做市机器人...
echo [提示] 按 Ctrl+C 可以停止程序
echo.
echo ========================================
echo.

REM 启动程序
python -m uv run python main.py

REM 如果程序异常退出
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)

