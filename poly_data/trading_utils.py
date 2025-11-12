import math
from poly_data.data_utils import update_positions
import poly_data.global_state as global_state

# def get_avgPrice(position, assetId):
#     curr_global = global_state.all_positions[global_state.all_positions['asset'] == str(assetId)]
#     api_position_size = 0
#     api_avgPrice = 0

#     if len(curr_global) > 0:
#         c_row = curr_global.iloc[0]
#         api_avgPrice = round(c_row['avgPrice'], 2)
#         api_position_size = c_row['size']

#     if position > 0:
#         if abs((api_position_size - position)/position * 100) > 5:
#             print("更新全局持仓")
#             update_positions()

#             try:
#                 c_row = curr_global.iloc[0]
#                 api_avgPrice = round(c_row['avgPrice'], 2)
#                 api_position_size = c_row['size']
#             except:
#                 return 0
#     return api_avgPrice

def get_best_bid_ask_deets(market, name, size, deviation_threshold=0.05):

    best_bid, best_bid_size, second_best_bid, second_best_bid_size, top_bid = find_best_price_with_size(global_state.all_data[market]['bids'], size, reverse=True)
    best_ask, best_ask_size, second_best_ask, second_best_ask_size, top_ask = find_best_price_with_size(global_state.all_data[market]['asks'], size, reverse=False)

    # 处理mid_price计算中的None值
    if best_bid is not None and best_ask is not None:
        mid_price = (best_bid + best_ask) / 2
        bid_sum_within_n_percent = sum(size for price, size in global_state.all_data[market]['bids'].items() if best_bid <= price <= mid_price * (1 + deviation_threshold))
        ask_sum_within_n_percent = sum(size for price, size in global_state.all_data[market]['asks'].items() if mid_price * (1 - deviation_threshold) <= price <= best_ask)
    else:
        mid_price = None
        bid_sum_within_n_percent = 0
        ask_sum_within_n_percent = 0

    if name == 'token2':
        # 在算术运算前处理None值
        if all(x is not None for x in [best_bid, best_ask, second_best_bid, second_best_ask, top_bid, top_ask]):
            best_bid, second_best_bid, top_bid, best_ask, second_best_ask, top_ask = 1 - best_ask, 1 - second_best_ask, 1 - top_ask, 1 - best_bid, 1 - second_best_bid, 1 - top_bid
            best_bid_size, second_best_bid_size, best_ask_size, second_best_ask_size = best_ask_size, second_best_ask_size, best_bid_size, second_best_bid_size
            bid_sum_within_n_percent, ask_sum_within_n_percent = ask_sum_within_n_percent, bid_sum_within_n_percent
        else:
            # 处理某些价格为None的情况 - 使用可用值或默认值
            if best_bid is not None and best_ask is not None:
                best_bid, best_ask = 1 - best_ask, 1 - best_bid
                best_bid_size, best_ask_size = best_ask_size, best_bid_size
            if second_best_bid is not None:
                second_best_bid = 1 - second_best_bid
            if second_best_ask is not None:
                second_best_ask = 1 - second_best_ask
            if top_bid is not None:
                top_bid = 1 - top_bid
            if top_ask is not None:
                top_ask = 1 - top_ask
            bid_sum_within_n_percent, ask_sum_within_n_percent = ask_sum_within_n_percent, bid_sum_within_n_percent



    # 以字典形式返回
    return {
        'best_bid': best_bid,
        'best_bid_size': best_bid_size,
        'second_best_bid': second_best_bid,
        'second_best_bid_size': second_best_bid_size,
        'top_bid': top_bid,
        'best_ask': best_ask,
        'best_ask_size': best_ask_size,
        'second_best_ask': second_best_ask,
        'second_best_ask_size': second_best_ask_size,
        'top_ask': top_ask,
        'bid_sum_within_n_percent': bid_sum_within_n_percent,
        'ask_sum_within_n_percent': ask_sum_within_n_percent
    }


def find_best_price_with_size(price_dict, min_size, reverse=False):
    lst = list(price_dict.items())

    if reverse:
        lst.reverse()

    best_price, best_size = None, None
    second_best_price, second_best_size = None, None
    top_price = None
    set_best = False

    for price, size in lst:
        if top_price is None:
            top_price = price

        if set_best:
            second_best_price, second_best_size = price, size
            break

        if size > min_size:
            if best_price is None:
                best_price, best_size = price, size
                set_best = True

    return best_price, best_size, second_best_price, second_best_size, top_price

def get_order_prices(best_bid, best_bid_size, top_bid,  best_ask, best_ask_size, top_ask, avgPrice, row):

    bid_price = best_bid + row['tick_size']
    ask_price = best_ask - row['tick_size']

    if best_bid_size < row['min_size'] * 1.5:
        bid_price = best_bid

    if best_ask_size < 250 * 1.5:
        ask_price = best_ask


    if bid_price >= top_ask:
        bid_price = top_bid

    if ask_price <= top_bid:
        ask_price = top_ask

    if bid_price == ask_price:
        bid_price = top_bid
        ask_price = top_ask

    # if ask_price <= avgPrice:
    #     if avgPrice - ask_price <= (row['max_spread']*1.7/100):
    #         ask_price = avgPrice

    # 临时用于休眠
    if ask_price <= avgPrice and avgPrice > 0:
        ask_price = avgPrice

    return bid_price, ask_price




def round_down(number, decimals):
    factor = 10 ** decimals
    return math.floor(number * factor) / factor

def round_up(number, decimals):
    factor = 10 ** decimals
    return math.ceil(number * factor) / factor

def get_buy_sell_amount(position, bid_price, row, other_token_position=0):
    buy_amount = 0
    sell_amount = 0

    # 获取max_size，如果未指定则默认为trade_size
    max_size = row.get('max_size', row['trade_size'])
    trade_size = row['trade_size']

    # 计算两边的总敞口
    total_exposure = position + other_token_position

    # 如果任一边未达到max_size，继续建仓
    if position < max_size:
        # 继续报价trade_size数量直到达到max_size
        remaining_to_max = max_size - position
        buy_amount = min(trade_size, remaining_to_max)

        # 只有在有实质性持仓时才卖出（以便在需要时退出）
        if position >= trade_size:
            sell_amount = min(position, trade_size)
        else:
            sell_amount = 0
    else:
        # 已达到max_size，实施渐进式退出策略
        # 在max_size时始终提供卖出trade_size数量
        sell_amount = min(position, trade_size)

        # 如果总敞口允许，继续报价买入
        if total_exposure < max_size * 2:  # 为做市提供一些灵活性
            buy_amount = trade_size
        else:
            buy_amount = 0

    # 确保符合最小订单规模
    if buy_amount > 0.7 * row['min_size'] and buy_amount < row['min_size']:
        buy_amount = row['min_size']

    # 对低价资产应用乘数
    if bid_price < 0.1 and buy_amount > 0:
        if row['multiplier'] != '':
            print(f"将买入数量乘以 {int(row['multiplier'])}")
            buy_amount = buy_amount * int(row['multiplier'])

    return buy_amount, sell_amount

