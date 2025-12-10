# -*- coding: utf-8 -*-
import os
import sys
import math
import glob
import logging
import ffmpeg # type: ignore
from typing import Optional

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from telegram.ext import ContextTypes
from telegram.error import TimedOut, TelegramError
from contextlib import suppress
from logger import get_logger, log_with_context, TRACE_LEVEL
from config import get_sent_archive_path, get_config_provider

# 使用统一的日志系统
logger = get_logger('bot.send_file')


def extract_video_info_from_filename(filename: str) -> tuple:
    """
    从文件名中提取频道名、视频ID和标题
    
    文件名格式: {频道名}.{video_id}.{title}.m4a 或 {频道名}.{video_id}.{title}_1.m4a (分段文件)
    
    Args:
        filename: 文件名
    
    Returns:
        (channel_name, video_id, title) 元组
    """
    base_name = os.path.splitext(filename)[0]  # 去掉扩展名
    
    # 处理分段文件（例如：channel.videoid.title_1）
    if '_' in base_name:
        parts = base_name.split('_')
        if parts[-1].isdigit():
            base_name = '_'.join(parts[:-1])
    
    # 分割频道名、video_id 和 title
    parts = base_name.split('.', 2)  # 最多分3部分
    if len(parts) >= 3:
        channel_name = parts[0]
        video_id = parts[1]
        title = parts[2]
    elif len(parts) == 2:
        # 向后兼容旧格式（只有频道名.标题 或 video_id.标题）
        channel_name = parts[0]
        video_id = parts[0]  # 如果是旧格式，用频道名作为ID
        title = parts[1]
    else:
        # 如果格式不符合预期，使用整个文件名
        channel_name = base_name
        video_id = base_name
        title = base_name
    
    return channel_name, video_id, title


def record_sent_file(chat_id: str, video_id: str, title: str, channel_name: str = None) -> None:
    """
    记录已发送的文件（使用配置提供者，支持本地和Notion）
    
    Args:
        chat_id: Telegram 频道 ID
        video_id: YouTube 视频 ID
        title: 视频标题
        channel_name: YouTube 频道名（可选）
    """
    try:
        # 使用配置提供者记录
        provider = get_config_provider()
        
        # 检查是否已存在
        if provider.has_sent_record(video_id, chat_id):
            logger.trace(f"视频 {video_id} 已在发送记录中")
            return
        
        # 添加记录（配置提供者会处理本地或Notion存储）
        file_path = f"{channel_name or 'unknown'}.{video_id}.{title}.m4a"
        success = provider.add_sent_record(video_id, chat_id, title, file_path)
        
        if not success:
            log_with_context(
                logger, logging.WARNING,
                "记录发送记录失败，可能影响发送",
                video_id=video_id,
                chat_id=chat_id
            )
        
    except Exception as e:
        log_with_context(
            logger, logging.ERROR,
            "记录发送记录失败",
            video_id=video_id,
            chat_id=chat_id,
            error=str(e)
        )


def _get_segment_index_from_filename(filename: str) -> int:
    """
    从文件名中提取分段索引号
    
    Args:
        filename: 文件名（不含路径）
    
    Returns:
        分段索引（0, 1, 2...），如果不是分段文件则返回 math.inf
    """
    base_name = os.path.splitext(filename)[0]
    if '_' not in base_name:
        return math.inf
    suffix = base_name.rsplit('_', 1)[-1]
    return int(suffix) if suffix.isdigit() else math.inf


def _is_segment_file(filename: str) -> bool:
    """判断文件是否是分段文件（以 _数字 结尾）"""
    base_name = os.path.splitext(filename)[0]
    if '_' not in base_name:
        return False
    suffix = base_name.rsplit('_', 1)[-1]
    return suffix.isdigit()


def _get_segment_base_name(filename: str) -> str:
    """获取分段文件的基础名称（去除 _数字 后缀）"""
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    if '_' in base_name:
        parts = base_name.rsplit('_', 1)
        if parts[-1].isdigit():
            return parts[0] + ext
    return filename


async def send_file(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id,
    audio_folder,
    group_name: Optional[str] = None,
) -> None:
    if not os.path.exists(audio_folder):
        logger.warning(f"音频文件夹不存在: {audio_folder}")
        return
    # 过滤掉隐藏文件和临时文件(.tmp后缀或包含.tmp.)
    files = [f for f in os.listdir(audio_folder) 
             if os.path.isfile(os.path.join(audio_folder, f)) 
             and not f.startswith('.') 
             and not f.endswith('.tmp')
             and '.tmp.' not in f]  # 也过滤掉 .tmp.m4a 这种格式
    if not files:
        return
    
    # 分离分段文件和普通文件
    segment_files = [f for f in files if _is_segment_file(f)]
    normal_files = [f for f in files if not _is_segment_file(f)]
    
    # 按文件创建时间排序普通文件，确保最早的文件先发送
    normal_files.sort(key=lambda x: os.path.getctime(os.path.join(audio_folder, x)))
    
    # 优先处理残留的分段文件（按正确顺序发送）
    if segment_files:
        # 按基础名称分组
        segment_groups = {}
        for f in segment_files:
            base = _get_segment_base_name(f)
            if base not in segment_groups:
                segment_groups[base] = []
            segment_groups[base].append(f)
        
        # 对每组分段文件按数字后缀排序后发送
        for base_name, group_files in segment_groups.items():
            # 按分段索引排序（0, 1, 2...）
            group_files.sort(key=_get_segment_index_from_filename)
            log_with_context(
                logger, logging.INFO,
                "发送残留分段文件组",
                base_name=base_name,
                segment_count=len(group_files)
            )
            for seg_file in group_files:
                file_path = os.path.join(audio_folder, seg_file)
                await send_single_file(
                    context,
                    chat_id,
                    file_path,
                    group_name=group_name,
                )
                try:
                    os.remove(file_path)
                    logger.trace(f"已删除分段文件: {seg_file}")
                except OSError as e:
                    logger.error(f"删除分段文件失败: {seg_file}, 错误: {e}")
        return  # 处理完分段文件后返回，下次再处理普通文件
    
    # 处理普通文件
    for file_name in normal_files:
        file_path = os.path.join(audio_folder, file_name)

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # 文件大小（MB）
        if file_size_mb > 49: # Use a slightly lower threshold to be safe
            log_with_context(
                logger, logging.INFO,
                "文件超过49MB限制，将进行切割",
                file_name=file_name,
                size_mb=round(file_size_mb, 2)
            )
            # Initial calculation of num_parts based on 45MB target
            initial_target_segment_size_mb = 45
            initial_num_parts = math.ceil(file_size_mb / initial_target_segment_size_mb)
            
            # Max parts can be, for example, if segments were 10MB on average, or a fixed higher cap
            # For a 100MB file, this would be 10 parts. For 1000MB, 100 parts.
            # Or, a simpler cap like initial_num_parts + 10 (max 10 retries)
            max_parts_cap = initial_num_parts + 10 

            split_files = _recursive_split_and_check(file_path, file_size_mb, initial_num_parts, max_parts_cap)
            
            if split_files:
                log_with_context(
                    logger, logging.INFO,
                    "文件切割成功，准备发送",
                    file_name=file_name,
                    parts_count=len(split_files)
                )
                for idx, split_file_path in enumerate(split_files):
                    await send_single_file(
                        context,
                        chat_id,
                        split_file_path,
                        group_name=group_name,
                    )
                    try:
                        os.remove(split_file_path)  # 发送后删除临时文件
                        logger.trace(f"已删除切割文件: {split_file_path}")
                    except OSError as e:
                        logger.error(f"删除切割文件失败: {split_file_path}, 错误: {e}")
                try:
                    os.remove(file_path)  # 发送完成后删除原始文件
                    logger.info(f"已删除原始大文件: {file_path}")
                except OSError as e:
                    logger.error(f"删除原始大文件失败: {file_path}, 错误: {e}")
            else:
                logger.error(f"文件切割失败或超出重试次数，跳过: {file_name}")
        else:
            await send_single_file(
                context,
                chat_id,
                file_path,
                group_name=group_name,
            )
            try:
                os.remove(file_path)  # 发送后删除文件
                logger.info(f"已删除文件: {file_path}")
            except OSError as e:
                logger.error(f"删除文件失败: {file_path}, 错误: {e}")
        
        break  # 每次任务只处理一个原始文件（或其分片）

def _segment_file_paths(base_name: str, ext: str) -> list[str]:
    """Collect generated segment files sorted by numeric suffix."""
    pattern = f"{glob.escape(base_name)}_*{ext}"
    segment_files = glob.glob(pattern)

    def _segment_index(path: str) -> int:
        stem = os.path.splitext(path)[0]
        suffix = stem.rsplit('_', 1)[-1]
        return int(suffix) if suffix.isdigit() else math.inf

    return sorted(segment_files, key=_segment_index)


def _cleanup_segment_files(base_name: str, ext: str) -> None:
    """Remove all segment files for the given base name."""
    for segment_path in _segment_file_paths(base_name, ext):
        try:
            os.remove(segment_path)
        except OSError:
            pass


def _probe_duration_seconds(file_path: str) -> Optional[int]:
    """
    使用 ffprobe 获取音频时长（秒）

    Args:
        file_path: 音频文件路径

    Returns:
        时长（向下取整）或 None
    """
    try:
        probe = ffmpeg.probe(file_path)
        duration_str = probe.get("format", {}).get("duration")
        if duration_str is None:
            return None
        duration = float(duration_str)
        if duration <= 0:
            return None
        # Telegram 如果收到略短的 duration 会提前结束播放，这里向上取整并额外补 1 秒
        padded = math.ceil(duration) + 1
        return max(1, padded)
    except Exception as err:
        log_with_context(
            logger, logging.WARNING,
            "获取音频时长失败，将由 Telegram 推断",
            file_path=file_path,
            error=str(err),
            error_type=type(err).__name__
        )
        return None


def _recursive_split_and_check(file_path, original_file_size_mb, num_parts_to_try, max_parts_cap, recursion_depth=0, max_recursion_depth=10):
    """
    Recursively attempts to split a file, checking segment sizes and increasing parts if needed.
    file_path: path to the original large file.
    original_file_size_mb: size of the original file in MB (for logging/reference).
    num_parts_to_try: current number of segments to attempt splitting into.
    max_parts_cap: a hard limit on the number of parts we will try.
    recursion_depth: current depth of recursion to prevent infinite loops.
    max_recursion_depth: maximum allowed recursion calls.
    """
    log_with_context(
        logger, TRACE_LEVEL,
        "尝试切割文件",
        file_name=os.path.basename(file_path),
        num_parts=num_parts_to_try,
        recursion_depth=recursion_depth
    )

    if num_parts_to_try <= 0:
        logger.error("num_parts_to_try 无效 (<=0)")
        return []
    if num_parts_to_try > max_parts_cap:
        log_with_context(
            logger, logging.ERROR,
            "尝试的分段数超过最大允许分段数，停止切割",
            num_parts=num_parts_to_try,
            max_parts_cap=max_parts_cap
        )
        return []
    if recursion_depth >= max_recursion_depth:
        logger.error(f"已达到最大递归深度 ({max_recursion_depth})，停止切割")
        return []

    output_segments = []
    base_name, ext = os.path.splitext(file_path)
    # FFmpeg's segment muxer uses % as format character, need to escape it
    # Replace % with %% to escape it for FFmpeg
    safe_base_name = base_name.replace('%', '%%')
    segment_pattern = f"{safe_base_name}_%d{ext}" # ffmpeg default is 0-indexed

    try:
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        
        if duration <= 0:
            logger.error(f"文件时长无效: {file_path} ({duration}s)")
            return []
            
        segment_duration = duration / num_parts_to_try
        if segment_duration < 1: # Avoid segments that are too short (e.g. less than 1s)
            logger.warning(f"计算的段时长过短: {segment_duration:.2f}s (尝试分成 {num_parts_to_try} 段)")
            # Potentially add a condition here to stop if segments are too short, e.g., return []
            # For now, let it proceed but be aware.

        log_with_context(
            logger, TRACE_LEVEL,
            "FFmpeg 切割参数",
            input_file=file_path,
            output_pattern=segment_pattern,
            num_parts=num_parts_to_try,
            segment_duration=round(segment_duration, 2)
        )
        
        ffmpeg.input(file_path).output(
            segment_pattern,
            format='segment',
            segment_time=segment_duration,
            c='copy',
            reset_timestamps=1
        ).run(quiet=True, overwrite_output=True)

        # Validate segments
        # Note: FFmpeg creates files using the original base_name (not safe_base_name with %%)
        all_segments_ok = True
        max_segment_size_mb = 0
        segment_files = _segment_file_paths(base_name, ext)

        if not segment_files:
            logger.warning(f"FFmpeg 切割后未生成任何分段文件: {file_path}")
            return []

        for segment_name in segment_files:
            size_bytes = os.path.getsize(segment_name)
            if size_bytes <= 0:
                logger.warning(f"切割段为空或大小为0: {segment_name}")
                all_segments_ok = False
                break
            current_segment_size_mb = size_bytes / (1024 * 1024)
            if current_segment_size_mb > max_segment_size_mb:
                max_segment_size_mb = current_segment_size_mb
            if current_segment_size_mb >= 50: # Check against Telegram's hard limit
                log_with_context(
                    logger, logging.WARNING,
                    "切割段大小仍超限",
                    segment_name=segment_name,
                    size_mb=round(current_segment_size_mb, 2)
                )
                all_segments_ok = False
                break # No need to check further for this attempt
            output_segments.append(segment_name)

        if not all_segments_ok:
            logger.info(f"当前切割尝试 (目标 {num_parts_to_try} 段) 失败，清理临时文件并重试...")
            _cleanup_segment_files(base_name, ext)
            return _recursive_split_and_check(file_path, original_file_size_mb, num_parts_to_try + 1, max_parts_cap, recursion_depth + 1, max_recursion_depth)
        
        log_with_context(
            logger, logging.INFO,
            "文件切割成功",
            file_name=os.path.basename(file_path),
            segments_count=len(output_segments),
            target_segments=num_parts_to_try,
            max_segment_size_mb=round(max_segment_size_mb, 2)
        )
        return output_segments

    except ffmpeg.Error as e:
        log_with_context(
            logger, logging.ERROR,
            "FFmpeg 切割错误",
            num_parts=num_parts_to_try,
            error=e.stderr.decode('utf8', errors='ignore') if e.stderr else 'N/A'
        )
        # Cleanup on ffmpeg error (use original base_name for cleanup)
        _cleanup_segment_files(base_name, ext)
        return [] # Indicate failure for this path
    except Exception as e:
        log_with_context(
            logger, logging.ERROR,
            "切割文件时发生意外错误",
            num_parts=num_parts_to_try,
            error=str(e),
            error_type=type(e).__name__
        )
        # Cleanup on exception (use original base_name for cleanup)
        _cleanup_segment_files(base_name, ext)
        return []

async def send_single_file(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id,
    file_path,
    group_name: Optional[str] = None,
):
    """
    发送单个文件到指定的聊天
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logger.error(f"文件不存在或为空，跳过发送: {file_path}")
        return

    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        file_name_for_meta = os.path.basename(file_path)
        
        # 从文件名中提取频道名、视频ID和标题
        channel_name, video_id, base_title = extract_video_info_from_filename(file_name_for_meta)
        
        # 处理分段文件的标题显示
        base_name = os.path.splitext(file_name_for_meta)[0]
        if '_' in base_name:
            parts = base_name.split('_')
            if parts[-1].isdigit():
                title = f"{base_title} (Part {int(parts[-1]) + 1})"  # 1-indexed for display
            else:
                title = base_title
        else:
            title = base_title
        
        # 使用频道名作为 performer
        performer = channel_name if channel_name else "Unknown"
        # 主动提供精准时长，避免元数据时长不准确导致播放尾部被截断
        duration_seconds = _probe_duration_seconds(file_path)

        with open(file_path, 'rb') as file_to_send:
            with suppress(TimedOut):
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=file_to_send,
                    title=title,
                    performer=performer,
                    duration=duration_seconds,
                    # Consider adding duration if easily obtainable from ffmpeg.probe and passing it
                )
        
        # 记录已发送的文件（包含频道名）
        record_sent_file(chat_id, video_id, base_title, channel_name)
        log_with_context(
            logger, logging.INFO,
            "文件发送完成",
            file_name=os.path.basename(file_path),
            size_mb=round(file_size_mb, 2),
            video_id=video_id,
            channel_name=channel_name,
            chat_id=chat_id
        )
        
        group_label = group_name or str(chat_id)
        log_with_context(
            logger,
            logging.INFO,
            f"频道组 {group_label} 发送音频《{title}》",
            telegram_chat_id=chat_id,
            youtube_channel=channel_name,
            video_id=video_id,
            audio_title=title,
        )
    except TelegramError as te:
        log_with_context(
            logger, logging.ERROR,
            "发送文件时发生 Telegram 错误",
            file_name=os.path.basename(file_path),
            error=str(te)
        )
        # Do not remove the file if sending failed, so it can be retried
    except FileNotFoundError:
        logger.error(f"文件在发送前找不到了，可能已被其他进程删除: {file_path}")
    except Exception as e:
        log_with_context(
            logger, logging.ERROR,
            "发送文件时发生意外错误",
            file_name=os.path.basename(file_path),
            error=str(e),
            error_type=type(e).__name__
        )
        # Do not remove the file if sending failed
