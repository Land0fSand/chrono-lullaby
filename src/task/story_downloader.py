# -*- coding: utf-8 -*-
import datetime
import logging
import os
import random
import re
import time
from typing import Optional

import yt_dlp

from config import (
    AUDIO_FOLDER,
    COOKIES_FILE,
    get_config_provider,
    get_video_delay_max,
    get_video_delay_min,
)
from logger import TRACE_LEVEL, get_logger, log_with_context
from task.download_state import check_cookies, record_download_entry
from task.download_filters import member_content_filter
from task.ytdlp_support import (
    apply_js_runtime,
    cleanup_incomplete_downloads,
    safe_rename_file,
    sanitize_filename,
)

logger = get_logger('downloader.dl_audio')

yt_base_url = "https://www.youtube.com/"

PREFERRED_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh-CN;q=0.9,zh;q=0.8,en;q=0.7,ja;q=0.6",
    "Sec-Fetch-Mode": "navigate",
}

PREFERRED_YT_EXTRACTOR_ARGS = {
    'youtube': {
        'lang': ['zh-TW'],
        'player-client': ['web_embedded', 'ios', 'android']
    }
}


def _extract_timestamp_from_entry(entry: dict) -> Optional[int]:
    """Extract upload timestamp (UTC seconds) from yt-dlp entry."""
    if not entry:
        return None
    ts = entry.get("timestamp")
    if ts is not None:
        return ts
    upload_date = entry.get("upload_date")
    if upload_date:
        try:
            naive = datetime.datetime.strptime(upload_date, "%Y%m%d")
            return int(naive.replace(tzinfo=datetime.timezone.utc).timestamp())
        except Exception:
            return None
    return None


def dl_audio_story(channel_name: str, audio_folder: str, group_name: str, items_per_run: int = 1) -> bool:
    """Download next batch for story-type channels (oldest to newest)."""
    if not check_cookies():
        return False

    target_folder = audio_folder if audio_folder else AUDIO_FOLDER
    os.makedirs(target_folder, exist_ok=True)
    cleanup_incomplete_downloads(target_folder)

    provider = get_config_provider()
    progress: dict = {}
    try:
        progress = provider.get_story_progress(group_name) or {}
    except Exception as err:
        logger.warning(f"读取故事进度失败: {err}")
        progress = {}

    last_video_id = progress.get("last_video_id")
    last_ts = progress.get("last_timestamp")
    run_started_ts = time.time()

    list_opts = {
        "quiet": True,
        "cookiefile": COOKIES_FILE,
        "playlistreverse": True,
        "http_headers": PREFERRED_HTTP_HEADERS,
        "extractor_args": PREFERRED_YT_EXTRACTOR_ARGS,
    }
    list_opts = apply_js_runtime(list_opts)

    last_ts_int: Optional[int] = None
    if last_ts is not None:
        try:
            last_ts_int = int(last_ts)
        except (TypeError, ValueError):
            last_ts_int = None

    timestamp_checkpoint_value = last_ts_int if last_ts_int is not None else last_ts

    if last_ts_int is not None:
        try:
            cutoff_dt = datetime.datetime.fromtimestamp(
                last_ts_int, tz=datetime.timezone.utc
            )
            dateafter_value = cutoff_dt.strftime("%Y%m%d")
            list_opts["dateafter"] = dateafter_value
            logger.trace(
                f"📚 故事频道 {group_name} 使用 dateafter 过滤：{dateafter_value}"
            )
        except Exception as err:
            logger.trace(
                f"⚠️ 故事频道 {group_name} 设置 dateafter 失败，将回退到完整扫描: {err}"
            )
    selected_entries: list = []
    items_limit = max(1, int(items_per_run or 1))

    entries = []
    seen_ids: set = set()
    story_tab_counts = {}
    with yt_dlp.YoutubeDL(list_opts) as list_ydl:
        for tab in ["videos", "streams"]:
            tab_url = f"{yt_base_url}{channel_name}/{tab}"
            log_with_context(
                logger, TRACE_LEVEL,
                f"Story mode: 开始获取 /{tab} 列表",
                yt_channel=channel_name, url=tab_url
            )
            try:
                tab_info = list_ydl.extract_info(tab_url, download=False)
            except Exception as err:
                log_with_context(
                    logger,
                    logging.WARNING,
                    f"Story mode: failed to fetch /{tab} entries, skipping",
                    yt_channel=channel_name,
                    error=str(err),
                )
                story_tab_counts[tab] = 0
                continue

            if not tab_info:
                log_with_context(
                    logger, logging.WARNING,
                    f"Story mode: /{tab} 返回空结果，跳过",
                    yt_channel=channel_name
                )
                story_tab_counts[tab] = 0
                continue

            raw_entries = tab_info.get("entries")
            if raw_entries is None:
                log_with_context(
                    logger,
                    TRACE_LEVEL,
                    f"Story mode: 频道 /{tab} 无内容（该频道可能没有此类视频）",
                    yt_channel=channel_name,
                )
                story_tab_counts[tab] = 0
                continue

            tab_added = 0
            tab_dupes = 0
            for entry in raw_entries:
                if not entry or not isinstance(entry, dict):
                    continue
                vid_id = entry.get("id")
                if vid_id and vid_id in seen_ids:
                    tab_dupes += 1
                    continue
                if vid_id:
                    seen_ids.add(vid_id)
                entries.append(entry)
                tab_added += 1

            story_tab_counts[tab] = tab_added
            log_with_context(
                logger, TRACE_LEVEL,
                f"Story mode: /{tab} 列表获取完成",
                yt_channel=channel_name,
                tab=tab,
                new_entries=tab_added,
                duplicates_skipped=tab_dupes
            )

    if not entries:
        log_with_context(
            logger,
            logging.WARNING,
            "Story mode: channel returned no entries",
            yt_channel=channel_name,
        )

    def _sort_ts(entry):
        ts = _extract_timestamp_from_entry(entry)
        return ts if ts is not None else float('inf')

    entries.sort(key=_sort_ts)

    log_with_context(
        logger, TRACE_LEVEL,
        "Story mode: 频道条目合并完成",
        yt_channel=channel_name,
        total_entries=len(entries),
        from_videos=story_tab_counts.get('videos', 0),
        from_streams=story_tab_counts.get('streams', 0)
    )

    if entries:
        if last_ts_int is not None:
            for entry in entries:
                entry_ts = _extract_timestamp_from_entry(entry)
                if entry_ts is None:
                    log_with_context(
                        logger,
                        TRACE_LEVEL,
                        "Story mode: skip entry without timestamp while checkpoint is set",
                        yt_channel=channel_name,
                        video_id=entry.get("id"),
                    )
                    continue
                if entry_ts <= last_ts_int:
                    continue
                selected_entries.append(entry)
                if len(selected_entries) >= items_limit:
                    break
        else:
            found_last_id = last_video_id is None
            for entry in entries:
                entry_id = entry.get("id")
                if not found_last_id:
                    if entry_id == last_video_id:
                        found_last_id = True
                    continue
                selected_entries.append(entry)
                if len(selected_entries) >= items_limit:
                    break
            if last_video_id and not found_last_id:
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Story mode: checkpoint video not found, defaulting to earliest entries",
                    yt_channel=channel_name,
                    checkpoint_video=last_video_id,
                )
                selected_entries = entries[:items_limit]
    else:
        log_with_context(
            logger,
            logging.INFO,
            "Story mode: no valid entries returned by channel",
            yt_channel=channel_name,
        )

    if not selected_entries:
        log_with_context(
            logger,
            logging.INFO,
            "Story mode: no pending entries to download",
            yt_channel=channel_name,
            last_timestamp=timestamp_checkpoint_value,
            last_video_id=last_video_id,
        )

    last_progress_id = None
    last_progress_ts = None
    downloaded = 0

    for entry in selected_entries:
        video_id = entry.get("id") or ""
        if not video_id:
            continue
        video_url = entry.get("webpage_url") or entry.get("url") or f"{yt_base_url}watch?v={video_id}"

        downloaded_file_info = {"path": None}

        def story_progress_hook(data):
            if data['status'] == 'finished':
                downloaded_file_info["path"] = data.get('filename')

        uploader = entry.get("uploader") or entry.get("channel") or channel_name or "UnknownChannel"
        safe_uploader = sanitize_filename(uploader)
        title = entry.get("fulltitle") or entry.get("title") or video_id
        safe_title = sanitize_filename(title)
        ts = _extract_timestamp_from_entry(entry)

        final_stem = f"{safe_uploader}.{video_id}.{safe_title}"
        expected_audio_ext = ".m4a"
        final_destination_audio_path = os.path.join(target_folder, f"{final_stem}{expected_audio_ext}")

        last_progress_id = video_id
        last_progress_ts = ts

        if downloaded > 0:
            v_delay_min = get_video_delay_min()
            v_delay_max = get_video_delay_max()
            if v_delay_max > 0 and v_delay_max >= v_delay_min:
                delay = random.uniform(v_delay_min, v_delay_max)
                log_with_context(
                    logger,
                    logging.INFO,
                    "故事条目间延迟",
                    yt_channel=channel_name,
                    delay_seconds=round(delay, 2)
                )
                time.sleep(delay)

        if os.path.exists(final_destination_audio_path):
            log_with_context(
                logger, logging.INFO,
                "故事视频已存在",
                yt_channel=channel_name,
                video_id=video_id
            )
            continue

        custom_opts = {
            "match_filter": member_content_filter,
            "keepvideo": False,
            "outtmpl": os.path.join(target_folder, "%(uploader)s.%(id)s.%(title)s.tmp"),
            "progress_hooks": [story_progress_hook],
        }

        from task.dl_audio import get_ydl_opts
        ydl_opts = get_ydl_opts(custom_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except yt_dlp.utils.DownloadError as err:
            logger.error(f"故事视频下载错误: {err}")
            continue
        except Exception as err:
            logger.error(f"故事视频下载异常: {err}")
            continue

        hook_reported_temp_path = downloaded_file_info.get("path")
        actual_temp_path = hook_reported_temp_path
        resolved_temp_path = None

        candidate_paths = []
        if actual_temp_path:
            candidate_paths.append(actual_temp_path)
            parent_dir, temp_filename = os.path.split(actual_temp_path)
            if ".tmp.f" in temp_filename:
                normalized_filename = re.sub(r"(\.tmp)\.f\d+(?=\.)", r"\1", temp_filename)
                candidate_paths.append(os.path.join(parent_dir, normalized_filename))

        for candidate in candidate_paths:
            if candidate and os.path.exists(candidate):
                resolved_temp_path = candidate
                break

        if not resolved_temp_path:
            for file_name in os.listdir(target_folder):
                if video_id in file_name and (file_name.endswith('.tmp.m4a') or file_name.endswith('.tmp')):
                    resolved_temp_path = os.path.join(target_folder, file_name)
                    break

        actual_temp_path = resolved_temp_path

        if actual_temp_path and os.path.exists(actual_temp_path):
            if safe_rename_file(actual_temp_path, final_destination_audio_path):
                file_size_mb = os.path.getsize(final_destination_audio_path) / (1024 * 1024)
                log_with_context(
                    logger, logging.INFO,
                    "故事视频下载成功",
                    yt_channel=channel_name,
                    video_id=video_id,
                    size_mb=round(file_size_mb, 2)
                )
                downloaded += 1
                record_download_entry(video_id, channel_name)
            else:
                logger.error(f"故事视频重命名失败: {actual_temp_path}")
        else:
            logger.error(f"未找到预期的临时文件 (hook path: {hook_reported_temp_path})")

    if last_progress_id:
        provider.update_story_progress(group_name, {
            "last_video_id": last_progress_id,
            "last_timestamp": last_progress_ts,
            "last_run_ts": int(run_started_ts)
        })
    else:
        provider.update_story_progress(group_name, {"last_run_ts": int(run_started_ts)})

    return downloaded > 0
