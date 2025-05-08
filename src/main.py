#!/usr/bin/env python
import os
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from task.dl_audio import dl_audio_latest, dl_audio_closest_after
from task.send_file import send_file
from util import refresh_channels_from_file
from commands.add_channel import add_channel
import time
import random
from config import AUDIO_FOLDER, ENV_FILE

load_dotenv(ENV_FILE)

SPEEDRUN = 1 * 60 * 60 + 22 * 60
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
# TOKEN = os.environ.get("BOT_TOKEN_DEV")
# CHAT_ID = os.environ.get("CHAT_ID_DEV")


def dl_youtube(channels) -> None:
    for channel in channels:
        try:
            delay = random.uniform(30, 60)
            time.sleep(delay)
            dl_audio_latest(channel_name=channel)
        except Exception as e:
            print(f"Error downloading from {channel}: {str(e)}")
            continue


async def dl_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    channels = refresh_channels_from_file()
    dl_youtube(channels)


async def send_file_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_file(context=context, chat_id=CHAT_ID, audio_folder=AUDIO_FOLDER)


async def dl_story(context: ContextTypes.DEFAULT_TYPE) -> None:
    channels = refresh_channels_from_file()
    dl_youtube(channels)


def main():
    request = HTTPXRequest(read_timeout=60, write_timeout=60)
    application = Application.builder().token(TOKEN).request(request).build()
    application.job_queue.run_repeating(
        dl_task,
        interval=SPEEDRUN * 6,
        first=5,
    )
    application.job_queue.run_repeating(
        send_file_task,
        interval=SPEEDRUN // 32,
        first=SPEEDRUN // 16,
    )
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.run_polling()


if __name__ == "__main__":
    main()
