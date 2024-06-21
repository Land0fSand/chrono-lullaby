import yt_dlp
import os
import datetime

yt_base_url = "https://www.youtube.com/"
download_archive_path = "download_archive.txt"


def dateafter_filter(info_dict):
    timestamp = info_dict.get("timestamp")
    if timestamp:
        upload_datetime = datetime.datetime.fromtimestamp(
            timestamp, tz=datetime.timezone.utc
        )
        one_day_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=1
        )
    else:
        upload_date = info_dict.get("upload_date")
        if not upload_date:
            return None
        naive_upload_datetime = datetime.datetime.strptime(upload_date, "%Y%m%d")
        upload_datetime = naive_upload_datetime.replace(tzinfo=datetime.timezone.utc)
        one_day_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=2
        )

    if upload_datetime < one_day_ago:
        return "Video is older than one day"
    return None


def run_ytdlp(au_folder, channel_name):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(au_folder, "%(uploader)s.%(fulltitle)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "aac",
                "preferredquality": "64",
            }
        ],
        "download_archive": download_archive_path,
        "playlistend": 3,
        "match_filter": dateafter_filter,
        "ignoreerrors": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"{yt_base_url}{channel_name}"])
