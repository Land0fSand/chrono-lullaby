import subprocess
import os

yt_base_url = "https://www.youtube.com/"
download_archive_path = "download_archive.txt"


def run_ytdlp(au_folder, channel_name):
    output_path = os.path.join(au_folder, "%(uploader)s.%(fulltitle)s.%(ext)s")

    subprocess.run(
        [
            "yt-dlp",
            f"{yt_base_url}{channel_name}",
            "--playlist-end",
            "3",
            "--dateafter",
            "now-1day",
            "-x",
            "--audio-format",
            "aac",
            "--audio-quality",
            "64K",
            "--download-archive",
            download_archive_path,
            "-o",
            output_path,
        ]
    )
