from telegram import Update
from telegram.ext import ContextTypes


def refresh_channels_from_file():
    try:
        with open("channels.txt", "r") as f:
            channels = f.read().splitlines()
        global channal_name
        channal_name = tuple(channels)
    except FileNotFoundError:
        open("channels.txt", "w").close()
        channal_name = ()


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    refresh_channels_from_file()
    command_parts = update.message.text.split()
    if len(command_parts) < 2:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please provide the channel name. YouTube channel names usually start with @, please include the @ in the name.",
        )
        return
    new_channel = command_parts[1]
    print(new_channel)
    if new_channel not in channal_name:
        with open("channels.txt", "a") as f:
            f.write(f"{new_channel}\n")
        refresh_channels_from_file()
        print(channal_name)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="The channel list has been updated, a new channel has been added.",
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="The channel already exists, no need to add.",
        )
