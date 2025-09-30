# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ContextTypes
import os
import sys

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from config import CHANNELS_FILE


async def show_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process the received message and print `chat_id`.

    Due to Telegram Bot API restrictions, it is not possible to directly obtain the chat_id; it needs to be acquired through the message object.
    If you are not the type of bot that replies to messages but instead sends messages directly, then you need to obtain the chat_id.
    This method provides a way to obtain the chat_id. For example, you use this type of code:
    application.add_handler(MessageHandler(filters.TEXT, show_chat_id))
    Then, when a user types something in the current channel, this method will print the chat_id.

        Args:
            update (Update): A Telegram update object that contains message and chat information.
            context (ContextTypes.DEFAULT_TYPE): A context object that contains related callback data.

        Returns:
            None
    """
    chat_id = update.message.chat_id
    print(f"Received a message from chat ID: {chat_id}")


def refresh_channels_from_file():  # 移除了script_dir参数，支持注释行
    try:
        # 使用UTF-8编码读取文件以支持中文字符
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        # 过滤掉注释行和空行
        channels = []
        for line in lines:
            line = line.strip()  # 去除首尾空白
            if line and not line.startswith('#'):  # 跳过空行和注释行
                channels.append(line)

        return tuple(channels)
    except FileNotFoundError:
        # 创建UTF-8编码的文件
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            f.write("# ChronoLullaby Channels List\n")
            f.write("# 使用 # 开头的行会被忽略\n")
            f.write("# 格式: @channelname 或 channelname\n")
        return ()
    except UnicodeDecodeError:
        # 如果UTF-8失败，尝试GBK编码（Windows兼容）
        try:
            with open(CHANNELS_FILE, "r", encoding="gbk") as f:
                lines = f.read().splitlines()

            # 过滤掉注释行和空行
            channels = []
            for line in lines:
                line = line.strip()  # 去除首尾空白
                if line and not line.startswith('#'):  # 跳过空行和注释行
                    channels.append(line)

            return tuple(channels)
        except Exception as e:
            print(f"读取channels.txt文件时出错: {e}")
            return ()
