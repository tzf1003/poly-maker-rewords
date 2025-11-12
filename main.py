import gc                      # 垃圾回收
import time                    # 时间函数
import asyncio                 # 异步I/O
import traceback               # 异常处理
import threading               # 线程管理

from poly_data.polymarket_client import PolymarketClient
from poly_data.data_utils import update_markets, update_positions, update_orders
from poly_data.websocket_handlers import connect_market_websocket, connect_user_websocket
import poly_data.global_state as global_state
from poly_data.data_processing import remove_from_performing
from dotenv import load_dotenv

load_dotenv()

def update_once():
    """
    通过获取市场数据、持仓和订单来初始化应用程序状态
    """
    update_markets()    # 从Google Sheets获取市场信息
    update_positions()  # 从Polymarket获取当前持仓
    update_orders()     # 从Polymarket获取当前订单

def remove_from_pending():
    """
    清理挂起时间过长的陈旧交易（>15秒）
    这可以防止系统卡在可能已失败的交易上
    """
    try:
        current_time = time.time()

        # 遍历所有执行中的交易
        for col in list(global_state.performing.keys()):
            for trade_id in list(global_state.performing[col]):

                try:
                    # 如果交易挂起超过15秒，移除它
                    if current_time - global_state.performing_timestamps[col].get(trade_id, current_time) > 15:
                        print(f"移除陈旧条目 {trade_id} 从 {col}，已超过15秒")
                        remove_from_performing(col, trade_id)
                        print("移除后: ", global_state.performing, global_state.performing_timestamps)
                except:
                    print("remove_from_pending 错误")
                    print(traceback.format_exc())
    except:
        print("remove_from_pending 错误")
        print(traceback.format_exc())

def update_periodically():
    """
    后台线程函数，定期更新市场数据、持仓和订单
    - 持仓和订单每5秒更新一次
    - 市场数据每30秒更新一次（每6个周期）
    - 每个周期都会移除陈旧的挂起交易
    """
    i = 1
    while True:
        time.sleep(5)  # 每5秒更新一次

        try:
            # 清理陈旧交易
            remove_from_pending()

            # 每个周期更新持仓和订单
            update_positions(avgOnly=True)  # 只更新平均价格，不更新持仓数量
            update_orders()

            # 每第6个周期更新市场数据（30秒）
            if i % 6 == 0:
                update_markets()
                i = 1

            gc.collect()  # 强制垃圾回收以释放内存
            i += 1
        except:
            print("update_periodically 错误")
            print(traceback.format_exc())

async def main():
    """
    主应用程序入口点。初始化客户端、数据并管理websocket连接
    """
    # 初始化客户端
    global_state.client = PolymarketClient()

    # 初始化状态并获取初始数据
    global_state.all_tokens = []
    update_once()
    print("初始更新后: ", global_state.orders, global_state.positions)

    print("\n")
    print(f'共有 {len(global_state.df)} 个市场, {len(global_state.positions)} 个持仓和 {len(global_state.orders)} 个订单。起始持仓: {global_state.positions}')

    # 启动后台更新线程
    update_thread = threading.Thread(target=update_periodically, daemon=True)
    update_thread.start()

    # 主循环 - 维护websocket连接
    while True:
        try:
            # 同时连接到市场和用户websockets
            await asyncio.gather(
                connect_market_websocket(global_state.all_tokens),
                connect_user_websocket()
            )
            print("重新连接到websocket")
        except:
            print("主循环错误")
            print(traceback.format_exc())

        await asyncio.sleep(1)
        gc.collect()  # 清理内存

if __name__ == "__main__":
    asyncio.run(main())