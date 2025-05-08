import os
from telegram.ext import ContextTypes
from telegram.error import TimedOut
from contextlib import suppress


async def send_file(context: ContextTypes.DEFAULT_TYPE, chat_id, audio_folder) -> None:
    if not os.path.exists(audio_folder):
        return
    files = os.listdir(audio_folder)
    if not files:
        return
    for file_name in files:
        file_path = os.path.join(audio_folder, file_name)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as file:
                artist = file_name.split(".")[0]
                mainFilename = file_name.split(".")[1]
                with suppress(TimedOut):
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=file,
                        title=mainFilename,
                        performer=artist,
                    )
            os.remove(file_path)
            break
        else:
            continue
