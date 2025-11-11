# -*- coding: utf-8 -*-
import yt_dlp
import os
import datetime
import json
import sys
import time
import logging
import re
import copy
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
    get_video_delay_min,
    get_video_delay_max,
    get_filter_days,
    get_max_videos_per_channel,
    get_config_provider,
)
from logger import get_logger, log_with_context, TRACE_LEVEL
import random

# 使用统一的日志系统
logger = get_logger('downloader.dl_audio')


def _resolve_js_runtime_path(raw_path: str) -> str:
    """将用户输入的路径展开为绝对路径"""
    return os.path.abspath(
        os.path.expanduser(
            os.path.expandvars(raw_path)
        )
    )


def _detect_js_runtime():
    """
    检测可用的 JavaScript 运行时（默认为 Deno）
    - 支持通过环境变量 YT_DLP_JS_RUNTIME=runtime_name:/path/to/bin 覆盖
    - 默认回退到 ~/.deno/bin/deno(.exe)
    """
    runtime_override = os.environ.get("YT_DLP_JS_RUNTIME")
    if runtime_override:
        runtime_name, _, runtime_path = runtime_override.partition(':')
        runtime_name = (runtime_name or 'deno').strip()
        runtime_config = {runtime_name: {}}
        runtime_path = runtime_path.strip()
        if runtime_path:
            resolved = _resolve_js_runtime_path(runtime_path)
            if os.path.exists(resolved):
                runtime_config[runtime_name]['path'] = resolved
                logger.info(f"使用环境变量指定的 JavaScript 运行时: {runtime_name} -> {resolved}")
            else:
                logger.warning(f"环境变量 YT_DLP_JS_RUNTIME 指定的路径不存在: {resolved}")
        else:
            logger.trace(f"使用环境变量指定的 JavaScript 运行时: {runtime_name} (PATH 搜索)")
        return runtime_config

    home_dir = os.path.expanduser("~")
    deno_binary = os.path.join(
        home_dir,
        ".deno",
        "bin",
        "deno.exe" if os.name == "nt" else "deno"
    )
    if os.path.exists(deno_binary):
        logger.info(f"检测到 Deno 运行时，将用于解析 YouTube n signature: {deno_binary}")
        return {'deno': {'path': deno_binary}}

    logger.warning("未检测到可用的 JavaScript 运行时，YouTube 下载可能失败 (缺少 Deno/Node/Bun/QuickJS)")
    return None


JS_RUNTIME_CONFIG = _detect_js_runtime()


def apply_js_runtime(opts: dict) -> dict:
    """为 yt-dlp 配置注入统一的 JavaScript 运行时设置"""
    if JS_RUNTIME_CONFIG:
        opts['js_runtimes'] = copy.deepcopy(JS_RUNTIME_CONFIG)
    return opts


class TimestampedYTDLLogger:
    """自定义yt-dlp日志处理器，桥接到统一日志系统"""

    def __init__(self):
        self._logger = get_logger('downloader.yt-dlp')

    def _clean_message(self, msg):
        if msg is None:
            return ""
        text = str(msg).strip()
        if not text:
            return ""
        text = text.replace('[0;31m', '').replace('[0m', '')
        return re.sub(r'\x1b\[[0-9;]*m', '', text).strip()

    def _log_trace(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.trace(cleaned)

    def debug(self, msg):
        self._log_trace(msg)

    def info(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.info(cleaned)

    def warning(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.warning(cleaned)

    def error(self, msg):
        cleaned = self._clean_message(msg)
        if not cleaned:
            return
        lower = cleaned.lower()
        if 'members-only content' in lower or 'join this channel' in lower:
            # yt-dlp 提示会员专享内容，降级为 trace 以避免刷屏
            self._logger.trace(cleaned)
        else:
            self._logger.error(cleaned)

    def critical(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.critical(cleaned)

yt_base_url = "https://www.youtube.com/"

# 文件系统非法字符（Windows + Linux）
ILLEGAL_FILENAME_CHARS = '<>:"/\\|?*'


def sanitize_filename(filename: str) -> str:
    """
    智能清理文件名：
    - 保留所有可见字符（中文、英文、标点、表情、特殊符号等）
    - 只替换文件系统非法字符和不可见字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的安全文件名
    """
    result = []
    for char in filename:
        # 检查是否为文件系统非法字符
        if char in ILLEGAL_FILENAME_CHARS:
            result.append('_')
        # 检查是否为可打印字符（排除控制字符、零宽字符等不可见字符）
        elif char.isprintable():
            result.append(char)
        # 不可见字符替换为下划线
        else:
            result.append('_')
    
    return ''.join(result)


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


def record_download_entry(video_id: str, channel_name: Optional[str]) -> None:
    """
    ��¼������¼���������ṩ�ߣ�֧�ֱ��غ� Notion��
    """
    try:
        provider = get_config_provider()
        if provider is None:
            return

        has_check = getattr(provider, "has_download_record", None)
        if callable(has_check) and has_check(video_id):
            logger.trace(f"������浵��¼�Ѵ���: {video_id}")
            return

        add_record = getattr(provider, "add_download_record", None)
        if callable(add_record):
            success = add_record(video_id, channel_name or "unknown")
            if success:
                log_with_context(
                    logger, TRACE_LEVEL,
                    "�Ѽ�¼����浵",
                    video_id=video_id,
                    channel=channel_name
                )
            else:
                log_with_context(
                    logger, logging.WARNING,
                    "��¼����浵ʧ��",
                    video_id=video_id,
                    channel=channel_name
                )
    except Exception as err:
        log_with_context(
            logger, logging.ERROR,
            "��¼����浵����",
            video_id=video_id,
            channel=channel_name,
            error=str(err)
        )


def ensure_cookies_available() -> bool:
    """
    确保 cookies 文件可用：
    - notion 模式：每次启动都从 Notion 覆盖写入
    - local 模式：若本地存在则直接使用，否则尝试从 Notion 拉取
    """
    try:
        provider = get_config_provider()
    except Exception as err:
        logger.warning(f"获取配置提供者失败: {err}")
        provider = None

    is_notion_mode = provider and provider.__class__.__name__ == "NotionConfigProvider"

    if os.path.exists(COOKIES_FILE) and not is_notion_mode:
        return True

    if not provider:
        return os.path.exists(COOKIES_FILE)

    fetcher = getattr(provider, "get_cookies_content", None)
    if not callable(fetcher):
        return os.path.exists(COOKIES_FILE)

    try:
        content = fetcher()
    except Exception as err:
        logger.error(f"从 Notion 获取 cookies 失败: {err}")
        return os.path.exists(COOKIES_FILE)

    if not content or not content.strip():
        logger.warning("从 Notion 未获取到有效 cookies 数据")
        return os.path.exists(COOKIES_FILE)

    target_dir = os.path.dirname(COOKIES_FILE)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"已从 Notion 同步 cookies 至本地: {COOKIES_FILE}")
        return True
    except Exception as err:
        logger.error(f"写入 cookies 文件失败: {err}")
        return os.path.exists(COOKIES_FILE)


def member_content_filter(info_dict):
    """
    过滤会员专属内容
    
    策略：
    1. 几乎不预判，让 yt-dlp + cookies 决定能否下载
    2. 原因：
       - 用户可能购买了某些频道的会员
       - 有些主播会下放会员视频
       - cookies 中包含会员权限信息
    3. 只过滤明确的私人视频（这个确实下载不了）
    4. 下载失败时，再从错误信息判断是否为会员内容
    """
    try:
        video_id = info_dict.get("id", "")

        # 只过滤私人视频（这个确实无法下载）
        if info_dict.get("availability") == "private":
            logger.trace(f"⏭️ 跳过私人视频: {video_id}")
            return "私人视频"

        # 其他情况：允许尝试下载
        # 包括 subscriber_only，因为用户的 cookies 可能有会员权限
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
            logger.trace(f"过滤器跳过: {info_dict.get('title', '未知标题')} - {member_result}")
            return member_result

        # 再检查时间过滤
        time_result = oneday_filter(info_dict)
        if time_result:
            logger.trace(f"过滤器跳过: {info_dict.get('title', '未知标题')} - {time_result}")
            return time_result

        return None
    except Exception as e:
        logger.warning(f"组合过滤器错误: {e}")
        return None


def oneday_filter(info_dict):
    """过滤最近N天的视频（N从配置读取）"""
    try:
        timestamp = info_dict.get("timestamp")
        upload_datetime = None
        
        # 优先使用 timestamp
        if timestamp:
            upload_datetime = datetime.datetime.fromtimestamp(
                timestamp, tz=datetime.timezone.utc
            )
        # 回退到 upload_date
        elif info_dict.get("upload_date"):
            upload_date = info_dict.get("upload_date")
            naive_upload_datetime = datetime.datetime.strptime(upload_date, "%Y%m%d")
            upload_datetime = naive_upload_datetime.replace(tzinfo=datetime.timezone.utc)
        else:
            # 无时间信息，不过滤
            return None
            
        # 从配置读取过滤天数（支持热重载）
        filter_days = get_filter_days()
        days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=filter_days)
        
        if upload_datetime > days_ago:
            # 通过过滤（最近N天的视频）
            return None
        else:
            # 拒绝（超过N天）
            return f"视频超过{filter_days}天"
            
    except Exception as e:
        logger.warning(f"过滤器错误: {str(e)}")
        return None


def check_cookies():
    """检查cookies文件是否存在且有效"""
    if not os.path.exists(COOKIES_FILE):
        if ensure_cookies_available() and os.path.exists(COOKIES_FILE):
            return True
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
    # 注意：FFmpeg后处理器会替换文件扩展名，所以我们只用一个模板
    # 最终格式：filename.tmp.m4a (yt-dlp下载为filename.tmp，FFmpeg转换为filename.tmp.m4a)
    # 文件名格式：{video_id}.{title}.m4a（使用 id 而不是 uploader，便于记录和追踪）
    base_format = "bestvideo[height<=480][vcodec!=none]+bestaudio/best"
    base_opts = {
        "format": base_format,
        "outtmpl": os.path.join(AUDIO_FOLDER, "%(id)s.%(title)s.tmp"),
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
        "ignoreerrors": True,  # 跳过错误视频（如会员内容），继续处理其他视频
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
    
    base_opts = apply_js_runtime(base_opts)
    
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
                    logger.trace(f"下载进度: {percent:.1f}% - {speed_mb:.1f}MB/s")
                else:
                    logger.trace(f"下载进度: {percent:.1f}%")
        except Exception:
            pass
    elif d['status'] == 'finished':
        logger.trace(f"下载完成: {os.path.basename(d.get('filename', ''))}")
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
    
    # 使用指定的目录，如果未指定则使用默认目录
    target_folder = audio_folder if audio_folder else AUDIO_FOLDER
    
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        logger.info(f"已创建音频目录: {target_folder}")

    # 从配置读取最大视频数（支持热重载）
    max_videos = get_max_videos_per_channel()
    
    custom_opts = {
        "download_archive": DOWNLOAD_ARCHIVE,
        "playlistend": max_videos,
        "match_filter": combined_filter,
        "keepvideo": False,
        "outtmpl": os.path.join(target_folder, "%(uploader)s.%(id)s.%(title)s.%(ext)s"),  # 文件名格式：{频道名}.{video_id}.{title}.m4a
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
    
    # 第一步：获取视频列表（使用测试脚本中成功的配置）
    list_opts = {
        "quiet": True,
        "playlistend": max_videos,
        "cookiefile": COOKIES_FILE,
    }
    list_opts = apply_js_runtime(list_opts)
    
    with yt_dlp.YoutubeDL(list_opts) as list_ydl:
        try:
            log_context = {
                "channel": channel_name,
                "audio_folder": target_folder
            }
            if group_name:
                log_context["group"] = group_name
            
            log_with_context(
                logger, logging.INFO,
                "开始获取频道视频列表",
                **log_context
            )
            # YouTube频道结构变化：直接访问 /videos 页面获取视频列表
            url = f"{yt_base_url}{channel_name}/videos"
            logger.trace(f"访问URL: {url}")
            channel_info = list_ydl.extract_info(url, download=False)
            
            # 调试：打印 channel_info 的详细信息
            logger.info(f"[调试] channel_info 类型: {type(channel_info)}")
            logger.info(f"[调试] channel_info 是否为 None: {channel_info is None}")
            if channel_info:
                logger.info(f"[调试] channel_info 键: {list(channel_info.keys())[:10]}")
                logger.info(f"[调试] _type: {channel_info.get('_type')}")
                logger.info(f"[调试] 是否有 entries: {'entries' in channel_info}")
                if 'entries' in channel_info:
                    raw_entries = channel_info.get('entries')
                    logger.info(f"[调试] entries 类型: {type(raw_entries)}")
                    if raw_entries:
                        try:
                            entries_list = list(raw_entries) if hasattr(raw_entries, '__iter__') else []
                            logger.info(f"[调试] entries 长度: {len(entries_list)}")
                        except Exception as e:
                            logger.info(f"[调试] 无法转换 entries 为列表: {e}")
            
            if not channel_info or 'entries' not in channel_info:
                log_with_context(
                    logger, logging.WARNING,
                    "频道未找到视频或信息不完整",
                    channel=channel_name
                )
                return False

            # 处理返回的视频列表
            # 注意：不使用 extract_flat 时，entries 可能是 LazyList 或 generator
            entries_to_download = []
            raw_entries = channel_info.get('entries') if channel_info else []
            
            if raw_entries:
                # 将 entries 转换为列表（如果是 generator）
                for idx, entry in enumerate(raw_entries[:5]):  # 只看前5个
                    logger.info(f"[调试] Entry {idx}: type={type(entry)}, is_dict={isinstance(entry, dict)}, is_none={entry is None}")
                    if entry:
                        logger.info(f"[调试] Entry {idx} keys: {list(entry.keys())[:10] if isinstance(entry, dict) else 'N/A'}")
                
                for entry in raw_entries:
                    if entry and isinstance(entry, dict):
                        entries_to_download.append(entry)
                        # 只获取 max_videos 个
                        if len(entries_to_download) >= max_videos:
                            break
            
            logger.trace(f"频道返回 {len(entries_to_download)} 个有效视频")
            
            # 记录找到的视频总数
            stats['total'] = len(entries_to_download)
            log_with_context(
                logger, logging.INFO,
                "频道视频列表获取完成",
                channel=channel_name,
                total_videos=stats['total'],
                max_to_process=max_videos
            )

            for idx, video_info in enumerate(entries_to_download, 1):
                video_title = video_info.get('title', '未知标题')
                video_id = video_info.get('id', 'unknown')
                
                # 使用 extract_flat 后，webpage_url 可能缺失，需要从 id 构建
                video_url = video_info.get("webpage_url")
                if not video_url and video_id and video_id != 'unknown':
                    # 从 video_id 构建完整的 YouTube URL
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    logger.trace(f"从 video_id 构建 URL: {video_url}")
                
                if not video_url:
                    logger.trace(f"跳过条目，无URL且无ID: {video_title}")
                    stats['error'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'no_url',
                        'reason': '无视频URL'
                    })
                    continue

                # 获取上传时间（用于日志和过滤）
                upload_date_str = "未知"
                if video_info.get('timestamp'):
                    upload_dt = datetime.datetime.fromtimestamp(video_info.get('timestamp'), tz=datetime.timezone.utc)
                    upload_date_str = upload_dt.strftime('%m-%d')
                elif video_info.get('upload_date'):
                    upload_date_str = video_info.get('upload_date')[4:]  # 取月日部分 MMDD
                    upload_date_str = f"{upload_date_str[:2]}-{upload_date_str[2:]}"
                
                log_with_context(
                    logger, TRACE_LEVEL,
                    f"检查视频 [{idx}/{stats['total']}] {video_id}",
                    channel=channel_name,
                    title=video_title[:60] + "..." if len(video_title) > 60 else video_title,
                    upload_date=upload_date_str
                )
                
                # 应用过滤器（日期过滤、会员内容过滤等）
                filter_result = combined_filter(video_info)
                if filter_result:
                    logger.trace(f"⏭️ 跳过视频（{filter_result}）: {video_title[:40]}")
                    stats['filtered'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'filtered',
                        'reason': filter_result
                    })
                    continue
                
                # 构建文件名：{频道名}.{video_id}.{title}.m4a
                uploader = video_info.get('uploader') or video_info.get('channel') or channel_name or 'UnknownChannel'
                safe_uploader = sanitize_filename(uploader)
                
                fulltitle = video_info.get('fulltitle') or video_info.get('title') or 'UnknownTitle'
                safe_title = sanitize_filename(fulltitle)
                
                expected_audio_ext = ".m4a"
                final_audio_filename_stem = f"{safe_uploader}.{video_id}.{safe_title}"
                
                temp_audio_path_without_ext = os.path.join(target_folder, final_audio_filename_stem)
                expected_temp_audio_path = temp_audio_path_without_ext + ".tmp" + expected_audio_ext
                possible_temp_paths = [
                    expected_temp_audio_path,
                    temp_audio_path_without_ext + expected_audio_ext,
                ]

                # 正式文件路径（不带 .tmp）
                final_destination_audio_path = os.path.join(target_folder, f"{final_audio_filename_stem}{expected_audio_ext}")

                if os.path.exists(final_destination_audio_path):
                    log_with_context(
                        logger, logging.INFO,
                        f"⏭️  跳过 {video_id} (文件已存在)",
                        channel=channel_name
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
                # FFmpeg后处理器会将 filename.tmp 转换为 filename.tmp.m4a
                current_video_ydl_opts['outtmpl'] = temp_audio_path_without_ext + '.tmp'

                log_with_context(
                    logger, TRACE_LEVEL,
                    "下载路径配置",
                    temp_template=f"{temp_audio_path_without_ext}.tmp",
                    expected_temp=expected_temp_audio_path,
                    final_destination=final_destination_audio_path
                )

                # 先检查过滤器（避免被过滤的视频被误报为下载失败）
                filter_result = combined_filter(video_info)
                if filter_result:
                    log_with_context(
                        logger, TRACE_LEVEL,
                        f"⏭️ 跳过 {video_id} ({filter_result})",
                        channel=channel_name
                    )
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
                    
                    temp_audio_path = next((p for p in possible_temp_paths if os.path.exists(p)), None)
                    if temp_audio_path:
                        logger.trace(f"转换完成: {os.path.basename(temp_audio_path)}")
                        if os.path.normcase(temp_audio_path) == os.path.normcase(final_destination_audio_path):
                            rename_ok = True
                        else:
                            rename_ok = safe_rename_file(temp_audio_path, final_destination_audio_path)

                        if rename_ok:
                            file_size_mb = os.path.getsize(final_destination_audio_path) / (1024 * 1024)
                            log_with_context(
                                logger, logging.INFO,
                                f"✅ 下载成功 {video_id}",
                                channel=channel_name,
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

                            record_download_entry(video_id, channel_name)

                            # 视频间延迟（如果不是最后一个视频）
                            if idx < stats['total']:
                                video_delay_min = get_video_delay_min()
                                video_delay_max = get_video_delay_max()
                                if video_delay_max > 0:  # 只在配置了延迟时才执行
                                    delay = random.uniform(video_delay_min, video_delay_max)
                                    log_with_context(
                                        logger, logging.INFO,
                                        f"⏳ 等待 {round(delay)}秒",
                                        channel=channel_name
                                    )
                                    time.sleep(delay)
                        else:
                            log_with_context(
                                logger, logging.ERROR,
                                f"❌ 重命名失败 {video_id}",
                                channel=channel_name
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
                            f"❌ 转换失败 {video_id} (文件未找到)",
                            channel=channel_name
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
                            f"🔒 会员专属 {video_id} (下载被拒绝)",
                            channel=channel_name
                        )
                        stats['member_only'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'member_only',
                            'reason': '会员专属内容（下载时确认）'
                        })
                    elif "premieres in" in error_str.lower() or "premiere" in error_str.lower():
                        # YouTube Premiere（首映）视频，尚未到首映时间
                        premiere_info = error_str.split(":")[-1].strip() if ":" in error_str else "待首映"
                        log_with_context(
                            logger, logging.INFO,
                            f"⏰ 待首映 {video_id}",
                            channel=channel_name,
                            premiere_info=premiere_info
                        )
                        stats['filtered'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'premiere',
                            'reason': f'待首映: {premiere_info}'
                        })
                    else:
                        # 简短的错误信息
                        error_msg = str(de)[:100] if len(str(de)) > 100 else str(de)
                        log_with_context(
                            logger, logging.ERROR,
                            f"❌ 下载失败 {video_id}",
                            channel=channel_name,
                            error=error_msg
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
                            logger.trace(f"已清理部分下载的音频文件: {expected_temp_audio_path}")
                        except OSError: pass
                    for ext_try in ['.webm', '.mp4', '.mkv']:
                        potential_orig_file = temp_audio_path_without_ext + ext_try + '.tmp'
                        if os.path.exists(potential_orig_file):
                            try:
                                os.remove(potential_orig_file)
                                logger.trace(f"已清理部分下载的视频文件: {potential_orig_file}")
                            except OSError: pass
                            break
                    continue
                except Exception as e:
                    error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
                    log_with_context(
                        logger, logging.ERROR,
                        f"❌ 未知错误 {video_id}",
                        channel=channel_name,
                        error_type=type(e).__name__,
                        error=error_msg
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
                f"✅ 频道处理完成",
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
            
            # 详细列表信息已通过每个视频的独立日志输出，此处不再重复输出
            # 格式化的文本列表不适合 JSON 结构化日志
        
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            
            # 检查是否为直播预告（还未开始的直播）
            if "live event will begin in" in error_str.lower():
                logger.info(f"频道 {channel_name} 包含直播预告视频，稍后自动下载")
                return True  # 不算错误，返回成功
            
            # 检查是否为 YouTube Premiere（首映）视频
            if "premieres in" in error_str.lower() or "premiere" in error_str.lower():
                logger.info(f"频道 {channel_name} 包含待首映视频，稍后自动下载")
                return True  # 不算错误，返回成功
            
            # 检查是否为会员专属内容错误（频道视频都是会员内容时会在获取列表阶段就报错）
            if ("members-only" in error_str.lower() or 
                ("member" in error_str.lower() and "join this channel" in error_str.lower())):
                log_with_context(
                    logger, logging.INFO,
                    f"⏭️ 频道当前视频为会员专属，跳过",
                    channel=channel_name
                )
                return True  # 不算错误，只是暂时没有可下载内容
            
            # 记录实际错误（不包含 traceback，避免日志过长）
            # 只保留错误消息的前200个字符
            error_msg = error_str[:200] if len(error_str) > 200 else error_str
            log_with_context(
                logger, logging.ERROR,
                f"❌ 处理频道失败",
                channel=channel_name,
                error_type=error_type,
                error=error_msg
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

            video_id_history = closest_video.get('id', 'unknown_id')
            
            log_with_context(
                logger, logging.INFO,
                "选定要下载的历史视频",
                video_id=video_id_history,
                title=closest_video.get('title', '未知标题')
            )

            # 构建文件名：{频道名}.{video_id}.{title}.m4a
            uploader = closest_video.get('uploader') or closest_video.get('channel') or channel_name or 'UnknownChannel'
            safe_uploader = sanitize_filename(uploader)
            
            fulltitle = closest_video.get('fulltitle') or closest_video.get('title') or 'UnknownTitle'
            safe_title = sanitize_filename(fulltitle)
            expected_audio_ext = ".m4a"
            final_audio_filename_stem = f"{safe_uploader}.{video_id_history}.{safe_title}"

            # 临时文件格式：filename.tmp.m4a (yt-dlp下载为filename.tmp，FFmpeg转换为filename.tmp.m4a)
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
            # FFmpeg后处理器会将 filename.tmp 转换为 filename.tmp.m4a
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
