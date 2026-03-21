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
from util import get_channel_groups_with_details
from config import ENV_FILE, get_download_interval, get_channel_delay_min, get_channel_delay_max, get_config_check_interval
from logger import get_logger, log_with_context
import logging
from runtime_guard import install_runtime_diagnostics
from runtime_state import ProcessHeartbeat

# 使用统一的日志系统
logger = get_logger('downloader', separate_error_file=True)
mark_runtime_shutdown = install_runtime_diagnostics(logger, "downloader")
heartbeat = ProcessHeartbeat("downloader")
heartbeat.start()

# 加载环境变量（如果使用传统配置）
load_dotenv(ENV_FILE)

# 从配置获取下载间隔
DOWNLOAD_INTERVAL = get_download_interval()
logger.info(f"下载间隔配置：{DOWNLOAD_INTERVAL} 秒 ({DOWNLOAD_INTERVAL/3600:.2f} 小时)")


def _group_name(group):
    return group.get('name', 'story')


def _group_channels(group):
    return group.get('youtube_channels', [])


def _group_audio_folder(group):
    return group.get('audio_folder')


def _group_channel_type(group):
    return group.get('channel_type')


def _group_story_interval(group):
    return int(group.get('story_interval_seconds', 86400))


def _group_story_items_per_run(group):
    return int(group.get('story_items_per_run', 1))


def _group_story_last_run_ts(group):
    return group.get('story_last_run_ts')


def _build_realtime_channel_item(channel, group_name, audio_folder):
    return {
        'channel': channel,
        'group_name': group_name,
        'audio_folder': audio_folder,
    }


def _build_story_task(group, items_per_run):
    channels = _group_channels(group)
    return {
        'group_name': _group_name(group),
        'audio_folder': _group_audio_folder(group),
        'channel': channels[0] if channels else None,
        'items_per_run': items_per_run,
    }


def _build_realtime_group_iterator(group):
    channels = _group_channels(group)
    return {
        'group_name': _group_name(group),
        'audio_folder': _group_audio_folder(group),
        'channels': channels[:],
        'index': 0,
    }


def build_realtime_channel_tasks(channel_groups):
    """
    将多个频道组的频道交替穿插，确保每个组都能及时得到处理
    
    策略：按比例轮询，确保较小的频道组不会等待太久
    
    Args:
        channel_groups: 频道组列表
    
    Returns:
        交替排列的频道任务列表
    """
    group_iterators = [
        _build_realtime_group_iterator(group)
        for group in channel_groups
        if _group_channels(group)
    ]
    
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
            result.append(
                _build_realtime_channel_item(
                    channel=channel,
                    group_name=group_iter['group_name'],
                    audio_folder=group_iter['audio_folder'],
                )
            )
            group_iter['index'] += 1
        
        # 移到下一个组
        current_group_idx = (current_group_idx + 1) % len(group_iterators)
    
    return result


def _sleep_before_channel(idx, total_channels, channel, group_name=None):
    delay_min = get_channel_delay_min()
    delay_max = get_channel_delay_max()
    if delay_max <= 0 or idx <= 1:
        return

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


def _run_latest_channel_task(task, idx, total_channels):
    channel = task['channel']
    group_name = task.get('group_name')
    audio_folder = task.get('audio_folder')

    _sleep_before_channel(idx, total_channels, channel, group_name)

    log_with_context(
        logger,
        logging.INFO,
        f"▶️ 处理频道 [{idx}/{total_channels}]",
        tg_channel=group_name,
        yt_channel=channel
    )
    heartbeat.update(
        "processing_channel",
        index=idx,
        total=total_channels,
        tg_channel=group_name,
        yt_channel=channel,
    )

    dl_audio_latest(
        channel_name=channel,
        audio_folder=audio_folder,
        group_name=group_name
    )


def _collect_story_due_state(story_groups, story_last_run, now_ts):
    story_due_min = None
    story_due_name = None
    due_story_groups = []

    for group in story_groups:
        group_name = _group_name(group)
        interval = _group_story_interval(group)
        items_per_run = _group_story_items_per_run(group)
        last_run_ts = _group_story_last_run_ts(group)
        if last_run_ts is None:
            last_run_ts = story_last_run.get(group_name, 0)
        due_in = interval - (now_ts - last_run_ts)

        if due_in <= 0:
            due_story_groups.append(_build_story_task(group, items_per_run))
            due_in = interval

        if story_due_min is None or due_in < story_due_min:
            story_due_min = due_in
            story_due_name = group_name

    return due_story_groups, story_due_min, story_due_name


def _run_due_story_groups(due_story_groups, story_last_run):
    story_delay_min = get_channel_delay_min()
    story_delay_max = get_channel_delay_max()

    for idx, task in enumerate(due_story_groups):
        if idx > 0 and story_delay_max >= story_delay_min and story_delay_max > 0:
            c_delay = random.uniform(story_delay_min, story_delay_max)
            log_with_context(
                logger,
                logging.INFO,
                "故事频道间延迟",
                tg_channel=task['group_name'],
                delay_seconds=round(c_delay, 2)
            )
            time.sleep(c_delay)

        group_name = task['group_name']
        channel = task['channel']
        if not channel:
            logger.warning(f"故事模式 {group_name} 未配置 YouTube 频道")
            continue

        log_with_context(
            logger,
            logging.INFO,
            "📚 故事模式下载",
            tg_channel=group_name,
            yt_channel=channel,
            items=task['items_per_run']
        )
        dl_audio_story(
            channel_name=channel,
            audio_folder=task['audio_folder'],
            group_name=group_name,
            items_per_run=task['items_per_run']
        )
        story_last_run[group_name] = time.time()


def _run_realtime_groups(realtime_groups):
    if not realtime_groups:
        logger.info("当前没有实时型频道组需要下载")
        return None

    total_channels = sum(len(_group_channels(group)) for group in realtime_groups)
    log_with_context(
        logger,
        logging.INFO,
        "刷新实时频道列表",
        group_count=len(realtime_groups),
        total_channels=total_channels
    )
    dl_youtube_multi_groups(realtime_groups)
    return time.time()


def _build_wait_context(realtime_due, story_due_min, story_due_name):
    wait_candidates = []
    next_realtime_due = None

    if DOWNLOAD_INTERVAL > 0:
        next_realtime_due = DOWNLOAD_INTERVAL if realtime_due <= 0 else realtime_due
        wait_candidates.append(next_realtime_due)
    if story_due_min is not None:
        wait_candidates.append(max(1, story_due_min))
    if not wait_candidates:
        wait_candidates.append(60)

    config_check_interval = get_config_check_interval()
    wait_candidates.append(config_check_interval)

    wait_time = max(1, min(wait_candidates))
    wait_context = {
        "wait_seconds": wait_time,
        "wait_hours": round(wait_time / 3600, 2),
    }
    if next_realtime_due is not None:
        wait_context["next_realtime_seconds"] = round(next_realtime_due, 2)
    if story_due_name is not None and story_due_min is not None:
        wait_context["next_story"] = story_due_name
        wait_context["next_story_seconds"] = round(story_due_min, 2)
    if wait_time == config_check_interval:
        wait_context["reason"] = "config_check"

    return wait_time, wait_context


def _build_wait_log_signature(wait_context):
    next_realtime = wait_context.get("next_realtime_seconds")
    next_story = wait_context.get("next_story_seconds")
    reason = wait_context.get("reason")

    if next_realtime is None:
        realtime_bucket = None
    elif next_realtime > 300:
        realtime_bucket = int(next_realtime // 60)
    elif next_realtime > 60:
        realtime_bucket = int(next_realtime // 30)
    else:
        realtime_bucket = int(next_realtime // 10)

    if next_story is None:
        story_bucket = None
    elif next_story > 3600:
        story_bucket = int(next_story // 1800)
    elif next_story > 600:
        story_bucket = int(next_story // 300)
    else:
        story_bucket = int(next_story // 60)

    return (reason, wait_context["wait_seconds"], realtime_bucket, story_bucket)


def dl_youtube_multi_groups(channel_groups) -> None:
    """
    为多个频道组下载 YouTube 音频（支持频道穿插）
    
    Args:
        channel_groups: 频道组列表，每个组包含 youtube_channels, audio_folder, name 等信息
    """
    # 统计所有频道总数
    total_channels = sum(len(_group_channels(group)) for group in channel_groups)
    
    logger.info(f"🚀 开始批量下载，共 {len(channel_groups)} 个频道组，{total_channels} 个YouTube频道")
    logger.info(f"⏱️ 频道间延迟：{get_channel_delay_min()}-{get_channel_delay_max()}秒（随机）")
    
    # 显示各组信息
    for group in channel_groups:
        channels = _group_channels(group)
        if channels:
            log_with_context(
                logger,
                logging.INFO,
                f"📋 频道组配置",
                group_name=_group_name(group),
                channel_count=len(channels),
                audio_folder=_group_audio_folder(group)
            )
    
    # 将频道穿插排列为标准任务项
    interleaved_channels = build_realtime_channel_tasks(channel_groups)
    
    logger.info(f"🔁 已优化下载顺序：多个频道组交替进行，确保及时性")
    
    # 按穿插后的顺序处理
    for idx, task in enumerate(interleaved_channels, 1):
        try:
            _run_latest_channel_task(
                task=task,
                idx=idx,
                total_channels=total_channels,
            )
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                f"❌ 下载频道失败",
                tg_channel=task.get('group_name'),
                yt_channel=task['channel'],
                error=str(e),
                error_type=type(e).__name__
            )
            continue
    
def dl_youtube(channels) -> None:
    """下载 YouTube 频道的音频（向后兼容的旧接口）"""
    logger.info(f"🚀 开始批量下载，共 {len(channels)} 个频道")

    for idx, channel in enumerate(channels, 1):
        try:
            _run_latest_channel_task(
                task=_build_realtime_channel_item(
                    channel=channel,
                    group_name=None,
                    audio_folder=None,
                ),
                idx=idx,
                total_channels=len(channels),
            )
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                f"❌ 下载频道失败",
                yt_channel=channel,
                error=str(e),
                error_type=type(e).__name__
            )
            continue
    

def main():
    logger.info("YouTube 下载调度器")
    heartbeat.update("scheduler_started")
    story_last_run = {}
    last_realtime_run_ts = 0  # 首次启动立即跑实时型
    last_wait_log_signature = None

    while True:
        try:
            channel_groups = get_channel_groups_with_details(reload=True)

            if not channel_groups:
                logger.warning("未找到任何频道分组配置")
                time.sleep(60)
                continue

            realtime_groups = [g for g in channel_groups if _group_channel_type(g) != 'story']
            story_groups = [g for g in channel_groups if _group_channel_type(g) == 'story']

            now_ts = time.time()

            # 计算实时型到期
            next_realtime_due = None
            if DOWNLOAD_INTERVAL > 0:
                realtime_due = max(0, DOWNLOAD_INTERVAL - (now_ts - last_realtime_run_ts))
                next_realtime_due = realtime_due
            else:
                realtime_due = 0

            due_story_groups, story_due_min, story_due_name = _collect_story_due_state(
                story_groups,
                story_last_run,
                now_ts,
            )

            # 运行实时型（仅到期才跑）
            if realtime_due <= 0 and realtime_groups:
                last_realtime_run_ts = _run_realtime_groups(realtime_groups)
            elif not realtime_groups:
                logger.info("当前没有实时型频道组需要下载")

            # 运行到期的故事型
            if due_story_groups:
                _run_due_story_groups(due_story_groups, story_last_run)

            wait_time, wait_context = _build_wait_context(
                realtime_due,
                story_due_min,
                story_due_name,
            )

            wait_signature = _build_wait_log_signature(wait_context)
            if wait_signature != last_wait_log_signature:
                log_with_context(
                    logger,
                    logging.INFO,
                    "等待下一轮",
                    **wait_context
                )
                last_wait_log_signature = wait_signature
            heartbeat.update("waiting", **wait_context)
            time.sleep(wait_time)

        except KeyboardInterrupt:
            mark_runtime_shutdown("keyboard_interrupt", expected=True)
            heartbeat.stop("keyboard_interrupt")
            logger.info("收到停止信号，准备退出...")
            break
        except Exception as e:
            heartbeat.update("loop_exception", error=str(e), error_type=type(e).__name__)
            logger.exception("调度循环出现未预期的错误")
            time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    finally:
        heartbeat.stop("main_return")
        mark_runtime_shutdown("main_return", expected=True)
