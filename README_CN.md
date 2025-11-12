# Poly-Maker

一个用于Polymarket预测市场的做市机器人。该机器人通过可配置参数在订单簿的两侧维护订单，自动化为Polymarket市场提供流动性的过程。我运行此机器人的经验总结可在[这里](https://x.com/defiance_cr/status/1906774862254800934)查看。

## 概述

Poly-Maker是Polymarket上自动化做市的综合解决方案。它包括：

- 通过WebSocket实时监控订单簿
- 带有风险控制的持仓管理
- 从Google Sheets获取的可自定义交易参数
- 自动化持仓合并功能
- 复杂的价差和价格管理

## 结构

该仓库由几个相互关联的模块组成：

- `poly_data`: 核心数据管理和做市逻辑
- `poly_merger`: 持仓合并工具（基于开源Polymarket代码）
- `poly_stats`: 账户统计跟踪
- `poly_utils`: 共享实用函数
- `data_updater`: 用于收集市场信息的独立模块

## 要求

- Python 3.9.10或更高版本
- Node.js（用于poly_merger）
- Google Sheets API凭证
- Polymarket账户和API凭证

## 安装

此项目使用UV进行快速、可靠的包管理。

### 安装UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用pip
pip install uv
```

### 安装依赖

```bash
# 安装所有依赖
uv sync

# 安装开发依赖（black, pytest）
uv sync --extra dev
```

### 快速开始

```bash
# 运行做市机器人（推荐）
uv run python main.py

# 更新市场数据
uv run python update_markets.py

# 更新统计数据
uv run python update_stats.py
```

### 设置步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/poly-maker.git
cd poly-maker
```

#### 2. 安装Python依赖

```bash
uv sync
```

#### 3. 为合并器安装Node.js依赖

```bash
cd poly_merger
npm install
cd ..
```

#### 4. 设置环境变量

```bash
cp .env.example .env
```

#### 5. 在`.env`中配置您的凭证

编辑`.env`文件并填入您的凭证：
- `PK`: 您的Polymarket私钥
- `BROWSER_ADDRESS`: 您的钱包地址

**重要提示：** 确保您的钱包已通过UI进行过至少一次交易，以便权限正确设置。

#### 6. 设置Google Sheets集成

- 创建Google服务账户并将凭证下载到主目录
- 复制[示例Google表格](https://docs.google.com/spreadsheets/d/1Kt6yGY7CZpB75cLJJAdWo7LSp9Oz7pjqfuVWwgtn7Ns/edit?gid=1884499063#gid=1884499063)
- 将您的Google服务账户添加到表格并授予编辑权限
- 在您的`.env`文件中更新`SPREADSHEET_URL`

#### 7. 更新市场数据

运行市场数据更新器以获取所有可用市场：

```bash
uv run python update_markets.py
```

这应该在后台持续运行（最好在与您的交易机器人不同的IP上）。

- 将您想要交易的市场添加到"Selected Markets"工作表
- 从"Volatility Markets"工作表中选择市场
- 在"Hyperparameters"工作表中配置参数（包含了11月份效果良好的默认参数）

#### 8. 启动做市机器人

```bash
uv run python main.py
```

## 配置

机器人通过包含多个工作表的Google电子表格进行配置：

- **Selected Markets**: 您想要交易的市场
- **All Markets**: Polymarket上所有市场的数据库
- **Hyperparameters**: 交易逻辑的配置参数


## Poly Merger

`poly_merger`模块是一个特别强大的工具，用于处理Polymarket上的持仓合并。它基于开源Polymarket代码构建，提供了一种流畅的方式来合并持仓，降低gas费用并提高资金效率。

## 重要说明

- 此代码与真实市场交互，可能会损失真实资金
- 在使用大量资金部署之前，请使用小额资金进行充分测试
- `data_updater`技术上是一个独立的仓库，但为了方便起见包含在这里

## 许可证

MIT

