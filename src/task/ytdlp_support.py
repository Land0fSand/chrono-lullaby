# -*- coding: utf-8 -*-
import copy
import logging
import os
import re
from pathlib import Path

from config import DOWNLOAD_ARCHIVE
from logger import TRACE_LEVEL, get_logger, log_with_context

logger = get_logger('downloader.dl_audio')

_download_archive_cache = {
    "mtime": None,
    "entries": set(),
}

PREFERRED_REMOTE_COMPONENTS = {'ejs:github'}


def cleanup_incomplete_downloads(folder: str, force: bool = False) -> int:
    """
    删除音频目录中残留的 .tmp/.part 等未完成下载文件，避免下次继续下载报 416。
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
    """删除某个视频对应的残留 .tmp/.part 文件。"""
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
    """读取 download archive 并缓存结果，避免每次都重新加载大文件。"""
    path = DOWNLOAD_ARCHIVE
    if not path:
        return set()
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
        return _download_archive_cache.get("entries", set())

    _download_archive_cache["mtime"] = current_mtime
    _download_archive_cache["entries"] = entries
    return entries


def is_video_in_download_archive(video_id: str) -> bool:
    """判断指定视频 ID 是否已经记录在 download archive 中。"""
    if not video_id:
        return False
    entries = _load_download_archive()
    return video_id in entries


def _resolve_js_runtime_path(raw_path: str) -> str:
    """将用户输入的路径展开为绝对路径。"""
    return os.path.abspath(
        os.path.expanduser(
            os.path.expandvars(raw_path)
        )
    )


def _detect_js_runtime():
    """
    检测可用的 JavaScript 运行时。
    - 支持通过环境变量 YT_DLP_JS_RUNTIME=deno:/path/to/bin 覆盖
    - 仅使用 Deno（不回退 Node）
    """
    import shutil

    runtime_override = os.environ.get("YT_DLP_JS_RUNTIME")
    if runtime_override:
        runtime_name, _, runtime_path = runtime_override.partition(':')
        runtime_name = (runtime_name or 'deno').strip().lower()
        if runtime_name != 'deno':
            logger.warning(
                f"YT_DLP_JS_RUNTIME 仅支持 deno，已忽略: {runtime_name}. 将继续自动检测 Deno。"
            )
        else:
            runtime_config = {'deno': {}}
            runtime_path = runtime_path.strip()
            if runtime_path:
                resolved = _resolve_js_runtime_path(runtime_path)
                if os.path.exists(resolved):
                    runtime_config['deno']['path'] = resolved
                    logger.info(f"使用环境变量指定的 JavaScript 运行时: deno -> {resolved}")
                else:
                    logger.warning(f"环境变量 YT_DLP_JS_RUNTIME 指定的路径不存在: {resolved}")
            else:
                logger.trace("使用环境变量指定的 JavaScript 运行时: deno (PATH 搜索)")
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

    deno_path = shutil.which("deno")
    if deno_path:
        logger.info(f"检测到 Deno 运行时 (PATH)，将用于解析 YouTube n signature: {deno_path}")
        return {'deno': {'path': deno_path}}

    logger.warning("未检测到可用的 Deno 运行时，YouTube 下载可能失败")
    return None


JS_RUNTIME_CONFIG = _detect_js_runtime()


def apply_js_runtime(opts: dict) -> dict:
    """为 yt-dlp 配置注入统一的 JavaScript 运行时与 challenge solver 组件设置。"""
    if JS_RUNTIME_CONFIG:
        opts['js_runtimes'] = copy.deepcopy(JS_RUNTIME_CONFIG)
    opts.setdefault('remote_components', set(PREFERRED_REMOTE_COMPONENTS))
    return opts


class TimestampedYTDLLogger:
    """自定义 yt-dlp 日志处理器，桥接到统一日志系统。"""

    def __init__(self):
        self._logger = get_logger('downloader.yt-dlp')
        self._seen_warnings = set()

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
        return bool(re.match(r'^\[download\]\s+\d+(?:\.\d+)?%\b', text))

    def _log_trace(self, msg):
        return

    def debug(self, msg):
        self._log_trace(msg)

    def info(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.info(cleaned)

    def warning(self, msg):
        cleaned = self._clean_message(msg)
        if not cleaned:
            return
        if cleaned in self._seen_warnings:
            return
        self._seen_warnings.add(cleaned)
        self._logger.warning(f"⚠️ yt-dlp: {cleaned}")

    def error(self, msg):
        cleaned = self._clean_message(msg)
        if not cleaned:
            return
        if is_member_only_message(cleaned):
            self._logger.trace(cleaned)
        else:
            self._logger.error(f"❌ yt-dlp: {cleaned}")

    def critical(self, msg):
        cleaned = self._clean_message(msg)
        if cleaned:
            self._logger.critical(cleaned)


def sanitize_filename(filename: str) -> str:
    """
    智能清理文件名：
    - 保留所有可见字符
    - 只替换文件系统非法字符和不可见字符
    """
    result = []
    illegal_filename_chars = '<>:"/\\|?*'
    for char in filename:
        if char in illegal_filename_chars:
            result.append('_')
        elif char.isprintable():
            result.append(char)
        else:
            result.append('_')
    return ''.join(result)


def safe_rename_file(src, dst, max_retries=5):
    """安全重命名文件，包含重试机制处理文件锁定问题。"""
    for attempt in range(max_retries):
        try:
            os.rename(src, dst)
            return True
        except (OSError, PermissionError) as err:
            if attempt < max_retries - 1:
                log_with_context(
                    logger, logging.WARNING,
                    "文件重命名失败，准备重试",
                    src=src, dst=dst, attempt=attempt + 1, max_retries=max_retries, error=str(err)
                )
                import time
                time.sleep(0.5 * (attempt + 1))
            else:
                log_with_context(
                    logger, logging.ERROR,
                    "文件重命名失败，已达最大重试次数",
                    src=src, dst=dst, max_retries=max_retries, error=str(err)
                )
                try:
                    os.remove(src)
                    logger.warning(f"已删除无法重命名的临时文件: {src}")
                except OSError:
                    logger.error(f"无法删除临时文件: {src}")
                return False
        except Exception as err:
            log_with_context(
                logger, logging.ERROR,
                "文件重命名意外错误",
                src=src, dst=dst, error=str(err), error_type=type(err).__name__
            )
            return False
    return False


def is_member_only_message(message: str) -> bool:
    """统一判断一段错误消息是否表达会员/订阅专属限制。"""
    text = (message or "").lower()
    patterns = [
        "members-only",
        "members only",
        "member-only",
        "join this channel",
        "available to this channel's members",
        "this video is available to this channel's members",
        "会员",
        "頻道會員",
        "频道会员",
        "僅限頻道會員",
        "仅限频道会员",
        "成為這個頻道的會員",
        "成为这个频道的会员",
        "這部影片僅供以下等級的頻道會員觀看",
        "这部影片仅供以下等级的频道会员观看",
        "付费",
        "订阅者专享",
        "订阅专属",
    ]
    return any(p in text for p in patterns)
