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
from pathlib import Path
import random
# 使用统一的日志系统
logger = get_logger('downloader.dl_audio')

_download_archive_cache = {
    "mtime": None,
    "entries": set(),
}

def cleanup_incomplete_downloads(folder: str, force: bool = False) -> int:
    """
    删除音频目录中残留的 .tmp/.part 等未完成下载文件，避免下次继续下载报 416。
    
    Args:
        folder: 要清理的目录
        force: 是否强制清理（True=总是清理，False=只记录日志但总是执行清理）
    """
    if not folder:
        return 0
    abs_folder = os.path.abspath(folder)
    path = Path(abs_folder)
    if not path.exists():
        return 0

    removed = 0
    for entry in path.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        if (
            name.endswith('.tmp')
            or '.tmp.' in name
            or name.endswith('.part')
            or name.endswith('.ytdl')
        ):
            try:
                entry.unlink()
                removed += 1
            except OSError:
                continue

    if removed:
        log_with_context(
            logger, logging.INFO,
            "🧹 清理未完成的下载残留",
            audio_folder=abs_folder,
            removed_files=removed
        )

    return removed


def cleanup_partial_files_for_base(base_path: str) -> int:
    """
    删除某个视频对应的残留 .tmp/.part 文件。
    """
    if not base_path:
        return 0
    path = Path(base_path)
    parent = path.parent
    if not parent.exists():
        return 0
    prefix = path.name
    removed = 0
    for entry in parent.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        if not name.startswith(prefix):
            continue
        if '.tmp' in name or name.endswith('.part'):
            try:
                entry.unlink()
                removed += 1
            except OSError:
                continue
    return removed


def _load_download_archive() -> set:
    """
    读取 download archive 并缓存结果，避免每次都重新加载大文件
    """
    path = DOWNLOAD_ARCHIVE
    if not path:
        return set()
    video_title = None  # 用于异常分支的安全引用
    video_id = None
    try:
        current_mtime = os.path.getmtime(path)
    except (FileNotFoundError, OSError):
        return set()

    cached_mtime = _download_archive_cache.get("mtime")
    if cached_mtime == current_mtime:
        return _download_archive_cache.get("entries", set())

    entries = set()
    try:
        with open(path, "r", encoding="utf-8") as archive_file:
            for line in archive_file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if not parts:
                    continue
                video_id = parts[-1]
                entries.add(video_id)
    except Exception:
        # 出现异常时不更新缓存，避免使用不完整数据
        return _download_archive_cache.get("entries", set())

    _download_archive_cache["mtime"] = current_mtime
    _download_archive_cache["entries"] = entries
    return entries


def is_video_in_download_archive(video_id: str) -> bool:
    """
    判断指定视频 ID 是否已经记录在 download archive 中
    """
    if not video_id:
        return False
    entries = _load_download_archive()
    return video_id in entries


def _resolve_js_runtime_path(raw_path: str) -> str:
    """将用户输入的路径展开为绝对路径"""
    return os.path.abspath(
        os.path.expanduser(
            os.path.expandvars(raw_path)
        )
    )


def _detect_js_runtime():
    """
    检测可用的 JavaScript 运行时
    - 支持通过环境变量 YT_DLP_JS_RUNTIME=runtime_name:/path/to/bin 覆盖
    - 优先检测 Deno (~/.deno/bin/deno)
    - 其次检测 Node (PATH 中的 node 命令)
    """
    import shutil
    
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

    # 1. 优先检测 Deno
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
    
    # 2. 检测 PATH 中的 Node.js（需要 Node 20.0.0+）
    node_path = shutil.which("node")
    if node_path:
        logger.info(f"检测到 Node.js 运行时，将用于解析 YouTube n signature: {node_path}")
        return {'node': {'path': node_path}}
    
    # 3. 检测 PATH 中的 Deno
    deno_path = shutil.which("deno")
    if deno_path:
        logger.info(f"检测到 Deno 运行时 (PATH)，将用于解析 YouTube n signature: {deno_path}")
        return {'deno': {'path': deno_path}}

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
        text = re.sub(r'\x1b\[[0-9;]*m', '', text).strip()
        text = re.sub(r'^(ERROR|WARNING|INFO)\s*:\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\[download\]\s+', '', text, flags=re.IGNORECASE)
        return text

    def _is_progress_message(self, text: str) -> bool:
        """
        yt-dlp 会用 [download] xxx% ... 每次回调都刷一条，这里直接丢弃，避免日志被进度刷屏。
        """
        return bool(re.match(r'^\\[download\\]\\s+\\d+(?:\\.\\d+)?%\\b', text))

    def _log_trace(self, msg):
        # 提升默认日志级别到 INFO：忽略 yt-dlp 的 debug/trace 输出
        return

    def debug(self, msg):
        self._log_trace(msg)

    def info(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.info(cleaned)

    def warning(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.warning(f'⚠️ yt-dlp: {cleaned}')

    def error(self, msg):
        cleaned = self._clean_message(msg)
        if not cleaned:
            return
        lower = cleaned.lower()
        if 'members-only content' in lower or 'join this channel' in lower:
            # yt-dlp 提示会员专属内容，降级为 trace 以免刷屏
            self._logger.trace(cleaned)
        else:
            self._logger.error(f'❌ yt-dlp: {cleaned}')

    def critical(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.critical(cleaned)

yt_base_url = "https://www.youtube.com/"

# 文件系统非法字符（Windows + Linux）
ILLEGAL_FILENAME_CHARS = '<>:"/\\|?*'

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
PREFERRED_YT_EXTRACTOR_ARGS = {'youtube': {'lang': ['zh-TW']}}


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
    把成功下载的视频记录到配置提供者（本地/Notion），避免重复下载。
    """
    try:
        provider = get_config_provider()
        if provider is None:
            return

        has_check = getattr(provider, "has_download_record", None)
        if callable(has_check) and has_check(video_id):
            logger.trace(f"下载存档记录已存在: {video_id}")
            return

        add_record = getattr(provider, "add_download_record", None)
        if callable(add_record):
            success = add_record(video_id, channel_name or "unknown")
            if success:
                log_with_context(
                    logger, TRACE_LEVEL,
                    "已记录下载存档",
                    video_id=video_id,
                    yt_channel=channel_name
                )
            else:
                log_with_context(
                    logger, logging.WARNING,
                    "记录下载存档失败",
                    video_id=video_id,
                    yt_channel=channel_name
                )
    except Exception as err:
        log_with_context(
            logger, logging.ERROR,
            "记录下载存档异常",
            video_id=video_id,
            yt_channel=channel_name,
            error=str(err)
        )


def sync_download_archive():
    """从 Provider 同步已下载记录到本地文件，供 yt-dlp 使用"""
    try:
        provider = get_config_provider()
        if not provider:
            return

        # 检查是否是 NotionConfigProvider (只有 Notion 模式需要同步)
        if provider.__class__.__name__ != 'NotionConfigProvider':
            return

        # 获取 Notion 记录 (利用私有方法或缓存)
        # 注意: 这里假设 Provider 实现了 _load_download_archive 返回 set
        fetch_method = getattr(provider, "_load_download_archive", None)
        if not callable(fetch_method):
            return

        notion_records = fetch_method()
        if not notion_records:
            return

        # 读取本地文件记录
        local_records = set()
        if os.path.exists(DOWNLOAD_ARCHIVE):
            try:
                with open(DOWNLOAD_ARCHIVE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                             parts = line.split()
                             if parts:
                                 local_records.add(parts[-1])
            except Exception:
                pass
        
        # 找出差异 (Notion 有但本地没有的)
        new_records = notion_records - local_records
        
        if new_records:
            logger.info(f"📥 从 Notion 同步了 {len(new_records)} 条下载历史到本地 Archive")
            # 确保目录存在
            os.makedirs(os.path.dirname(DOWNLOAD_ARCHIVE), exist_ok=True)
            with open(DOWNLOAD_ARCHIVE, 'a', encoding='utf-8') as f:
                for vid in new_records:
                    f.write(f"youtube {vid}\n")
                    
    except Exception as e:
        logger.warning(f"同步下载存档失败: {e}")


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
        # 如果是 Notion 模式但没配 Cookies，可能是有意的？
        # 但我们还是检查本地有没有，有就用
        if is_notion_mode and not os.path.exists(COOKIES_FILE):
             logger.warning("Notion 中未配置 Cookies，且本地无 Cookies 文件，下载可能会受限")
        return os.path.exists(COOKIES_FILE)

    target_dir = os.path.dirname(COOKIES_FILE)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"🍪 已从 Notion 同步 Cookies 至本地: {COOKIES_FILE}")
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


def shorts_filter(info_dict):
    """过滤 YouTube Shorts（短视频）"""
    try:
        video_id = info_dict.get('id', '')

        # 通过 URL 判断：yt-dlp 对 Shorts 的 webpage_url 包含 /shorts/
        url = info_dict.get('webpage_url') or info_dict.get('url') or ''
        if '/shorts/' in url:
            logger.trace(f"⏭️ 跳过 Shorts（URL含/shorts/）: {video_id}")
            return "YouTube Shorts"

        # 通过时长判断：Shorts 定义为 ≤ 60 秒
        # 注意：extract_flat=True 时 duration 可能为 None，None 时不过滤
        duration = info_dict.get('duration')
        if duration is not None and duration <= 60:
            logger.trace(f"⏭️ 跳过 Shorts（时长{duration}s≤60s）: {video_id}")
            return "YouTube Shorts (时长≤60s)"

        return None
    except Exception as e:
        logger.warning(f"Shorts过滤器错误: {e}")
        return None


def combined_filter(info_dict):
    """组合过滤器：同时应用时间过滤、Shorts过滤和会员内容过滤"""
    try:
        # 先检查 Shorts 过滤
        shorts_result = shorts_filter(info_dict)
        if shorts_result:
            return shorts_result

        # 再检查会员内容过滤
        member_result = member_content_filter(info_dict)
        if member_result:
            return member_result

        # 再检查时间过滤
        time_result = oneday_filter(info_dict)
        if time_result:
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
    # 总是尝试调用 ensure_cookies_available，让它内部决定是否需要从 Notion 拉取
    if ensure_cookies_available():
        return True
        
    if not os.path.exists(COOKIES_FILE):
        logger.error(f"未找到cookies文件！预期路径: {COOKIES_FILE}")
        logger.info("请按以下步骤操作：")
        logger.info("1. 安装Chrome扩展：'Cookie-Editor'")
        logger.info("2. 访问 YouTube 并确保已登录")
        logger.info("3. 点击Cookie-Editor扩展图标")
        logger.info("4. 点击'Export'按钮，选择'Netscape HTTP Cookie File'格式")
        logger.info(f"5. 将导出的内容保存到文件: {COOKIES_FILE}")
        logger.info("6. 完成后重新运行程序")
        return False
    return True


def get_ydl_opts(custom_opts=None):
    # 确保音频文件夹存在
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)
        logger.info(f"已创建音频目录: {AUDIO_FOLDER}")
    cleanup_incomplete_downloads(AUDIO_FOLDER)

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
                "preferredcodec": "m4a",  # 使用 MP4/M4A 容器，确保时长元数据准确
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
        # 跳过 yt-dlp 下载中间产生的 .tmp.fXXX 片段日志，避免重复噪音
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
    
    # 清理目标目录中的残留临时文件
    cleanup_incomplete_downloads(target_folder)
    
    # 同步 Notion 中的下载历史到本地 Archive (供 yt-dlp 去重)
    sync_download_archive()

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
    # 兜底初始化，防止在拉取列表阶段异常时未赋值就被引用
    video_title = None
    video_id = None
    
    # 第一步：获取视频列表 - 依次从 /videos（普通视频）和 /streams（直播录播）获取，合并去重
    list_opts = {
        "quiet": True,
        "playlistend": max_videos,
        "cookiefile": COOKIES_FILE,
        "extract_flat": True,
        "http_headers": PREFERRED_HTTP_HEADERS,
        "extractor_args": PREFERRED_YT_EXTRACTOR_ARGS,
    }
    list_opts = apply_js_runtime(list_opts)
    
    with yt_dlp.YoutubeDL(list_opts) as list_ydl:
        try:
            channel_display_name = None
            entries_to_download = []
            seen_ids: set = set()
            tab_counts = {}  # 记录每个 tab 的条目数，供汇总日志使用

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

                # 从第一个成功的请求中提取频道显示名
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

            entries_count = len(entries_to_download)
            log_with_context(logger, logging.INFO, "频道信息获取完成",
                yt_channel=channel_name, display_name=channel_display_name,
                entries_count=entries_count,
                from_videos=tab_counts.get('videos', 0),
                from_streams=tab_counts.get('streams', 0))

            # 如果没有有效条目，记录警告
            if not entries_to_download:
                log_with_context(
                    logger, logging.WARNING,
                    "频道视频列表为空或全部无效",
                    yt_channel=channel_name
                )
                return True  # 不算错误，可能是新频道或视频都被删了

            # 记录找到的视频总数
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
                
                # 应用过滤器（日期过滤、会员内容过滤等）；命中过滤时直接记录跳过原因。
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
                    stats['filtered'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'filtered',
                        'reason': filter_result
                    })
                    continue

                # 文件存在性检查：用 video_id 匹配，而非精确文件名。
                # 标题语言由 yt-dlp 完整下载阶段（extractor_args lang=zh-TW 生效）决定，
                # extract_flat 阶段的 lang 参数不可靠，不在此预计算文件名。
                expected_audio_ext = ".m4a"
                try:
                    existing_files = [
                        f for f in os.listdir(target_folder)
                        if f'.{video_id}.' in f and f.endswith(expected_audio_ext) and '.tmp' not in f
                    ]
                except OSError:
                    existing_files = []

                if existing_files:
                    log_with_context(
                        logger, TRACE_LEVEL,
                        f"⏭️  文件已存在，跳过 {video_id}",
                        yt_channel=channel_name
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

                if is_video_in_download_archive(video_id):
                    stats['archived'] += 1
                    stats['details'].append({
                        'index': idx,
                        'title': video_title,
                        'id': video_id,
                        'status': 'archived',
                        'reason': 'archive_hit_no_file'
                    })
                    continue
                
                current_video_ydl_opts = ydl_opts.copy()
                # 使用 %(title)s 模板：让 yt-dlp 在完整提取阶段（extractor_args lang=zh-TW 生效）
                # 决定标题语言，避免 extract_flat=True 阶段 lang 不生效导致英文标题写入文件名。
                # FFmpeg后处理器会将 filename.tmp 转换为 filename.tmp.m4a
                current_video_ydl_opts['outtmpl'] = os.path.join(
                    target_folder, "%(uploader)s.%(id)s.%(title)s.tmp"
                )
                # 捕获实际下载文件路径（完整提取时 lang=zh-TW 生效，title 将是中文）
                downloaded_file_info = {"path": None}
                def per_video_progress_hook(d, _info=downloaded_file_info):
                    if d['status'] == 'finished':
                        path = d.get('filename', '')
                        if path and '.tmp.f' not in os.path.basename(path):
                            _info["path"] = path
                current_video_ydl_opts['progress_hooks'] = list(
                    current_video_ydl_opts.get('progress_hooks', [])
                ) + [per_video_progress_hook]

                # 先检查过滤器（避免被过滤的视频被误报为下载失败）
                # 注意：extract_flat=True 时，video_info 可能缺少 timestamp/upload_date
                # 如果缺少日期信息，跳过此处的手动过滤，让 yt-dlp 在 download 内部获取完整信息后通过 match_filter 过滤
                has_date_info = video_info.get('timestamp') is not None or video_info.get('upload_date') is not None
                
                if has_date_info:
                    filter_result = combined_filter(video_info)
                    if filter_result:
                        log_with_context(
                            logger, TRACE_LEVEL,
                            f"⏭️ 跳过 {video_id} ({filter_result})",
                            yt_channel=channel_name
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
                else:
                    # 没有日期信息，无法在下载前过滤，交由 video_ydl.download 处理
                    # 但我们需要注意，如果 video_ydl.download 过滤了视频，会抛出 DownloadError 还是静默？
                    # 通常 match_filter 返回 string 会导致 "Video ... does not pass filter" 并抛出 DownloadError (或 warning)
                    pass

                # 用于追踪 yt-dlp 下载过程中是否遇到会员/权限问题或被过滤
                download_context = {
                    'member_blocked': False,
                    'error_reason': None,
                    'filtered': False,
                    'filter_reason': None
                }
                
                # 包装 yt-dlp logger 以捕获会员相关错误和过滤消息
                class ContextAwareYTDLLogger(TimestampedYTDLLogger):
                    def warning(self, msg):
                        cleaned = self._clean_message(msg)
                        if not cleaned:
                            return
                        # 检测 match_filter 过滤消息
                        # yt-dlp 格式: "[download] Video ... does not pass filter: <reason>"
                        if 'does not pass filter' in cleaned.lower():
                            download_context['filtered'] = True
                            # 提取过滤原因
                            if ':' in cleaned:
                                download_context['filter_reason'] = cleaned.split(':', 1)[-1].strip()
                            else:
                                download_context['filter_reason'] = '被日期过滤器拦截'
                            # 降级为 trace，不刷屏（这是预期行为）
                            self._logger.trace(f"⏭️ {cleaned}")
                        else:
                            self._logger.warning(f'⚠️ yt-dlp: {cleaned}')
                    
                    def error(self, msg):
                        cleaned = self._clean_message(msg)
                        if not cleaned:
                            return
                        lower = cleaned.lower()
                        # 检测会员/订阅相关错误
                        if any(kw in lower for kw in ['members-only', 'member', 'join this channel', 'subscriber', 'premium']):
                            download_context['member_blocked'] = True
                            download_context['error_reason'] = '会员专属内容'
                            # 降级为 trace，不刷屏
                            self._logger.trace(f"🔒 {cleaned}")
                        elif 'requested format is not available' in lower and download_context.get('member_blocked'):
                            # 格式不可用可能是会员限制的结果，静默处理
                            self._logger.trace(cleaned)
                        else:
                            self._logger.error(f'❌ yt-dlp: {cleaned}')
                
                current_video_ydl_opts['logger'] = ContextAwareYTDLLogger()
                
                try:
                    with yt_dlp.YoutubeDL(current_video_ydl_opts) as video_ydl:
                        video_ydl.download([video_url])

                    # 优先使用 progress hook 捕获的路径；否则按 video_id 扫描目录
                    temp_audio_path = downloaded_file_info.get("path")
                    if not temp_audio_path or not os.path.exists(temp_audio_path):
                        temp_audio_path = None
                        try:
                            for fname in os.listdir(target_folder):
                                if f'.{video_id}.' in fname and fname.endswith('.tmp.m4a'):
                                    temp_audio_path = os.path.join(target_folder, fname)
                                    break
                        except OSError:
                            pass

                    if temp_audio_path and os.path.exists(temp_audio_path):
                        logger.trace(f"转换完成: {os.path.basename(temp_audio_path)}")
                        # 最终文件名：去掉 stem 中的 .tmp（e.g., XXX.tmp.m4a → XXX.m4a）
                        final_destination_audio_path = re.sub(r'\.tmp(\.m4a)$', r'\1', temp_audio_path)
                        if os.path.normcase(temp_audio_path) == os.path.normcase(final_destination_audio_path):
                            rename_ok = True
                        else:
                            rename_ok = safe_rename_file(temp_audio_path, final_destination_audio_path)

                        if rename_ok:
                            file_size_mb = os.path.getsize(final_destination_audio_path) / (1024 * 1024)
                            log_with_context(
                                logger, logging.INFO,
                                f"✅ 下载成功 {video_id}",
                                yt_channel=channel_name,
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
                                        "⏳ 视频间延迟",
                                        yt_channel=channel_name,
                                        delay_seconds=round(delay, 2),
                                        current_video=idx,
                                        total_videos=stats['total']
                                    )
                                    time.sleep(delay)
                        else:
                            log_with_context(
                                logger, logging.ERROR,
                                f"❌ 重命名失败 {video_id}",
                                yt_channel=channel_name
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
                        # 文件未找到：检查是否是被过滤或会员内容导致的静默跳过
                        if download_context.get('filtered'):
                            # 视频被 match_filter 过滤（如超出日期范围），这是预期行为
                            filter_reason = download_context.get('filter_reason', '被过滤器拦截')
                            log_with_context(
                                logger, TRACE_LEVEL,
                                f"⏭️ 跳过已过滤视频 {video_id}",
                                yt_channel=channel_name,
                                reason=filter_reason
                            )
                            stats['filtered'] += 1
                            stats['details'].append({
                                'index': idx,
                                'title': video_title,
                                'id': video_id,
                                'status': 'filtered',
                                'reason': filter_reason
                            })
                        elif download_context.get('member_blocked'):
                            # 会员内容被静默跳过，这是预期行为，用 DEBUG 级别记录
                            log_with_context(
                                logger, TRACE_LEVEL,
                                f"🔒 跳过会员视频 {video_id}",
                                yt_channel=channel_name,
                                reason=download_context.get('error_reason', '会员专属内容')
                            )
                            stats['member_only'] += 1
                            stats['details'].append({
                                'index': idx,
                                'title': video_title,
                                'id': video_id,
                                'status': 'member_only',
                                'reason': download_context.get('error_reason', '会员专属内容')
                            })
                        else:
                            # 真正的错误：文件未找到且不是会员问题也不是被过滤
                            log_with_context(
                                logger, logging.ERROR,
                                f"❌ 转换失败 {video_id} (文件未找到)",
                                yt_channel=channel_name
                            )
                            found_raw = False
                            try:
                                for fname in os.listdir(target_folder):
                                    if f'.{video_id}.' in fname and fname.endswith('.tmp') and not fname.endswith('.m4a'):
                                        logger.warning(f"找到原始下载文件: {os.path.join(target_folder, fname)}，但未转换为 {expected_audio_ext}")
                                        found_raw = True
                                        break
                            except OSError:
                                pass
                            if not found_raw:
                                logger.trace(f"原始下载文件也未找到（video_id={video_id}）")

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
                    error_lower = error_str.lower()
                    if "already been recorded in the archive" in error_str:
                        log_with_context(
                            logger, logging.INFO,
                            "视频已在存档中记录，跳过",
                            yt_channel=channel_name,
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
                    elif "members-only" in error_lower or "member" in error_lower or "premium" in error_lower or "subscriber" in error_lower:
                        log_with_context(
                            logger, logging.INFO,
                            f"🔒 会员专属 {video_id} (下载被拒绝)",
                            yt_channel=channel_name
                        )
                        stats['member_only'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'member_only',
                            'reason': '会员专属内容（下载时确认）'
                        })
                    elif "premieres in" in error_lower or "premiere" in error_lower:
                        # YouTube Premiere（首映）视频，尚未到首映时间
                        premiere_info = error_str.split(":")[-1].strip() if ":" in error_str else "待首映"
                        log_with_context(
                            logger, logging.INFO,
                            f"⏰ 待首映 {video_id}",
                            yt_channel=channel_name,
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
                    elif 'requested range not satisfiable' in error_lower or 'http error 416' in error_lower:
                        removed_chunks = 0
                        try:
                            for fname in list(os.listdir(target_folder)):
                                if f'.{video_id}.' in fname and '.tmp' in fname:
                                    try:
                                        os.remove(os.path.join(target_folder, fname))
                                        removed_chunks += 1
                                    except OSError:
                                        pass
                        except OSError:
                            pass
                        log_with_context(
                            logger, logging.WARNING,
                            f'🧹 HTTP 416：检测到无效的下载范围，已清理残留片段 {video_id}',
                            yt_channel=channel_name,
                            video_id=video_id,
                            removed_chunks=removed_chunks
                        )
                        stats['error'] += 1
                        stats['details'].append({
                            'index': idx,
                            'title': video_title,
                            'id': video_id,
                            'status': 'error',
                            'reason': 'HTTP 416 - range 无效'
                        })
                    
                    else:
                        # 简短的错误信息
                        error_msg = str(de)[:100] if len(str(de)) > 100 else str(de)
                        log_with_context(
                            logger, logging.ERROR,
                            f"❌ 下载失败 {video_id}",
                            yt_channel=channel_name,
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
                    try:
                        for fname in list(os.listdir(target_folder)):
                            if f'.{video_id}.' in fname and '.tmp' in fname:
                                path = os.path.join(target_folder, fname)
                                try:
                                    os.remove(path)
                                    logger.trace(f"已清理部分下载临时文件: {path}")
                                except OSError:
                                    pass
                    except OSError:
                        pass
                    continue
                except Exception as e:
                    error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
                    log_with_context(
                        logger, logging.ERROR,
                        f"❌ 未知错误 {video_id}",
                        yt_channel=channel_name,
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
                yt_channel=channel_name,
                total_videos=stats['total'],
                success=stats['success'],
                filtered=stats['filtered'],
                already_exists=stats['already_exists'],
                archived=stats['archived'],
                member_only=stats['member_only'],
                error=stats['error']
            )
            
            # 详细列表信息已通过每个视频的独立日志输出，此处不再重复输出
            # 格式化的文本列表不适合 JSON 结构化日志
        
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            
            # 检查是否为直播预告（还未开始的直播）
            if "live event will begin in" in error_str.lower():
                log_with_context(
                    logger, logging.INFO,
                    "频道包含直播预告视频，稍后自动下载",
                    yt_channel=channel_name,
                    note="直播尚未开始"
                )
                return True  # 不算错误，返回成功
            
            # 检查是否为 YouTube Premiere（首映）视频
            if "premieres in" in error_str.lower() or "premiere" in error_str.lower():
                log_with_context(
                    logger, logging.INFO,
                    "频道包含待首映视频，稍后自动下载",
                    yt_channel=channel_name,
                    note="首映尚未开始"
                )
                return True  # 不算错误，返回成功
            
            # 检查是否为被过滤器拦截的视频 (yt-dlp match_filter returned message)
            if "does not pass filter" in error_str:
                 log_with_context(
                    logger, logging.INFO if has_date_info else logging.DEBUG, # 如果之前没能过滤，这里是第一次过滤，用DEBUG避免刷屏？不，还是INFO好知道发生了什么
                    f"⏭️ 视频被过滤规则拦截",
                    yt_channel=channel_name,
                    video_id=video_id,
                    reason=error_msg
                )
                 # 这种情况下我们应该增加 filtered 计数
                 stats['filtered'] += 1
                 return True

            # 检查是否为会员专属内容错误（频道视频都是会员内容时会在获取列表阶段就报错）
            if ("members-only" in error_str.lower() or 
                ("member" in error_str.lower() and "join this channel" in error_str.lower())):
                safe_title = video_title or "未知标题"
                safe_id = video_id or "unknown"
                log_with_context(
                    logger, logging.INFO,
                    f"⏭️ 频道当前视频《{safe_title}》为会员专属，跳过",
                    yt_channel=channel_name,
                    video_title=safe_title,
                    video_id=safe_id
                )
                return True  # 不算错误，只是暂时没有可下载内容
            
            # 记录实际错误（不包含 traceback，避免日志过长）
            # 只保留错误消息的前200个字符
            error_msg = error_str[:200] if len(error_str) > 200 else error_str
            log_with_context(
                logger, logging.ERROR,
                f"❌ 处理频道失败",
                yt_channel=channel_name,
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
        yt_channel=channel_name
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
                yt_channel=channel_name,
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
            yt_channel=channel_name,
            timestamp=timestamp
        )
        dl_audio_closest_after(AUDIO_FOLDER, channel_name, timestamp)

# ===== Story download helpers =====

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
    
    # 清理目标目录中的残留临时文件
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

    # 依次从 /videos（普通视频）和 /streams（直播录播）获取内容，合并去重后按时间排序
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

    # 合并后按时间戳升序排列（最旧在前），与 playlistreverse=True 的预期顺序一致
    def _sort_ts(e):
        ts = _extract_timestamp_from_entry(e)
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

        # 准备一个容器来接真实文件名
        downloaded_file_info = {"path": None}

        def story_progress_hook(d):
            if d['status'] == 'finished':
                # 获取真实的文件路径
                downloaded_file_info["path"] = d.get('filename')

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

        # 同一批故事条目之间增加视频级延迟，降低请求频率
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
            "outtmpl": os.path.join(target_folder, f"%(uploader)s.%(id)s.%(title)s.tmp"),
            "progress_hooks": [story_progress_hook],
        }
        ydl_opts = get_ydl_opts(custom_opts)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except yt_dlp.utils.DownloadError as de:
            logger.error(f"故事视频下载错误: {de}")
            continue
        except Exception as e:
            logger.error(f"故事视频下载异常: {e}")
            continue

        # 使用 Hook 捕获的真实路径
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

        # 如果 Hook 没拿到，尝试模糊查找
        if not resolved_temp_path:
            for f in os.listdir(target_folder):
                if video_id in f and (f.endswith('.tmp.m4a') or f.endswith('.tmp')):
                    resolved_temp_path = os.path.join(target_folder, f)
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
