import yt_dlp
import os
import datetime
import json
import sys
from config import (
    AUDIO_FOLDER, 
    DOWNLOAD_ARCHIVE, 
    DEBUG_INFO, 
    STORY_FILE,
    COOKIES_FILE,
)

yt_base_url = "https://www.youtube.com/"


def oneday_filter(info_dict):
    """过滤最近3天的视频"""
    try:
        timestamp = info_dict.get("timestamp")
        if timestamp:
            upload_datetime = datetime.datetime.fromtimestamp(
                timestamp, tz=datetime.timezone.utc
            )
            three_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                days=3
            )
            
            if upload_datetime > three_days_ago:
                print(f"\n发现最近视频: {info_dict.get('title', '未知标题')}")
                print(f"上传时间: {upload_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                return None
            return "视频超过3天"
            
        upload_date = info_dict.get("upload_date")
        if not upload_date:
            print(f"\n无法获取视频时间: {info_dict.get('title', '未知标题')}")
            return None
            
        naive_upload_datetime = datetime.datetime.strptime(upload_date, "%Y%m%d")
        upload_datetime = naive_upload_datetime.replace(tzinfo=datetime.timezone.utc)
        three_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=3
        )
        
        if upload_datetime > three_days_ago:
            print(f"\n发现最近视频: {info_dict.get('title', '未知标题')}")
            print(f"上传时间: {upload_datetime.strftime('%Y-%m-%d')}")
            return None
        return "视频超过3天"
    except Exception as e:
        print(f"过滤器错误: {str(e)}")
        return None


def check_cookies():
    """检查cookies文件是否存在且有效"""
    if not os.path.exists(COOKIES_FILE):
        print("\n未找到cookies文件！")
        print("请按以下步骤操作：")
        print("1. 安装Chrome扩展：'Cookie-Editor'")
        print("2. 访问 YouTube 并确保已登录")
        print("3. 点击Cookie-Editor扩展图标")
        print("4. 点击'Export'按钮，选择'Netscape HTTP Cookie File'格式")
        print("5. 将导出的内容保存到项目根目录下的 'youtube.cookies' 文件中")
        print("6. 完成后重新运行程序")
        return False
    return True


def get_ydl_opts(custom_opts=None):
    base_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "aac",
                "preferredquality": "64",
            }
        ],
        "cookiefile": COOKIES_FILE,
        "sleep_interval": 88,
        "max_sleep_interval": 208,
        "random_sleep": True,
        "ignoreerrors": False,
        "format_sort": ["+hasaud", "+hasvid", "+codec:opus", "+codec:aac", "+codec:mp3"],
        "format_fallback": True,
        "progress_hooks": [progress_hook],
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate",
        }
    }
    
    if custom_opts:
        base_opts.update(custom_opts)
    
    return base_opts


def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get('speed', 0)
                if speed:
                    speed_mb = speed / 1024 / 1024
                    print(f"\r下载进度: {percent:.1f}% - {speed_mb:.1f}MB/s", end='', flush=True)
                else:
                    print(f"\r下载进度: {percent:.1f}%", end='', flush=True)
        except Exception:
            pass
    elif d['status'] == 'finished':
        print(f"\n已完成下载: {d.get('filename', '')}")
    elif d['status'] == 'already_downloaded':
        print(f"已存在: {d.get('title', '')}")


def get_available_format(url):
    """获取视频的可用格式，并选择一个合适的格式进行下载"""
    ydl_opts = {
        "listformats": True,
        "cookiefile": COOKIES_FILE,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        audio_formats = [f for f in formats if f.get("acodec") != "none"]
        if audio_formats:
            return audio_formats[0].get("format_id", "bestaudio/best")
        # 如果没有音频格式，尝试选择任何可用的视频格式
        video_formats = [f for f in formats if f.get("vcodec") != "none"]
        if video_formats:
            return video_formats[0].get("format_id", "best")
        # 如果都没有，尝试选择任何可用格式
        if formats:
            return formats[0].get("format_id", "best")
        # 如果都没有，返回默认值
        return "best"


def dl_audio_latest(channel_name):
    if not check_cookies():
        return False
    
    custom_opts = {
        "download_archive": DOWNLOAD_ARCHIVE,
        "playlistend": 3,
        "match_filter": oneday_filter,
    }
    
    ydl_opts = get_ydl_opts(custom_opts)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"开始获取频道 {channel_name} 的视频列表...")
            url = f"{yt_base_url}{channel_name}"
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries", [])
            for entry in entries:
                video_entries = entry.get("entries", [])
                for video in video_entries:
                    video_url = video.get("webpage_url", "")
                    if video_url:
                        format_id = get_available_format(video_url)
                        video_ydl_opts = ydl_opts.copy()
                        video_ydl_opts["format"] = format_id
                        with yt_dlp.YoutubeDL(video_ydl_opts) as video_ydl:
                            try:
                                video_ydl.download([video_url])
                            except Exception as e:
                                print(f"下载视频 {video.get('title', '未知标题')} 时发生错误: {str(e)}")
                                continue
        except Exception as e:
            print(f"下载时发生错误: {str(e)}")
            if "HTTP Error 404" in str(e):
                print(f"频道 {channel_name} 不存在，请检查频道名称是否正确")
            elif any(msg in str(e) for msg in ["Sign in to confirm", "Unable to download API page", "not a bot"]):
                print("\nCookies可能已过期！")
                print("请按以下步骤更新cookies：")
                print("1. 使用Cookie-Editor导出新的cookies")
                print("2. 将新的cookies内容覆盖保存到 'youtube.cookies' 文件")
                print("3. 完成后按 Enter 键继续程序")
                input("等待用户更新 cookies，按 Enter 键继续...")
                if not check_cookies():
                    print("仍然未找到有效的 cookies 文件，程序退出")
                    return False
                print("检测到新的 cookies 文件，继续下载过程...")
                return dl_audio_latest(channel_name)  # 递归调用以重试下载
            return False
    return True


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
    print(f"\n开始处理频道历史视频: {channel_name}")
    if not check_cookies():
        return False
    
    ydl_opts = get_ydl_opts()
    print("已配置下载选项")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print("正在获取频道信息...")
            info_dict = ydl.extract_info(f"{yt_base_url}{channel_name}", download=False)
            if not info_dict:
                print(f"无法获取频道信息: {channel_name}")
                return False
                
            print("正在处理视频列表...")
            entries = info_dict.get("entries", [])
            
            if not entries:
                print("未找到任何视频")
                return False

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
                return False

            with open(DEBUG_INFO, "w", encoding="utf-8") as debug_file:
                json.dump(closest_video, debug_file, ensure_ascii=False, indent=4)

            timestamp = closest_video.get("timestamp", closest_video.get("upload_date"))
            if not timestamp:
                print("No valid timestamp or upload_date found for the video")
                return False

            update_channel_info_file(channel_name, timestamp, STORY_FILE)

            if "videos" in entry.get("title", "").lower():
                ydl.download([closest_video["webpage_url"]])
            else:
                print(f"Skipped downloading video from playlist: {entry.get('title', '')}")

            return True
        except Exception as e:
            print(f"获取视频信息时发生错误: {str(e)}")
            return False


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
