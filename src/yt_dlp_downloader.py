# -*- coding: utf-8 -*-
import os
import sys
import random
import time

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from task.dl_audio import dl_audio_latest
from util import refresh_channels_from_file
from config import ENV_FILE
from logger import get_logger, log_with_context
import logging

# 使用统一的日志系统
logger = get_logger('downloader', separate_error_file=True)

load_dotenv(ENV_FILE)

SPEEDRUN = 1 * 60 * 60 + 22 * 60

def dl_youtube(channels) -> None:
    """下载 YouTube 频道的音频"""
    logger.info(f"开始批量下载，共 {len(channels)} 个频道")
    
    for idx, channel in enumerate(channels, 1):
        try:
            delay = random.uniform(30, 60)
            log_with_context(
                logger,
                logging.INFO,
                f"处理频道 [{idx}/{len(channels)}]",
                channel=channel,
                delay_seconds=round(delay, 2)
            )
            time.sleep(delay)
            
            dl_audio_latest(channel_name=channel)
            
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                f"下载频道失败",
                channel=channel,
                error=str(e),
                error_type=type(e).__name__
            )
            continue
    
    logger.info("本轮下载任务完成")

def main():
    logger.info("YouTube 下载器启动")
    
    while True:
        try:
            channels = refresh_channels_from_file()
            log_with_context(
                logger,
                logging.INFO,
                "刷新频道列表",
                channel_count=len(channels)
            )
            
            dl_youtube(channels)
            
            wait_time = SPEEDRUN * 6
            log_with_context(
                logger,
                logging.INFO,
                "等待下一轮下载",
                wait_hours=round(wait_time / 3600, 2)
            )
            time.sleep(wait_time)
            
        except KeyboardInterrupt:
            logger.info("接收到停止信号，正在退出...")
            break
        except Exception as e:
            logger.exception("下载器主循环发生未预期的错误")
            time.sleep(60)  # 出错后等待1分钟再重试

if __name__ == "__main__":
    main() 