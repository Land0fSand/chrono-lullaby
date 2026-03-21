# -*- coding: utf-8 -*-
import yt_dlp
import os
import datetime
import sys
import time
import logging
import re

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from config import (
    AUDIO_FOLDER,
    DOWNLOAD_ARCHIVE,
    COOKIES_FILE,
    get_video_delay_min,
    get_video_delay_max,
    get_max_videos_per_channel,
)
from logger import get_logger, log_with_context, TRACE_LEVEL
import random
from task.download_state import (
    check_cookies,
    record_download_entry,
    sync_download_archive,
)
from task.ytdlp_support import (
    TimestampedYTDLLogger,
    apply_js_runtime,
    cleanup_incomplete_downloads,
    cleanup_partial_files_for_base,
    is_member_only_message,
    is_video_in_download_archive,
    safe_rename_file,
)
from task.download_filters import combined_filter
from task.channel_listing import fetch_channel_entries
from task.history_downloader import (
    closest_after_filter,
    dl_audio_closest_after,
    read_and_process_channels,
    update_channel_info_file,
)
from task.story_downloader import dl_audio_story

# 使用统一的日志系统
logger = get_logger('downloader.dl_audio')

yt_base_url = "https://www.youtube.com/"

# 统一 HTTP 请求头（Accept-Language 对 YouTube InnerTube API 无效，保留作为通用 header）
PREFERRED_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh-CN;q=0.9,zh;q=0.8,en;q=0.7,ja;q=0.6",
    "Sec-Fetch-Mode": "navigate",
}

# YouTube 提取器语言参数：通过 InnerTube API 的 hl 字段控制标题语言
# 优先返回繁体中文，YouTube 会自动 fallback：zh-TW → zh-CN → 视频默认语言
# 注意：值必须为 list，传字符串会导致 yt-dlp 逐字符解析报错
# 使用 web_embedded 客户端目前能绕过部分 n-sig 解析问题
PREFERRED_YT_EXTRACTOR_ARGS = {
    'youtube': {
        'lang': ['zh-TW'],
        'player-client': ['web_embedded', 'ios', 'android']
    }
}


def get_ydl_opts(custom_opts=None):
    # 确保音频文件夹存在
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)
        logger.info(f"已创建音频目录: {AUDIO_FOLDER}")
    cleanup_incomplete_downloads(AUDIO_FOLDER)

    # 使用 .tmp 后缀来标记正在下载的文件
    # 注意：FFmpeg后处理器会替换文件扩展名，所以我们只用一个模板
    # 最终格式：filename.tmp.m4a (yt-dlp下载为filename.tmp，FFmpeg转换为filename.tmp.m4a)
    base_format = "bestaudio[ext=m4a]/bestaudio/best"
    base_opts = {
        "format": base_format,
        "outtmpl": os.path.join(AUDIO_FOLDER, "%(id)s.%(title)s.tmp"),
        "logger": TimestampedYTDLLogger(),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "64",
                "nopostoverwrites": False,
            }
        ],
        "keepvideo": False,
        "cookiefile": COOKIES_FILE,
        "cache_dir": False,
        "sleep_interval": 30,
        "max_sleep_interval": 60,
        "random_sleep": True,
        "ignoreerrors": True,
        "format_sort": ["+hasaud", "+hasvid", "+codec:opus", "+codec:aac", "+codec:mp3"],
        "format_fallback": True,
        "progress_hooks": [progress_hook],
        "http_headers": PREFERRED_HTTP_HEADERS,
        "extractor_args": PREFERRED_YT_EXTRACTOR_ARGS,
    }

    base_opts = apply_js_runtime(base_opts)

    if custom_opts:
        base_opts.update(custom_opts)

    return base_opts


def progress_hook(d):
    if d['status'] == 'finished':
        filename = os.path.basename(d.get('filename', ''))
        if ".tmp.f" in filename:
            return
        logger.trace(f"下载完成: {filename}")
    elif d['status'] == 'already_downloaded':
        logger.trace(f"已存在: {d.get('title', '')}")


def get_available_format(url):
    """获取视频的可用格式，并选择一个合适的格式进行下载"""
    ydl_opts = {
        "listformats": True,
        "cookiefile": COOKIES_FILE,
        "quiet": True,
    }
    ydl_opts = apply_js_runtime(ydl_opts)
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


def _append_stats_detail(stats, *, index, title, video_id, status, reason, **extra):
    stats[status] += 1
    detail = {
        'index': index,
        'title': title,
        'id': video_id,
        'status': status,
        'reason': reason,
    }
    detail.update(extra)
    stats['details'].append(detail)


def _log_video_status(channel_name, stats, index, video_title, video_id, status, reason, level=logging.INFO, **extra):
    log_with_context(
        logger,
        level,
        f"视频处理结果 [{index}/{stats['total']}]",
        yt_channel=channel_name,
        video_id=video_id,
        title=video_title[:60] + "..." if len(video_title) > 60 else video_title,
        status=status,
        reason=reason,
        **extra,
    )


def _resolve_video_url(video_info, video_id):
    video_url = video_info.get("webpage_url")
    if not video_url and video_id and video_id != 'unknown':
        video_url = f"{yt_base_url}watch?v={video_id}"
    return video_url


def _format_upload_date(video_info):
    if video_info.get('timestamp'):
        upload_dt = datetime.datetime.fromtimestamp(
            video_info['timestamp'],
            tz=datetime.timezone.utc,
        )
        return upload_dt.strftime('%m-%d')
    upload_date = video_info.get('upload_date')
    if upload_date and len(upload_date) >= 8:
        return f"{upload_date[4:6]}-{upload_date[6:8]}"
    return "未知"


def _find_existing_audio_file(target_folder, video_id):
    try:
        for name in os.listdir(target_folder):
            if f'.{video_id}.' in name and name.endswith('.m4a') and '.tmp' not in name:
                return os.path.join(target_folder, name)
    except OSError:
        return None
    return None


def _resolve_temp_audio_path(target_folder, video_id, downloaded_file_info):
    temp_audio_path = downloaded_file_info.get('path')
    if temp_audio_path and os.path.exists(temp_audio_path):
        return temp_audio_path
    try:
        for name in os.listdir(target_folder):
            if f'.{video_id}.' in name and name.endswith('.tmp.m4a'):
                return os.path.join(target_folder, name)
    except OSError:
        return None
    return None


def _build_per_video_ydl_opts(base_opts, target_folder, download_context, downloaded_file_info):
    current_video_ydl_opts = base_opts.copy()
    current_video_ydl_opts['outtmpl'] = os.path.join(
        target_folder,
        "%(uploader)s.%(id)s.%(title)s.tmp",
    )

    def per_video_progress_hook(d, _info=downloaded_file_info):
        if d.get('status') == 'finished':
            path = d.get('filename')
            if path and '.tmp.f' not in os.path.basename(path):
                _info['path'] = path

    class ContextAwareYTDLLogger(TimestampedYTDLLogger):
        def warning(self, msg):
            cleaned = self._clean_message(msg)
            if not cleaned:
                return
            lower = cleaned.lower()
            if 'does not pass filter' in lower:
                download_context['filtered'] = True
                download_context['filter_reason'] = (
                    cleaned.split(':', 1)[-1].strip()
                    if ':' in cleaned else '被过滤器拦截'
                )
                self._logger.trace(f"⏭️ {cleaned}")
                return
            self._logger.warning(f'⚠️ yt-dlp: {cleaned}')

        def error(self, msg):
            cleaned = self._clean_message(msg)
            if not cleaned:
                return
            if is_member_only_message(cleaned):
                download_context['member_blocked'] = True
                download_context['error_reason'] = cleaned
                self._logger.trace(f"🔒 {cleaned}")
                return
            self._logger.error(f'❌ yt-dlp: {cleaned}')

    current_video_ydl_opts['logger'] = ContextAwareYTDLLogger()
    current_video_ydl_opts['progress_hooks'] = list(
        current_video_ydl_opts.get('progress_hooks', [])
    ) + [per_video_progress_hook]
    return current_video_ydl_opts


def _process_latest_video_entry(
    *,
    idx,
    video_info,
    stats,
    channel_name,
    target_folder,
    ydl_opts,
):
    video_title = video_info.get('title', '未知标题')
    video_id = video_info.get('id', 'unknown')
    video_url = _resolve_video_url(video_info, video_id)

    log_with_context(
        logger,
        logging.INFO,
        f"开始处理视频 [{idx}/{stats['total']}]",
        yt_channel=channel_name,
        video_id=video_id,
        title=video_title[:60] + "..." if len(video_title) > 60 else video_title,
    )

    if not video_url:
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='error',
            reason='无视频URL',
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'error', '无视频URL', level=logging.WARNING)
        return video_title, video_id

    upload_date_str = _format_upload_date(video_info)
    filter_result = combined_filter(video_info)
    if filter_result:
        log_with_context(
            logger, TRACE_LEVEL,
            f"⏭️ 跳过视频（{filter_result}）",
            yt_channel=channel_name,
            title=video_title[:60] + "..." if len(video_title) > 60 else video_title,
            video_id=video_id,
            index=idx,
            total=stats['total'],
            upload_date=upload_date_str
        )
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='filtered',
            reason=filter_result,
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'filtered', filter_result)
        return video_title, video_id

    if _find_existing_audio_file(target_folder, video_id):
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='already_exists',
            reason='文件已存在',
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'already_exists', '文件已存在')
        return video_title, video_id

    if is_video_in_download_archive(video_id):
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='archived',
            reason='archive_hit_no_file',
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'archived', '已在下载存档中')
        return video_title, video_id

    downloaded_file_info = {"path": None}
    download_context = {
        'member_blocked': False,
        'error_reason': None,
        'filtered': False,
        'filter_reason': None,
    }
    current_video_ydl_opts = _build_per_video_ydl_opts(
        ydl_opts,
        target_folder,
        download_context,
        downloaded_file_info,
    )

    try:
        with yt_dlp.YoutubeDL(current_video_ydl_opts) as video_ydl:
            video_ydl.download([video_url])
    except yt_dlp.utils.DownloadError as err:
        error_str = str(err)
        error_lower = error_str.lower()
        if "already been recorded in the archive" in error_str:
            _append_stats_detail(
                stats,
                index=idx,
                title=video_title,
                video_id=video_id,
                status='archived',
                reason='已在存档中',
            )
            _log_video_status(channel_name, stats, idx, video_title, video_id, 'archived', '已在存档中')
            return video_title, video_id
        if 'does not pass filter' in error_lower:
            reason = error_str.split(':', 1)[-1].strip() if ':' in error_str else '被过滤器拦截'
            _append_stats_detail(
                stats,
                index=idx,
                title=video_title,
                video_id=video_id,
                status='filtered',
                reason=reason,
            )
            _log_video_status(channel_name, stats, idx, video_title, video_id, 'filtered', reason)
            return video_title, video_id
        if is_member_only_message(error_str):
            _append_stats_detail(
                stats,
                index=idx,
                title=video_title,
                video_id=video_id,
                status='member_only',
                reason=error_str,
            )
            _log_video_status(channel_name, stats, idx, video_title, video_id, 'member_only', '会员专属或权限受限')
            return video_title, video_id
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='error',
            reason=error_str,
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'error', error_str, level=logging.ERROR)
        return video_title, video_id
    except Exception as err:
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='error',
            reason=str(err),
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'error', str(err), level=logging.ERROR)
        return video_title, video_id

    temp_audio_path = _resolve_temp_audio_path(
        target_folder,
        video_id,
        downloaded_file_info,
    )

    if not temp_audio_path or not os.path.exists(temp_audio_path):
        if download_context.get('filtered'):
            reason = download_context.get('filter_reason') or '被过滤器拦截'
            _append_stats_detail(
                stats,
                index=idx,
                title=video_title,
                video_id=video_id,
                status='filtered',
                reason=reason,
            )
            _log_video_status(channel_name, stats, idx, video_title, video_id, 'filtered', reason)
            return video_title, video_id
        if download_context.get('member_blocked'):
            reason = download_context.get('error_reason') or '会员专属内容'
            _append_stats_detail(
                stats,
                index=idx,
                title=video_title,
                video_id=video_id,
                status='member_only',
                reason=reason,
            )
            _log_video_status(channel_name, stats, idx, video_title, video_id, 'member_only', reason)
            return video_title, video_id
        cleanup_partial_files_for_base(os.path.join(target_folder, video_id))
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='error',
            reason='转换失败或文件未找到',
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'error', '转换失败或文件未找到', level=logging.ERROR)
        return video_title, video_id

    final_destination_audio_path = re.sub(r'\.tmp(\.m4a)$', r'\1', temp_audio_path)
    rename_ok = (
        os.path.normcase(temp_audio_path) == os.path.normcase(final_destination_audio_path)
        or safe_rename_file(temp_audio_path, final_destination_audio_path)
    )
    if not rename_ok:
        _append_stats_detail(
            stats,
            index=idx,
            title=video_title,
            video_id=video_id,
            status='error',
            reason='文件重命名失败',
        )
        _log_video_status(channel_name, stats, idx, video_title, video_id, 'error', '文件重命名失败', level=logging.ERROR)
        return video_title, video_id

    file_size_mb = os.path.getsize(final_destination_audio_path) / (1024 * 1024)
    _append_stats_detail(
        stats,
        index=idx,
        title=video_title,
        video_id=video_id,
        status='success',
        reason='下载成功',
        size_mb=round(file_size_mb, 2),
    )
    _log_video_status(
        channel_name,
        stats,
        idx,
        video_title,
        video_id,
        'success',
        '下载成功',
        size_mb=round(file_size_mb, 2),
    )
    record_download_entry(video_id, channel_name)

    if idx < stats['total']:
        video_delay_min = get_video_delay_min()
        video_delay_max = get_video_delay_max()
        if video_delay_max > 0:
            delay = random.uniform(video_delay_min, video_delay_max)
            log_with_context(
                logger, logging.INFO,
                "⏳ 视频间延迟",
                yt_channel=channel_name,
                delay_seconds=round(delay, 2),
                current_video=idx,
                total_videos=stats['total']
            )
            time.sleep(delay)

    return video_title, video_id


def _handle_latest_channel_error(channel_name, err, video_title, video_id):
    error_str = str(err)
    error_type = type(err).__name__
    if "live event will begin in" in error_str.lower():
        log_with_context(
            logger, logging.INFO,
            "频道包含直播预告视频，稍后自动下载",
            yt_channel=channel_name,
            note="直播尚未开始"
        )
        return True
    if "premieres in" in error_str.lower() or "premiere" in error_str.lower():
        log_with_context(
            logger, logging.INFO,
            "频道包含待首映视频，稍后自动下载",
            yt_channel=channel_name,
            note="首映尚未开始"
        )
        return True
    if "does not pass filter" in error_str:
        log_with_context(
            logger, logging.INFO,
            "⏭️ 视频被过滤规则拦截",
            yt_channel=channel_name,
            video_id=video_id,
            reason=error_str[:200]
        )
        return True
    if is_member_only_message(error_str):
        safe_title = video_title or "未知标题"
        safe_id = video_id or "unknown"
        log_with_context(
            logger, logging.INFO,
            f"⏭️ 频道当前视频《{safe_title}》为会员专属，跳过",
            yt_channel=channel_name,
            video_title=safe_title,
            video_id=safe_id
        )
        return True

    log_with_context(
        logger, logging.ERROR,
        "❌ 处理频道失败",
        yt_channel=channel_name,
        error_type=error_type,
        error=error_str[:200]
    )
    if "HTTP Error 404" in error_str:
        logger.error(f"频道 {channel_name} 不存在或无法访问，请检查频道名称是否正确。")
    elif any(msg in error_str.lower() for msg in ["sign in to confirm", "unable to download api page", "not a bot", "consent"]):
        logger.error("Cookies可能已过期或需要同意YouTube政策！")
        logger.info("请按以下步骤更新cookies：")
        logger.info("1. (浏览器) 清除youtube.com的cookies，访问YouTube并确保已登录及处理任何弹窗。")
        logger.info("2. (浏览器) 使用Cookie-Editor导出新的cookies。")
        logger.info("3. 将新的cookies内容覆盖保存到 'youtube.cookies' 文件。")
        logger.info("4. 完成后按 Enter 键继续程序或重启程序。")
    return False


def dl_audio_latest(channel_name, audio_folder=None, group_name=None):
    """
    下载指定YouTube频道的最新音频

    Args:
        channel_name: YouTube频道名称
        audio_folder: 音频保存目录（可选，默认使用AUDIO_FOLDER）
        group_name: 频道组名称（用于日志）
    """
    if not check_cookies():
        return False

    target_folder = audio_folder if audio_folder else AUDIO_FOLDER
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        logger.info(f"已创建音频目录: {target_folder}")

    cleanup_incomplete_downloads(target_folder)
    sync_download_archive()

    max_videos = get_max_videos_per_channel()
    custom_opts = {
        "download_archive": DOWNLOAD_ARCHIVE,
        "playlistend": max_videos,
        "match_filter": combined_filter,
        "keepvideo": False,
        "outtmpl": os.path.join(target_folder, "%(uploader)s.%(id)s.%(title)s.%(ext)s"),
    }
    ydl_opts = get_ydl_opts(custom_opts)

    stats = {
        'total': 0,
        'success': 0,
        'already_exists': 0,
        'filtered': 0,
        'archived': 0,
        'member_only': 0,
        'error': 0,
        'details': [],
    }
    video_title = None
    video_id = None

    try:
        listing = fetch_channel_entries(
            channel_name=channel_name,
            max_videos=max_videos,
            cookies_file=COOKIES_FILE,
        )
        entries_to_download = listing["entries"]

        if not entries_to_download:
            log_with_context(
                logger, logging.WARNING,
                "频道视频列表为空或全部无效",
                yt_channel=channel_name
            )
            return True

        stats['total'] = len(entries_to_download)
        log_with_context(
            logger, logging.INFO,
            "📋 频道视频列表获取完成",
            yt_channel=channel_name,
            total_videos=stats['total'],
            max_to_process=max_videos,
            tg_channel=group_name if group_name else None
        )

        for idx, video_info in enumerate(entries_to_download, 1):
            video_title, video_id = _process_latest_video_entry(
                idx=idx,
                video_info=video_info,
                stats=stats,
                channel_name=channel_name,
                target_folder=target_folder,
                ydl_opts=ydl_opts,
            )

        log_with_context(
            logger, logging.INFO,
            "频道下载处理完成",
            yt_channel=channel_name,
            total=stats['total'],
            success=stats['success'],
            filtered=stats['filtered'],
            already_exists=stats['already_exists'],
            archived=stats['archived'],
            member_only=stats['member_only'],
            error=stats['error']
        )
    except Exception as err:
        return _handle_latest_channel_error(channel_name, err, video_title, video_id)
    return True
