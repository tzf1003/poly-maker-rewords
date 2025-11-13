@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ======================================
echo 启动 poly-maker-rewords 服务
echo ======================================
echo.

REM 检查虚拟环境是否存在
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ 错误: 虚拟环境不存在
    echo 请先运行: build.bat
    echo.
    pause
    exit /b 1
)

echo ✓ 虚拟环境已就绪
echo.

REM 检查 .env 文件
if not exist ".env" (
    echo ❌ 错误: 未找到 .env 文件
    echo 请先配置环境变量文件
    echo.
    pause
    exit /b 1
)

echo ✓ .env 文件已配置
echo.

REM 检查 credentials.json 文件
if not exist "credentials.json" (
    echo ⚠️  警告: 未找到 credentials.json 文件
    echo 如需使用 Google Sheets 功能，请配置此文件
    echo.
)

echo 🚀 启动服务...
echo.
echo 将在两个新窗口中启动：
echo   1. main.py - 主做市程序
echo   2. update_markets.py - 市场数据更新程序
echo.
echo 提示：
echo   - 关闭窗口或按 Ctrl+C 可停止对应程序
echo   - 日志文件保存在 logs\ 目录
echo.

REM 启动 main.py（在新窗口）
echo 启动 main.py...
start "Poly-Maker: Main" cmd /k ".venv\Scripts\activate.bat && python main.py"

REM 等待 1 秒
timeout /t 1 /nobreak >nul

REM 启动 update_markets.py（在新窗口）
echo 启动 update_markets.py...
start "Poly-Maker: Update Markets" cmd /k ".venv\Scripts\activate.bat && python update_markets.py"

echo.
echo ======================================
echo ✅ 服务启动成功！
echo ======================================
echo.
echo 已启动两个窗口：
echo   - Poly-Maker: Main
echo   - Poly-Maker: Update Markets
echo.
echo 查看日志：
echo   - logs\main.log
echo   - logs\update_markets.log
echo.
echo 停止服务：关闭对应的窗口或按 Ctrl+C
echo.

pause


