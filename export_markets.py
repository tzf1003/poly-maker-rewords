#!/usr/bin/env python3
"""
导出市场数据用于 AI 分析
"""

import pandas as pd
from poly_utils.google_utils import get_spreadsheet
import sys

def export_markets_for_ai(sheet_name='All Markets', output_file='markets_for_ai.csv'):
    """
    从 Google Sheets 导出市场数据用于 AI 分析
    
    参数:
        sheet_name: 工作表名称 ('All Markets' 或 'Volatility Markets')
        output_file: 输出文件名
    """
    print(f"📊 正在从 '{sheet_name}' 导出市场数据...")
    
    try:
        # 获取表格数据
        spreadsheet = get_spreadsheet(read_only=True)
        ws = spreadsheet.worksheet(sheet_name)
        data = ws.get_all_records()
        
        # 转换为 DataFrame
        df = pd.DataFrame(data)
        
        print(f"✅ 成功获取 {len(df)} 个市场")
        
        # 选择关键字段用于 AI 分析
        columns = [
            'question',
            'answer1', 
            'answer2',
            'spread',
            'rewards_daily_rate',
            'gm_reward_per_100',
            'sm_reward_per_100',
            'bid_reward_per_100',
            'ask_reward_per_100',
            'volatility_sum',
            'volatilty/reward',
            'min_size',
            '1_hour',
            '3_hour',
            '6_hour',
            '12_hour',
            '24_hour',
            '7_day',
            '30_day',
            'best_bid',
            'best_ask',
            'volatility_price',
            'max_spread',
            'tick_size',
            'neg_risk',
            'market_slug'
        ]
        
        # 检查哪些列存在
        available_columns = [col for col in columns if col in df.columns]
        missing_columns = [col for col in columns if col not in df.columns]
        
        if missing_columns:
            print(f"⚠️  以下字段不存在: {', '.join(missing_columns)}")
        
        df_export = df[available_columns]
        
        # 导出为 CSV
        df_export.to_csv(output_file, index=False)
        print(f"✅ 已导出到 {output_file}")
        
        # 打印统计信息
        print("\n📈 市场统计:")
        print(f"  总市场数: {len(df_export)}")
        
        if 'spread' in df_export.columns:
            print(f"  平均价差: {df_export['spread'].mean():.4f}")
            print(f"  最小价差: {df_export['spread'].min():.4f}")
            print(f"  最大价差: {df_export['spread'].max():.4f}")
        
        if 'rewards_daily_rate' in df_export.columns:
            print(f"  平均奖励率: {df_export['rewards_daily_rate'].mean():.2f}%")
            print(f"  最高奖励率: {df_export['rewards_daily_rate'].max():.2f}%")
        
        if 'volatility_sum' in df_export.columns:
            print(f"  平均波动率: {df_export['volatility_sum'].mean():.2f}%")
            print(f"  最低波动率: {df_export['volatility_sum'].min():.2f}%")
        
        if 'min_size' in df_export.columns:
            print(f"  平均最小规模: {df_export['min_size'].mean():.2f} USDC")
        
        # 打印前 3 行预览
        print("\n📋 数据预览（前 3 行）:")
        print("=" * 100)
        
        preview_columns = ['question', 'spread', 'rewards_daily_rate', 'volatility_sum', 'min_size', 'best_bid', 'best_ask']
        preview_columns = [col for col in preview_columns if col in df_export.columns]
        
        for idx, row in df_export[preview_columns].head(3).iterrows():
            print(f"\n市场 {idx + 1}:")
            for col in preview_columns:
                print(f"  {col}: {row[col]}")
        
        print("\n" + "=" * 100)
        
        # 生成 AI 提示词模板
        print("\n💡 使用提示:")
        print(f"1. 打开 {output_file}")
        print("2. 复制 CSV 内容")
        print("3. 使用 AI_MARKET_SELECTION_PROMPT.md 中的提示词")
        print("4. 将 CSV 数据粘贴到提示词中")
        print("5. 发送给 AI (ChatGPT, Claude 等) 进行分析")
        
        return df_export
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def filter_markets(df, max_spread=0.15, min_rewards=15, max_volatility=15, max_min_size=50):
    """
    预筛选市场
    
    参数:
        df: 市场数据 DataFrame
        max_spread: 最大价差
        min_rewards: 最小奖励率
        max_volatility: 最大波动率
        max_min_size: 最大最小规模
    """
    print(f"\n🔍 应用筛选条件:")
    print(f"  spread < {max_spread}")
    print(f"  rewards_daily_rate > {min_rewards}%")
    print(f"  volatility_sum < {max_volatility}%")
    print(f"  min_size < {max_min_size} USDC")
    
    filtered = df.copy()
    
    if 'spread' in filtered.columns:
        filtered = filtered[filtered['spread'] < max_spread]
    
    if 'rewards_daily_rate' in filtered.columns:
        filtered = filtered[filtered['rewards_daily_rate'] > min_rewards]
    
    if 'volatility_sum' in filtered.columns:
        filtered = filtered[filtered['volatility_sum'] < max_volatility]
    
    if 'min_size' in filtered.columns:
        filtered = filtered[filtered['min_size'] < max_min_size]
    
    print(f"\n✅ 筛选后剩余 {len(filtered)} 个市场（原始 {len(df)} 个）")
    
    return filtered

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='导出市场数据用于 AI 分析')
    parser.add_argument('--sheet', default='All Markets', 
                        choices=['All Markets', 'Volatility Markets'],
                        help='工作表名称')
    parser.add_argument('--output', default='markets_for_ai.csv',
                        help='输出文件名')
    parser.add_argument('--filter', action='store_true',
                        help='应用预筛选条件')
    parser.add_argument('--max-spread', type=float, default=0.15,
                        help='最大价差（默认 0.15）')
    parser.add_argument('--min-rewards', type=float, default=15,
                        help='最小奖励率（默认 15%%）')
    parser.add_argument('--max-volatility', type=float, default=15,
                        help='最大波动率（默认 15%%）')
    parser.add_argument('--max-min-size', type=float, default=50,
                        help='最大最小规模（默认 50 USDC）')
    
    args = parser.parse_args()
    
    # 导出数据
    df = export_markets_for_ai(args.sheet, args.output)
    
    if df is not None and args.filter:
        # 应用筛选
        filtered_df = filter_markets(
            df,
            max_spread=args.max_spread,
            min_rewards=args.min_rewards,
            max_volatility=args.max_volatility,
            max_min_size=args.max_min_size
        )
        
        # 保存筛选后的数据
        filtered_output = args.output.replace('.csv', '_filtered.csv')
        filtered_df.to_csv(filtered_output, index=False)
        print(f"\n✅ 筛选后的数据已保存到 {filtered_output}")
        
        # 显示筛选后的市场列表
        if len(filtered_df) > 0:
            print("\n📋 筛选后的市场:")
            print("=" * 100)
            for idx, row in filtered_df.iterrows():
                print(f"\n{idx + 1}. {row.get('question', 'N/A')}")
                print(f"   价差: {row.get('spread', 'N/A'):.4f} | "
                      f"奖励: {row.get('rewards_daily_rate', 'N/A'):.1f}% | "
                      f"波动: {row.get('volatility_sum', 'N/A'):.2f}% | "
                      f"最小规模: {row.get('min_size', 'N/A')} USDC")

