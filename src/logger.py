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


TRACE_LEVEL = 5
TRACE = TRACE_LEVEL
logging.addLevelName(TRACE_LEVEL, "TRACE")
setattr(logging, "TRACE", TRACE_LEVEL)


def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)


logging.Logger.trace = _trace


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


def _get_configured_log_level(default_level: int) -> int:
    """读取配置文件中的 log.level，如果不存在则返回默认级别"""
    try:
        import config as config_module
        yaml_config = config_module.load_yaml_config()
        if not yaml_config:
            return default_level

        log_config = yaml_config.get('log') or yaml_config.get('logging')
        if isinstance(log_config, dict):
            level_value = log_config.get('level')
            if isinstance(level_value, str):
                level_name = level_value.upper()
                if level_name == 'TRACE':
                    return TRACE_LEVEL
                candidate = getattr(logging, level_name, None)
                if isinstance(candidate, int):
                    return candidate
    except Exception:
        pass
    return default_level


class NotionLogHandler(logging.Handler):
    """
    将日志转发到 Notion 同步服务
    """
    
    def __init__(self, log_type: str, component_name: str):
        super().__init__()
        self.log_type = log_type
        self.component_name = component_name
        self._init_attempted = False
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            from notion_sync import get_sync_service  # 延迟导入避免循环依赖
            service = get_sync_service()
            if service is None and not self._init_attempted:
                self._attempt_init_service()
                service = get_sync_service()
        except ImportError:
            return
        
        if service is None:
            return
        
        try:
            message = record.getMessage()
            
            extra_data = getattr(record, 'extra_data', None)
            if extra_data:
                context_str = ", ".join(f"{key}={value}" for key, value in extra_data.items())
                message = f"{message} | {context_str}"
            
            service.queue_log(self.log_type, record.levelname.upper(), message)
        except Exception:
            self.handleError(record)
    
    def _attempt_init_service(self) -> None:
        """在当前进程尝试初始化 Notion 同步服务"""
        self._init_attempted = True
        try:
            import config
            provider = config.get_config_provider()
            if provider.__class__.__name__ != 'NotionConfigProvider':
                return
            
            from notion_sync import init_sync_service
            yaml_config = config.load_yaml_config()
            notion_cfg = {}
            if yaml_config:
                notion_cfg = yaml_config.get('notion', {})
                if not notion_cfg:
                    notion_cfg = yaml_config.get('config_source', {}).get('notion', {})
            sync_cfg = notion_cfg.get('sync', {}) if isinstance(notion_cfg, dict) else {}
            init_sync_service(provider, sync_cfg)
        except Exception:
            # 避免在日志处理过程中抛出异常，静默失败
            return


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
        target_level = _get_configured_log_level(level)
        logger.setLevel(target_level)
        logger.propagate = False

        if logger.handlers:
            for handler in logger.handlers:
                if handler.level not in (logging.ERROR, logging.NOTSET):
                    handler.setLevel(target_level)
            return logger

        # 控制台 Handler（人类可读格式）
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(target_level)
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
            file_handler.setLevel(target_level)
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

        base_component = component.split('.')[0] if component else ''
        notion_log_type = base_component if base_component in ('downloader', 'bot') else 'error'
        notion_handler = NotionLogHandler(notion_log_type, component or base_component or 'unknown')
        notion_handler.setLevel(logging.NOTSET)
        logger.addHandler(notion_handler)

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


def get_system_logger() -> logging.Logger:
    """
    获取系统级logger，用于记录系统事件和调试信息
    
    系统日志特点：
    - 日志文件：logs/system.log
    - 记录内容：启动/停止、配置变更、进程管理等系统级事件
    - 完全本地存储：不同步到Notion，确保即使Notion出现问题也能查看系统状态
    - 支持所有日志级别：DEBUG到CRITICAL
    - 格式：控制台人类可读，文件JSONL格式
    
    典型使用场景：
    - 进程生命周期事件（启动、停止、重启）
    - 配置加载和模式切换
    - 服务启动和关闭
    - 异常的系统状态
    - 手动调试信息
    
    Returns:
        配置好的系统级 logger 对象
    
    Examples:
        >>> sys_logger = get_system_logger()
        >>> sys_logger.info("启动器初始化完成")
        >>> sys_logger.debug("子进程状态检查", extra={'extra_data': {'process': 'downloader', 'pid': 12345}})
        >>> sys_logger.error("配置加载失败", extra={'extra_data': {'config_file': 'config.yaml', 'error': 'not found'}})
    """
    logger = logging.getLogger("chronolullaby.system")
    target_level = _get_configured_log_level(logging.DEBUG)  # 系统日志默认支持 DEBUG
    logger.setLevel(target_level)
    logger.propagate = False

    # 如果已经配置过，直接返回
    if logger.handlers:
        for handler in logger.handlers:
            if handler.level not in (logging.ERROR, logging.NOTSET):
                handler.setLevel(target_level)
        return logger

    manager = LoggerManager()
    
    # 控制台 Handler（人类可读格式）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(target_level)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)

    # 文件 Handler（JSONL 格式）- 系统日志
    log_file = manager.log_dir / "system.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(target_level)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # 系统日志不添加 Notion Handler，确保完全本地化
    # 这样即使 Notion 同步出问题，系统日志也能正常工作

    return logger


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
    test_logger = get_logger("test", level=TRACE_LEVEL)
    
    # 测试各个级别
    test_logger.trace("这是 TRACE 消息")
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

