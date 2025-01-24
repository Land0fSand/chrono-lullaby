import yt_dlp
import os
import datetime
import json
from config import AUDIO_FOLDER, DOWNLOAD_ARCHIVE, DEBUG_INFO, STORY_FILE

yt_base_url = "https://www.youtube.com/"


def oneday_filter(info_dict):
    timestamp = info_dict.get("timestamp")
    if timestamp:
        upload_datetime = datetime.datetime.fromtimestamp(
            timestamp, tz=datetime.timezone.utc
        )
        one_day_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=4
        )
    else:
        upload_date = info_dict.get("upload_date")
        if not upload_date:
            return None
        naive_upload_datetime = datetime.datetime.strptime(upload_date, "%Y%m%d")
        upload_datetime = naive_upload_datetime.replace(tzinfo=datetime.timezone.utc)
        one_day_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=5
        )

    if upload_datetime < one_day_ago:
        return "Video is older than one day"
    return None


def dl_audio_latest(channel_name):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "aac",
                "preferredquality": "64",
            }
        ],
        "download_archive": DOWNLOAD_ARCHIVE,
        "playlistend": 12,
        "match_filter": oneday_filter,
        "ignoreerrors": True,
        "sleep_interval": 7,
        "max_sleep_interval": 18,
        "random_sleep": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"{yt_base_url}{channel_name}"])


def closest_after_filter(target_timestamp):
    def filter_func(info_dict):
        timestamp = info_dict.get("timestamp")
        if not timestamp:
            return "No timestamp available"

        if timestamp <= target_timestamp:
            return "Video is older than the target time"

        return None

    return filter_func


def update_channel_info_file(channel_name, target_timestamp, info_file_path):
    updated = False
    lines = []

    if os.path.exists(STORY_FILE):
        with open(STORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    for i, line in enumerate(lines):
        if line.startswith(channel_name):
            lines[i] = f"{channel_name} {target_timestamp}\n"
            updated = True
            break

    if not updated:
        lines.append(f"{channel_name} {target_timestamp}\n")

    with open(STORY_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def dl_audio_closest_after(au_folder, channel_name, target_timestamp=None):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "outtmpl": os.path.join(AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "aac",
                "preferredquality": "64",
            }
        ],
        "ignoreerrors": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(f"{yt_base_url}{channel_name}", download=False)
        entries = info_dict.get("entries", [])

        if not entries:
            print("No videos found")
            return

        closest_video = None
        closest_time_diff = float("inf")
        oldest_video = None
        oldest_timestamp = float("inf")

        for entry in entries:
            video_entries = entry.get("entries", [])
            for video in video_entries:
                video_timestamp = video.get("timestamp")
                if not video_timestamp:
                    upload_date = video.get("upload_date")
                    if upload_date:
                        video_timestamp = int(
                            datetime.datetime.strptime(
                                upload_date, "%Y%m%d"
                            ).timestamp()
                        )
                    else:
                        continue

                if video_timestamp < oldest_timestamp:
                    oldest_timestamp = video_timestamp
                    oldest_video = video

                if target_timestamp is not None:
                    time_diff = video_timestamp - target_timestamp
                    if 0 < time_diff < closest_time_diff:
                        closest_time_diff = time_diff
                        closest_video = video

        if target_timestamp is None:
            closest_video = oldest_video

        if not closest_video:
            print("No suitable video found")
            return

        with open(DEBUG_INFO, "w", encoding="utf-8") as debug_file:
            json.dump(closest_video, debug_file, ensure_ascii=False, indent=4)

        timestamp = closest_video.get("timestamp", closest_video.get("upload_date"))
        if not timestamp:
            print("No valid timestamp or upload_date found for the video")
            return

        update_channel_info_file(channel_name, timestamp, STORY_FILE)

        if "videos" in entry.get("title", "").lower():
            ydl.download([closest_video["webpage_url"]])
        else:
            print(f"Skipped downloading video from playlist: {entry.get('title', '')}")


def read_and_process_channels(channels_file_path, au_folder):
    if not os.path.exists(channels_file_path):
        print(f"No channel info file found at {channels_file_path}")
        return

    with open(channels_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        channel_name = parts[0]
        timestamp = int(parts[1]) if len(parts) > 1 else None

        print(f"Processing channel {channel_name} with timestamp {timestamp}")
        dl_audio_closest_after(AUDIO_FOLDER, channel_name, timestamp)
