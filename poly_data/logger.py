"""
日志模块 - 提供统一的日志记录功能
"""
import os
import sys
from datetime import datetime
from pathlib import Path


class Logger:
    """
    简单的日志记录器，支持同时输出到控制台和文件
    """
    
    def __init__(self, name, log_dir='logs', console_output=True):
        """
        初始化日志记录器
        
        参数:
            name: 日志文件名(不含扩展名)
            log_dir: 日志目录
            console_output: 是否同时输出到控制台
        """
        self.name = name
        self.console_output = console_output
        
        # 创建日志目录
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 日志文件路径
        self.log_file = self.log_dir / f"{name}.log"
    
    def _format_message(self, level, message):
        """格式化日志消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return f"[{timestamp}] [{level}] {message}"
    
    def _write(self, level, message):
        """写入日志"""
        formatted_msg = self._format_message(level, message)
        
        # 写入文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_msg + '\n')
        except Exception as e:
            print(f"写入日志文件失败: {e}", file=sys.stderr)
        
        # 输出到控制台
        if self.console_output:
            print(formatted_msg)
    
    def info(self, message):
        """记录信息级别日志"""
        self._write('INFO', message)
    
    def warning(self, message):
        """记录警告级别日志"""
        self._write('WARNING', message)
    
    def error(self, message):
        """记录错误级别日志"""
        self._write('ERROR', message)
    
    def debug(self, message):
        """记录调试级别日志"""
        self._write('DEBUG', message)
    
    def exception(self, message, exc_info=None):
        """记录异常信息"""
        import traceback
        self._write('ERROR', message)
        if exc_info:
            tb = ''.join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))
            self._write('ERROR', f"异常详情:\n{tb}")


# 全局日志实例
_loggers = {}


def get_logger(name, log_dir='logs', console_output=True):
    """
    获取或创建日志记录器
    
    参数:
        name: 日志文件名
        log_dir: 日志目录
        console_output: 是否输出到控制台
    
    返回:
        Logger实例
    """
    if name not in _loggers:
        _loggers[name] = Logger(name, log_dir, console_output)
    return _loggers[name]

