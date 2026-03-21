# -*- coding: utf-8 -*-
import datetime
import logging
import os

import yt_dlp

from config import AUDIO_FOLDER, STORY_FILE
from logger import get_logger, log_with_context
from task.download_state import check_cookies, record_download_entry
from task.ytdlp_support import safe_rename_file, sanitize_filename

logger = get_logger('downloader.dl_audio')

yt_base_url = "https://www.youtube.com/"


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
        with open(STORY_FILE, "r", encoding="utf-8") as file:
            lines = file.readlines()

    for index, line in enumerate(lines):
        if line.startswith(channel_name):
            lines[index] = f"{channel_name} {target_timestamp}\n"
            updated = True
            break

    if not updated:
        lines.append(f"{channel_name} {target_timestamp}\n")

    with open(STORY_FILE, "w", encoding="utf-8") as file:
        file.writelines(lines)


def dl_audio_closest_after(au_folder, channel_name, target_timestamp=None):
    log_with_context(
        logger, logging.INFO,
        "开始处理频道历史视频",
        yt_channel=channel_name
    )
    if not check_cookies():
        return False

    from task.dl_audio import get_ydl_opts
    ydl_opts = get_ydl_opts()
    logger.trace("已配置下载选项 (将使用临时目录)")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            logger.info("正在获取频道信息...")
            info_dict = ydl.extract_info(f"{yt_base_url}{channel_name}", download=False)
            if not info_dict:
                logger.error(f"无法获取频道信息: {channel_name}")
                return False

            logger.info("正在处理视频列表以查找目标视频...")
            entries = info_dict.get("entries", [])
            if not entries:
                logger.warning("未找到任何视频条目")
                return False

            closest_video = None
            closest_time_diff = float("inf")
            oldest_video = None
            oldest_timestamp = float("inf")

            processed_videos_for_closest = []
            if info_dict.get('_type') == 'playlist':
                for entry_playlist in info_dict.get('entries', []):
                    if entry_playlist and entry_playlist.get('_type') == 'playlist':
                        nested_entries = entry_playlist.get('entries') or []
                        for video_in_playlist in nested_entries:
                            if video_in_playlist:
                                processed_videos_for_closest.append(video_in_playlist)
                    elif entry_playlist:
                        processed_videos_for_closest.append(entry_playlist)
            else:
                processed_videos_for_closest = info_dict.get('entries') or []

            for video_data in processed_videos_for_closest:
                video_timestamp = video_data.get("timestamp")
                if not video_timestamp:
                    upload_date = video_data.get("upload_date")
                    if upload_date:
                        try:
                            video_timestamp = int(datetime.datetime.strptime(upload_date, "%Y%m%d").timestamp())
                        except ValueError:
                            continue
                    else:
                        continue

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
                logger.warning("根据时间戳未找到合适视频")
                return False

            video_webpage_url = closest_video.get("webpage_url")
            if not video_webpage_url:
                logger.error(f"选定视频没有webpage_url: {closest_video.get('title', '未知')}")
                return False

            video_id_history = closest_video.get('id', 'unknown_id')

            log_with_context(
                logger, logging.INFO,
                "选定要下载的历史视频",
                video_id=video_id_history,
                title=closest_video.get('title', '未知标题')
            )

            uploader = closest_video.get('uploader') or closest_video.get('channel') or channel_name or 'UnknownChannel'
            safe_uploader = sanitize_filename(uploader)

            fulltitle = closest_video.get('fulltitle') or closest_video.get('title') or 'UnknownTitle'
            safe_title = sanitize_filename(fulltitle)
            expected_audio_ext = ".m4a"
            final_audio_filename_stem = f"{safe_uploader}.{video_id_history}.{safe_title}"

            temp_audio_path_without_ext = os.path.join(au_folder, final_audio_filename_stem)
            expected_temp_audio_path = temp_audio_path_without_ext + ".tmp" + expected_audio_ext
            final_destination_audio_path = os.path.join(au_folder, f"{final_audio_filename_stem}{expected_audio_ext}")

            if os.path.exists(final_destination_audio_path):
                logger.trace(f"最终音频文件已存在，跳过: {final_destination_audio_path}")
                timestamp_to_update = closest_video.get("timestamp", closest_video.get("upload_date"))
                if timestamp_to_update:
                    if isinstance(timestamp_to_update, str):
                        timestamp_to_update = int(datetime.datetime.strptime(timestamp_to_update, "%Y%m%d").timestamp())
                    update_channel_info_file(channel_name, timestamp_to_update, STORY_FILE)
                return True

            single_video_ydl_opts = ydl_opts.copy()
            single_video_ydl_opts['outtmpl'] = temp_audio_path_without_ext + '.tmp'
            single_video_ydl_opts.pop('playlistend', None)
            single_video_ydl_opts.pop('match_filter', None)

            with yt_dlp.YoutubeDL(single_video_ydl_opts) as single_video_downloader:
                single_video_downloader.download([video_webpage_url])

            if os.path.exists(expected_temp_audio_path):
                logger.info(f"历史视频转换后音频已下载（临时文件）: {expected_temp_audio_path}")
                if safe_rename_file(expected_temp_audio_path, final_destination_audio_path):
                    log_with_context(
                        logger, logging.INFO,
                        "成功重命名历史视频音频",
                        destination=final_destination_audio_path
                    )
                    record_download_entry(video_id_history, channel_name)
                else:
                    logger.error("历史视频重命名失败，跳过此文件")

                timestamp_to_update = closest_video.get("timestamp", closest_video.get("upload_date"))
                if timestamp_to_update:
                    if isinstance(timestamp_to_update, str):
                        timestamp_to_update = int(datetime.datetime.strptime(timestamp_to_update, "%Y%m%d").timestamp())
                    update_channel_info_file(channel_name, timestamp_to_update, STORY_FILE)
                return True

            logger.error(f"历史视频转换后的音频文件（临时文件）未找到: {expected_temp_audio_path}")
            return False

        except Exception as err:
            log_with_context(
                logger, logging.ERROR,
                "处理历史视频时发生错误",
                yt_channel=channel_name,
                error=str(err)
            )
            return False


def read_and_process_channels(channels_file_path, au_folder):
    if not os.path.exists(channels_file_path):
        logger.error(f"No channel info file found at {channels_file_path}")
        return

    with open(channels_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    for line in lines:
        parts = line.strip().split()
        channel_name = parts[0]
        timestamp = int(parts[1]) if len(parts) > 1 else None

        log_with_context(
            logger, logging.INFO,
            "Processing channel",
            yt_channel=channel_name,
            timestamp=timestamp
        )
        dl_audio_closest_after(AUDIO_FOLDER, channel_name, timestamp)
