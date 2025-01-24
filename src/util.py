from telegram import Update
from telegram.ext import ContextTypes
import os
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


def refresh_channels_from_file():  # 移除了script_dir参数
    try:
        with open(CHANNELS_FILE, "r") as f:
            read_channels = f.read().splitlines()
        channels = tuple(read_channels)
    except FileNotFoundError:
        open(CHANNELS_FILE, "w").close()
        channels = ()
    return channels
