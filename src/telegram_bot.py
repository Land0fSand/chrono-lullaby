#!/usr/bin/env python
import os
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from task.send_file import send_file
from commands.add_channel import add_channel
from config import AUDIO_FOLDER, ENV_FILE

load_dotenv(ENV_FILE)

SPEEDRUN = 1 * 60 * 60 + 22 * 60
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

async def send_file_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_file(context=context, chat_id=CHAT_ID, audio_folder=AUDIO_FOLDER)

def main():
    request = HTTPXRequest(read_timeout=60, write_timeout=60)
    application = Application.builder().token(TOKEN).request(request).build()
    application.job_queue.run_repeating(
        send_file_task,
        interval=SPEEDRUN // 32,
        first=SPEEDRUN // 256,
    )
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.run_polling()

if __name__ == "__main__":
    main() 