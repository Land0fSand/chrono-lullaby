# -*- coding: utf-8 -*-
import os
import sys
import math
import logging
import ffmpeg # type: ignore

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from telegram.ext import ContextTypes
from telegram.error import TimedOut, TelegramError
from contextlib import suppress
from logger import get_logger, log_with_context
from config import get_sent_archive_path

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
    记录已发送的文件到两个archive文件
    
    Args:
        chat_id: Telegram 频道 ID
        video_id: YouTube 视频 ID
        title: 视频标题
        channel_name: YouTube 频道名（可选）
    """
    try:
        # 1. 记录机器格式（yt-dlp 格式）
        machine_archive = get_sent_archive_path(chat_id, readable=False)
        machine_line = f"youtube {video_id}\n"
        
        # 检查是否已存在，避免重复记录
        if os.path.exists(machine_archive):
            with open(machine_archive, 'r', encoding='utf-8') as f:
                if machine_line in f.read():
                    logger.debug(f"视频 {video_id} 已在发送记录中")
                    return
        
        with open(machine_archive, 'a', encoding='utf-8') as f:
            f.write(machine_line)
        
        # 2. 记录人类可读格式（包含频道名）
        readable_archive = get_sent_archive_path(chat_id, readable=True)
        if channel_name:
            readable_line = f"{video_id} [{channel_name}] {title}\n"
        else:
            readable_line = f"{video_id} [{title}]\n"
        
        with open(readable_archive, 'a', encoding='utf-8') as f:
            f.write(readable_line)
        
        log_with_context(
            logger, logging.DEBUG,
            "已记录发送记录",
            video_id=video_id,
            channel_name=channel_name,
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


async def send_file(context: ContextTypes.DEFAULT_TYPE, chat_id, audio_folder) -> None:
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
        logger.debug("没有找到音频文件")
        return
    # 按文件创建时间排序，确保最早的文件先发送
    files.sort(key=lambda x: os.path.getctime(os.path.join(audio_folder, x)))
    for file_name in files:
        file_path = os.path.join(audio_folder, file_name)
        
        # Skip already segmented files (e.g., those ending with _1.mp3, _2.mp3)
        # to avoid trying to re-segment them if a previous run failed mid-sending.
        if '_' in os.path.splitext(file_name)[0] and os.path.splitext(file_name)[0].split('_')[-1].isdigit():
            logger.info(f"跳过已分段文件: {file_name}")
            # We will send these individual segments directly if they are valid
            await send_single_file(context, chat_id, file_path)
            os.remove(file_path) # Remove after attempting to send
            continue # Move to the next file in the directory

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # 文件大小（MB）
        log_with_context(
            logger, logging.INFO,
            "准备发送文件",
            file_name=file_name,
            size_mb=round(file_size_mb, 2)
        )
        
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
                for split_file_path in split_files:
                    await send_single_file(context, chat_id, split_file_path)
                    try:
                        os.remove(split_file_path)  # 发送后删除临时文件
                        logger.debug(f"已删除切割文件: {split_file_path}")
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
            await send_single_file(context, chat_id, file_path)
            try:
                os.remove(file_path)  # 发送后删除文件
                logger.info(f"已删除文件: {file_path}")
            except OSError as e:
                logger.error(f"删除文件失败: {file_path}, 错误: {e}")
        
        break  # 每次任务只处理一个原始文件（或其分片）

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
        logger, logging.DEBUG,
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
            logger, logging.DEBUG,
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
        for i in range(num_parts_to_try):
            segment_name = f"{base_name}_{i}{ext}"
            if os.path.exists(segment_name) and os.path.getsize(segment_name) > 0:
                output_segments.append(segment_name)
                current_segment_size_mb = os.path.getsize(segment_name) / (1024 * 1024)
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
            else:
                logger.warning(f"预期切割段未找到或为空: {segment_name}")
                all_segments_ok = False
                break

        if not all_segments_ok or len(output_segments) != num_parts_to_try:
            logger.info(f"当前切割尝试 ({num_parts_to_try} 段) 失败，清理临时文件并重试...")
            for seg_file in output_segments: # output_segments might be partially filled
                try: os.remove(seg_file) 
                except OSError: pass
            # Also attempt to clean any other numbered segments ffmpeg might have created
            for i in range(num_parts_to_try + 2): # Check a bit beyond just in case
                stale_segment = f"{base_name}_{i}{ext}"
                if os.path.exists(stale_segment) and stale_segment not in output_segments: # Avoid deleting what might be kept if logic changes
                    try: os.remove(stale_segment)
                    except OSError: pass 
            
            return _recursive_split_and_check(file_path, original_file_size_mb, num_parts_to_try + 1, max_parts_cap, recursion_depth + 1, max_recursion_depth)
        
        log_with_context(
            logger, logging.INFO,
            "文件切割成功",
            file_name=os.path.basename(file_path),
            segments_count=len(output_segments),
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
        for i in range(num_parts_to_try + 2):
            segment_name = f"{base_name}_{i}{ext}"
            if os.path.exists(segment_name):
                try: os.remove(segment_name)
                except OSError: pass
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
        for i in range(num_parts_to_try + 2):
            segment_name = f"{base_name}_{i}{ext}"
            if os.path.exists(segment_name):
                try: os.remove(segment_name)
                except OSError: pass
        return []

async def send_single_file(context: ContextTypes.DEFAULT_TYPE, chat_id, file_path):
    """
    发送单个文件到指定的聊天
    """
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logger.error(f"文件不存在或为空，跳过发送: {file_path}")
        return

    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        log_with_context(
            logger, logging.INFO,
            "正在发送文件",
            file_name=os.path.basename(file_path),
            size_mb=round(file_size_mb, 2)
        )
        
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

        with open(file_path, 'rb') as file_to_send:
            with suppress(TimedOut):
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=file_to_send,
                    title=title,
                    performer=performer,
                    # Consider adding duration if easily obtainable from ffmpeg.probe and passing it
                )
        
        # 记录已发送的文件（包含频道名）
        record_sent_file(chat_id, video_id, base_title, channel_name)
        
        log_with_context(
            logger, logging.INFO,
            "文件发送成功",
            file_name=os.path.basename(file_path),
            video_id=video_id
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
