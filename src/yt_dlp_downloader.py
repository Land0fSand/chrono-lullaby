# -*- coding: utf-8 -*-
import os
import sys
import random
import time

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from task.dl_audio import dl_audio_latest, dl_audio_story
from util import refresh_channels_from_file, get_channel_groups_with_details
from config import ENV_FILE, get_download_interval, get_channel_delay_min, get_channel_delay_max
from logger import get_logger, log_with_context, TRACE_LEVEL
import logging

# 使用统一的日志系统
logger = get_logger('downloader', separate_error_file=True)

# 加载环境变量（如果使用传统配置）
load_dotenv(ENV_FILE)

# 从配置获取下载间隔
DOWNLOAD_INTERVAL = get_download_interval()
logger.info(f"下载间隔配置：{DOWNLOAD_INTERVAL} 秒 ({DOWNLOAD_INTERVAL/3600:.2f} 小时)")

def interleave_channels(channel_groups):
    """
    将多个频道组的频道交替穿插，确保每个组都能及时得到处理
    
    策略：按比例轮询，确保较小的频道组不会等待太久
    
    Args:
        channel_groups: 频道组列表
    
    Returns:
        交替排列的频道列表，每个元素包含 (channel_name, group_name, audio_folder)
    """
    # 准备每个组的频道迭代器
    group_iterators = []
    for group in channel_groups:
        if not group['youtube_channels']:
            continue
        group_iterators.append({
            'name': group['name'],
            'audio_folder': group['audio_folder'],
            'channels': group['youtube_channels'][:],  # 复制列表
            'index': 0
        })
    
    if not group_iterators:
        return []
    
    result = []
    total_channels = sum(len(g['channels']) for g in group_iterators)
    
    # 使用轮询方式交替选择
    current_group_idx = 0
    while len(result) < total_channels:
        group_iter = group_iterators[current_group_idx]
        
        # 如果当前组还有频道未处理
        if group_iter['index'] < len(group_iter['channels']):
            channel = group_iter['channels'][group_iter['index']]
            result.append({
                'channel': channel,
                'group_name': group_iter['name'],
                'audio_folder': group_iter['audio_folder']
            })
            group_iter['index'] += 1
        
        # 移到下一个组
        current_group_idx = (current_group_idx + 1) % len(group_iterators)
    
    return result

def dl_youtube_multi_groups(channel_groups) -> None:
    """
    为多个频道组下载 YouTube 音频（支持频道穿插）
    
    Args:
        channel_groups: 频道组列表，每个组包含 youtube_channels, audio_folder, name 等信息
    """
    # 统计所有频道总数
    total_channels = sum(len(group['youtube_channels']) for group in channel_groups)
    
    # 获取延迟配置
    delay_min = get_channel_delay_min()
    delay_max = get_channel_delay_max()
    
    logger.info(f"开始批量下载，共 {len(channel_groups)} 个频道组，{total_channels} 个YouTube频道")
    logger.info(f"频道间延迟：{delay_min}-{delay_max}秒（随机）")
    
    # 显示各组信息
    for group in channel_groups:
        if group['youtube_channels']:
            log_with_context(
                logger,
                logging.INFO,
                f"频道组配置",
                group_name=group['name'],
                channel_count=len(group['youtube_channels']),
                audio_folder=group['audio_folder']
            )
    
    # 将频道穿插排列
    interleaved_channels = interleave_channels(channel_groups)
    
    logger.info(f"已优化下载顺序：多个频道组交替进行，确保及时性")
    
    # 按穿插后的顺序处理
    for idx, item in enumerate(interleaved_channels, 1):
        channel = item['channel']
        group_name = item['group_name']
        audio_folder = item['audio_folder']
        
        try:
            # 频道间延迟（如果配置了的话）
            if delay_max > 0 and idx > 1:  # 第一个频道不延迟
                delay = random.uniform(delay_min, delay_max)
                log_with_context(
                    logger,
                    logging.INFO,
                    f"⏳ 频道间延迟 - 准备处理频道 [{idx}/{total_channels}]",
                    tg_channel=group_name,
                    yt_channel=channel,
                    delay_seconds=round(delay, 2)
                )
                time.sleep(delay)
            
            log_with_context(
                logger,
                logging.INFO,
                f"处理频道 [{idx}/{total_channels}]",
                tg_channel=group_name,
                yt_channel=channel
            )
            
            dl_audio_latest(
                channel_name=channel,
                audio_folder=audio_folder,
                group_name=group_name
            )
            
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                f"下载频道失败",
                tg_channel=group_name,
                yt_channel=channel,
                error=str(e),
                error_type=type(e).__name__
            )
            continue
    
    logger.info("本轮下载任务完成")

def dl_youtube(channels) -> None:
    """下载 YouTube 频道的音频（向后兼容的旧接口）"""
    logger.info(f"开始批量下载，共 {len(channels)} 个频道")
    
    # 从配置读取频道间延迟
    delay_min = get_channel_delay_min()
    delay_max = get_channel_delay_max()
    
    for idx, channel in enumerate(channels, 1):
        try:
            # 频道间延迟（如果配置了的话）
            if delay_max > 0 and idx > 1:  # 第一个频道不延迟
                delay = random.uniform(delay_min, delay_max)
                log_with_context(
                    logger,
                    logging.INFO,
                    f"⏳ 频道间延迟 - 处理频道 [{idx}/{len(channels)}]",
                    yt_channel=channel,
                    delay_seconds=round(delay, 2)
                )
                time.sleep(delay)
            
            log_with_context(
                logger,
                logging.INFO,
                f"处理频道 [{idx}/{len(channels)}]",
                yt_channel=channel
            )
            
            dl_audio_latest(channel_name=channel)
            
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                f"下载频道失败",
                yt_channel=channel,
                error=str(e),
                error_type=type(e).__name__
            )
            continue
    
    logger.info("本轮下载任务完成")


def main():
    logger.info("YouTube 下载调度器")
    story_last_run = {}
    last_realtime_run_ts = 0  # 首次启动立即跑实时型

    while True:
        try:
            channel_groups = get_channel_groups_with_details(reload=True)

            if not channel_groups:
                logger.warning("未找到任何频道分组配置")
                time.sleep(60)
                continue

            realtime_groups = [g for g in channel_groups if g.get('channel_type') != 'story']
            story_groups = [g for g in channel_groups if g.get('channel_type') == 'story']

            now_ts = time.time()

            # 计算实时型到期
            if DOWNLOAD_INTERVAL > 0:
                realtime_due = max(0, DOWNLOAD_INTERVAL - (now_ts - last_realtime_run_ts))
            else:
                realtime_due = 0

            # 计算故事型最早到期
            story_due_min = None
            due_story_groups = []
            for group in story_groups:
                group_name = group.get('name', 'story')
                interval = int(group.get('story_interval_seconds', 86400))
                items_per_run = int(group.get('story_items_per_run', 1))
                last_run_ts = group.get('story_last_run_ts')
                if last_run_ts is None:
                    last_run_ts = story_last_run.get(group_name, 0)
                due_in = interval - (now_ts - last_run_ts)

                if due_in <= 0:
                    due_story_groups.append((group, items_per_run))
                    due_in = interval  # 下次到期时间

                if story_due_min is None or due_in < story_due_min:
                    story_due_min = due_in

            # 运行实时型（仅到期才跑）
            if realtime_due <= 0 and realtime_groups:
                total_channels = sum(len(group['youtube_channels']) for group in realtime_groups)
                log_with_context(
                    logger,
                    logging.INFO,
                    "刷新实时频道列表",
                    group_count=len(realtime_groups),
                    total_channels=total_channels
                )
                dl_youtube_multi_groups(realtime_groups)
                last_realtime_run_ts = time.time()
            elif not realtime_groups:
                logger.info("当前没有实时型频道组需要下载")

            # 运行到期的故事型
            if due_story_groups:
                story_delay_min = get_channel_delay_min()
                story_delay_max = get_channel_delay_max()
                for idx, (group, items_per_run) in enumerate(due_story_groups):
                    if idx > 0 and story_delay_max >= story_delay_min and story_delay_max > 0:
                        c_delay = random.uniform(story_delay_min, story_delay_max)
                        log_with_context(
                            logger,
                            logging.INFO,
                            "故事频道间延迟",
                            tg_channel=group.get('name', 'story'),
                            delay_seconds=round(c_delay, 2)
                        )
                        time.sleep(c_delay)

                    group_name = group.get('name', 'story')
                    yt_list = group.get('youtube_channels', [])
                    if not yt_list:
                        logger.warning(f"故事模式 {group_name} 未配置 YouTube 频道")
                        continue
                    channel = yt_list[0]
                    log_with_context(
                        logger,
                        logging.INFO,
                        "故事模式下载",
                        tg_channel=group_name,
                        yt_channel=channel,
                        items=items_per_run
                    )
                    dl_audio_story(
                        channel_name=channel,
                        audio_folder=group.get('audio_folder'),
                        group_name=group_name,
                        items_per_run=items_per_run
                    )
                    story_last_run[group_name] = time.time()

            # 计算下一次睡眠
            wait_candidates = []
            if DOWNLOAD_INTERVAL > 0:
                next_realtime_due = DOWNLOAD_INTERVAL if realtime_due <= 0 else realtime_due
                wait_candidates.append(next_realtime_due)
            if story_due_min is not None:
                wait_candidates.append(max(1, story_due_min))
            if not wait_candidates:
                wait_candidates.append(60)

            wait_time = max(1, min(wait_candidates))
            log_with_context(
                logger,
                logging.INFO,
                "等待下一轮",
                wait_seconds=wait_time,
                wait_hours=round(wait_time / 3600, 2)
            )
            time.sleep(wait_time)

        except KeyboardInterrupt:
            logger.info("收到停止信号，准备退出...")
            break
        except Exception as e:
            logger.exception("调度循环出现未预期的错误")
            time.sleep(60)


if __name__ == "__main__":
    main() 
