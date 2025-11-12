from dotenv import load_dotenv          # 环境变量管理
import os                           # 操作系统接口

# Polymarket API客户端库
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, BalanceAllowanceParams, AssetType, PartialCreateOrderOptions
from py_clob_client.constants import POLYGON

# Web3库用于区块链交互
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

import requests                     # HTTP请求
import pandas as pd                 # 数据分析
import json                         # JSON处理
import subprocess                   # 用于调用外部进程

from py_clob_client.clob_types import OpenOrderParams

# 智能合约ABIs
from poly_data.abis import NegRiskAdapterABI, ConditionalTokenABI, erc20_abi

# 网络工具和日志
from poly_data.network_utils import retry_on_network_error
from poly_data.logger import get_logger

# 创建客户端日志记录器
client_logger = get_logger('polymarket_client', console_output=True)

# 加载环境变量
load_dotenv()


class PolymarketClient:
    """
    用于与Polymarket的API和智能合约交互的客户端。

    此类提供以下方法：
    - 创建和管理订单
    - 查询订单簿数据
    - 检查余额和持仓
    - 合并持仓

    客户端连接到Polymarket API和Polygon区块链。
    """

    def __init__(self, pk='default') -> None:
        """
        使用API和区块链连接初始化Polymarket客户端。

        参数：
            pk (str, optional): 私钥标识符，默认为'default'
        """
        host="https://clob.polymarket.com"

        # 从环境变量获取凭证
        key=os.getenv("PK")
        browser_address = os.getenv("BROWSER_ADDRESS")

        # 不打印敏感的钱包信息
        client_logger.info("正在初始化Polymarket客户端...")
        chain_id=POLYGON
        self.browser_wallet=Web3.to_checksum_address(browser_address)

        # 初始化Polymarket API客户端
        self.client = ClobClient(
            host=host,
            key=key,
            chain_id=chain_id,
            funder=self.browser_wallet,
            signature_type=2
        )

        # 设置API凭证
        self.creds = self.client.create_or_derive_api_creds()
        self.client.set_api_creds(creds=self.creds)

        # 初始化到Polygon的Web3连接
        web3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
        web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # 设置USDC合约用于余额检查
        self.usdc_contract = web3.eth.contract(
            address="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            abi=erc20_abi
        )

        # 存储关键合约地址
        self.addresses = {
            'neg_risk_adapter': '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296',
            'collateral': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
            'conditional_tokens': '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045'
        }

        # 初始化合约接口
        self.neg_risk_adapter = web3.eth.contract(
            address=self.addresses['neg_risk_adapter'],
            abi=NegRiskAdapterABI
        )

        self.conditional_tokens = web3.eth.contract(
            address=self.addresses['conditional_tokens'],
            abi=ConditionalTokenABI
        )

        self.web3 = web3


    def create_order(self, marketId, action, price, size, neg_risk=False):
        """
        创建并提交新订单到Polymarket订单簿。

        参数：
            marketId (str): 要交易的市场token ID
            action (str): "BUY" 或 "SELL"
            price (float): 订单价格（预测市场的0-1范围）
            size (float): 订单规模（USDC）
            neg_risk (bool, optional): 是否为负风险市场。默认为False。

        返回：
            dict: 包含订单详情的API响应，或错误时返回空字典
        """
        # 创建订单参数
        order_args = OrderArgs(
            token_id=str(marketId),
            price=price,
            size=size,
            side=action
        )

        signed_order = None

        # 对常规市场和负风险市场进行不同处理
        if neg_risk == False:
            signed_order = self.client.create_order(order_args)
        else:
            signed_order = self.client.create_order(order_args, options=PartialCreateOrderOptions(neg_risk=True))

        try:
            # 将签名订单提交到API
            resp = self.client.post_order(signed_order)
            return resp
        except Exception as ex:
            client_logger.error(f"创建订单失败: {ex}")
            return {}

    def get_order_book(self, market):
        """
        获取特定市场的当前订单簿。

        参数：
            market (str): 要查询的市场ID

        返回：
            tuple: (bids_df, asks_df) - 包含买单和卖单的DataFrames
        """
        orderBook = self.client.get_order_book(market)
        return pd.DataFrame(orderBook.bids).astype(float), pd.DataFrame(orderBook.asks).astype(float)


    def get_usdc_balance(self):
        """
        获取连接钱包的USDC余额。

        返回：
            float: 十进制格式的USDC余额
        """
        return self.usdc_contract.functions.balanceOf(self.browser_wallet).call() / 10**6

    @retry_on_network_error(max_retries=3, delay=2)
    def get_pos_balance(self):
        """
        获取连接钱包所有持仓的总价值。

        返回：
            float: USDC计价的总持仓价值
        """
        res = requests.get(f'https://data-api.polymarket.com/value?user={self.browser_wallet}', timeout=10)
        data = res.json()
        # API 返回的是列表，取第一个元素的 value 字段
        if isinstance(data, list) and len(data) > 0:
            return float(data[0]['value'])
        return 0.0

    def get_total_balance(self):
        """
        获取USDC余额和所有持仓的总价值。

        返回：
            float: USDC计价的总账户价值
        """
        return self.get_usdc_balance() + self.get_pos_balance()

    def get_all_positions(self):
        """
        获取连接钱包在所有市场的所有持仓。

        返回：
            DataFrame: 包含市场、规模、平均价格等详情的所有持仓
        """
        res = requests.get(f'https://data-api.polymarket.com/positions?user={self.browser_wallet}')
        return pd.DataFrame(res.json())

    def get_raw_position(self, tokenId):
        """
        获取特定市场结果token的原始token余额。

        参数：
            tokenId (int): 要查询的token ID

        返回：
            int: 原始token数量（小数转换前）
        """
        return int(self.conditional_tokens.functions.balanceOf(self.browser_wallet, int(tokenId)).call())

    def get_position(self, tokenId):
        """
        获取token的原始和格式化持仓规模。

        参数：
            tokenId (int): 要查询的token ID

        返回：
            tuple: (raw_position, shares) - 原始token数量和十进制份额
                   小于1的份额被视为0以避免灰尘数量
        """
        raw_position = self.get_raw_position(tokenId)
        shares = float(raw_position / 1e6)

        # 忽略非常小的持仓（灰尘）
        if shares < 1:
            shares = 0

        return raw_position, shares

    @retry_on_network_error(max_retries=3, delay=2)
    def get_all_orders(self):
        """
        获取连接钱包的所有未成交订单。

        返回：
            DataFrame: 包含详情的所有未成交订单
        """
        orders_df = pd.DataFrame(self.client.get_orders())

        # 将数值列转换为float
        for col in ['original_size', 'size_matched', 'price']:
            if col in orders_df.columns:
                orders_df[col] = orders_df[col].astype(float)

        return orders_df

    def get_market_orders(self, market):
        """
        获取特定市场的所有未成交订单。

        参数：
            market (str): 要查询的市场ID

        返回：
            DataFrame: 指定市场的未成交订单
        """
        orders_df = pd.DataFrame(self.client.get_orders(OpenOrderParams(
            market=market,
        )))

        # 将数值列转换为float
        for col in ['original_size', 'size_matched', 'price']:
            if col in orders_df.columns:
                orders_df[col] = orders_df[col].astype(float)

        return orders_df


    def cancel_all_asset(self, asset_id):
        """
        取消特定资产token的所有订单。

        参数：
            asset_id (str): 资产token ID
        """
        self.client.cancel_market_orders(asset_id=str(asset_id))



    def cancel_all_market(self, marketId):
        """
        取消特定市场的所有订单。

        参数：
            marketId (str): 市场ID
        """
        self.client.cancel_market_orders(market=marketId)


    def merge_positions(self, amount_to_merge, condition_id, is_neg_risk_market):
        """
        合并市场中的持仓以回收抵押品。

        此函数调用外部poly_merger Node.js脚本在链上执行合并操作。
        当您在同一市场持有YES和NO持仓时，合并它们可以回收您的USDC。

        参数：
            amount_to_merge (int): 要合并的原始token数量（小数转换前）
            condition_id (str): 市场条件ID
            is_neg_risk_market (bool): 是否为负风险市场

        返回：
            str: 交易哈希或合并脚本的输出

        异常：
            Exception: 如果合并操作失败
        """
        amount_to_merge_str = str(amount_to_merge)

        # 准备运行JavaScript脚本的命令
        node_command = f'node poly_merger/merge.js {amount_to_merge_str} {condition_id} {"true" if is_neg_risk_market else "false"}'
        client_logger.info(f"执行合并命令: {node_command}")

        # 运行命令并捕获输出
        result = subprocess.run(node_command, shell=True, capture_output=True, text=True)

        # 检查是否有错误
        if result.returncode != 0:
            client_logger.error(f"合并持仓错误: {result.stderr}")
            raise Exception(f"合并持仓时出错: {result.stderr}")

        client_logger.info("合并完成")

        # 返回交易哈希或输出
        return result.stdout