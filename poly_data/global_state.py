import threading
import pandas as pd

# ============ 市场数据 ============

# 正在跟踪的所有token列表
all_tokens = []

# 同一市场中token之间的映射（YES->NO, NO->YES）
REVERSE_TOKENS = {}

# 所有市场的订单簿数据
all_data = {}

# 来自Google Sheets的市场配置数据
df = None

# ============ 客户端和参数 ============

# Polymarket客户端实例
client = None

# 来自Google Sheets的交易参数
params = {}

# 用于线程安全交易操作的锁
lock = threading.Lock()

# ============ 交易状态 ============

# 跟踪已匹配但尚未上链的交易
# 格式: {"token_side": {trade_id1, trade_id2, ...}}
performing = {}

# 交易添加到performing时的时间戳
# 用于清除陈旧交易
performing_timestamps = {}

# 持仓最后更新的时间戳
last_trade_update = {}

# 每个token的当前未成交订单
# 格式: {token_id: {'buy': {price, size}, 'sell': {price, size}}}
orders = {}

# 每个token的当前持仓
# 格式: {token_id: {'size': float, 'avgPrice': float}}
positions = {}

