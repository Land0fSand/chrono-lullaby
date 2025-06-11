#!/usr/bin/env python
import os
import time
import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut
from dotenv import load_dotenv
from task.send_file import send_file
from commands.add_channel import add_channel
from config import AUDIO_FOLDER, ENV_FILE

# 设置日志记录
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv(ENV_FILE)

SPEEDRUN = 1 * 60 * 60 + 22 * 60
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

async def send_file_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await send_file(context=context, chat_id=CHAT_ID, audio_folder=AUDIO_FOLDER)
    except Exception as e:
        logger.error(f"发送文件任务错误: {e}")

def error_callback(update, context):
    """全局错误处理器"""
    logger.error(f'Update "{update}" caused error "{context.error}"')

def main():
    # 增加超时设置，添加连接池配置
    request = HTTPXRequest(
        read_timeout=120,  # 增加读取超时
        write_timeout=120,  # 增加写入超时
        connect_timeout=60,  # 连接超时
        pool_timeout=60,  # 连接池超时
        connection_pool_size=8,  # 连接池大小
        proxy_url=None,  # 如果需要代理，在这里设置
    )
    
    application = Application.builder().token(TOKEN).request(request).build()
    
    # 添加错误处理器
    application.add_error_handler(error_callback)
    
    application.job_queue.run_repeating(
        send_file_task,
        interval=SPEEDRUN // 32,
        first=SPEEDRUN // 256,
    )
    application.add_handler(CommandHandler("addchannel", add_channel))
    
    # 添加重试机制的轮询
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"启动Telegram Bot轮询 (尝试 {retry_count + 1}/{max_retries})")
            application.run_polling(
                drop_pending_updates=True,  # 忽略待处理的更新
                timeout=60,  # 轮询超时
                read_timeout=120,  # 读取超时
                write_timeout=120,  # 写入超时
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