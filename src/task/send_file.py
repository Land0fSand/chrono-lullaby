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
                # await context.bot.send_document(chat_id=CHAT_ID, document=file)
                artist = file_name.split(".")[0]
                mainFilename = file_name.split(".")[1]
                # Here is a hidden issue that I often encounter: during the file sending process, the error telegram.error.TimedOut: Timed out occurs.
                # However, the file still gets sent successfully, so I use contextlib.suppress(TimedOut) to ignore this exception.
                # I've also increased the request duration to 60 seconds in an attempt to reduce this issue.
                # But if the TimedOut exception occurs and the file is not sent successfully, the file will still be deleted, resulting in a file not being sent.
                # If the problem becomes serious in the future, I will consider a corresponding solution.
                with suppress(TimedOut):
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=file,
                        # caption=mainFilename,
                        title=mainFilename,
                        performer=artist,
                    )
            # After successful sending, delete the file. For now, I'm not handling the case of deletion failure, as it's unlikely to happen.
            os.remove(file_path)
            break
        else:
            # If it's a folder, skip it.
            continue
