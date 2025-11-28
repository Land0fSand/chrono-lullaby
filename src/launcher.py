# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
ChronoLullaby 启动器
同时启动 YouTube 下载器和 Telegram 机器人
"""

import os
import sys

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import time
import signal
import subprocess
import multiprocessing
import logging
from pathlib import Path
from logger import get_logger, log_with_context, get_system_logger
import config

# 使用统一的日志系统
logger = get_logger('launcher', level=logging.INFO)
# 系统级日志（用于记录进程管理和系统事件）
sys_logger = get_system_logger()

class ProcessManager:
    def __init__(self):
        self.downloader_process = None
        self.bot_process = None
        self.running = False
    
    def start_downloader(self):
        """启动 YouTube 下载器"""
        try:
            logger.info("启动 YouTube 下载器...")
            
            # 使用subprocess启动，确保使用poetry环境
            result = subprocess.run([
                "poetry", "run", "python", "yt_dlp_downloader.py"
            ], cwd=Path(__file__).parent)
            
        except Exception as e:
            log_with_context(
                logger, logging.ERROR,
                "YouTube 下载器错误",
                error=str(e)
            )
    
    def start_bot(self):
        """启动 Telegram 机器人"""
        try:
            logger.info("启动 Telegram 机器人...")
            
            # 使用subprocess启动，确保使用poetry环境
            result = subprocess.run([
                "poetry", "run", "python", "telegram_bot.py"
            ], cwd=Path(__file__).parent)
            
        except Exception as e:
            log_with_context(
                logger, logging.ERROR,
                "Telegram 机器人错误",
                error=str(e)
            )
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("接收到停止信号，正在关闭所有进程...")
        log_with_context(
            sys_logger, logging.INFO,
            "接收到系统信号",
            signal=signum,
            downloader_alive=self.downloader_process.is_alive() if self.downloader_process else False,
            bot_alive=self.bot_process.is_alive() if self.bot_process else False
        )
        self.stop_all()
        sys.exit(0)
    
    def stop_all(self):
        """停止所有进程"""
        self.running = False
        sys_logger.info("开始停止所有子进程")
        
        if self.downloader_process and self.downloader_process.is_alive():
            logger.info("停止 YouTube 下载器...")
            log_with_context(
                sys_logger, logging.INFO,
                "终止下载器进程",
                pid=self.downloader_process.pid
            )
            self.downloader_process.terminate()
            self.downloader_process.join(timeout=5)
            if self.downloader_process.is_alive():
                sys_logger.warning("下载器进程未响应 terminate，使用 kill")
                self.downloader_process.kill()
        
        if self.bot_process and self.bot_process.is_alive():
            logger.info("停止 Telegram 机器人...")
            log_with_context(
                sys_logger, logging.INFO,
                "终止机器人进程",
                pid=self.bot_process.pid
            )
            self.bot_process.terminate()
            self.bot_process.join(timeout=5)
            if self.bot_process.is_alive():
                sys_logger.warning("机器人进程未响应 terminate，使用 kill")
                self.bot_process.kill()
        
        logger.info("所有进程已停止")
        sys_logger.info("所有子进程已停止")
    
    def start(self):
        """启动所有服务"""
        logger.info("=== ChronoLullaby 启动器 ===")
        logger.info("按 Ctrl+C 停止所有服务")
        sys_logger.info("启动器初始化")
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # 启动下载器进程
            self.downloader_process = multiprocessing.Process(
                target=self.start_downloader,
                name="YouTubeDownloader"
            )
            self.downloader_process.start()
            log_with_context(
                logger, logging.INFO,
                "YouTube 下载器已启动",
                pid=self.downloader_process.pid
            )
            log_with_context(
                sys_logger, logging.INFO,
                "下载器进程已启动",
                process_name="YouTubeDownloader",
                pid=self.downloader_process.pid
            )
            
            # 等待2秒再启动机器人
            time.sleep(2)
            
            # 启动机器人进程
            self.bot_process = multiprocessing.Process(
                target=self.start_bot,
                name="TelegramBot"
            )
            self.bot_process.start()
            log_with_context(
                logger, logging.INFO,
                "Telegram 机器人已启动",
                pid=self.bot_process.pid
            )
            log_with_context(
                sys_logger, logging.INFO,
                "机器人进程已启动",
                process_name="TelegramBot",
                pid=self.bot_process.pid
            )
            
            self.running = True
            
            # 保存进程信息
            process_info = {
                'downloader_pid': self.downloader_process.pid,
                'bot_pid': self.bot_process.pid,
                'start_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            # 确保 data 目录存在
            data_dir = Path(__file__).parent / 'data'
            data_dir.mkdir(exist_ok=True)

            import json
            with open(data_dir / 'process_info.json', 'w', encoding='utf-8') as f:
                json.dump(process_info, f, indent=2, ensure_ascii=False)
            
            logger.info("进程信息已保存到 data/process_info.json")
            logger.info("服务正在运行...")
            sys_logger.info("所有服务已启动，进入监控循环")
            
            # 监控进程状态
            while self.running:
                time.sleep(10)  # 每10秒检查一次
                
                # 检查进程是否还在运行
                if not self.downloader_process.is_alive():
                    logger.warning("YouTube 下载器进程意外退出")
                    log_with_context(
                        sys_logger, logging.WARNING,
                        "下载器进程意外退出",
                        process_name="YouTubeDownloader",
                        pid=self.downloader_process.pid,
                        exitcode=self.downloader_process.exitcode
                    )
                    break
                
                if not self.bot_process.is_alive():
                    logger.warning("Telegram 机器人进程意外退出")
                    log_with_context(
                        sys_logger, logging.WARNING,
                        "机器人进程意外退出",
                        process_name="TelegramBot",
                        pid=self.bot_process.pid,
                        exitcode=self.bot_process.exitcode
                    )
                    break
        
        except KeyboardInterrupt:
            logger.info("接收到中断信号...")
            sys_logger.info("接收到 KeyboardInterrupt")
        except Exception as e:
            log_with_context(
                logger, logging.ERROR,
                "启动过程中发生错误",
                error=str(e)
            )
            log_with_context(
                sys_logger, logging.ERROR,
                "启动器异常",
                error=str(e),
                error_type=type(e).__name__
            )
        finally:
            self.stop_all()

def main():
    # 确保在正确的目录中
    os.chdir(Path(__file__).parent)
    
    sys_logger.info("ChronoLullaby 启动器开始初始化")
    
    # 初始化配置提供者（检查环境变量中的模式覆盖）
    mode_override = os.environ.get('CONFIG_MODE')
    if mode_override:
        logger.info(f"使用命令行指定的配置模式: {mode_override}")
        log_with_context(
            sys_logger, logging.INFO,
            "配置模式被环境变量覆盖",
            mode=mode_override,
            source="CONFIG_MODE env var"
        )
    
    try:
        config.init_config_provider(mode_override=mode_override)
        sys_logger.info("配置提供者初始化成功")
    except Exception as e:
        logger.error(f"初始化配置提供者失败: {e}")
        logger.warning("将使用默认本地配置模式")
        log_with_context(
            sys_logger, logging.ERROR,
            "配置提供者初始化失败",
            error=str(e),
            fallback="local"
        )
    
    # 如果是 Notion 模式，启动同步服务
    provider = config.get_config_provider()
    provider_name = provider.__class__.__name__
    log_with_context(
        sys_logger, logging.INFO,
        "当前配置提供者",
        provider=provider_name
    )
    
    if provider_name == 'NotionConfigProvider':
        try:
            from notion_sync import init_sync_service
            yaml_config = config.load_yaml_config()
            sync_config = {}
            if yaml_config:
                notion_block = yaml_config.get('notion') or yaml_config.get('config_source', {}).get('notion', {})
                if isinstance(notion_block, dict):
                    sync_config = notion_block.get('sync', {})
            if sync_config:
                init_sync_service(provider, sync_config)
                logger.info("Notion 同步服务已启动")
                sys_logger.info("Notion 同步服务启动成功")
        except Exception as e:
            logger.warning(f"启动 Notion 同步服务失败: {e}")
            log_with_context(
                sys_logger, logging.WARNING,
                "Notion 同步服务启动失败",
                error=str(e)
            )
    
    # 创建并启动进程管理器
    manager = ProcessManager()
    manager.start()

if __name__ == "__main__":
    main() 
