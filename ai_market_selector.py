#!/usr/bin/env python3
"""
AI 自动化市场选择器
使用 LangChain + OpenAI 自动分析和选择最优市场
"""

import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 本地导入
from poly_utils.google_utils import get_spreadsheet
from poly_data.polymarket_client import PolymarketClient
import ai_config

# 加载环境变量
load_dotenv()

# 全局变量用于存储 spreadsheet 对象和原始市场数据
_spreadsheet = None
_original_markets_df = None


def get_wallet_balance():
    """获取钱包余额"""
    try:
        client = PolymarketClient()
        # 使用 get_total_balance() 获取 USDC 余额 + 持仓价值
        balance = client.get_total_balance()
        return float(balance)
    except Exception as e:
        print(f"⚠️  无法获取钱包余额: {e}")
        return 200.0  # 默认值


def get_liquidity_markets(sheet_name='Volatility Markets'):
    """获取流动性市场列表"""
    global _spreadsheet
    
    if _spreadsheet is None:
        _spreadsheet = get_spreadsheet(read_only=True)
    
    ws = _spreadsheet.worksheet(sheet_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    
    # 按 volatilty/reward 比率排序（越低越好）
    if 'volatilty/reward' in df.columns:
        df = df.sort_values('volatilty/reward')
    
    return df


def get_current_selections():
    """获取当前选择列表"""
    global _spreadsheet
    
    if _spreadsheet is None:
        _spreadsheet = get_spreadsheet(read_only=True)
    
    ws = _spreadsheet.worksheet('Selected Markets')
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    
    return df


def get_hyperparameters():
    """获取超参数表"""
    global _spreadsheet
    
    if _spreadsheet is None:
        _spreadsheet = get_spreadsheet(read_only=True)
    
    ws = _spreadsheet.worksheet('Hyperparameters')
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    
    return df


@tool
def update_selected_markets(markets: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    更新 Google Sheets 中的 Selected Markets 工作表

    参数:
        markets: 市场列表。每个市场包含:
            - row_id: 市场在流动性市场表中的行号（从 0 开始）
            - max_size: 最大持仓
            - trade_size: 每次交易规模
            - param_type: 风险策略
            - comments: 备注（包含理由和置信度）

    示例:
        - 添加市场: markets=[{"row_id": 0, "max_size": 100, "trade_size": 50, "param_type": "mid", "comments": "..."}, ...]
        - 清空所有市场: markets=[]

    返回:
        成功或失败的消息
    """
    # 如果 markets 为 None，设置为空列表
    if markets is None:
        markets = []

    try:
        global _spreadsheet, _original_markets_df

        if _spreadsheet is None:
            _spreadsheet = get_spreadsheet(read_only=False)

        # 检查原始市场数据
        if _original_markets_df is None or len(_original_markets_df) == 0:
            return "❌ 错误: 无法获取原始市场数据"

        ws = _spreadsheet.worksheet('Selected Markets')

        # 清空现有数据
        ws.clear()

        # 准备所有数据（包括表头）
        headers = ['question', 'max_size', 'trade_size', 'param_type', 'comments']
        all_rows = [headers]

        # 添加市场数据
        for i, market in enumerate(markets):
            row_id = market.get('row_id')

            # 验证 row_id
            if row_id is None:
                print(f"⚠️  警告: 市场 {i+1} 缺少 row_id，跳过")
                continue

            if not isinstance(row_id, int) or row_id < 0 or row_id >= len(_original_markets_df):
                print(f"⚠️  警告: 市场 {i+1} 的 row_id={row_id} 无效，跳过")
                continue

            # 从原始数据中获取正确的 question
            question = _original_markets_df.iloc[row_id]['question']

            print(f"✅ 市场 {i+1}: row_id={row_id} → {question[:60]}...")

            row = [
                question,  # 从原始数据获取，保证正确
                market.get('max_size', 0),
                market.get('trade_size', 0),
                str(market.get('param_type', 'mid')),
                str(market.get('comments', ''))
            ]
            all_rows.append(row)

        # 使用 batch_update 一次性写入所有数据
        ws.update(values=all_rows, range_name='A1', value_input_option='RAW')

        return f"✅ 成功更新 {len(all_rows)-1} 个市场到 Selected Markets 工作表"

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 更新失败详情:\n{error_detail}")
        return f"❌ 更新失败: {str(e)}"


def format_markets_for_prompt(df: pd.DataFrame, limit: int = 50) -> str:
    """格式化市场数据用于提示词"""
    if len(df) == 0:
        return "（无数据）"

    # 添加 row_id 列（从 0 开始的索引）
    df_with_id = df.copy()
    df_with_id.insert(0, 'row_id', range(len(df_with_id)))

    # 选择关键字段（row_id 放在最前面）
    columns = [
        'row_id', 'question', 'spread', 'rewards_daily_rate', 'volatility_sum',
        'volatilty/reward', 'min_size', 'best_bid', 'best_ask',
        '1_hour', '3_hour', '6_hour', '12_hour', '24_hour'
    ]

    # 过滤存在的列
    available_columns = [col for col in columns if col in df_with_id.columns]

    # 限制数量
    df_limited = df_with_id[available_columns].head(limit)

    # 转换为 Markdown 表格
    return df_limited.to_markdown(index=False)


def format_hyperparameters(df: pd.DataFrame) -> str:
    """格式化超参数表"""
    if len(df) == 0:
        return "（无数据）"
    
    # 按 type 分组
    result = []
    for param_type in ['very', 'high', 'mid', 'shit']:
        type_df = df[df['type'] == param_type]
        if len(type_df) > 0:
            result.append(f"\n### {param_type.upper()} 策略:")
            for _, row in type_df.iterrows():
                result.append(f"- {row['param']}: {row['value']}")
    
    return '\n'.join(result)


def create_ai_agent(config: Dict[str, Any]):
    """创建 AI Agent"""

    # 初始化 OpenAI 客户端
    llm = ChatOpenAI(
        model=os.getenv('OPENAI_MODEL', 'gpt-5'),
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_API_BASE'),
        temperature=0.3  # 降低温度以获得更稳定的输出
    )

    # 定义工具
    tools = [update_selected_markets]

    # 创建提示词模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", ai_config.SYSTEM_PROMPT),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 创建 agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 创建 executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )

    return agent_executor


def run_ai_selector(config: Dict[str, Any] = None):
    """运行 AI 市场选择器"""

    print("🤖 AI 市场选择器启动中...")
    print("=" * 80)

    # 使用默认配置或用户提供的配置
    if config is None:
        config = ai_config.DEFAULT_CONFIG.copy()

    # 获取钱包余额
    print("\n📊 正在获取数据...")
    wallet_balance = get_wallet_balance()
    config['wallet_balance'] = wallet_balance
    print(f"💵 钱包余额: {wallet_balance} USDC")

    # 获取流动性市场列表
    liquidity_markets_df = get_liquidity_markets()
    print(f"📈 流动性市场数量: {len(liquidity_markets_df)}")

    # 保存到全局变量供修复使用
    global _original_markets_df
    _original_markets_df = liquidity_markets_df.copy()

    # 获取当前选择列表
    current_selections_df = get_current_selections()
    print(f"📋 当前选择数量: {len(current_selections_df)}")

    # 获取超参数表
    hyperparameters_df = get_hyperparameters()
    print(f"⚙️  超参数配置: {len(hyperparameters_df)} 条")
    
    # 构建用户提示词
    print("\n🔧 构建提示词...")
    user_prompt = ai_config.USER_PROMPT_TEMPLATE.format(
        wallet_balance=config['wallet_balance'],
        risk_preference=config['risk_preference'],
        max_markets=config['max_markets'],
        max_size_per_market=config['max_size_per_market'],
        trade_size=config['trade_size'],
        additional_preferences=config.get('additional_preferences', ''),
        liquidity_markets=format_markets_for_prompt(liquidity_markets_df),
        current_selections=format_markets_for_prompt(current_selections_df, limit=100),
        hyperparameters=format_hyperparameters(hyperparameters_df)
    )
    
    # 创建 AI Agent
    print("\n🤖 初始化 AI Agent...")
    agent_executor = create_ai_agent(config)
    
    # 运行 AI 分析
    print("\n🧠 AI 分析中...")
    print("=" * 80)
    
    try:
        result = agent_executor.invoke({"input": user_prompt})
        
        print("\n" + "=" * 80)
        print("✅ AI 分析完成！")
        print("\n📝 AI 决策:")
        print(result['output'])
        
        return result
        
    except Exception as e:
        print(f"\n❌ AI 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AI 自动化市场选择器')
    parser.add_argument('--wallet-balance', type=float, help='钱包余额（USDC）')
    parser.add_argument('--risk', choices=['conservative', 'balanced', 'aggressive'],
                        default='conservative', help='风险偏好')
    parser.add_argument('--max-markets', type=int,
                        default=int(os.getenv('AI_MAX_MARKETS', '3')),
                        help='最大市场数量')
    parser.add_argument('--max-size', type=float, default=20, help='单个市场最大投入（USDC）')
    parser.add_argument('--trade-size', type=float, default=20, help='每次交易规模（USDC）')
    parser.add_argument('--preferences', type=str, default='', help='额外偏好（如：避免加密货币相关市场）')
    
    args = parser.parse_args()
    
    # 构建配置
    config = {
        'wallet_balance': args.wallet_balance if args.wallet_balance else get_wallet_balance(),
        'risk_preference': ai_config.RISK_PREFERENCES.get(args.risk, ai_config.RISK_PREFERENCES['conservative']),
        'max_markets': args.max_markets,
        'max_size_per_market': args.max_size,
        'trade_size': args.trade_size,
        'additional_preferences': args.preferences
    }
    
    # 运行 AI 选择器
    run_ai_selector(config)

