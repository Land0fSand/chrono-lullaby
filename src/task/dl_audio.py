import yt_dlp
import os
import datetime
import json
import sys
import shutil
from config import (
    AUDIO_FOLDER, 
    TEMP_AUDIO_FOLDER,
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
    if not os.path.exists(TEMP_AUDIO_FOLDER):
        os.makedirs(TEMP_AUDIO_FOLDER)
        print(f"已创建临时下载目录: {TEMP_AUDIO_FOLDER}")

    base_opts = {
        "format": "bestaudio/best",
        "outtmpl": {
            'default': os.path.join(TEMP_AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.%(ext)s"),
            'aac': os.path.join(TEMP_AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.m4a"), 
        },
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
        print(f"\n下载完成 (原始文件): {d.get('filename', '')}")
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
        video_formats = [f for f in formats if f.get("vcodec") != "none"]
        if video_formats:
            return video_formats[0].get("format_id", "best")
        if formats:
            return formats[0].get("format_id", "best")
        return "best"


def dl_audio_latest(channel_name):
    if not check_cookies():
        return False
    
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)
        print(f"已创建最终音频目录: {AUDIO_FOLDER}")

    custom_opts = {
        "download_archive": DOWNLOAD_ARCHIVE,
        "playlistend": 6,
        "match_filter": oneday_filter,
        "keepvideo": False, 
    }
    
    ydl_opts = get_ydl_opts(custom_opts)
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"开始获取频道 {channel_name} 的视频列表...")
            url = f"{yt_base_url}{channel_name}"
            channel_info = ydl.extract_info(url, download=False)
            if not channel_info or 'entries' not in channel_info:
                print(f"频道 {channel_name} 未找到视频或信息不完整。")
                return False

            entries_to_download = []
            if channel_info.get('_type') == 'playlist':
                for video_playlist_entry in channel_info.get('entries', []):
                    if video_playlist_entry and video_playlist_entry.get('_type') == 'playlist':
                        for video_in_playlist in video_playlist_entry.get('entries', []):
                             if video_in_playlist: entries_to_download.append(video_in_playlist)
                    elif video_playlist_entry:
                        entries_to_download.append(video_playlist_entry)
            else:
                entries_to_download = channel_info.get('entries', [])

            for video_info in entries_to_download:
                video_url = video_info.get("webpage_url")
                if not video_url:
                    print(f"  跳过条目，无URL: {video_info.get('title', '未知标题')}")
                    continue

                print(f"  准备处理视频: {video_info.get('title', '未知标题')} ({video_url})")
                
                uploader = video_info.get('uploader', 'UnknownUploader')
                fulltitle = video_info.get('fulltitle', video_info.get('title', 'UnknownTitle'))
                safe_title = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in fulltitle)
                safe_uploader = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in uploader)

                expected_audio_ext = ".m4a"
                final_audio_filename_stem = f"{safe_uploader}.{safe_title}"
                
                temp_audio_path_without_ext = os.path.join(TEMP_AUDIO_FOLDER, final_audio_filename_stem)
                expected_temp_audio_path = temp_audio_path_without_ext + expected_audio_ext

                final_destination_audio_path = os.path.join(AUDIO_FOLDER, f"{final_audio_filename_stem}{expected_audio_ext}")

                if os.path.exists(final_destination_audio_path):
                    print(f"  最终音频文件已存在于目标目录: {final_destination_audio_path}，跳过。")
                    continue
                
                current_video_ydl_opts = ydl_opts.copy()
                current_video_ydl_opts['outtmpl'] = {
                    'default': temp_audio_path_without_ext + '.%(ext)s',
                    'aac': temp_audio_path_without_ext + expected_audio_ext
                }

                print(f"    将下载到临时文件名模板: {temp_audio_path_without_ext}.%(ext)s")
                print(f"    预期转换后临时音频: {expected_temp_audio_path}")
                print(f"    最终将移动到: {final_destination_audio_path}")

                try:
                    with yt_dlp.YoutubeDL(current_video_ydl_opts) as video_ydl:
                        video_ydl.download([video_url]) 
                    
                    if os.path.exists(expected_temp_audio_path):
                        print(f"    转换后音频已在临时目录: {expected_temp_audio_path}")
                        print(f"    准备移动到: {final_destination_audio_path}")
                        shutil.move(expected_temp_audio_path, final_destination_audio_path)
                        print(f"    成功移动到: {final_destination_audio_path}")
                    else:
                        print(f"错误: 转换后的音频文件 {expected_temp_audio_path} 在临时目录中未找到！")
                        original_downloaded_file_actual_ext = None
                        for ext_try in ['.webm', '.mp4', '.mkv', '.flv', '.avi', '.mov', '.opus', '.ogg', '.mp3']:
                            potential_orig_file = temp_audio_path_without_ext + ext_try
                            if os.path.exists(potential_orig_file):
                                original_downloaded_file_actual_ext = ext_try
                                print(f"      找到原始下载文件: {potential_orig_file}，但未转换为 {expected_audio_ext}")
                                break
                        if not original_downloaded_file_actual_ext:
                             print(f"      原始下载文件也未找到 (尝试的模板: {temp_audio_path_without_ext}.*)")

                except yt_dlp.utils.DownloadError as de:
                    if "already been recorded in the archive" in str(de):
                        print(f"  视频已在存档中记录，跳过: {video_info.get('title', '未知标题')}")
                    else:
                        print(f"  下载视频 {video_info.get('title', '未知标题')} 时发生 yt-dlp DownloadError: {str(de)}")
                    if os.path.exists(expected_temp_audio_path):
                        try: os.remove(expected_temp_audio_path); print(f"    已清理部分下载的音频文件: {expected_temp_audio_path}")
                        except OSError: pass
                    for ext_try in ['.webm', '.mp4', '.mkv']: 
                        potential_orig_file = temp_audio_path_without_ext + ext_try
                        if os.path.exists(potential_orig_file):
                            try: os.remove(potential_orig_file); print(f"    已清理部分下载的视频文件: {potential_orig_file}")
                            except OSError: pass
                            break
                    continue
                except Exception as e:
                    print(f"  下载视频 {video_info.get('title', '未知标题')} 时发生一般错误: {type(e).__name__} - {str(e)}")
                    continue
        
        except Exception as e:
            print(f"处理频道 {channel_name} 时发生错误: {type(e).__name__} - {str(e)}")
            if "HTTP Error 404" in str(e):
                print(f"频道 {channel_name} 不存在或无法访问，请检查频道名称是否正确。")
            elif any(msg in str(e).lower() for msg in ["sign in to confirm", "unable to download api page", "not a bot", "consent"]):
                print("\nCookies可能已过期或需要同意YouTube政策！")
                print("请按以下步骤更新cookies：")
                print("1. (浏览器) 清除youtube.com的cookies，访问YouTube并确保已登录及处理任何弹窗。")
                print("2. (浏览器) 使用Cookie-Editor导出新的cookies。")
                print("3. 将新的cookies内容覆盖保存到 'youtube.cookies' 文件。")
                print("4. 完成后按 Enter 键继续程序或重启程序。")
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
    print("已配置下载选项 (将使用临时目录)")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print("正在获取频道信息...")
            info_dict = ydl.extract_info(f"{yt_base_url}{channel_name}", download=False)
            if not info_dict:
                print(f"无法获取频道信息: {channel_name}")
                return False
                
            print("正在处理视频列表以查找目标视频...")
            entries = info_dict.get("entries", [])
            if not entries:
                print("未找到任何视频条目")
                return False

            closest_video = None
            closest_time_diff = float("inf")
            oldest_video = None
            oldest_timestamp = float("inf")

            processed_videos_for_closest = []
            if info_dict.get('_type') == 'playlist':
                 for entry_playlist in info_dict.get('entries', []):
                    if entry_playlist and entry_playlist.get('_type') == 'playlist':
                        for video_in_playlist in entry_playlist.get('entries', []):
                             if video_in_playlist: processed_videos_for_closest.append(video_in_playlist)
                    elif entry_playlist:
                        processed_videos_for_closest.append(entry_playlist)
            else:
                processed_videos_for_closest = info_dict.get('entries', [])

            for video_data in processed_videos_for_closest:
                video_timestamp = video_data.get("timestamp")
                if not video_timestamp:
                    upload_date = video_data.get("upload_date")
                    if upload_date:
                        try:
                            video_timestamp = int(datetime.datetime.strptime(upload_date, "%Y%m%d").timestamp())
                        except ValueError: continue
                    else: continue

                if video_timestamp < oldest_timestamp:
                    oldest_timestamp = video_timestamp
                    oldest_video = video_data
                if target_timestamp is not None:
                    time_diff = video_timestamp - target_timestamp
                    if 0 < time_diff < closest_time_diff:
                        closest_time_diff = time_diff
                        closest_video = video_data
            
            if target_timestamp is None and oldest_video:
                closest_video = oldest_video
            
            if not closest_video:
                print("根据时间戳未找到合适视频")
                return False
            
            video_webpage_url = closest_video.get("webpage_url")
            if not video_webpage_url:
                print(f"选定视频没有webpage_url: {closest_video.get('title', '未知')}")
                return False

            print(f"选定要下载的历史视频: {closest_video.get('title', '未知标题')}")

            uploader = closest_video.get('uploader', 'UnknownUploader')
            fulltitle = closest_video.get('fulltitle', closest_video.get('title', 'UnknownTitle'))
            safe_title = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in fulltitle)
            safe_uploader = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in uploader)
            expected_audio_ext = ".m4a"
            final_audio_filename_stem = f"{safe_uploader}.{safe_title}"

            temp_audio_path_without_ext = os.path.join(TEMP_AUDIO_FOLDER, final_audio_filename_stem)
            expected_temp_audio_path = temp_audio_path_without_ext + expected_audio_ext
            final_destination_audio_path = os.path.join(au_folder, f"{final_audio_filename_stem}{expected_audio_ext}")

            if os.path.exists(final_destination_audio_path):
                print(f"  最终音频文件已存在于目标目录: {final_destination_audio_path}，跳过。")
                timestamp_to_update = closest_video.get("timestamp", closest_video.get("upload_date"))
                if timestamp_to_update:
                    if isinstance(timestamp_to_update, str):
                         timestamp_to_update = int(datetime.datetime.strptime(timestamp_to_update, "%Y%m%d").timestamp())
                    update_channel_info_file(channel_name, timestamp_to_update, STORY_FILE)
                return True

            single_video_ydl_opts = ydl_opts.copy()
            single_video_ydl_opts['outtmpl'] = {
                'default': temp_audio_path_without_ext + '.%(ext)s',
                'aac': temp_audio_path_without_ext + expected_audio_ext
            }
            single_video_ydl_opts.pop('playlistend', None) 
            single_video_ydl_opts.pop('match_filter', None)

            with yt_dlp.YoutubeDL(single_video_ydl_opts) as single_video_downloader:
                single_video_downloader.download([video_webpage_url])

            if os.path.exists(expected_temp_audio_path):
                print(f"    历史视频转换后音频已在临时目录: {expected_temp_audio_path}")
                shutil.move(expected_temp_audio_path, final_destination_audio_path)
                print(f"    成功将历史视频音频移动到: {final_destination_audio_path}")

                timestamp_to_update = closest_video.get("timestamp", closest_video.get("upload_date"))
                if timestamp_to_update:
                    if isinstance(timestamp_to_update, str):
                         timestamp_to_update = int(datetime.datetime.strptime(timestamp_to_update, "%Y%m%d").timestamp())
                    update_channel_info_file(channel_name, timestamp_to_update, STORY_FILE)
                return True
            else:
                print(f"错误: 历史视频转换后的音频文件 {expected_temp_audio_path} 在临时目录中未找到！")
                return False
            
        except Exception as e:
            print(f"处理历史视频 {channel_name} 时发生错误: {str(e)}")
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
