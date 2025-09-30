# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import sys

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from telegram.ext import Application, ContextTypes, CommandHandler
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
from config import ENV_FILE, CHANNELS_FILE

load_dotenv(ENV_FILE)
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


async def add_channel(update, context: ContextTypes.DEFAULT_TYPE):
    channel = " ".join(context.args)
    if channel:
        with open(CHANNELS_FILE, "a") as f:
            f.write(f"{channel}\n")
        await update.message.reply_text(f"Channel {channel} added successfully!")
    else:
        await update.message.reply_text("Please provide a channel name.")


def main():
    request = HTTPXRequest(read_timeout=60, write_timeout=60)
    application = Application.builder().token(TOKEN).request(request).build()
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.run_polling()


if __name__ == "__main__":
    main()
