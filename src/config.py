# -*- coding: utf-8 -*-
import os
import sys
import yaml
from typing import Optional, Dict, Any, List

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv

# 延迟导入系统日志以避免循环依赖
_sys_logger = None

def _get_sys_logger():
    """延迟初始化系统日志"""
    global _sys_logger
    if _sys_logger is None:
        try:
            from logger import get_system_logger
            _sys_logger = get_system_logger()
        except Exception:
            # 如果导入失败，使用None
            pass
    return _sys_logger

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 配置提供者管理
# ============================================================
_config_provider = None  # 全局配置提供者实例

# ============================================================
# 配置文件路径
# ============================================================
CONFIG_YAML_FILE = os.path.join(PROJECT_ROOT, "config", "config.yaml")
CHANNELS_FILE = os.path.join(PROJECT_ROOT, "config", "channels.txt")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
DEBUG_INFO = os.path.join(PROJECT_ROOT, "debug_closest_video.json")
STORY_FILE = os.path.join(PROJECT_ROOT, "story.txt")
STORY_PROGRESS_FILE = os.path.join(PROJECT_ROOT, "data", "story_progress.json")

# ============================================================
# 配置源初始化
# ============================================================

def init_config_provider(mode_override: Optional[str] = None):
    """
    初始化配置提供者
    
    Args:
        mode_override: 覆盖配置文件中的模式（'local' 或 'notion'）
    """
    global _config_provider
    
    # 加载基础配置（先加载配置，避免循环依赖）
    config = load_yaml_config()
    
    # 配置加载完成后，才能安全地使用系统日志
    sys_logger = _get_sys_logger()
    
    if sys_logger:
        sys_logger.debug("开始初始化配置提供者", extra={'extra_data': {'mode_override': mode_override}})
    
    if config is None:
        # 回退到本地模式
        from config_provider import LocalConfigProvider
        _config_provider = LocalConfigProvider(PROJECT_ROOT, CONFIG_YAML_FILE)
        if sys_logger:
            sys_logger.info("配置文件不存在，使用本地配置提供者")
        return
    
    # 确定配置模式
    legacy_source = config.get('config_source', {})
    mode = mode_override or config.get('mode') or legacy_source.get('mode', 'local')
    
    if sys_logger:
        from logger import log_with_context
        import logging
        log_with_context(
            sys_logger, logging.INFO,
            "确定配置模式",
            mode=mode,
            override=mode_override is not None,
            source="override" if mode_override else "config file"
        )

    if mode == 'notion':
        # Notion 模式
        try:
            from notion_adapter import NotionAdapter
            from config_provider import NotionConfigProvider
            
            notion_config = config.get('notion', {})
            if not notion_config:
                notion_config = legacy_source.get('notion', {})
            api_key = notion_config.get('api_key')
            
            if not api_key or api_key == 'secret_xxxxx':
                print("错误：Notion API Key 未配置，降级到本地模式")
                if sys_logger:
                    sys_logger.warning("Notion API Key 未配置，降级到本地模式")
                from config_provider import LocalConfigProvider
                _config_provider = LocalConfigProvider(PROJECT_ROOT, CONFIG_YAML_FILE)
                return
            
            # 创建 Notion 适配器
            adapter = NotionAdapter(api_key)
            _config_provider = NotionConfigProvider(adapter, notion_config)
            print("✅ 使用 Notion 远程配置模式")
            if sys_logger:
                from logger import log_with_context
                import logging
                log_with_context(
                    sys_logger, logging.INFO,
                    "Notion 配置提供者初始化成功",
                    page_id=notion_config.get('page_id', 'N/A')[:8] + '...'
                )
            
        except Exception as e:
            print(f"错误：初始化 Notion 配置提供者失败: {e}")
            print("降级到本地模式")
            if sys_logger:
                from logger import log_with_context
                import logging
                log_with_context(
                    sys_logger, logging.ERROR,
                    "Notion 配置提供者初始化失败，降级到本地模式",
                    error=str(e),
                    error_type=type(e).__name__
                )
            from config_provider import LocalConfigProvider
            _config_provider = LocalConfigProvider(PROJECT_ROOT, CONFIG_YAML_FILE)
    else:
        # 本地模式
        from config_provider import LocalConfigProvider
        _config_provider = LocalConfigProvider(PROJECT_ROOT, CONFIG_YAML_FILE)
        print("✅ 使用本地配置模式")
        if sys_logger:
            sys_logger.info("本地配置提供者初始化成功")


def get_config_provider():
    """
    获取配置提供者实例
    
    Returns:
        配置提供者实例
    """
    global _config_provider
    if _config_provider is None:
        init_config_provider()
    return _config_provider


# ============================================================
# YAML 配置加载
# ============================================================
_config_cache: Optional[Dict[str, Any]] = None

def load_yaml_config(reload: bool = False) -> Optional[Dict[str, Any]]:
    """
    加载 YAML 配置文件
    
    Args:
        reload: 是否强制重新加载配置（不使用缓存）
    
    Returns:
        配置字典，如果文件不存在或加载失败则返回 None
    
    注意：此函数不使用系统日志，因为它是最底层的配置加载函数，
    系统日志初始化时会调用此函数读取日志配置，会形成循环依赖。
    """
    global _config_cache
    
    if _config_cache is not None and not reload:
        return _config_cache
    
    if not os.path.exists(CONFIG_YAML_FILE):
        return None
    
    try:
        with open(CONFIG_YAML_FILE, 'r', encoding='utf-8') as f:
            _config_cache = yaml.safe_load(f)
            return _config_cache
    except Exception as e:
        print(f"警告：加载 config.yaml 失败: {e}")
        print("将回退到使用 channels.txt 和 .env")
        return None

def get_config_value(key_path: str, default: Any = None, reload: bool = False) -> Any:
    """
    从 YAML 配置中获取值，支持点号路径
    
    Args:
        key_path: 配置键路径，如 "telegram.bot_token"
        default: 默认值
        reload: 是否强制重新加载配置（不使用缓存）
    
    Returns:
        配置值或默认值
    """
    config = load_yaml_config(reload=reload)
    if config is None:
        return default
    
    keys = key_path.split('.')
    value = config
    
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

# ============================================================
# 向后兼容的配置值
# ============================================================

# 加载环境变量（如果没有 YAML 配置则使用）
load_dotenv(ENV_FILE)

# 音频文件夹：优先使用 YAML，否则使用默认值
def get_audio_folder() -> str:
    """获取音频文件夹路径"""
    # 从 YAML 获取第一个频道组的音频目录
    channel_groups = get_config_value('channel_groups', [])
    if channel_groups and len(channel_groups) > 0:
        folder = channel_groups[0].get('audio_folder', 'au')
        return os.path.join(PROJECT_ROOT, folder)
    return os.path.join(PROJECT_ROOT, "au")

def get_cookies_file() -> str:
    """获取 Cookies 文件路径"""
    cookies_file = get_config_value('downloader.cookies_file', 'config/youtube.cookies')
    if os.path.isabs(cookies_file):
        return cookies_file
    return os.path.join(PROJECT_ROOT, cookies_file)

def get_download_archive() -> str:
    """获取下载存档文件路径"""
    archive_file = get_config_value('downloader.download_archive', 'data/download_archive.txt')
    if os.path.isabs(archive_file):
        return archive_file
    return os.path.join(PROJECT_ROOT, archive_file)

def get_sent_archive_path(chat_id: str, readable: bool = False) -> str:
    """
    获取频道已发送记录文件路径
    
    Args:
        chat_id: Telegram 频道 ID
        readable: 是否为人类可读格式
    
    Returns:
        文件路径
    """
    # 清理 chat_id，去除负号和特殊字符
    clean_id = str(chat_id).replace('-', '').replace('+', '')
    
    if readable:
        filename = f"sent_archive_{clean_id}_readable.txt"
    else:
        filename = f"sent_archive_{clean_id}.txt"
    
    return os.path.join(PROJECT_ROOT, 'data', filename)

# 为向后兼容，提供常量
AUDIO_FOLDER = get_audio_folder()
COOKIES_FILE = get_cookies_file()
DOWNLOAD_ARCHIVE = get_download_archive()

# ============================================================
# 配置获取函数
# ============================================================

def get_telegram_token(group_index: int = 0) -> Optional[str]:
    """
    获取 Telegram Bot Token
    
    Args:
        group_index: 频道组索引（默认第一组）
    
    Returns:
        Bot Token，优先级：频道组配置 > 全局配置 > 环境变量
    """
    provider = get_config_provider()
    return provider.get_telegram_token(group_index)

def get_telegram_chat_id() -> Optional[str]:
    """获取 Telegram Chat ID"""
    # 优先从 YAML 读取第一个频道组的 chat_id
    channel_groups = get_config_value('channel_groups', [])
    if channel_groups and len(channel_groups) > 0:
        chat_id = channel_groups[0].get('telegram_chat_id')
        if chat_id and chat_id != "YOUR_CHAT_ID_HERE":
            return chat_id
    # 回退到环境变量
    return os.environ.get("CHAT_ID")

def get_send_interval() -> int:
    """获取发送间隔（秒）"""
    provider = get_config_provider()
    return provider.get_send_interval()

def get_download_interval() -> int:
    """获取下载间隔（秒）"""
    provider = get_config_provider()
    return provider.get_download_interval()

def get_filter_days() -> int:
    """获取视频过滤天数（支持热重载）"""
    provider = get_config_provider()
    return provider.get_filter_days()

def get_max_videos_per_channel() -> int:
    """获取每个频道检查的最大视频数（支持热重载）"""
    provider = get_config_provider()
    return provider.get_max_videos_per_channel()

def get_channel_delay_min() -> int:
    """获取频道间最小延迟（秒）"""
    provider = get_config_provider()
    return provider.get_channel_delay_min()

def get_channel_delay_max() -> int:
    """获取频道间最大延迟（秒）"""
    provider = get_config_provider()
    return provider.get_channel_delay_max()

def get_video_delay_min() -> int:
    """获取视频间最小延迟（秒）"""
    provider = get_config_provider()
    return provider.get_video_delay_min()

def get_video_delay_max() -> int:
    """获取视频间最大延迟（秒）"""
    provider = get_config_provider()
    return provider.get_video_delay_max()

def get_all_channel_groups(use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    获取所有频道组配置
    
    Args:
        use_cache: 是否使用缓存。True=使用缓存（默认），False=强制重新读取
    
    Returns:
        频道组列表
    """
    provider = get_config_provider()
    return provider.get_channel_groups(use_cache=use_cache)

# ============================================================
# 初始化
# ============================================================

# 确保必要的目录存在
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# 确保 data 目录存在（用于存放下载和发送记录）
data_dir = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(data_dir, exist_ok=True)

# 打印配置来源信息
if load_yaml_config() is not None:
    print("✅ 使用 config.yaml 配置文件")
else:
    print("ℹ️  未找到 config.yaml，使用传统配置方式（channels.txt + .env）")
