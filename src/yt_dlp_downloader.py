import os
import random
import time
from dotenv import load_dotenv
from task.dl_audio import dl_audio_latest
from util import refresh_channels_from_file
from config import ENV_FILE

load_dotenv(ENV_FILE)

SPEEDRUN = 1 * 60 * 60 + 22 * 60

def dl_youtube(channels) -> None:
    for channel in channels:
        try:
            delay = random.uniform(30, 60)
            time.sleep(delay)
            dl_audio_latest(channel_name=channel)
        except Exception as e:
            print(f"Error downloading from {channel}: {str(e)}")
            continue

def main():
    while True:
        channels = refresh_channels_from_file()
        dl_youtube(channels)
        time.sleep(SPEEDRUN * 6)

if __name__ == "__main__":
    main() 