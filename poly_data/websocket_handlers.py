import asyncio                      # 异步I/O
import json                        # JSON处理
import websockets                  # WebSocket客户端
import traceback                   # 异常处理

from poly_data.data_processing import process_data, process_user_data
import poly_data.global_state as global_state

async def connect_market_websocket(chunk):
    """
    连接到Polymarket的市场WebSocket API并处理市场更新

    此函数：
    1. 建立到Polymarket API的WebSocket连接
    2. 订阅指定市场token列表的更新
    3. 处理传入的订单簿和价格更新

    参数：
        chunk (list): 要订阅的token ID列表

    注意：
        如果连接丢失，函数将退出，主循环将在短暂延迟后尝试重新连接
    """
    uri = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    async with websockets.connect(uri, ping_interval=5, ping_timeout=None) as websocket:
        # 准备并发送订阅消息
        message = {"assets_ids": chunk}
        await websocket.send(json.dumps(message))

        print("\n")
        print(f"已发送市场订阅消息: {message}")

        try:
            # 无限期处理传入的市场数据
            while True:
                message = await websocket.recv()
                json_data = json.loads(message)
                # 处理订单簿更新并根据需要触发交易
                process_data(json_data)
        except websockets.ConnectionClosed:
            print("市场websocket连接已关闭")
            print(traceback.format_exc())
        except Exception as e:
            print(f"市场websocket异常: {e}")
            print(traceback.format_exc())
        finally:
            # 尝试重新连接前的短暂延迟
            await asyncio.sleep(5)

async def connect_user_websocket():
    """
    连接到Polymarket的用户WebSocket API并处理订单/交易更新

    此函数：
    1. 建立到Polymarket用户API的WebSocket连接
    2. 使用API凭证进行身份验证
    3. 处理用户的传入订单和交易更新

    注意：
        如果连接丢失，函数将退出，主循环将在短暂延迟后尝试重新连接
    """
    uri = "wss://ws-subscriptions-clob.polymarket.com/ws/user"

    async with websockets.connect(uri, ping_interval=5, ping_timeout=None) as websocket:
        # 准备带有API凭证的身份验证消息
        message = {
            "type": "user",
            "auth": {
                "apiKey": global_state.client.client.creds.api_key,
                "secret": global_state.client.client.creds.api_secret,
                "passphrase": global_state.client.client.creds.api_passphrase
            }
        }

        # 发送身份验证消息
        await websocket.send(json.dumps(message))

        print("\n")
        print(f"已发送用户订阅消息")

        try:
            # 无限期处理传入的用户数据
            while True:
                message = await websocket.recv()
                json_data = json.loads(message)
                # 处理交易和订单更新
                process_user_data(json_data)
        except websockets.ConnectionClosed:
            print("用户websocket连接已关闭")
            print(traceback.format_exc())
        except Exception as e:
            print(f"用户websocket异常: {e}")
            print(traceback.format_exc())
        finally:
            # 尝试重新连接前的短暂延迟
            await asyncio.sleep(5)