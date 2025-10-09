# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import sys
import time

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut
from dotenv import load_dotenv
from task.send_file import send_file
from commands.add_channel import add_channel
from config import (
    AUDIO_FOLDER, 
    ENV_FILE,
    get_telegram_token,
    get_telegram_chat_id,
    get_send_interval,
)
from logger import get_logger

# 使用统一的日志系统
logger = get_logger('bot', separate_error_file=True)

# 加载环境变量（如果使用传统配置）
load_dotenv(ENV_FILE)

# 从配置获取参数（优先 YAML，回退到 .env）
TOKEN = get_telegram_token()
CHAT_ID = get_telegram_chat_id()
SEND_INTERVAL = get_send_interval()

# 验证必需的配置
if not TOKEN:
    logger.error("❌ 未找到 BOT_TOKEN 配置！")
    logger.error("请在 config.yaml 或 .env 文件中配置 BOT_TOKEN")
    sys.exit(1)

if not CHAT_ID:
    logger.error("❌ 未找到 CHAT_ID 配置！")
    logger.error("请在 config.yaml 或 .env 文件中配置 CHAT_ID")
    sys.exit(1)

logger.info(f"配置加载成功：发送间隔 = {SEND_INTERVAL} 秒 ({SEND_INTERVAL/3600:.2f} 小时)")

async def send_file_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await send_file(context=context, chat_id=CHAT_ID, audio_folder=AUDIO_FOLDER)
    except Exception as e:
        logger.error(f"发送文件任务错误: {e}")

async def error_callback(update, context):
    """全局错误处理器"""
    logger.error(f'Update "{update}" caused error "{context.error}"')
    
    # 如果是Bot冲突错误，尝试优雅处理
    if "Conflict: terminated by other getUpdates request" in str(context.error):
        logger.warning("检测到Bot实例冲突，可能有多个Bot在运行")
        logger.info("建议使用 'ch-stop' 停止所有实例后重新启动")

def main():
    # 增加超时设置，添加连接池配置
    request = HTTPXRequest(
        read_timeout=120,  # 增加读取超时
        write_timeout=120,  # 增加写入超时
        connect_timeout=60,  # 连接超时
        pool_timeout=60,  # 连接池超时
        connection_pool_size=8,  # 连接池大小
        # proxy_url 参数在新版本中已移除，如需代理请使用 httpx 的方式配置
    )
    
    application = Application.builder().token(TOKEN).request(request).build()
    
    # 添加错误处理器
    application.add_error_handler(error_callback)
    
    # 使用配置的发送间隔
    # 将间隔除以32作为实际间隔，首次运行延迟为间隔的1/256
    application.job_queue.run_repeating(
        send_file_task,
        interval=SEND_INTERVAL // 32,
        first=SEND_INTERVAL // 256,
    )
    logger.info(f"文件发送任务已配置：每 {SEND_INTERVAL // 32} 秒检查一次")
    application.add_handler(CommandHandler("addchannel", add_channel))
    
    # 添加重试机制的轮询
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"启动Telegram Bot轮询 (尝试 {retry_count + 1}/{max_retries})")
            application.run_polling(
                drop_pending_updates=True,  # 忽略待处理的更新
            )
            break  # 成功运行，退出重试循环
        except NetworkError as e:
            retry_count += 1
            logger.error(f"网络错误 (尝试 {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                wait_time = min(60 * (2 ** retry_count), 600)  # 指数退避，最大10分钟
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error("达到最大重试次数，程序退出")
                raise
        except Exception as e:
            logger.error(f"意外错误: {e}")
            raise

if __name__ == "__main__":
    main() 