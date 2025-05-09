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
            split_files = split_audio_file(file_path, file_size_mb)
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
                print(f"文件 {file_name} 切割失败，跳过此文件。")
                # Optionally, decide what to do with the original large file if splitting fails
                # For now, we leave it, but you might want to move it to an error folder
        else:
            await send_single_file(context, chat_id, file_path)
            try:
                os.remove(file_path)  # 发送后删除文件
                print(f"已删除文件: {file_path}")
            except OSError as e:
                print(f"删除文件 {file_path} 失败: {e}")
        
        break  # 每次任务只处理一个原始文件（或其分片）

def split_audio_file(file_path, file_size_mb):
    """
    使用 ffmpeg-python 将大文件切割成多个部分，每个部分小于 50MB
    返回切割后的文件路径列表
    """
    output_files = []
    try:
        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        
        # Use 45MB as the target segment size to be safe with Telegram's 50MB limit
        target_segment_size_mb = 45 
        num_parts = math.ceil(file_size_mb / target_segment_size_mb)
        
        # Always add one more part to be safer with VBR files
        # This ensures shorter segment durations
        num_parts += 1

        if num_parts <= 1: # Should not happen if file_size_mb > 49 and we add 1
             print(f"警告: 计算出的分段数 ({num_parts}) 不大于1，即使文件大小 ({file_size_mb:.2f}MB) 超过限制。将尝试按原样发送。")
             return [file_path] # Return original path to be sent as is, though it might fail.

        segment_duration = duration / num_parts
        
        base_name, ext = os.path.splitext(file_path)
        
        # Generate expected output filenames (ffmpeg's segmenter is 0-indexed with %d)
        # However, we'll rename them to 1-indexed for clarity if needed or use as is.
        # For simplicity, let's stick to ffmpeg's default output name and then list them.
        # The output pattern ffmpeg uses for segment is base_name%d.ext (0-indexed)
        # We will generate a list of *expected* names to check against later.
        
        output_pattern = f"{base_name}_%d{ext}" # ffmpeg will create base_name_0.ext, base_name_1.ext ...
        
        print(f"FFmpeg 切割参数: input='{file_path}', output='{output_pattern}', segment_time='{segment_duration}'")

        ffmpeg.input(file_path).output(
            output_pattern,
            format='segment',
            segment_time=segment_duration,
            c='copy', # Use stream copy for speed if format is compatible
            reset_timestamps=1 # Helpful for segments
        ).run(quiet=True, overwrite_output=True) # quiet=False for debugging ffmpeg

        # After ffmpeg runs, list the files created based on the pattern
        # ffmpeg creates base_name_0.ext, base_name_1.ext ... base_name_N-1.ext
        for i in range(num_parts):
            # ffmpeg by default creates base_name_0.ext, base_name_1.ext etc.
            # The output_pattern for ffmpeg.output already handles the %d
            # So we just need to construct the names it *should* have created.
            potential_segment_name = f"{base_name}_{i}{ext}" # Files like filename_0.mp3, filename_1.mp3
            if os.path.exists(potential_segment_name) and os.path.getsize(potential_segment_name) > 0:
                output_files.append(potential_segment_name)
            else:
                # If a segment is missing or empty, it's a failure
                print(f"错误: 预期切割文件 {potential_segment_name} 未找到或为空。切割失败。")
                # Cleanup any segments that were created before the error
                for f_to_delete in output_files: # output_files only contains successfully created ones so far
                    try:
                        os.remove(f_to_delete)
                        print(f"已清理部分切割文件: {f_to_delete}")
                    except OSError as e:
                        print(f"清理部分切割文件 {f_to_delete} 失败: {e}")
                # Also cleanup ffmpeg's other possible outputs if the pattern was different
                for k in range(num_parts): # Check for base_name_0, base_name_1 ...
                    temp_name_to_check = f"{base_name}_{k}{ext}"
                    if os.path.exists(temp_name_to_check) and temp_name_to_check not in output_files:
                        try:
                            os.remove(temp_name_to_check)
                            print(f"已清理额外切割文件: {temp_name_to_check}")
                        except OSError as e:
                             print(f"清理额外切割文件 {temp_name_to_check} 失败: {e}")
                return [] # Indicate failure

        if not output_files or len(output_files) != num_parts :
            print(f"错误: 切割后文件的数量 ({len(output_files)}) 与预期数量 ({num_parts}) 不符。")
            # Cleanup
            for f_to_delete in output_files:
                try:
                    os.remove(f_to_delete)
                except OSError: pass
            for k in range(num_parts): # Check for base_name_0, base_name_1 ...
                    temp_name_to_check = f"{base_name}_{k}{ext}"
                    if os.path.exists(temp_name_to_check) and temp_name_to_check not in output_files:
                        try:
                            os.remove(temp_name_to_check)
                        except OSError: pass
            return []

        print(f"文件 {file_path} 已成功切割成 {len(output_files)} 个部分: {output_files}")
        return output_files

    except ffmpeg.Error as e:
        print(f"FFmpeg 切割文件 {file_path} 时出错:")
        print(f"  FFmpeg stdout: {e.stdout.decode('utf8', errors='ignore') if e.stdout else 'N/A'}")
        print(f"  FFmpeg stderr: {e.stderr.decode('utf8', errors='ignore') if e.stderr else 'N/A'}")
        # Cleanup any partially created files by ffmpeg based on the expected pattern
        base_name, ext = os.path.splitext(file_path)
        # num_parts might not be calculated if error was before it, assume a reasonable max to check
        # Or better, just check for files matching base_name_*.ext pattern
        # This is a bit tricky as we don't know how many it *tried* to make.
        # Let's just iterate through what might exist if num_parts was calculated
        if 'num_parts' in locals():
            for i in range(num_parts):
                potential_segment_name = f"{base_name}_{i}{ext}"
                if os.path.exists(potential_segment_name):
                    try:
                        os.remove(potential_segment_name)
                        print(f"已清理FFmpeg错误后残留文件: {potential_segment_name}")
                    except OSError as ose:
                        print(f"清理FFmpeg错误后残留文件 {potential_segment_name} 失败: {ose}")
        return []
    except Exception as e:
        print(f"切割文件 {file_path} 时发生意外错误: {type(e).__name__} - {str(e)}")
        # Similar cleanup for unexpected errors
        base_name, ext = os.path.splitext(file_path)
        if 'num_parts' in locals():
            for i in range(num_parts):
                potential_segment_name = f"{base_name}_{i}{ext}"
                if os.path.exists(potential_segment_name):
                    try:
                        os.remove(potential_segment_name)
                        print(f"已清理意外错误后残留文件: {potential_segment_name}")
                    except OSError as ose:
                        print(f"清理意外错误后残留文件 {potential_segment_name} 失败: {ose}")
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
