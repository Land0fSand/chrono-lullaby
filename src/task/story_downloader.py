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
from task.download_state import check_cookies
from task.download_state import has_story_download_record, record_story_download_entry
from task.download_filters import member_content_filter
from task.channel_listing import (
    PREFERRED_HTTP_HEADERS,
    PREFERRED_YT_EXTRACTOR_ARGS,
    fetch_channel_entries,
)
from task.ytdlp_support import (
    apply_js_runtime,
    cleanup_incomplete_downloads,
    safe_rename_file,
    sanitize_filename,
)

logger = get_logger('downloader.dl_audio')

yt_base_url = "https://www.youtube.com/"


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


def _hydrate_story_entries(channel_name: str, entries: list[dict]) -> list[dict]:
    """Resolve per-video metadata so story mode can filter/sort safely."""
    detail_opts = {
        "quiet": True,
        "cookiefile": COOKIES_FILE,
        "noplaylist": True,
        "http_headers": PREFERRED_HTTP_HEADERS,
        "extractor_args": PREFERRED_YT_EXTRACTOR_ARGS,
    }
    detail_opts = apply_js_runtime(detail_opts)

    hydrated_entries: list[dict] = []
    with yt_dlp.YoutubeDL(detail_opts) as detail_ydl:
        for entry in entries:
            if not entry or not isinstance(entry, dict):
                continue
            video_id = entry.get("id")
            if not video_id:
                continue
            video_url = entry.get("webpage_url") or entry.get("url") or f"{yt_base_url}watch?v={video_id}"
            try:
                detail_info = detail_ydl.extract_info(video_url, download=False)
            except Exception as err:
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Story mode: failed to hydrate entry metadata, skipping item",
                    yt_channel=channel_name,
                    video_id=video_id,
                    error=str(err),
                )
                continue

            merged = dict(entry)
            if isinstance(detail_info, dict):
                merged.update(detail_info)
            if not merged.get("webpage_url"):
                merged["webpage_url"] = video_url
            hydrated_entries.append(merged)

    hydrated_entries.sort(
        key=lambda item: _extract_timestamp_from_entry(item) or float('inf')
    )
    return hydrated_entries


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
    if not progress:
        log_with_context(
            logger,
            logging.INFO,
            "Story mode: no stored checkpoint found",
            yt_channel=channel_name,
            tg_channel=group_name,
        )

    last_video_id = progress.get("last_video_id")
    last_ts = progress.get("last_timestamp")
    run_started_ts = time.time()

    last_ts_int: Optional[int] = None
    if last_ts is not None:
        try:
            last_ts_int = int(last_ts)
        except (TypeError, ValueError):
            last_ts_int = None

    timestamp_checkpoint_value = last_ts_int if last_ts_int is not None else last_ts

    selected_entries: list = []
    items_limit = max(1, int(items_per_run or 1))
    dateafter_value = None
    if last_ts_int is not None:
        try:
            cutoff_dt = datetime.datetime.fromtimestamp(
                last_ts_int, tz=datetime.timezone.utc
            )
            dateafter_value = cutoff_dt.strftime("%Y%m%d")
            logger.trace(
                f"📚 故事频道 {group_name} 使用 dateafter 过滤：{dateafter_value}"
            )
        except Exception as err:
            logger.trace(
                f"⚠️ 故事频道 {group_name} 设置 dateafter 失败，将回退到完整扫描: {err}"
            )

    listing = fetch_channel_entries(
        channel_name=channel_name,
        max_videos=max(200, items_limit * 50),
        cookies_file=COOKIES_FILE,
        playlist_reverse=True,
        dateafter=dateafter_value,
        extract_flat=True,
        log_prefix="Story mode",
        trace_success_logs=True,
    )
    entries = listing["entries"]
    story_tab_counts = listing["tab_counts"]
    listing_errors = listing.get("tab_errors") or {}
    fetch_failures = sum(1 for err in listing_errors.values() if err)

    if fetch_failures and not entries:
        log_with_context(
            logger,
            logging.ERROR,
            "Story mode: failed to fetch any channel entries; aborting progress update",
            yt_channel=channel_name,
            tg_channel=group_name,
            failed_tabs=",".join(sorted(tab for tab, err in listing_errors.items() if err)),
        )
        return False

    entries = _hydrate_story_entries(channel_name, entries)
    if not entries:
        log_with_context(
            logger,
            logging.WARNING,
            "Story mode: channel returned no usable entries",
            yt_channel=channel_name,
        )

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
    skipped_unavailable = 0

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
            record_story_download_entry(video_id, channel_name, group_name)
            downloaded += 1
            last_progress_id = video_id
            last_progress_ts = ts
            continue

        if has_story_download_record(video_id, group_name):
            log_with_context(
                logger, logging.INFO,
                "故事视频已在故事存档中",
                yt_channel=channel_name,
                tg_channel=group_name,
                video_id=video_id,
            )
            downloaded += 1
            last_progress_id = video_id
            last_progress_ts = ts
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
            log_with_context(
                logger,
                logging.WARNING,
                "故事视频下载失败，跳过并继续推进",
                yt_channel=channel_name,
                tg_channel=group_name,
                video_id=video_id,
                error=str(err),
            )
            skipped_unavailable += 1
            last_progress_id = video_id
            last_progress_ts = ts
            continue
        except Exception as err:
            log_with_context(
                logger,
                logging.WARNING,
                "故事视频下载异常，跳过并继续推进",
                yt_channel=channel_name,
                tg_channel=group_name,
                video_id=video_id,
                error=str(err),
            )
            skipped_unavailable += 1
            last_progress_id = video_id
            last_progress_ts = ts
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
                record_story_download_entry(video_id, channel_name, group_name)
                last_progress_id = video_id
                last_progress_ts = ts
            else:
                log_with_context(
                    logger,
                    logging.WARNING,
                    "故事视频重命名失败，跳过并继续推进",
                    yt_channel=channel_name,
                    tg_channel=group_name,
                    video_id=video_id,
                    temp_path=actual_temp_path,
                )
                skipped_unavailable += 1
                last_progress_id = video_id
                last_progress_ts = ts
        else:
            log_with_context(
                logger,
                logging.WARNING,
                "故事视频未找到预期文件，跳过并继续推进",
                yt_channel=channel_name,
                tg_channel=group_name,
                video_id=video_id,
                hook_path=hook_reported_temp_path,
            )
            skipped_unavailable += 1
            last_progress_id = video_id
            last_progress_ts = ts

    if last_progress_id:
        provider.update_story_progress(group_name, {
            "last_video_id": last_progress_id,
            "last_timestamp": last_progress_ts,
            "last_run_ts": int(run_started_ts)
        })
    else:
        provider.update_story_progress(group_name, {"last_run_ts": int(run_started_ts)})

    if skipped_unavailable > 0:
        log_with_context(
            logger,
            logging.INFO,
            "故事模式本轮跳过不可用条目",
            yt_channel=channel_name,
            tg_channel=group_name,
            skipped_unavailable=skipped_unavailable,
            downloaded=downloaded,
        )

    return True
