# -*- coding: utf-8 -*-
import datetime

from config import get_filter_days
from logger import get_logger

logger = get_logger('downloader.dl_audio')


def member_content_filter(info_dict):
    """
    过滤会员专属内容

    策略：
    1. 几乎不预判，让 yt-dlp + cookies 决定能否下载
    2. 只过滤明确的私人视频
    """
    try:
        video_id = info_dict.get("id", "")

        if info_dict.get("availability") == "private":
            logger.trace(f"⏭️ 跳过私人视频: {video_id}")
            return "私人视频"

        return None

    except Exception as err:
        logger.warning(f"会员过滤器错误: {err}")
        return None


def shorts_filter(info_dict):
    """过滤 YouTube Shorts（短视频）"""
    try:
        video_id = info_dict.get('id', '')

        url = info_dict.get('webpage_url') or info_dict.get('url') or ''
        if '/shorts/' in url:
            logger.trace(f"⏭️ 跳过 Shorts（URL含/shorts/）: {video_id}")
            return "YouTube Shorts"

        duration = info_dict.get('duration')
        if duration is not None and duration <= 60:
            logger.trace(f"⏭️ 跳过 Shorts（时长{duration}s≤60s）: {video_id}")
            return "YouTube Shorts (时长≤60s)"

        return None
    except Exception as err:
        logger.warning(f"Shorts过滤器错误: {err}")
        return None


def oneday_filter(info_dict):
    """过滤最近N天的视频（N从配置读取）"""
    try:
        timestamp = info_dict.get("timestamp")
        upload_datetime = None

        if timestamp:
            upload_datetime = datetime.datetime.fromtimestamp(
                timestamp, tz=datetime.timezone.utc
            )
        elif info_dict.get("upload_date"):
            upload_date = info_dict.get("upload_date")
            naive_upload_datetime = datetime.datetime.strptime(upload_date, "%Y%m%d")
            upload_datetime = naive_upload_datetime.replace(tzinfo=datetime.timezone.utc)
        else:
            return None

        filter_days = get_filter_days()
        days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=filter_days)

        if upload_datetime > days_ago:
            return None
        return f"视频超过{filter_days}天"

    except Exception as err:
        logger.warning(f"过滤器错误: {str(err)}")
        return None


def combined_filter(info_dict):
    """组合过滤器：同时应用时间过滤、Shorts过滤和会员内容过滤"""
    try:
        shorts_result = shorts_filter(info_dict)
        if shorts_result:
            return shorts_result

        member_result = member_content_filter(info_dict)
        if member_result:
            return member_result

        time_result = oneday_filter(info_dict)
        if time_result:
            return time_result

        return None
    except Exception as err:
        logger.warning(f"组合过滤器错误: {err}")
        return None
