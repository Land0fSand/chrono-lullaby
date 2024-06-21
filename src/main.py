#!/usr/bin/env python
import os
from telegram.ext import Application, ContextTypes
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from yt import run_ytdlp
from task.send_file import send_file

# from util import show_chat_id

load_dotenv()
FAST_PASS = 1 * 60 * 60 + 22 * 60
AUDIO_FOLDER = "au"
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
# TOKEN = os.environ.get("BOT_TOKEN_DEV")
# CHAT_ID = os.environ.get("CHAT_ID_DEV")


def refresh_channels_from_file():
    try:
        with open("channels.txt", "r") as f:
            read_channels = f.read().splitlines()
        global channels
        channels = tuple(read_channels)
    except FileNotFoundError:
        open("channels.txt", "w").close()
        channels = ()


refresh_channels_from_file()


def dl_youtube() -> None:
    for channal in channels:
        run_ytdlp(au_folder=AUDIO_FOLDER, channel_name=channal)


async def dl_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    dl_youtube()


async def send_file_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_file(context=context, chat_id=CHAT_ID, audio_folder=AUDIO_FOLDER)


def main():
    request = HTTPXRequest(read_timeout=60, write_timeout=60)
    application = Application.builder().token(TOKEN).request(request).build()
    application.job_queue.run_repeating(
        dl_task, interval=FAST_PASS, first=FAST_PASS // 256
    )
    application.job_queue.run_repeating(
        send_file_task, interval=FAST_PASS // 32, first=FAST_PASS // 16
    )
    # application.add_handler(MessageHandler(filters.TEXT, show_chat_id))
    # application.add_handler(CommandHandler("addchannel", add_channel))
    application.run_polling()


if __name__ == "__main__":
    main()
