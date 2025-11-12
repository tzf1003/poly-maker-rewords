import time
import pandas as pd
from data_updater.trading_utils import get_clob_client
from data_updater.google_utils import get_spreadsheet
from data_updater.find_markets import get_sel_df, get_all_markets, get_all_results, get_markets, add_volatility_to_df
from gspread_dataframe import set_with_dataframe
import traceback

# 初始化全局变量
spreadsheet = get_spreadsheet()
client = get_clob_client()

wk_all = spreadsheet.worksheet("All Markets")
wk_vol = spreadsheet.worksheet("Volatility Markets")

sel_df = get_sel_df(spreadsheet, "Selected Markets")

def update_sheet(data, worksheet):
    all_values = worksheet.get_all_values()
    existing_num_rows = len(all_values)
    existing_num_cols = len(all_values[0]) if all_values else 0

    num_rows, num_cols = data.shape
    max_rows = max(num_rows, existing_num_rows)
    max_cols = max(num_cols, existing_num_cols)

    # 创建最大尺寸的DataFrame并用空字符串填充
    padded_data = pd.DataFrame('', index=range(max_rows), columns=range(max_cols))

    # 用原始数据及其列更新填充的DataFrame
    padded_data.iloc[:num_rows, :num_cols] = data.values
    padded_data.columns = list(data.columns) + [''] * (max_cols - num_cols)

    # 用填充的DataFrame更新表格，包括列标题
    set_with_dataframe(worksheet, padded_data, include_index=False, include_column_header=True, resize=True)

def sort_df(df):
    # 计算每列的均值和标准差
    mean_gm = df['gm_reward_per_100'].mean()
    std_gm = df['gm_reward_per_100'].std()

    mean_volatility = df['volatility_sum'].mean()
    std_volatility = df['volatility_sum'].std()

    # 标准化列
    df['std_gm_reward_per_100'] = (df['gm_reward_per_100'] - mean_gm) / std_gm
    df['std_volatility_sum'] = (df['volatility_sum'] - mean_volatility) / std_volatility

    # 为best_bid和best_ask定义自定义评分函数
    def proximity_score(value):
        if 0.1 <= value <= 0.25:
            return (0.25 - value) / 0.15
        elif 0.75 <= value <= 0.9:
            return (value - 0.75) / 0.15
        else:
            return 0

    df['bid_score'] = df['best_bid'].apply(proximity_score)
    df['ask_score'] = df['best_ask'].apply(proximity_score)

    # 创建综合得分（奖励越高越好，波动性越低越好，加上接近度得分）
    df['composite_score'] = (
        df['std_gm_reward_per_100'] -
        df['std_volatility_sum'] +
        df['bid_score'] +
        df['ask_score']
    )

    # 按综合得分降序排序
    sorted_df = df.sort_values(by='composite_score', ascending=False)

    # 删除用于计算的中间列
    sorted_df = sorted_df.drop(columns=['std_gm_reward_per_100', 'std_volatility_sum', 'bid_score', 'ask_score', 'composite_score'])

    return sorted_df

def fetch_and_process_data():
    global spreadsheet, client, wk_all, wk_vol, sel_df

    spreadsheet = get_spreadsheet()
    client = get_clob_client()

    wk_all = spreadsheet.worksheet("All Markets")
    wk_vol = spreadsheet.worksheet("Volatility Markets")
    wk_full = spreadsheet.worksheet("Full Markets")

    sel_df = get_sel_df(spreadsheet, "Selected Markets")


    all_df = get_all_markets(client)
    print("获取了所有市场")
    all_results = get_all_results(all_df, client)
    print("获取了所有结果")
    m_data, all_markets = get_markets(all_results, sel_df, maker_reward=0.75)
    print("获取了所有订单簿")

    print(f'{pd.to_datetime("now")}: 获取了长度为{len(all_markets)}的所有市场数据。')
    new_df = add_volatility_to_df(all_markets)
    new_df['volatility_sum'] =  new_df['24_hour'] + new_df['7_day'] + new_df['14_day']

    new_df = new_df.sort_values('volatility_sum', ascending=True)
    new_df['volatilty/reward'] = ((new_df['gm_reward_per_100'] / new_df['volatility_sum']).round(2)).astype(str)

    new_df = new_df[['question', 'answer1', 'answer2', 'spread', 'rewards_daily_rate', 'gm_reward_per_100', 'sm_reward_per_100', 'bid_reward_per_100', 'ask_reward_per_100',  'volatility_sum', 'volatilty/reward', 'min_size', '1_hour', '3_hour', '6_hour', '12_hour', '24_hour', '7_day', '30_day',
                     'best_bid', 'best_ask', 'volatility_price', 'max_spread', 'tick_size',
                     'neg_risk',  'market_slug', 'token1', 'token2', 'condition_id']]


    volatility_df = new_df.copy()
    volatility_df = volatility_df[new_df['volatility_sum'] < 20]
    # volatility_df = sort_df(volatility_df)
    volatility_df = volatility_df.sort_values('gm_reward_per_100', ascending=False)

    new_df = new_df.sort_values('gm_reward_per_100', ascending=False)


    print(f'{pd.to_datetime("now")}: 获取了长度为{len(new_df)}的选定市场。')

    if len(new_df) > 50:
        update_sheet(new_df, wk_all)
        update_sheet(volatility_df, wk_vol)
        update_sheet(m_data, wk_full)
    else:
        print(f'{pd.to_datetime("now")}: 由于长度为{len(new_df)}，未更新表格。')

if __name__ == "__main__":
    while True:
        try:
            fetch_and_process_data()
            time.sleep(60 * 60)  # 休眠一小时
        except Exception as e:
            traceback.print_exc()
            print(str(e))
