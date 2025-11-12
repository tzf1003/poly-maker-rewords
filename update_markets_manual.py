#!/usr/bin/env python3
"""
手动更新 Selected Markets
使用正确的 max_size 和 trade_size 比例
"""

from poly_utils.google_utils import get_spreadsheet

def update_selected_markets():
    """更新 Selected Markets 工作表"""
    
    spreadsheet = get_spreadsheet()
    ws = spreadsheet.worksheet('Selected Markets')
    
    # 清空现有数据
    ws.clear()
    
    # 添加表头
    ws.append_row(['question', 'max_size', 'trade_size', 'param_type', 'comments'])
    
    # 添加市场（使用正确的参数比例）
    markets = [
        {
            'question': 'Metamask FDV above $1B one day after launch?',
            'max_size': 100,
            'trade_size': 25,
            'param_type': 'mid',
            'comments': 'AI选择: 流动性极佳(spread 0.01), 奖励率高(10%), 波动率适中(9.43%), 综合评分 87/100 | 置信度: 88%'
        },
        {
            'question': 'U.S. agrees to a new trade deal with "Australia"?',
            'max_size': 100,
            'trade_size': 25,
            'param_type': 'mid',
            'comments': 'AI选择: 流动性极佳(spread 0.01), 低波动率(6.8%), 主题独立性强, 综合评分 82/100 | 置信度: 82%'
        },
        {
            'question': 'Will Atlas introduce ads by December 31?',
            'max_size': 80,
            'trade_size': 20,
            'param_type': 'mid',
            'comments': 'AI选择: 流动性优秀(spread 0.03), 低波动率(6.69%), vol/reward 0.12 极佳, 综合评分 82/100 | 置信度: 82%'
        }
    ]
    
    for market in markets:
        ws.append_row([
            market['question'],
            market['max_size'],
            market['trade_size'],
            market['param_type'],
            market['comments']
        ])
    
    print(f"✅ 成功更新 {len(markets)} 个市场到 Selected Markets")
    print("\n市场列表:")
    for i, market in enumerate(markets, 1):
        print(f"{i}. {market['question']}")
        print(f"   max_size: {market['max_size']}, trade_size: {market['trade_size']}")
        print(f"   比例: trade_size = max_size / {market['max_size'] / market['trade_size']:.1f}")
        print()

if __name__ == '__main__':
    update_selected_markets()

