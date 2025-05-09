import os
import math
import ffmpeg # type: ignore
from telegram.ext import ContextTypes
from telegram.error import TimedOut, TelegramError
from contextlib import suppress


async def send_file(context: ContextTypes.DEFAULT_TYPE, chat_id, audio_folder) -> None:
    if not os.path.exists(audio_folder):
        print(f"音频文件夹 {audio_folder} 不存在")
        return
    files = [f for f in os.listdir(audio_folder) if os.path.isfile(os.path.join(audio_folder, f)) and not f.startswith('.')] # Ignore hidden files
    if not files:
        print("没有找到音频文件")
        return
    # 按文件创建时间排序，确保最早的文件先发送
    files.sort(key=lambda x: os.path.getctime(os.path.join(audio_folder, x)))
    for file_name in files:
        file_path = os.path.join(audio_folder, file_name)
        
        # Skip already segmented files (e.g., those ending with _1.mp3, _2.mp3)
        # to avoid trying to re-segment them if a previous run failed mid-sending.
        if '_' in os.path.splitext(file_name)[0] and os.path.splitext(file_name)[0].split('_')[-1].isdigit():
            print(f"跳过已分段文件: {file_name}")
            # We will send these individual segments directly if they are valid
            await send_single_file(context, chat_id, file_path)
            os.remove(file_path) # Remove after attempting to send
            continue # Move to the next file in the directory

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # 文件大小（MB）
        print(f"准备发送文件: {file_name}, 大小: {file_size_mb:.2f} MB")
        
        if file_size_mb > 49: # Use a slightly lower threshold to be safe
            print(f"文件 {file_name} 超过 49MB 限制，将进行切割")
            # Initial calculation of num_parts based on 45MB target
            initial_target_segment_size_mb = 45
            initial_num_parts = math.ceil(file_size_mb / initial_target_segment_size_mb)
            
            # Max parts can be, for example, if segments were 10MB on average, or a fixed higher cap
            # For a 100MB file, this would be 10 parts. For 1000MB, 100 parts.
            # Or, a simpler cap like initial_num_parts + 10 (max 10 retries)
            max_parts_cap = initial_num_parts + 10 

            split_files = _recursive_split_and_check(file_path, file_size_mb, initial_num_parts, max_parts_cap)
            
            if split_files:
                print(f"文件 {file_name} 成功切割成 {len(split_files)} 个部分，准备发送...")
                for split_file_path in split_files:
                    await send_single_file(context, chat_id, split_file_path)
                    try:
                        os.remove(split_file_path)  # 发送后删除临时文件
                        print(f"已删除切割文件: {split_file_path}")
                    except OSError as e:
                        print(f"删除切割文件 {split_file_path} 失败: {e}")
                try:
                    os.remove(file_path)  # 发送完成后删除原始文件
                    print(f"已删除原始大文件: {file_path}")
                except OSError as e:
                    print(f"删除原始大文件 {file_path} 失败: {e}")
            else:
                print(f"文件 {file_name} 切割失败或超出重试次数，跳过此文件。")
        else:
            await send_single_file(context, chat_id, file_path)
            try:
                os.remove(file_path)  # 发送后删除文件
                print(f"已删除文件: {file_path}")
            except OSError as e:
                print(f"删除文件 {file_path} 失败: {e}")
        
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
    print(f"尝试切割: {os.path.basename(file_path)} 成 {num_parts_to_try} 段 (递归深度: {recursion_depth})")

    if num_parts_to_try <= 0:
        print("错误: num_parts_to_try 无效 (<=0)")
        return []
    if num_parts_to_try > max_parts_cap:
        print(f"错误: 尝试的分段数 ({num_parts_to_try}) 已超过最大允许分段数 ({max_parts_cap})。停止切割。")
        return []
    if recursion_depth >= max_recursion_depth:
        print(f"错误: 已达到最大递归深度 ({max_recursion_depth})。停止切割。")
        return []

    output_segments = []
    base_name, ext = os.path.splitext(file_path)
    segment_pattern = f"{base_name}_%d{ext}" # ffmpeg default is 0-indexed

    try:
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        
        if duration <= 0:
            print(f"错误: 文件 {file_path} 时长无效 ({duration}s)。")
            return []
            
        segment_duration = duration / num_parts_to_try
        if segment_duration < 1: # Avoid segments that are too short (e.g. less than 1s)
            print(f"警告: 计算的段时长 ({segment_duration:.2f}s) 过短 (尝试分成 {num_parts_to_try} 段)。可能导致问题或切割过多。")
            # Potentially add a condition here to stop if segments are too short, e.g., return []
            # For now, let it proceed but be aware.

        print(f"  FFmpeg 参数: input='{file_path}', output='{segment_pattern}', num_parts={num_parts_to_try}, seg_time={segment_duration:.2f}s")
        
        ffmpeg.input(file_path).output(
            segment_pattern,
            format='segment',
            segment_time=segment_duration,
            c='copy',
            reset_timestamps=1
        ).run(quiet=True, overwrite_output=True)

        # Validate segments
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
                    print(f"  失败: 切割段 {segment_name} 大小为 {current_segment_size_mb:.2f}MB (>= 50MB)")
                    all_segments_ok = False
                    break # No need to check further for this attempt
            else:
                print(f"  错误: 预期切割段 {segment_name} 未找到或为空。")
                all_segments_ok = False
                break

        if not all_segments_ok or len(output_segments) != num_parts_to_try:
            print(f"  当前切割尝试 ({num_parts_to_try} 段) 失败。清理临时文件并重试...")
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
        
        print(f"  成功: 文件 {os.path.basename(file_path)} 切割成 {len(output_segments)} 段，最大段大小: {max_segment_size_mb:.2f}MB")
        return output_segments

    except ffmpeg.Error as e:
        print(f"  FFmpeg 错误 (尝试 {num_parts_to_try} 段): {e.stderr.decode('utf8', errors='ignore') if e.stderr else 'N/A'}")
        # Cleanup on ffmpeg error
        for i in range(num_parts_to_try + 2):
            segment_name = f"{base_name}_{i}{ext}"
            if os.path.exists(segment_name):
                try: os.remove(segment_name)
                except OSError: pass
        return [] # Indicate failure for this path
    except Exception as e:
        print(f"  意外错误 (尝试 {num_parts_to_try} 段): {type(e).__name__} - {str(e)}")
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
        print(f"错误: 文件 {file_path} 不存在或为空，跳过发送。")
        return

    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"正在发送文件: {os.path.basename(file_path)}, 大小: {file_size_mb:.2f} MB")
        
        file_name_for_meta = os.path.basename(file_path)
        base_for_meta, ext_for_meta = os.path.splitext(file_name_for_meta)
        
        parts = base_for_meta.split('.')
        performer = "Unknown"
        title = base_for_meta # Default title to base filename if parsing fails

        if len(parts) >= 2:
            performer = parts[0]
            # Join all parts after the first as the title, then remove trailing _segmentNumber
            title_candidate = ".".join(parts[1:])
            title_parts = title_candidate.split('_')
            if len(title_parts) > 1 and title_parts[-1].isdigit():
                title = "_".join(title_parts[:-1]) + f" (Part {int(title_parts[-1]) + 1})" # Make it 1-indexed for display
            else:
                title = title_candidate
        elif len(parts) == 1: # Only one part, likely the title itself, performer unknown
            title_candidate = parts[0]
            title_parts = title_candidate.split('_')
            if len(title_parts) > 1 and title_parts[-1].isdigit():
                title = "_".join(title_parts[:-1]) + f" (Part {int(title_parts[-1]) + 1})" # Make it 1-indexed for display
            else:
                title = title_candidate


        with open(file_path, 'rb') as file_to_send:
            with suppress(TimedOut):
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=file_to_send,
                    title=title,
                    performer=performer,
                    # Consider adding duration if easily obtainable from ffmpeg.probe and passing it
                )
        print(f"文件 {os.path.basename(file_path)} 发送成功")
    except TelegramError as te:
        print(f"发送文件 {os.path.basename(file_path)} 时发生 Telegram 错误: {str(te)}")
        # Do not remove the file if sending failed, so it can be retried
    except FileNotFoundError:
        print(f"错误: 文件 {file_path} 在发送前找不到了。可能已被其他进程删除。")
    except Exception as e:
        print(f"发送文件 {os.path.basename(file_path)} 时发生意外错误: {type(e).__name__} - {str(e)}")
        # Do not remove the file if sending failed
