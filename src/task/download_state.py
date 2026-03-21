# -*- coding: utf-8 -*-
import logging
import os
from typing import Optional

from config import COOKIES_FILE, DOWNLOAD_ARCHIVE, get_config_provider
from logger import TRACE_LEVEL, get_logger, log_with_context

logger = get_logger('downloader.dl_audio')


def record_download_entry(video_id: str, channel_name: Optional[str]) -> None:
    """把成功下载的视频记录到配置提供者（本地/Notion），避免重复下载。"""
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
    """从 Provider 同步已下载记录到本地文件，供 yt-dlp 使用。"""
    try:
        provider = get_config_provider()
        if not provider:
            return

        if provider.__class__.__name__ != 'NotionConfigProvider':
            return

        fetch_method = getattr(provider, "_load_download_archive", None)
        if not callable(fetch_method):
            return

        notion_records = fetch_method()
        if not notion_records:
            return

        local_records = set()
        if os.path.exists(DOWNLOAD_ARCHIVE):
            try:
                with open(DOWNLOAD_ARCHIVE, 'r', encoding='utf-8') as file:
                    for line in file:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if parts:
                                local_records.add(parts[-1])
            except Exception:
                pass

        new_records = notion_records - local_records
        if new_records:
            logger.info(f"📥 从 Notion 同步了 {len(new_records)} 条下载历史到本地 Archive")
            os.makedirs(os.path.dirname(DOWNLOAD_ARCHIVE), exist_ok=True)
            with open(DOWNLOAD_ARCHIVE, 'a', encoding='utf-8') as file:
                for video_id in new_records:
                    file.write(f"youtube {video_id}\n")

    except Exception as err:
        logger.warning(f"同步下载存档失败: {err}")


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
        if is_notion_mode and not os.path.exists(COOKIES_FILE):
            logger.warning("Notion 中未配置 Cookies，且本地无 Cookies 文件，下载可能会受限")
        return os.path.exists(COOKIES_FILE)

    target_dir = os.path.dirname(COOKIES_FILE)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as file:
            file.write(content)
        logger.info(f"🍪 已从 Notion 同步 Cookies 至本地: {COOKIES_FILE}")
        return True
    except Exception as err:
        logger.error(f"写入 cookies 文件失败: {err}")
        return os.path.exists(COOKIES_FILE)


def check_cookies():
    """检查 cookies 文件是否存在且可用。"""
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
