# -*- coding: utf-8 -*-
import logging

import yt_dlp

from logger import TRACE_LEVEL, get_logger, log_with_context
from task.ytdlp_support import apply_js_runtime

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


def fetch_channel_entries(channel_name: str, max_videos: int, cookies_file: str):
    """
    从频道的 /videos 和 /streams 拉取条目，合并去重后返回。

    Returns:
        dict: {
            "channel_display_name": str | None,
            "entries": list[dict],
            "tab_counts": dict[str, int],
        }
    """
    list_opts = {
        "quiet": True,
        "playlistend": max_videos,
        "cookiefile": cookies_file,
        "extract_flat": True,
        "http_headers": PREFERRED_HTTP_HEADERS,
        "extractor_args": PREFERRED_YT_EXTRACTOR_ARGS,
    }
    list_opts = apply_js_runtime(list_opts)

    channel_display_name = None
    entries_to_download = []
    seen_ids: set = set()
    tab_counts = {}

    with yt_dlp.YoutubeDL(list_opts) as list_ydl:
        for tab in ["videos", "streams"]:
            tab_url = f"{yt_base_url}{channel_name}/{tab}"
            log_with_context(
                logger, logging.INFO,
                "开始获取频道视频列表" if tab == "videos" else "开始获取频道直播录播列表",
                yt_channel=channel_name, url=tab_url
            )
            try:
                tab_info = list_ydl.extract_info(tab_url, download=False)
            except Exception as tab_err:
                log_with_context(
                    logger, logging.WARNING,
                    f"获取 /{tab} 列表失败，跳过",
                    yt_channel=channel_name, error=str(tab_err)
                )
                tab_counts[tab] = 0
                continue

            if not tab_info:
                log_with_context(
                    logger, logging.WARNING,
                    f"/{tab} 返回空结果，跳过",
                    yt_channel=channel_name
                )
                tab_counts[tab] = 0
                continue

            if channel_display_name is None:
                channel_display_name = (
                    tab_info.get('channel')
                    or tab_info.get('uploader')
                    or tab_info.get('title')
                )
                for suffix in [' - Videos', ' - Streams', ' - Live']:
                    if channel_display_name and channel_display_name.endswith(suffix):
                        channel_display_name = channel_display_name[:-len(suffix)]
                        break

            if 'entries' not in tab_info:
                log_with_context(
                    logger, TRACE_LEVEL,
                    f"频道 /{tab} 无内容（该频道可能没有此类视频）",
                    yt_channel=channel_name
                )
                tab_counts[tab] = 0
                continue

            tab_added = 0
            tab_dupes = 0
            for entry in tab_info.get('entries') or []:
                if not entry or not isinstance(entry, dict):
                    continue
                vid_id = entry.get('id')
                if vid_id and vid_id in seen_ids:
                    tab_dupes += 1
                    continue
                if vid_id:
                    seen_ids.add(vid_id)
                entries_to_download.append(entry)
                tab_added += 1
                if len(entries_to_download) >= max_videos:
                    break

            tab_counts[tab] = tab_added
            log_with_context(
                logger, logging.INFO,
                f"/{tab} 列表获取完成",
                yt_channel=channel_name,
                tab=tab,
                new_entries=tab_added,
                duplicates_skipped=tab_dupes
            )

            if len(entries_to_download) >= max_videos:
                break

    log_with_context(
        logger, logging.INFO, "频道信息获取完成",
        yt_channel=channel_name,
        display_name=channel_display_name,
        entries_count=len(entries_to_download),
        from_videos=tab_counts.get('videos', 0),
        from_streams=tab_counts.get('streams', 0)
    )

    return {
        "channel_display_name": channel_display_name,
        "entries": entries_to_download,
        "tab_counts": tab_counts,
    }
