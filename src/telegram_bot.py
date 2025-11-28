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

from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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
from util import get_channel_groups_with_details, show_chat_id
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

logger.info(f"🛠️ 配置加载成功：发送任务轮询间隔 = {SEND_INTERVAL} 秒 ({SEND_INTERVAL/3600:.2f} 小时)")

def create_send_file_task(chat_id: str, audio_folder: str, group_name: str):
    """
    创建发送文件任务的闭包函数
    
    Args:
        chat_id: Telegram 频道 ID
        audio_folder: 音频文件夹路径
        group_name: 频道组名称（用于日志）
    
    Returns:
        发送文件的异步任务函数
    """
    async def send_file_task(context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await send_file(
                context=context,
                chat_id=chat_id,
                audio_folder=audio_folder,
                group_name=group_name,
            )
        except Exception as e:
            logger.error(f"发送文件任务错误 (频道组: {group_name}): {e}")
    
    return send_file_task

async def send_file_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    """默认发送文件任务（向后兼容）"""
    try:
        await send_file(context=context, chat_id=CHAT_ID, audio_folder=AUDIO_FOLDER)
    except Exception as e:
        logger.error(f"发送文件任务错误: {e}")

async def test_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """测试命令 - 用于验证 Bot 是否能在频道中接收消息"""
    try:
        chat = update.effective_chat
        chat_id = chat.id
        chat_type = chat.type
        chat_title = chat.title if chat.title else "未命名"
        
        message = f"✅ Bot 正常工作！\n\n"
        message += f"收到来自 {chat_type} 的消息\n"
        message += f"Chat ID: {chat_id}\n"
        message += f"标题: {chat_title}"
        
        # 支持频道消息和普通消息
        if update.channel_post:
            await update.channel_post.reply_text(message)
        else:
            await update.message.reply_text(message)
        
        logger.info(f"🧪 /test 命令 - Chat ID: {chat_id}, 类型: {chat_type}, 标题: {chat_title}")
    except Exception as e:
        logger.error(f"❌ /test 命令执行失败: {e}")

async def echo_handler(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """消息回显处理器 - 用于测试 Bot 是否能接收普通消息"""
    try:
        chat = update.effective_chat
        
        # 支持频道消息和普通消息
        if update.channel_post:
            message_obj = update.channel_post
            message_text = message_obj.text if message_obj.text else "[非文本消息]"
        else:
            message_obj = update.message
            message_text = message_obj.text if message_obj else "[无消息内容]"
        
        logger.info(f"📨 收到消息: '{message_text}' 来自 {chat.type} (ID: {chat.id})")
        
        # 只在包含"测试"时回复，避免干扰正常使用
        if message_text and "测试" in message_text.lower():
            await message_obj.reply_text(f"✅ 收到你的消息: {message_text}")
    except Exception as e:
        logger.error(f"❌ 消息处理失败: {e}")

async def error_callback(update, context):
    """全局错误处理器"""
    logger.error(f'Update "{update}" caused error "{context.error}"')
    
    # 如果是Bot冲突错误，尝试优雅处理
    if "Conflict: terminated by other getUpdates request" in str(context.error):
        logger.warning("检测到Bot实例冲突，可能有多个Bot在运行")
        logger.info("建议使用 'ch-stop' 停止所有实例后重新启动")
        try:
            from notion_sync import stop_sync_service
            stop_sync_service()
        except Exception:
            pass
        logger.info("检测到冲突，当前进程将退出以避免重复运行")
        os._exit(1)

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
    
    # 获取频道组配置
    channel_groups = get_channel_groups_with_details()
    
    if not channel_groups:
        logger.error("❌ 未找到任何频道组配置！")
        logger.error("请在 config.yaml 中配置 channel_groups")
        sys.exit(1)
    
    logger.info(f"✅ 找到 {len(channel_groups)} 个频道组配置")
    
    # 为每个频道组创建独立的发送任务
    task_interval = SEND_INTERVAL // 32
    for idx, group in enumerate(channel_groups):
        group_name = group['name']
        chat_id = group['telegram_chat_id']
        audio_folder = group['audio_folder']
        
        if not chat_id:
            logger.warning(f"⚠️  频道组 '{group_name}' 未配置 telegram_chat_id，跳过")
            continue
        
        # 为每个组错开启动时间，避免同时发送
        first_delay = (SEND_INTERVAL // 256) + (idx * 10)
        
        # 创建该组的发送任务
        task_func = create_send_file_task(chat_id, audio_folder, group_name)
        application.job_queue.run_repeating(
            task_func,
            interval=task_interval,
            first=first_delay,
            name=f"send_task_{group_name}"
        )
        
        logger.info(
            f"📤 已配置发送任务: {group_name} -> {chat_id}\n"
            f"   音频目录: {audio_folder}\n"
            f"   检查间隔: {task_interval}秒 ({task_interval/60:.1f}分钟)\n"
            f"   首次延迟: {first_delay}秒"
        )
    
    logger.info(f"✅ 所有发送任务已配置完成")
    
    # 注册命令处理器（私聊/群组）
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("chatid", show_chat_id))
    application.add_handler(CommandHandler("test", test_command))
    
    # 注册频道命令处理器（频道消息需要单独处理）
    application.add_handler(MessageHandler(
        filters.UpdateType.CHANNEL_POST & filters.Regex(r'^/addchannel'), 
        add_channel
    ))
    application.add_handler(MessageHandler(
        filters.UpdateType.CHANNEL_POST & filters.Regex(r'^/chatid'), 
        show_chat_id
    ))
    application.add_handler(MessageHandler(
        filters.UpdateType.CHANNEL_POST & filters.Regex(r'^/test'), 
        test_command
    ))
    
    # 注册消息处理器（用于调试，记录所有收到的文本消息，但排除命令）
    # 注意：这个要放在最后，优先级最低
    application.add_handler(MessageHandler(
        (filters.TEXT & ~filters.COMMAND) | 
        (filters.UpdateType.CHANNEL_POST & filters.TEXT & ~filters.Regex(r'^/')),
        echo_handler
    ))
    
    logger.info("✅ 已注册命令: /addchannel, /chatid, /test（支持私聊/群组/频道）")
    logger.info("✅ 已注册消息处理器（调试模式）")
    
    # 添加重试机制的轮询
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"🤖 启动 Telegram Bot 轮询 (尝试 {retry_count + 1}/{max_retries})")
            application.run_polling(
                drop_pending_updates=True,  # 忽略待处理的更新
            )
            break  # 成功运行，退出重试循环
        except NetworkError as e:
            retry_count += 1
            logger.error(f"🌐 网络错误 (尝试 {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                wait_time = min(60 * (2 ** retry_count), 600)  # 指数退避，最大10分钟
                logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error("🛑 达到最大重试次数，程序退出")
                raise
        except Exception as e:
            logger.error(f"意外错误: {e}")
            raise

if __name__ == "__main__":
    main()
