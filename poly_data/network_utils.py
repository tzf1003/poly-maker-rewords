"""
网络工具模块 - 提供网络重试机制和日志功能
"""
import time
import functools
import traceback
from typing import Callable, Any
import requests
from py_clob_client.exceptions import PolyApiException
from poly_data.logger import get_logger

# 创建网络工具日志记录器
network_logger = get_logger('network', console_output=True)


def retry_on_network_error(max_retries=3, delay=2, backoff=2, exceptions=(
    requests.exceptions.RequestException,
    requests.exceptions.ConnectionError,
    requests.exceptions.SSLError,
    requests.exceptions.Timeout,
    PolyApiException,
    ConnectionError,
    TimeoutError,
)):
    """
    网络请求重试装饰器
    
    参数:
        max_retries: 最大重试次数
        delay: 初始延迟时间(秒)
        backoff: 延迟时间的倍数增长因子
        exceptions: 需要重试的异常类型元组
    
    使用示例:
        @retry_on_network_error(max_retries=3, delay=2)
        def fetch_data():
            return requests.get('https://api.example.com/data')
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        network_logger.warning(f"{func.__name__} 网络错误 (尝试 {attempt + 1}/{max_retries + 1}): {type(e).__name__}")
                        network_logger.info(f"等待 {current_delay} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        network_logger.error(f"{func.__name__} 失败，已达最大重试次数 ({max_retries + 1})")
                        network_logger.error(f"最后错误: {type(e).__name__}: {str(e)}")
                except Exception as e:
                    # 非网络错误，直接抛出
                    network_logger.error(f"{func.__name__} 发生非网络错误: {type(e).__name__}: {str(e)}")
                    raise
            
            # 如果所有重试都失败，抛出最后一个异常
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def safe_api_call(func: Callable, default_value=None, log_error=True) -> Callable:
    """
    安全的API调用包装器，捕获异常并返回默认值
    
    参数:
        func: 要包装的函数
        default_value: 发生错误时返回的默认值
        log_error: 是否打印错误信息
    
    使用示例:
        result = safe_api_call(lambda: client.get_orders(), default_value=[])
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_error:
                network_logger.warning(f"API调用失败: {func.__name__ if hasattr(func, '__name__') else 'unknown'}")
                network_logger.warning(f"错误: {type(e).__name__}: {str(e)}")
            return default_value
    
    return wrapper()

