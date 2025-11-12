import gc                       # 垃圾回收
import os                       # 操作系统接口
import json                     # JSON处理
import asyncio                  # 异步I/O
import traceback                # 异常处理
import pandas as pd             # 数据分析库
import math                     # 数学函数

import poly_data.global_state as global_state
import poly_data.CONSTANTS as CONSTANTS

# 导入交易工具函数
from poly_data.trading_utils import get_best_bid_ask_deets, get_order_prices, get_buy_sell_amount, round_down, round_up
from poly_data.data_utils import get_position, get_order, set_position

# 创建目录用于存储持仓风险信息
if not os.path.exists('positions/'):
    os.makedirs('positions/')

def send_buy_order(order):
    """
    为特定token创建买单

    此函数：
    1. 取消该token的任何现有订单
    2. 检查订单价格是否在可接受范围内
    3. 如果条件满足则创建新的买单

    参数：
        order (dict): 订单详情，包括token、价格、数量和市场参数
    """
    client = global_state.client

    # 只有在需要进行重大更改时才取消现有订单
    existing_buy_size = order['orders']['buy']['size']
    existing_buy_price = order['orders']['buy']['price']

    # 如果价格变化显著或数量需要大幅调整，则取消订单
    price_diff = abs(existing_buy_price - order['price']) if existing_buy_price > 0 else float('inf')
    size_diff = abs(existing_buy_size - order['size']) if existing_buy_size > 0 else float('inf')

    should_cancel = (
        price_diff > 0.005 or  # 如果价格差 > 0.5分则取消
        size_diff > order['size'] * 0.1 or  # 如果数量差 > 10%则取消
        existing_buy_size == 0  # 如果没有现有买单则取消
    )

    if should_cancel and (existing_buy_size > 0 or order['orders']['sell']['size'] > 0):
        print(f"取消买单 - 价格差: {price_diff:.4f}, 数量差: {size_diff:.1f}")
        client.cancel_all_asset(order['token'])
    elif not should_cancel:
        print(f"保持现有买单 - 微小变化: 价格差: {price_diff:.4f}, 数量差: {size_diff:.1f}")
        return  # 如果现有订单没问题就不下新单

    # 根据市场价差计算最低可接受价格
    incentive_start = order['mid_price'] - order['max_spread']/100

    trade = True

    # 不要下低于激励阈值的订单
    if order['price'] < incentive_start:
        trade = False

    if trade:
        # 只下价格在0.1到0.9之间的订单，避免极端持仓
        if order['price'] >= 0.1 and order['price'] < 0.9:
            print(f'创建新订单，数量 {order["size"]}，价格 {order["price"]}')
            print(order['token'], 'BUY', order['price'], order['size'])
            client.create_order(
                order['token'],
                'BUY',
                order['price'],
                order['size'],
                True if order['neg_risk'] == 'TRUE' else False
            )
        else:
            print("不创建买单，因为价格超出可接受范围(0.1-0.9)")
    else:
        print(f'不创建新订单，因为订单价格 {order["price"]} 低于激励起始价格 {incentive_start}。中间价为 {order["mid_price"]}')


def send_sell_order(order):
    """
    为特定token创建卖单

    此函数：
    1. 取消该token的任何现有订单
    2. 使用指定参数创建新的卖单

    参数：
        order (dict): 订单详情，包括token、价格、数量和市场参数
    """
    client = global_state.client

    # 只有在需要进行重大更改时才取消现有订单
    existing_sell_size = order['orders']['sell']['size']
    existing_sell_price = order['orders']['sell']['price']

    # 如果价格变化显著或数量需要大幅调整，则取消订单
    price_diff = abs(existing_sell_price - order['price']) if existing_sell_price > 0 else float('inf')
    size_diff = abs(existing_sell_size - order['size']) if existing_sell_size > 0 else float('inf')

    should_cancel = (
        price_diff > 0.005 or  # 如果价格差 > 0.5分则取消
        size_diff > order['size'] * 0.1 or  # 如果数量差 > 10%则取消
        existing_sell_size == 0  # 如果没有现有卖单则取消
    )

    if should_cancel and (existing_sell_size > 0 or order['orders']['buy']['size'] > 0):
        print(f"取消卖单 - 价格差: {price_diff:.4f}, 数量差: {size_diff:.1f}")
        client.cancel_all_asset(order['token'])
    elif not should_cancel:
        print(f"保持现有卖单 - 微小变化: 价格差: {price_diff:.4f}, 数量差: {size_diff:.1f}")
        return  # 如果现有订单没问题就不下新单

    print(f'创建新订单，数量 {order["size"]}，价格 {order["price"]}')
    client.create_order(
        order['token'],
        'SELL',
        order['price'],
        order['size'],
        True if order['neg_risk'] == 'TRUE' else False
    )

# 字典，用于存储每个市场的锁，防止同一市场的并发交易
market_locks = {}

async def perform_trade(market):
    """
    处理特定市场做市的主交易函数

    此函数：
    1. 在可能的情况下合并持仓以释放资金
    2. 分析市场以确定最优买卖价格
    3. 根据持仓规模和市场条件管理买卖订单
    4. 实施止损和止盈的风险管理逻辑

    参数：
        market (str): 要交易的市场ID
    """
    # 如果此市场的锁不存在，则创建一个
    if market not in market_locks:
        market_locks[market] = asyncio.Lock()

    # 使用锁防止同一市场的并发交易
    async with market_locks[market]:
        try:
            client = global_state.client
            # 从配置中获取市场详情
            row = global_state.df[global_state.df['condition_id'] == market].iloc[0]
            # 从tick_size确定小数精度
            round_length = len(str(row['tick_size']).split(".")[1])

            # 获取此市场类型的交易参数
            params = global_state.params[row['param_type']]

            # 创建包含市场两个结果的列表
            deets = [
                {'name': 'token1', 'token': row['token1'], 'answer': row['answer1']},
                {'name': 'token2', 'token': row['token2'], 'answer': row['answer2']}
            ]
            print(f"\n\n{pd.Timestamp.utcnow().tz_localize(None)}: {row['question']}")

            # 获取两个结果的当前持仓
            pos_1 = get_position(row['token1'])['size']
            pos_2 = get_position(row['token2'])['size']

            # ------- 持仓合并逻辑 -------
            # 计算是否有可以合并的对立持仓
            amount_to_merge = min(pos_1, pos_2)

            # 只有当持仓高于最小阈值时才合并
            if float(amount_to_merge) > CONSTANTS.MIN_MERGE_SIZE:
                # 从区块链获取精确的持仓规模用于合并
                pos_1 = client.get_position(row['token1'])[0]
                pos_2 = client.get_position(row['token2'])[0]
                amount_to_merge = min(pos_1, pos_2)
                scaled_amt = amount_to_merge / 10**6

                if scaled_amt > CONSTANTS.MIN_MERGE_SIZE:
                    print(f"持仓1规模为 {pos_1}，持仓2规模为 {pos_2}。正在合并持仓")
                    # 执行合并操作
                    client.merge_positions(amount_to_merge, market, row['neg_risk'] == 'TRUE')
                    # 更新我们的本地持仓跟踪
                    set_position(row['token1'], 'SELL', scaled_amt, 0, 'merge')
                    set_position(row['token2'], 'SELL', scaled_amt, 0, 'merge')

            # ------- 每个结果的交易逻辑 -------
            # 遍历市场中的两个结果（YES和NO）
            for detail in deets:
                token = int(detail['token'])

                # 获取此token的当前订单
                orders = get_order(token)

                # 获取市场深度和价格信息
                deets = get_best_bid_ask_deets(market, detail['name'], 100, 0.1)

                # 如果下面这些值中有None，则使用最小规模20调用
                if deets['best_bid'] is None or deets['best_ask'] is None or deets['best_bid_size'] is None or deets['best_ask_size'] is None:
                    deets = get_best_bid_ask_deets(market, detail['name'], 20, 0.1)

                # 提取所有订单簿详情
                best_bid = deets['best_bid']
                best_bid_size = deets['best_bid_size']
                second_best_bid = deets['second_best_bid']
                second_best_bid_size = deets['second_best_bid_size']
                top_bid = deets['top_bid']
                best_ask = deets['best_ask']
                best_ask_size = deets['best_ask_size']
                second_best_ask = deets['second_best_ask']
                second_best_ask_size = deets['second_best_ask_size']
                top_ask = deets['top_ask']

                # 将价格四舍五入到适当的精度
                best_bid = round(best_bid, round_length)
                best_ask = round(best_ask, round_length)

                # 计算市场中买入与卖出流动性的比率
                try:
                    overall_ratio = (deets['bid_sum_within_n_percent']) / (deets['ask_sum_within_n_percent'])
                except:
                    overall_ratio = 0

                try:
                    second_best_bid = round(second_best_bid, round_length)
                    second_best_ask = round(second_best_ask, round_length)
                except:
                    pass

                top_bid = round(top_bid, round_length)
                top_ask = round(top_ask, round_length)

                # 获取我们当前的持仓和平均价格
                pos = get_position(token)
                position = pos['size']
                avgPrice = pos['avgPrice']

                position = round_down(position, 2)

                # 根据市场条件计算最优买卖价格
                bid_price, ask_price = get_order_prices(
                    best_bid, best_bid_size, top_bid, best_ask,
                    best_ask_size, top_ask, avgPrice, row
                )

                bid_price = round(bid_price, round_length)
                ask_price = round(ask_price, round_length)

                # 计算中间价作为参考
                mid_price = (top_bid + top_ask) / 2

                # 记录此结果的市场条件
                print(f"\n对于 {detail['answer']}. 订单: {orders} 持仓: {position}, "
                      f"平均价: {avgPrice}, 最佳买价: {best_bid}, 最佳卖价: {best_ask}, "
                      f"买单价格: {bid_price}, 卖单价格: {ask_price}, 中间价: {mid_price}")

                # 获取相反token的持仓以计算总敞口
                other_token = global_state.REVERSE_TOKENS[str(token)]
                other_position = get_position(other_token)['size']

                # 根据我们的持仓计算买入或卖出多少
                buy_amount, sell_amount = get_buy_sell_amount(position, bid_price, row, other_position)

                # 获取max_size用于日志记录（与get_buy_sell_amount中的逻辑相同）
                max_size = row.get('max_size', row['trade_size'])

                # 准备包含所有必要信息的订单对象
                order = {
                    "token": token,
                    "mid_price": mid_price,
                    "neg_risk": row['neg_risk'],
                    "max_spread": row['max_spread'],
                    'orders': orders,
                    'token_name': detail['name'],
                    'row': row
                }

                print(f"持仓: {position}, 相反持仓: {other_position}, "
                      f"交易规模: {row['trade_size']}, 最大规模: {max_size}, "
                      f"买入数量: {buy_amount}, 卖出数量: {sell_amount}")

                # 存储此市场风险管理信息的文件
                fname = 'positions/' + str(market) + '.json'

                # ------- 卖单逻辑 -------
                if sell_amount > 0:
                    # 如果没有平均价格（没有真实持仓）则跳过
                    if avgPrice == 0:
                        print("平均价为0。跳过")
                        continue

                    order['size'] = sell_amount
                    order['price'] = ask_price

                    # 获取新的市场数据用于风险评估
                    n_deets = get_best_bid_ask_deets(market, detail['name'], 100, 0.1)

                    # 计算当前市场价格和价差
                    mid_price = round_up((n_deets['best_bid'] + n_deets['best_ask']) / 2, round_length)
                    spread = round(n_deets['best_ask'] - n_deets['best_bid'], 2)

                    # 计算持仓的当前盈亏
                    pnl = (mid_price - avgPrice) / avgPrice * 100

                    print(f"中间价: {mid_price}, 价差: {spread}, 盈亏: {pnl}")

                    # 准备风险详情用于跟踪
                    risk_details = {
                        'time': str(pd.Timestamp.utcnow().tz_localize(None)),
                        'question': row['question']
                    }

                    try:
                        ratio = (n_deets['bid_sum_within_n_percent']) / (n_deets['ask_sum_within_n_percent'])
                    except:
                        ratio = 0

                    pos_to_sell = sell_amount  # 风险规避场景下要卖出的数量

                    # ------- 止损逻辑 -------
                    # 触发止损如果满足以下任一条件：
                    # 1. 盈亏低于阈值且价差足够小可以退出
                    # 2. 波动性过高
                    if (pnl < params['stop_loss_threshold'] and spread <= params['spread_threshold']) or row['3_hour'] > params['volatility_threshold']:
                        risk_details['msg'] = (f"卖出 {pos_to_sell}，因为价差为 {spread}，盈亏为 {pnl}，"
                                              f"比率为 {ratio}，3小时波动率为 {row['3_hour']}")
                        print("止损触发: ", risk_details['msg'])

                        # 以市场最佳买价卖出以确保成交
                        order['size'] = pos_to_sell
                        order['price'] = n_deets['best_bid']

                        # 设置止损后避免交易的时间段
                        risk_details['sleep_till'] = str(pd.Timestamp.utcnow().tz_localize(None) +
                                                        pd.Timedelta(hours=params['sleep_period']))

                        print("风险规避中")
                        send_sell_order(order)
                        client.cancel_all_market(market)

                        # 将风险详情保存到文件
                        open(fname, 'w').write(json.dumps(risk_details))
                        continue

                # ------- 买单逻辑 -------
                # 获取max_size，如果未指定则默认为trade_size
                max_size = row.get('max_size', row['trade_size'])

                # 只有在以下情况下才买入：
                # 1. 持仓小于max_size（新逻辑）
                # 2. 持仓小于绝对上限（250）
                # 3. 买入数量高于最小规模
                if position < max_size and position < 250 and buy_amount > 0 and buy_amount >= row['min_size']:
                    # 从市场数据获取参考价格
                    sheet_value = row['best_bid']

                    if detail['name'] == 'token2':
                        sheet_value = 1 - row['best_ask']

                    sheet_value = round(sheet_value, round_length)
                    order['size'] = buy_amount
                    order['price'] = bid_price

                    # 检查价格是否远离参考值
                    price_change = abs(order['price'] - sheet_value)

                    send_buy = True

                    # ------- 风险规避期检查 -------
                    # 如果我们处于风险规避期（止损后），不要买入
                    if os.path.isfile(fname):
                        risk_details = json.load(open(fname))

                        start_trading_at = pd.to_datetime(risk_details['sleep_till'])
                        current_time = pd.Timestamp.utcnow().tz_localize(None)

                        print(risk_details, current_time, start_trading_at)
                        if current_time < start_trading_at:
                            send_buy = False
                            print(f"不发送买单，因为最近风险规避。"
                                 f"风险规避时间 {risk_details['time']}")

                    # 只有在不处于风险规避期时才继续
                    if send_buy:
                        # 如果波动性高或价格远离参考值，不要买入
                        if row['3_hour'] > params['volatility_threshold'] or price_change >= 0.05:
                            print(f'3小时波动率 {row["3_hour"]} 大于最大波动率 '
                                  f'{params["volatility_threshold"]} 或价格 {order["price"]} 超出 '
                                  f'{sheet_value} 的0.05范围。取消所有订单')
                            client.cancel_all_asset(order['token'])
                        else:
                            # 检查反向持仓（持有相反结果）
                            rev_token = global_state.REVERSE_TOKENS[str(token)]
                            rev_pos = get_position(rev_token)

                            # 如果我们有显著的对立持仓，不要再买入
                            if rev_pos['size'] > row['min_size']:
                                print("跳过创建新买单，因为存在反向持仓")
                                if orders['buy']['size'] > CONSTANTS.MIN_MERGE_SIZE:
                                    print("取消买单，因为存在反向持仓")
                                    client.cancel_all_asset(order['token'])

                                continue

                            # 检查市场买卖量比率
                            if overall_ratio < 0:
                                send_buy = False
                                print(f"不发送买单，因为总体比率为 {overall_ratio}")
                                client.cancel_all_asset(order['token'])
                            else:
                                # 如果满足以下任一条件，则下新买单：
                                # 1. 我们可以获得比当前订单更好的价格
                                if best_bid > orders['buy']['price']:
                                    print(f"为 {token} 发送买单，因为价格更好。"
                                          f"订单如下: {orders['buy']}。最佳买价: {best_bid}")
                                    send_buy_order(order)
                                # 2. 当前持仓 + 订单不足以达到max_size
                                elif position + orders['buy']['size'] < 0.95 * max_size:
                                    print(f"为 {token} 发送买单，因为持仓+规模不足")
                                    send_buy_order(order)
                                # 3. 我们当前的订单太大，需要调整规模
                                elif orders['buy']['size'] > order['size'] * 1.01:
                                    print(f"重新发送买单，因为未成交订单太大")
                                    send_buy_order(order)
                                # 注释掉的逻辑：当市场条件变化时取消订单
                                # elif best_bid_size < orders['buy']['size'] * 0.98 and abs(best_bid - second_best_bid) > 0.03:
                                #     print(f"取消买单，因为最佳规模小于未成交订单的90%且价差太大")
                                #     global_state.client.cancel_all_asset(order['token'])

                # ------- 止盈 / 卖单管理 -------
                elif sell_amount > 0:
                    order['size'] = sell_amount

                    # 根据平均成本计算止盈价格
                    tp_price = round_up(avgPrice + (avgPrice * params['take_profit_threshold']/100), round_length)
                    order['price'] = round_up(tp_price if ask_price < tp_price else ask_price, round_length)

                    tp_price = float(tp_price)
                    order_price = float(orders['sell']['price'])

                    # 计算当前订单与理想价格之间的百分比差异
                    diff = abs(order_price - tp_price)/tp_price * 100

                    # 更新卖单如果：
                    # 1. 当前订单价格与目标价格差异显著
                    if diff > 2:
                        print(f"为 {token} 发送卖单，因为当前订单价格 "
                              f"{order_price} 偏离止盈价格 {tp_price}，差异为 {diff}")
                        send_sell_order(order)
                    # 2. 当前订单规模对于我们的持仓来说太小
                    elif orders['sell']['size'] < position * 0.97:
                        print(f"为 {token} 发送卖单，因为卖出规模不足。"
                              f"持仓: {position}, 卖出规模: {orders['sell']['size']}")
                        send_sell_order(order)

                    # 注释掉的更新卖单的额外条件
                    # elif orders['sell']['price'] < ask_price:
                    #     print(f"更新 {token} 的卖单，因为价格不正确")
                    #     send_sell_order(order)
                    # elif best_ask_size < orders['sell']['size'] * 0.98 and abs(best_ask - second_best_ask) > 0.03...:
                    #     print(f"取消卖单，因为最佳规模小于未成交订单的90%...")
                    #     send_sell_order(order)

        except Exception as ex:
            print(f"为 {market} 执行交易时出错: {ex}")
            traceback.print_exc()

        # 清理内存并引入小延迟
        gc.collect()
        await asyncio.sleep(2)