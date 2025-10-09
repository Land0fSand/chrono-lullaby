# -*- coding: utf-8 -*-
"""
ChronoLullaby 统一日志配置模块
支持 JSONL 格式、日志轮转、多组件日志
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """
    JSON 格式化器，输出 JSONL 格式的日志
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON 字符串"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外的上下文信息
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加进程和线程信息（可选）
        log_data["process"] = record.process
        log_data["thread"] = record.thread
        
        # 添加文件和行号信息（用于调试）
        if record.levelno >= logging.WARNING:
            log_data["file"] = record.filename
            log_data["line"] = record.lineno
            log_data["function"] = record.funcName
        
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """
    控制台格式化器，输出人类可读的彩色日志
    """
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为彩色文本"""
        # 在 Windows 上可能需要启用 ANSI 支持
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 时间戳
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # 组件名（缩短）
        component = record.name.split('.')[-1]
        
        # 级别（固定宽度）
        level = f"{record.levelname:8}"
        
        # 消息
        message = record.getMessage()
        
        # 组合格式
        log_line = f"{timestamp} | {color}{level}{reset} | {component:12} | {message}"
        
        # 如果有异常信息，添加到下一行
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        
        return log_line


class LoggerManager:
    """
    日志管理器，负责创建和配置各个组件的 logger
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.log_dir = Path(__file__).parent.parent / "logs"
            self.log_dir.mkdir(exist_ok=True)
            LoggerManager._initialized = True
    
    def get_logger(
        self,
        component: str,
        level: int = logging.INFO,
        console: bool = True,
        file: bool = True,
        separate_error_file: bool = False
    ) -> logging.Logger:
        """
        获取指定组件的 logger
        
        Args:
            component: 组件名称（如 'bot', 'downloader', 'launcher'）
            level: 日志级别
            console: 是否输出到控制台
            file: 是否输出到文件
            separate_error_file: 是否单独记录错误日志
        
        Returns:
            配置好的 logger 对象
        """
        logger = logging.getLogger(f"chronolullaby.{component}")
        
        # 避免重复添加 handler
        if logger.handlers:
            return logger
        
        logger.setLevel(level)
        logger.propagate = False
        
        # 控制台 Handler（人类可读格式）
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(ConsoleFormatter())
            logger.addHandler(console_handler)
        
        # 文件 Handler（JSONL 格式）
        if file:
            # 主日志文件（所有级别）
            log_file = self.log_dir / f"{component}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
            
            # 错误日志文件（仅 ERROR 及以上）
            if separate_error_file:
                error_file = self.log_dir / f"{component}_error.log"
                error_handler = logging.handlers.RotatingFileHandler(
                    error_file,
                    maxBytes=10 * 1024 * 1024,  # 10 MB
                    backupCount=5,
                    encoding='utf-8'
                )
                error_handler.setLevel(logging.ERROR)
                error_handler.setFormatter(JSONFormatter())
                logger.addHandler(error_handler)
        
        return logger


def get_logger(component: str, **kwargs) -> logging.Logger:
    """
    便捷函数：获取指定组件的 logger
    
    Args:
        component: 组件名称
        **kwargs: 传递给 LoggerManager.get_logger 的其他参数
    
    Returns:
        配置好的 logger 对象
    
    Examples:
        >>> logger = get_logger('bot')
        >>> logger.info('Bot started')
        >>> logger.error('Connection failed', extra={'extra_data': {'retry_count': 3}})
    """
    manager = LoggerManager()
    return manager.get_logger(component, **kwargs)


def log_with_context(logger: logging.Logger, level: int, message: str, **context):
    """
    带上下文信息的日志记录
    
    Args:
        logger: logger 对象
        level: 日志级别
        message: 日志消息
        **context: 额外的上下文信息
    
    Examples:
        >>> logger = get_logger('bot')
        >>> log_with_context(logger, logging.INFO, 'File sent', file_name='audio.mp3', size_mb=5.2)
    """
    extra = {'extra_data': context} if context else {}
    logger.log(level, message, extra=extra)


# 便捷函数别名
def setup_logger(component: str, **kwargs) -> logging.Logger:
    """setup_logger 的别名"""
    return get_logger(component, **kwargs)


if __name__ == "__main__":
    # 测试代码
    print("=== 测试日志系统 ===\n")
    
    # 创建测试 logger
    test_logger = get_logger("test", level=logging.DEBUG)
    
    # 测试各个级别
    test_logger.debug("这是 DEBUG 消息")
    test_logger.info("这是 INFO 消息")
    test_logger.warning("这是 WARNING 消息")
    test_logger.error("这是 ERROR 消息")
    test_logger.critical("这是 CRITICAL 消息")
    
    # 测试带上下文的日志
    log_with_context(
        test_logger,
        logging.INFO,
        "下载完成",
        channel="@example",
        file_name="video.mp4",
        size_mb=15.5
    )
    
    # 测试异常日志
    try:
        1 / 0
    except Exception as e:
        test_logger.exception("发生了异常")
    
    print(f"\n日志文件已写入: {Path(__file__).parent.parent / 'logs' / 'test.log'}")
    print("可以使用 jq 工具查看: jq . logs/test.log")

