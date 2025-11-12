import json
from sortedcontainers import SortedDict
import poly_data.global_state as global_state
import poly_data.CONSTANTS as CONSTANTS

from trading import perform_trade
import time
import asyncio
from poly_data.data_utils import set_position, set_order, update_positions
from poly_data.logger import get_logger

# 创建数据处理日志记录器
processing_logger = get_logger('data_processing', console_output=True)

def process_book_data(asset, json_data):
    global_state.all_data[asset] = {
        'asset_id': json_data['asset_id'],  # Yes token的token_id
        'bids': SortedDict(),
        'asks': SortedDict()
    }

    global_state.all_data[asset]['bids'].update({float(entry['price']): float(entry['size']) for entry in json_data['bids']})
    global_state.all_data[asset]['asks'].update({float(entry['price']): float(entry['size']) for entry in json_data['asks']})

def process_price_change(asset, side, price_level, new_size, asset_id=None):
    # 如果提供了asset_id，检查是否匹配（跳过No token的更新以防止重复更新）
    if asset_id is not None and asset in global_state.all_data:
        if asset_id != global_state.all_data[asset]['asset_id']:
            return

    if side == 'bids':
        book = global_state.all_data[asset]['bids']
    else:
        book = global_state.all_data[asset]['asks']

    if new_size == 0:
        if price_level in book:
            del book[price_level]
    else:
        book[price_level] = new_size

def process_data(json_datas, trade=True):

    for json_data in json_datas:
        event_type = json_data['event_type']
        asset = json_data['market']

        if event_type == 'book':
            process_book_data(asset, json_data)

            if trade:
                asyncio.create_task(perform_trade(asset))

        elif event_type == 'price_change':
            for data in json_data['price_changes']:
                side = 'bids' if data['side'] == 'BUY' else 'asks'
                price_level = float(data['price'])
                new_size = float(data['size'])
                process_price_change(asset, side, price_level, new_size)

                if trade:
                    asyncio.create_task(perform_trade(asset))


        # pretty_print(f'收到 {asset} 的订单簿更新:', global_state.all_data[asset])

def add_to_performing(col, id):
    if col not in global_state.performing:
        global_state.performing[col] = set()

    if col not in global_state.performing_timestamps:
        global_state.performing_timestamps[col] = {}

    # 添加交易ID并跟踪其时间戳
    global_state.performing[col].add(id)
    global_state.performing_timestamps[col][id] = time.time()

def remove_from_performing(col, id):
    if col in global_state.performing:
        global_state.performing[col].discard(id)

    if col in global_state.performing_timestamps:
        global_state.performing_timestamps[col].pop(id, None)

def process_user_data(rows):

    for row in rows:
        market = row['market']

        side = row['side'].lower()
        token = row['asset_id']

        if token in global_state.REVERSE_TOKENS:
            col = token + "_" + side

            if row['event_type'] == 'trade':
                size = 0
                price = 0
                maker_outcome = ""
                taker_outcome = row['outcome']

                is_user_maker = False
                for maker_order in row['maker_orders']:
                    if maker_order['maker_address'].lower() == global_state.client.browser_wallet.lower():
                        processing_logger.debug("用户是做市方")
                        size = float(maker_order['matched_amount'])
                        price = float(maker_order['price'])

                        is_user_maker = True
                        maker_outcome = maker_order['outcome'] # 这很有趣

                        if maker_outcome == taker_outcome:
                            side = 'buy' if side == 'sell' else 'sell' # 需要反转，因为我们也反转了token
                        else:
                            token = global_state.REVERSE_TOKENS[token]

                if not is_user_maker:
                    size = float(row['size'])
                    price = float(row['price'])
                    processing_logger.debug("用户是吃单方")

                processing_logger.info(f"交易事件 - 市场: {row['market']}, ID: {row['id']}, 状态: {row['status']}, "
                                      f"方向: {row['side']}, 做市方结果: {maker_outcome}, 吃单方结果: {taker_outcome}, "
                                      f"处理后方向: {side}, 数量: {size}")


                if row['status'] == 'CONFIRMED' or row['status'] == 'FAILED' :
                    if row['status'] == 'FAILED':
                        processing_logger.warning(f"{token} 的交易失败，减少中")
                        asyncio.create_task(asyncio.sleep(2))
                        update_positions()
                    else:
                        remove_from_performing(col, row['id'])
                        processing_logger.info(f"已确认。执行中数量: {len(global_state.performing[col])}")
                        processing_logger.debug(f"最后交易更新: {global_state.last_trade_update}")
                        processing_logger.debug(f"执行中: {global_state.performing}")
                        processing_logger.debug(f"执行中时间戳: {global_state.performing_timestamps}")

                        asyncio.create_task(perform_trade(market))

                elif row['status'] == 'MATCHED':
                    add_to_performing(col, row['id'])

                    processing_logger.info(f"已匹配。执行中数量: {len(global_state.performing[col])}")
                    set_position(token, side, size, price)
                    processing_logger.info(f"匹配后持仓: {global_state.positions[str(token)]}")
                    processing_logger.debug(f"最后交易更新: {global_state.last_trade_update}")
                    processing_logger.debug(f"执行中: {global_state.performing}")
                    processing_logger.debug(f"执行中时间戳: {global_state.performing_timestamps}")
                    asyncio.create_task(perform_trade(market))
                elif row['status'] == 'MINED':
                    remove_from_performing(col, row['id'])

            elif row['event_type'] == 'order':
                processing_logger.info(f"订单事件 - 市场: {row['market']}, 状态: {row['status']}, 类型: {row['type']}, "
                                      f"方向: {side}, 原始数量: {row['original_size']}, 已匹配数量: {row['size_matched']}")

                set_order(token, side, float(row['original_size']) - float(row['size_matched']), row['price'])
                asyncio.create_task(perform_trade(market))

    else:
        processing_logger.warning(f"收到 {market} 的用户数据，但不在列表中")
