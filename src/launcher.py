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
import json
from pathlib import Path
from logger import get_logger, log_with_context, get_system_logger
import config
from runtime_guard import install_runtime_diagnostics
from runtime_state import ProcessHeartbeat

# 使用统一的日志系统
logger = get_logger('launcher', level=logging.INFO)
# 系统级日志（用于记录进程管理和系统事件）
sys_logger = get_system_logger()
PROJECT_ROOT = Path(__file__).parent.parent
PROCESS_INFO_PATH = PROJECT_ROOT / 'data' / 'process_info.json'
RESTART_BACKOFFS = [5, 15, 60, 300]
RESTART_RESET_WINDOW = 300
mark_runtime_shutdown = install_runtime_diagnostics(logger, "launcher")
heartbeat = ProcessHeartbeat("launcher")


def _write_process_info(downloader_pid=None, bot_pid=None):
    """写入统一的进程信息文件，供 ch.ps1 status/stop 使用。"""
    PROCESS_INFO_PATH.parent.mkdir(exist_ok=True)
    process_info = {
        'launcher_pid': os.getpid(),
        'downloader_pid': downloader_pid,
        'bot_pid': bot_pid,
        'start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'project_root': str(PROJECT_ROOT),
        'log_dir': str(PROJECT_ROOT / 'logs'),
        'launch_mode': 'python-launcher',
    }
    with open(PROCESS_INFO_PATH, 'w', encoding='utf-8') as f:
        json.dump(process_info, f, indent=2, ensure_ascii=False)

def _run_downloader():
    """子进程运行：YouTube 下载器"""
    try:
        subprocess.run([
            sys.executable, "src/yt_dlp_downloader.py"
        ], cwd=PROJECT_ROOT)
    except Exception as e:
        print(f"YouTube 下载器进程错误: {e}")

def _run_bot():
    """子进程运行：Telegram 机器人"""
    try:
        subprocess.run([
            sys.executable, "src/telegram_bot.py"
        ], cwd=PROJECT_ROOT)
    except Exception as e:
        print(f"Telegram 机器人进程错误: {e}")

class ProcessManager:
    def __init__(self):
        self.downloader_process = None
        self.bot_process = None
        self.running = False
        self.restart_counts = {
            "downloader": 0,
            "bot": 0,
        }
        self.start_times = {
            "downloader": None,
            "bot": None,
        }
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("接收到停止信号，正在关闭所有进程...")
        heartbeat.update("signal_stop", signal=signum)
        mark_runtime_shutdown(f"signal_{signum}", expected=True)
        self.stop_all()
        sys.exit(0)
    
    def stop_all(self):
        """停止所有进程"""
        self.running = False
        heartbeat.update("stopping_children")
        sys_logger.info("开始停止所有子进程")
        
        if self.downloader_process and self.downloader_process.is_alive():
            logger.info("停止 YouTube 下载器...")
            self.downloader_process.terminate()
            self.downloader_process.join(timeout=5)
            if self.downloader_process.is_alive():
                self.downloader_process.kill()
        
        if self.bot_process and self.bot_process.is_alive():
            logger.info("停止 Telegram 机器人...")
            self.bot_process.terminate()
            self.bot_process.join(timeout=5)
            if self.bot_process.is_alive():
                self.bot_process.kill()

        _write_process_info(downloader_pid=None, bot_pid=None)
        heartbeat.stop("children_stopped")

        logger.info("所有进程已停止")
        sys_logger.info("所有子进程已停止")

    def _start_downloader(self):
        self.downloader_process = multiprocessing.Process(
            target=_run_downloader,
            name="YouTubeDownloader"
        )
        self.downloader_process.start()
        logger.info(f"YouTube 下载器已启动 (PID: {self.downloader_process.pid})")
        self.start_times["downloader"] = time.time()
        heartbeat.update("downloader_started", pid=self.downloader_process.pid)
        _write_process_info(
            downloader_pid=self.downloader_process.pid,
            bot_pid=self.bot_process.pid if self.bot_process else None,
        )

    def _start_bot(self):
        self.bot_process = multiprocessing.Process(
            target=_run_bot,
            name="TelegramBot"
        )
        self.bot_process.start()
        logger.info(f"Telegram 机器人已启动 (PID: {self.bot_process.pid})")
        self.start_times["bot"] = time.time()
        heartbeat.update("bot_started", pid=self.bot_process.pid)
        _write_process_info(
            downloader_pid=self.downloader_process.pid if self.downloader_process else None,
            bot_pid=self.bot_process.pid,
        )
        log_with_context(
            sys_logger, logging.INFO,
            "机器人进程已启动",
            process_name="TelegramBot",
            pid=self.bot_process.pid
        )

    def _restart_process(self, process_name):
        retry_index = min(self.restart_counts[process_name], len(RESTART_BACKOFFS) - 1)
        delay = RESTART_BACKOFFS[retry_index]
        self.restart_counts[process_name] += 1

        log_with_context(
            sys_logger, logging.WARNING,
            "子进程退出，准备自动重启",
            process_name=process_name,
            restart_attempt=self.restart_counts[process_name],
            delay_seconds=delay,
        )
        heartbeat.update(
            "restarting_child",
            process_name=process_name,
            restart_attempt=self.restart_counts[process_name],
            delay_seconds=delay,
        )
        time.sleep(delay)

        if process_name == "downloader":
            self._start_downloader()
        else:
            self._start_bot()

    def _maybe_reset_restart_count(self, process_name):
        started_at = self.start_times.get(process_name)
        if started_at and (time.time() - started_at) >= RESTART_RESET_WINDOW:
            if self.restart_counts[process_name] != 0:
                logger.info(f"{process_name} 已稳定运行，重置重启计数")
            self.restart_counts[process_name] = 0
    
    def start(self):
        """启动所有服务"""
        logger.info("=== ChronoLullaby 启动器 ===")
        logger.info("按 Ctrl+C 停止所有服务")
        sys_logger.info("启动器初始化")
        heartbeat.start()
        heartbeat.update("launcher_starting")
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            self._start_downloader()
            
            # 等待2秒再启动机器人
            time.sleep(2)
            
            self._start_bot()
            
            self.running = True
            
            logger.info(f"进程信息已保存到 {PROCESS_INFO_PATH}")
            logger.info("服务正在运行...")
            sys_logger.info("所有服务已启动，进入监控循环")
            heartbeat.update(
                "monitoring",
                downloader_pid=self.downloader_process.pid if self.downloader_process else None,
                bot_pid=self.bot_process.pid if self.bot_process else None,
            )
            
            # 监控进程状态
            while self.running:
                time.sleep(10)  # 每10秒检查一次
                self._maybe_reset_restart_count("downloader")
                self._maybe_reset_restart_count("bot")
                heartbeat.update(
                    "monitoring",
                    downloader_pid=self.downloader_process.pid if self.downloader_process else None,
                    downloader_alive=self.downloader_process.is_alive() if self.downloader_process else False,
                    bot_pid=self.bot_process.pid if self.bot_process else None,
                    bot_alive=self.bot_process.is_alive() if self.bot_process else False,
                )
                
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
                    self._restart_process("downloader")
                    continue
                
                if not self.bot_process.is_alive():
                    logger.warning("Telegram 机器人进程意外退出")
                    log_with_context(
                        sys_logger, logging.WARNING,
                        "机器人进程意外退出",
                        process_name="TelegramBot",
                        pid=self.bot_process.pid,
                        exitcode=self.bot_process.exitcode
                    )
                    self._restart_process("bot")
                    continue
        
        except KeyboardInterrupt:
            logger.info("接收到中断信号...")
            sys_logger.info("接收到 KeyboardInterrupt")
            heartbeat.update("keyboard_interrupt")
            mark_runtime_shutdown("keyboard_interrupt", expected=True)
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
            heartbeat.update("launcher_exception", error=str(e), error_type=type(e).__name__)
            mark_runtime_shutdown("unhandled_exception", error=str(e))
        finally:
            self.stop_all()
            mark_runtime_shutdown("main_return", expected=True)

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
