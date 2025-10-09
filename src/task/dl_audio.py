# -*- coding: utf-8 -*-
import yt_dlp
import os
import datetime
import json
import sys
import time
import logging
from typing import Optional

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from config import (
    AUDIO_FOLDER,
    DOWNLOAD_ARCHIVE,
    DEBUG_INFO,
    STORY_FILE,
    COOKIES_FILE,
)
from logger import get_logger, log_with_context

# 使用统一的日志系统
logger = get_logger('downloader.dl_audio')


class TimestampedYTDLLogger:
    """自定义yt-dlp日志处理器，桥接到统一日志系统"""

    def __init__(self):
        self._logger = get_logger('downloader.yt-dlp')

    def debug(self, msg):
        if msg.strip():
            self._logger.debug(msg)

    def info(self, msg):
        if msg.strip():
            self._logger.info(msg)

    def warning(self, msg):
        if msg.strip():
            self._logger.warning(msg)

    def error(self, msg):
        if msg.strip():
            self._logger.error(msg)

    def critical(self, msg):
        if msg.strip():
            self._logger.critical(msg)

yt_base_url = "https://www.youtube.com/"


def safe_rename_file(src, dst, max_retries=5):
    """
    安全重命名文件（从.tmp到正式文件名），包含重试机制处理文件锁定问题
    """
    for attempt in range(max_retries):
        try:
            os.rename(src, dst)
            return True
        except (OSError, PermissionError) as e:
            if attempt < max_retries - 1:
                log_with_context(
                    logger, logging.WARNING,
                    "文件重命名失败，准备重试",
                    src=src, dst=dst, attempt=attempt + 1, max_retries=max_retries, error=str(e)
                )
                time.sleep(0.5 * (attempt + 1))  # 递增延迟
                continue
            else:
                log_with_context(
                    logger, logging.ERROR,
                    "文件重命名失败，已达最大重试次数",
                    src=src, dst=dst, max_retries=max_retries, error=str(e)
                )
                # 尝试强制删除临时文件
                try:
                    os.remove(src)
                    logger.warning(f"已删除无法重命名的临时文件: {src}")
                except OSError:
                    logger.error(f"无法删除临时文件: {src}")
                return False
        except Exception as e:
            log_with_context(
                logger, logging.ERROR,
                "文件重命名意外错误",
                src=src, dst=dst, error=str(e), error_type=type(e).__name__
            )
            return False


def member_content_filter(info_dict):
    """过滤会员专属内容"""
    try:
        video_id = info_dict.get("id", "")
        video_title = info_dict.get('title', '未知标题')[:50]
        logger.debug(f"过滤器检查视频: {video_id} - {video_title}...")

        # 已知的会员视频ID列表
        known_member_videos = [
            "NeEjMRUgFBI",  # 这是日志中出现的会员视频
            "QG_547yIt1Q"   # 这是日志中出现的会员视频
        ]

        if video_id in known_member_videos:
            log_with_context(
                logger, logging.INFO,
                "跳过已知会员视频",
                video_id=video_id, title=video_title
            )
            return "已知会员视频"

        # 检查视频描述中是否包含会员内容关键词
        description = info_dict.get("description", "").lower()
        title = info_dict.get("title", "").lower()

        # 会员内容关键词 - 使用更精确的匹配
        # 分为高优先级（确定是会员内容）和低优先级（需要更多上下文）
        high_priority_keywords = [
            "members-only", "members only", "member-only", "member only",
            "membership exclusive", "premium members", "subscriber exclusive",
            "会员专属", "付费会员", "订阅者专属"
        ]
        
        low_priority_keywords = [
            "membership", "premium content",
            "exclusive access", "subscriber perks",
            "会员", "专属内容", "付费内容"
        ]

        # 先检查高优先级关键词（确定性强）
        for keyword in high_priority_keywords:
            if keyword in description.lower() or keyword in title.lower():
                log_with_context(
                    logger, logging.INFO,
                    "跳过会员内容",
                    video_id=video_id, title=video_title, keyword=keyword
                )
                return "会员专属内容"
        
        # 低优先级关键词只在描述中检查，不在标题中检查（减少误判）
        for keyword in low_priority_keywords:
            if keyword in description.lower():
                log_with_context(
                    logger, logging.INFO,
                    "跳过疑似会员内容",
                    video_id=video_id, title=video_title, keyword=keyword
                )
                return "会员专属内容"

        # 检查是否有会员相关字段
        if info_dict.get("availability") == "subscriber_only":
            log_with_context(
                logger, logging.INFO,
                "跳过会员专属视频",
                video_id=video_id, title=video_title
            )
            return "会员专属内容"

        # 检查是否为私人视频（会员视频通常标记为私人）
        if info_dict.get("availability") == "private":
            log_with_context(
                logger, logging.INFO,
                "跳过私人视频",
                video_id=video_id, title=video_title
            )
            return "私人视频"

        return None
    except Exception as e:
        logger.warning(f"会员过滤器错误: {e}")
        return None


def combined_filter(info_dict):
    """组合过滤器：同时应用时间过滤和会员内容过滤"""
    try:
        # 先检查会员内容过滤
        member_result = member_content_filter(info_dict)
        if member_result:
            logger.debug(f"过滤器跳过: {info_dict.get('title', '未知标题')} - {member_result}")
            return member_result

        # 再检查时间过滤
        time_result = oneday_filter(info_dict)
        if time_result:
            logger.debug(f"过滤器跳过: {info_dict.get('title', '未知标题')} - {time_result}")
            return time_result

        return None
    except Exception as e:
        logger.warning(f"组合过滤器错误: {e}")
        return None


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
                log_with_context(
                    logger, logging.INFO,
                    "发现最近视频",
                    title=info_dict.get('title', '未知标题'),
                    upload_time=upload_datetime.strftime('%Y-%m-%d %H:%M:%S')
                )
                return None
            return "视频超过3天"
            
        upload_date = info_dict.get("upload_date")
        if not upload_date:
            logger.debug(f"无法获取视频时间: {info_dict.get('title', '未知标题')}")
            return None
            
        naive_upload_datetime = datetime.datetime.strptime(upload_date, "%Y%m%d")
        upload_datetime = naive_upload_datetime.replace(tzinfo=datetime.timezone.utc)
        three_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=3
        )
        
        if upload_datetime > three_days_ago:
            log_with_context(
                logger, logging.INFO,
                "发现最近视频",
                title=info_dict.get('title', '未知标题'),
                upload_time=upload_datetime.strftime('%Y-%m-%d')
            )
            return None
        return "视频超过3天"
    except Exception as e:
        logger.warning(f"过滤器错误: {str(e)}")
        return None


def check_cookies():
    """检查cookies文件是否存在且有效"""
    if not os.path.exists(COOKIES_FILE):
        logger.error("未找到cookies文件！")
        logger.info("请按以下步骤操作：")
        logger.info("1. 安装Chrome扩展：'Cookie-Editor'")
        logger.info("2. 访问 YouTube 并确保已登录")
        logger.info("3. 点击Cookie-Editor扩展图标")
        logger.info("4. 点击'Export'按钮，选择'Netscape HTTP Cookie File'格式")
        logger.info("5. 将导出的内容保存到项目根目录下的 'youtube.cookies' 文件中")
        logger.info("6. 完成后重新运行程序")
        return False
    return True


def get_ydl_opts(custom_opts=None):
    # 确保音频文件夹存在
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)
        logger.info(f"已创建音频目录: {AUDIO_FOLDER}")

    # 使用 .tmp 后缀来标记正在下载的文件
    # FFmpeg后处理器会在outtmpl指定的文件名后自动添加扩展名，最终格式：filename.tmp.m4a
    base_opts = {
        "format": "bestaudio/best",
        "outtmpl": {
            'default': os.path.join(AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.%(ext)s.tmp"),
            'aac': os.path.join(AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.tmp"),  # FFmpeg会自动添加.m4a
        },
        "logger": TimestampedYTDLLogger(),  # 使用自定义日志格式
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "aac",
                "preferredquality": "64",
                "nopostoverwrites": False,
            }
        ],
        "keepvideo": False,  # 不保留原始视频文件
        "cookiefile": COOKIES_FILE,
        "sleep_interval": 88,
        "max_sleep_interval": 208,
        "random_sleep": True,
        "ignoreerrors": False,  # 改为False，让过滤器处理会员内容
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
                    # 进度信息使用 DEBUG 级别，避免日志过多
                    logger.debug(f"下载进度: {percent:.1f}% - {speed_mb:.1f}MB/s")
                else:
                    logger.debug(f"下载进度: {percent:.1f}%")
        except Exception:
            pass
    elif d['status'] == 'finished':
        logger.info(f"下载完成 (原始文件): {d.get('filename', '')}")
    elif d['status'] == 'already_downloaded':
        logger.info(f"已存在: {d.get('title', '')}")


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
        logger.info(f"已创建最终音频目录: {AUDIO_FOLDER}")

    custom_opts = {
        "download_archive": DOWNLOAD_ARCHIVE,
        "playlistend": 6,
        "match_filter": combined_filter,
        "keepvideo": False, 
    }
    
    ydl_opts = get_ydl_opts(custom_opts)
    
    # 统计信息
    stats = {
        'total': 0,
        'success': 0,
        'already_exists': 0,
        'filtered': 0,
        'archived': 0,
        'member_only': 0,
        'error': 0,
        'details': []
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            log_with_context(
                logger, logging.INFO,
                "开始获取频道视频列表",
                channel=channel_name
            )
            url = f"{yt_base_url}{channel_name}"
            channel_info = ydl.extract_info(url, download=False)
            if not channel_info or 'entries' not in channel_info:
                log_with_context(
                    logger, logging.WARNING,
                    "频道未找到视频或信息不完整",
                    channel=channel_name
                )
                return False

            entries_to_download = []
            if channel_info.get('_type') == 'playlist':
                for video_playlist_entry in channel_info.get('entries', []):
                    if video_playlist_entry and video_playlist_entry.get('_type') == 'playlist':
                        # 确保 entries 不为 None
                        nested_entries = video_playlist_entry.get('entries') or []
                        for video_in_playlist in nested_entries:
                             if video_in_playlist: entries_to_download.append(video_in_playlist)
                    elif video_playlist_entry:
                        entries_to_download.append(video_playlist_entry)
            else:
                entries_to_download = channel_info.get('entries') or []
            
            # 记录找到的视频总数
            stats['total'] = len(entries_to_download)
            log_with_context(
                logger, logging.INFO,
                "频道视频列表获取完成",
                channel=channel_name,
                total_videos=stats['total'],
                max_to_process=6
            )

            for idx, video_info in enumerate(entries_to_download, 1):
                video_url = video_info.get("webpage_url")
                video_title = video_info.get('title', '未知标题')
                video_id = video_info.get('id', 'unknown')
                
                if not video_url:
                    logger.debug(f"跳过条目，无URL: {video_title}")
                    stats['error'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'no_url',
                        'reason': '无视频URL'
                    })
                    continue

                log_with_context(
                    logger, logging.INFO,
                    "开始处理视频",
                    channel=channel_name,
                    video_index=f"{idx}/{stats['total']}",
                    title=video_title,
                    video_id=video_id,
                    url=video_url
                )
                
                uploader = video_info.get('uploader') or 'UnknownUploader'
                fulltitle = video_info.get('fulltitle') or video_info.get('title') or 'UnknownTitle'
                safe_title = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in fulltitle)
                safe_uploader = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in uploader)

                expected_audio_ext = ".m4a"
                final_audio_filename_stem = f"{safe_uploader}.{safe_title}"
                
                # 临时文件使用 .tmp 后缀
                # 注意：FFmpegExtractAudio 实际输出格式是 .m4a.tmp（不是.tmp.m4a）
                temp_audio_path_without_ext = os.path.join(AUDIO_FOLDER, final_audio_filename_stem)
                expected_temp_audio_path = temp_audio_path_without_ext + expected_audio_ext + ".tmp"

                # 正式文件路径（不带 .tmp）
                final_destination_audio_path = os.path.join(AUDIO_FOLDER, f"{final_audio_filename_stem}{expected_audio_ext}")

                if os.path.exists(final_destination_audio_path):
                    log_with_context(
                        logger, logging.INFO,
                        "音频文件已存在，跳过下载",
                        channel=channel_name,
                        video_index=f"{idx}/{stats['total']}",
                        title=video_title,
                        video_id=video_id,
                        file=os.path.basename(final_destination_audio_path)
                    )
                    stats['already_exists'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'already_exists',
                        'reason': '文件已存在'
                    })
                    continue
                
                current_video_ydl_opts = ydl_opts.copy()
                current_video_ydl_opts['outtmpl'] = {
                    'default': temp_audio_path_without_ext + '.%(ext)s.tmp',
                    'aac': temp_audio_path_without_ext + '.tmp'  # FFmpeg会自动添加.m4a
                }

                log_with_context(
                    logger, logging.DEBUG,
                    "下载路径配置",
                    temp_template=f"{temp_audio_path_without_ext}.%(ext)s.tmp",
                    expected_temp=expected_temp_audio_path,
                    final_destination=final_destination_audio_path
                )

                # 先检查过滤器（避免被过滤的视频被误报为下载失败）
                filter_result = combined_filter(video_info)
                if filter_result:
                    logger.debug(f"视频被过滤器跳过: {filter_result}")
                    stats['filtered'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'filtered',
                        'reason': filter_result
                    })
                    continue

                try:
                    with yt_dlp.YoutubeDL(current_video_ydl_opts) as video_ydl:
                        video_ydl.download([video_url]) 
                    
                    if os.path.exists(expected_temp_audio_path):
                        logger.info(f"转换后音频已下载（临时文件）: {expected_temp_audio_path}")
                        if safe_rename_file(expected_temp_audio_path, final_destination_audio_path):
                            file_size_mb = os.path.getsize(final_destination_audio_path) / (1024 * 1024)
                            log_with_context(
                                logger, logging.INFO,
                                "✅ 视频下载成功",
                                channel=channel_name,
                                video_index=f"{idx}/{stats['total']}",
                                title=video_title,
                                video_id=video_id,
                                file=os.path.basename(final_destination_audio_path),
                                size_mb=round(file_size_mb, 2)
                            )
                            stats['success'] += 1
                            stats['details'].append({
                                'index': idx,
                                'title': video_title,
                                'id': video_id,
                                'status': 'success',
                                'reason': '下载成功',
                                'size_mb': round(file_size_mb, 2)
                            })
                        else:
                            log_with_context(
                                logger, logging.ERROR,
                                "❌ 视频下载失败 - 文件重命名失败",
                                channel=channel_name,
                                video_index=f"{idx}/{stats['total']}",
                                title=video_title,
                                video_id=video_id
                            )
                            stats['error'] += 1
                            stats['details'].append({
                                'index': idx,
                                'title': video_title,
                                'id': video_id,
                                'status': 'error',
                                'reason': '文件重命名失败'
                            })
                    else:
                        log_with_context(
                            logger, logging.ERROR,
                            "❌ 视频下载失败 - 转换后文件未找到",
                            channel=channel_name,
                            video_index=f"{idx}/{stats['total']}",
                            title=video_title,
                            video_id=video_id,
                            expected_file=expected_temp_audio_path
                        )
                        original_downloaded_file_actual_ext = None
                        for ext_try in ['.webm', '.mp4', '.mkv', '.flv', '.avi', '.mov', '.opus', '.ogg', '.mp3']:
                            potential_orig_file = temp_audio_path_without_ext + ext_try + '.tmp'
                            if os.path.exists(potential_orig_file):
                                original_downloaded_file_actual_ext = ext_try
                                logger.warning(f"找到原始下载文件: {potential_orig_file}，但未转换为 {expected_audio_ext}")
                                break
                        if not original_downloaded_file_actual_ext:
                             logger.error(f"原始下载文件也未找到 (尝试的模板: {temp_audio_path_without_ext}.*.tmp)")
                        
                        stats['error'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'error',
                            'reason': '转换失败或文件未找到'
                        })

                except yt_dlp.utils.DownloadError as de:
                    error_str = str(de)
                    if "already been recorded in the archive" in error_str:
                        log_with_context(
                            logger, logging.INFO,
                            "视频已在存档中记录，跳过",
                            channel=channel_name,
                            video_index=f"{idx}/{stats['total']}",
                            title=video_title,
                            video_id=video_id
                        )
                        stats['archived'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'archived',
                            'reason': '已在存档中'
                        })
                    elif "members-only" in error_str or "member" in error_str or "premium" in error_str or "subscriber" in error_str:
                        log_with_context(
                            logger, logging.INFO,
                            "跳过会员专属视频",
                            channel=channel_name,
                            video_index=f"{idx}/{stats['total']}",
                            title=video_title,
                            video_id=video_id
                        )
                        stats['member_only'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'member_only',
                            'reason': '会员专属内容'
                        })
                    else:
                        log_with_context(
                            logger, logging.ERROR,
                            "❌ 视频下载失败 - yt-dlp错误",
                            channel=channel_name,
                            video_index=f"{idx}/{stats['total']}",
                            title=video_title,
                            video_id=video_id,
                            error=str(de)
                        )
                        stats['error'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'error',
                            'reason': f'yt-dlp错误: {str(de)[:100]}'
                        })
                    if os.path.exists(expected_temp_audio_path):
                        try: 
                            os.remove(expected_temp_audio_path)
                            logger.debug(f"已清理部分下载的音频文件: {expected_temp_audio_path}")
                        except OSError: pass
                    for ext_try in ['.webm', '.mp4', '.mkv']:
                        potential_orig_file = temp_audio_path_without_ext + ext_try + '.tmp'
                        if os.path.exists(potential_orig_file):
                            try:
                                os.remove(potential_orig_file)
                                logger.debug(f"已清理部分下载的视频文件: {potential_orig_file}")
                            except OSError: pass
                            break
                    continue
                except Exception as e:
                    log_with_context(
                        logger, logging.ERROR,
                        "❌ 视频下载失败 - 未知错误",
                        channel=channel_name,
                        video_index=f"{idx}/{stats['total']}",
                        title=video_title,
                        video_id=video_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    stats['error'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'error',
                        'reason': f'{type(e).__name__}: {str(e)[:100]}'
                    })
                    continue
            
            # 输出频道处理汇总
            log_with_context(
                logger, logging.INFO,
                "=" * 60 + "\n频道处理完成 - 汇总统计",
                channel=channel_name,
                total_videos=stats['total'],
                success=stats['success'],
                already_exists=stats['already_exists'],
                filtered=stats['filtered'],
                archived=stats['archived'],
                member_only=stats['member_only'],
                error=stats['error'],
                success_rate=f"{round(stats['success'] / max(stats['total'], 1) * 100, 1)}%"
            )
            
            # 输出详细列表
            if stats['details']:
                logger.info(f"\n{'='*60}")
                logger.info(f"详细列表 - {channel_name}")
                logger.info(f"{'='*60}")
                for detail in stats['details']:
                    status_icon = {
                        'success': '✅',
                        'already_exists': '📦',
                        'filtered': '🚫',
                        'archived': '📚',
                        'member_only': '🔒',
                        'error': '❌',
                        'no_url': '⚠️'
                    }.get(detail['status'], '❓')
                    
                    logger.info(
                        f"{status_icon} [{detail['index']:2d}] {detail['status']:15s} | "
                        f"{detail['title'][:50]:50s} | {detail['reason']}"
                    )
        
        except Exception as e:
            import traceback
            traceback_str = ''.join(traceback.format_tb(e.__traceback__))
            log_with_context(
                logger, logging.ERROR,
                "处理频道时发生错误",
                channel=channel_name,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback_str
            )
            if "HTTP Error 404" in str(e):
                logger.error(f"频道 {channel_name} 不存在或无法访问，请检查频道名称是否正确。")
            elif any(msg in str(e).lower() for msg in ["sign in to confirm", "unable to download api page", "not a bot", "consent"]):
                logger.error("Cookies可能已过期或需要同意YouTube政策！")
                logger.info("请按以下步骤更新cookies：")
                logger.info("1. (浏览器) 清除youtube.com的cookies，访问YouTube并确保已登录及处理任何弹窗。")
                logger.info("2. (浏览器) 使用Cookie-Editor导出新的cookies。")
                logger.info("3. 将新的cookies内容覆盖保存到 'youtube.cookies' 文件。")
                logger.info("4. 完成后按 Enter 键继续程序或重启程序。")
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
    log_with_context(
        logger, logging.INFO,
        "开始处理频道历史视频",
        channel=channel_name
    )
    if not check_cookies():
        return False
    
    ydl_opts = get_ydl_opts()
    logger.debug("已配置下载选项 (将使用临时目录)")
    
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
                        # 确保 entries 不为 None
                        nested_entries = entry_playlist.get('entries') or []
                        for video_in_playlist in nested_entries:
                             if video_in_playlist: processed_videos_for_closest.append(video_in_playlist)
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
                logger.warning("根据时间戳未找到合适视频")
                return False
            
            video_webpage_url = closest_video.get("webpage_url")
            if not video_webpage_url:
                logger.error(f"选定视频没有webpage_url: {closest_video.get('title', '未知')}")
                return False

            log_with_context(
                logger, logging.INFO,
                "选定要下载的历史视频",
                title=closest_video.get('title', '未知标题')
            )

            uploader = closest_video.get('uploader') or 'UnknownUploader'
            fulltitle = closest_video.get('fulltitle') or closest_video.get('title') or 'UnknownTitle'
            safe_title = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in fulltitle)
            safe_uploader = "".join(c if c.isalnum() or c in " .-_()" else "_" for c in uploader)
            expected_audio_ext = ".m4a"
            final_audio_filename_stem = f"{safe_uploader}.{safe_title}"

            # 临时文件使用 .tmp 后缀
            # 注意：FFmpegExtractAudio 实际输出格式是 .m4a.tmp（不是.tmp.m4a）
            temp_audio_path_without_ext = os.path.join(au_folder, final_audio_filename_stem)
            expected_temp_audio_path = temp_audio_path_without_ext + expected_audio_ext + ".tmp"
            final_destination_audio_path = os.path.join(au_folder, f"{final_audio_filename_stem}{expected_audio_ext}")

            if os.path.exists(final_destination_audio_path):
                logger.debug(f"最终音频文件已存在，跳过: {final_destination_audio_path}")
                timestamp_to_update = closest_video.get("timestamp", closest_video.get("upload_date"))
                if timestamp_to_update:
                    if isinstance(timestamp_to_update, str):
                         timestamp_to_update = int(datetime.datetime.strptime(timestamp_to_update, "%Y%m%d").timestamp())
                    update_channel_info_file(channel_name, timestamp_to_update, STORY_FILE)
                return True

            single_video_ydl_opts = ydl_opts.copy()
            single_video_ydl_opts['outtmpl'] = {
                'default': temp_audio_path_without_ext + '.%(ext)s.tmp',
                'aac': temp_audio_path_without_ext + '.tmp'  # FFmpeg会自动添加.m4a
            }
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
                else:
                    logger.error(f"历史视频重命名失败，跳过此文件")

                timestamp_to_update = closest_video.get("timestamp", closest_video.get("upload_date"))
                if timestamp_to_update:
                    if isinstance(timestamp_to_update, str):
                         timestamp_to_update = int(datetime.datetime.strptime(timestamp_to_update, "%Y%m%d").timestamp())
                    update_channel_info_file(channel_name, timestamp_to_update, STORY_FILE)
                return True
            else:
                logger.error(f"历史视频转换后的音频文件（临时文件）未找到: {expected_temp_audio_path}")
                return False
            
        except Exception as e:
            log_with_context(
                logger, logging.ERROR,
                "处理历史视频时发生错误",
                channel=channel_name,
                error=str(e)
            )
            return False


def read_and_process_channels(channels_file_path, au_folder):
    if not os.path.exists(channels_file_path):
        logger.error(f"No channel info file found at {channels_file_path}")
        return

    with open(channels_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        channel_name = parts[0]
        timestamp = int(parts[1]) if len(parts) > 1 else None

        log_with_context(
            logger, logging.INFO,
            "Processing channel",
            channel=channel_name,
            timestamp=timestamp
        )
        dl_audio_closest_after(AUDIO_FOLDER, channel_name, timestamp)
