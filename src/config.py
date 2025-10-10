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

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 配置文件路径
# ============================================================
CONFIG_YAML_FILE = os.path.join(PROJECT_ROOT, "config", "config.yaml")
CHANNELS_FILE = os.path.join(PROJECT_ROOT, "config", "channels.txt")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
DEBUG_INFO = os.path.join(PROJECT_ROOT, "debug_closest_video.json")
STORY_FILE = os.path.join(PROJECT_ROOT, "story.txt")

# ============================================================
# YAML 配置加载
# ============================================================
_config_cache: Optional[Dict[str, Any]] = None

def load_yaml_config() -> Optional[Dict[str, Any]]:
    """
    加载 YAML 配置文件
    
    Returns:
        配置字典，如果文件不存在或加载失败则返回 None
    """
    global _config_cache
    
    if _config_cache is not None:
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

def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    从 YAML 配置中获取值，支持点号路径
    
    Args:
        key_path: 配置键路径，如 "telegram.bot_token"
        default: 默认值
    
    Returns:
        配置值或默认值
    """
    config = load_yaml_config()
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
    # 1. 尝试从指定频道组读取独立的 bot_token
    channel_groups = get_config_value('channel_groups', [])
    if channel_groups and group_index < len(channel_groups):
        group_token = channel_groups[group_index].get('bot_token')
        if group_token and group_token != "YOUR_BOT_TOKEN_HERE" and group_token.strip():
            return group_token
    
    # 2. 使用全局 telegram.bot_token
    global_token = get_config_value('telegram.bot_token')
    if global_token and global_token != "YOUR_BOT_TOKEN_HERE":
        return global_token
    
    # 3. 回退到环境变量
    return os.environ.get("BOT_TOKEN")

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
    return get_config_value('telegram.send_interval', 4920)

def get_download_interval() -> int:
    """获取下载间隔（秒）"""
    return get_config_value('downloader.download_interval', 29520)

def get_filter_days() -> int:
    """获取视频过滤天数"""
    return get_config_value('downloader.filter_days', 3)

def get_max_videos_per_channel() -> int:
    """获取每个频道检查的最大视频数"""
    return get_config_value('downloader.max_videos_per_channel', 6)

def get_channel_delay_min() -> int:
    """获取频道间最小延迟（秒）"""
    return get_config_value('downloader.channel_delay_min', 0)

def get_channel_delay_max() -> int:
    """获取频道间最大延迟（秒）"""
    return get_config_value('downloader.channel_delay_max', 0)

def get_video_delay_min() -> int:
    """获取视频间最小延迟（秒）"""
    return get_config_value('downloader.video_delay_min', 120)

def get_video_delay_max() -> int:
    """获取视频间最大延迟（秒）"""
    return get_config_value('downloader.video_delay_max', 240)

def get_all_channel_groups(use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    获取所有频道组配置
    
    Args:
        use_cache: 是否使用缓存。True=使用缓存（默认），False=强制重新读取
    
    Returns:
        频道组列表
    """
    if not use_cache:
        # 强制重新读取 YAML 文件（仅读取频道组配置）
        if not os.path.exists(CONFIG_YAML_FILE):
            return []
        
        try:
            with open(CONFIG_YAML_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('channel_groups', []) if config else []
        except Exception as e:
            print(f"警告：重新加载频道组配置失败: {e}")
            return []
    
    return get_config_value('channel_groups', [])

# ============================================================
# 初始化
# ============================================================

# 确保必要的目录存在
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# 打印配置来源信息
if load_yaml_config() is not None:
    print("✅ 使用 config.yaml 配置文件")
else:
    print("ℹ️  未找到 config.yaml，使用传统配置方式（channels.txt + .env）")
