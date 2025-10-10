# -*- coding: utf-8 -*-
from telegram import Update
from telegram.ext import ContextTypes
import os
import sys
from typing import Tuple, List

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from config import CHANNELS_FILE, get_all_channel_groups, load_yaml_config, PROJECT_ROOT


async def show_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process the received message and print `chat_id`.

    Due to Telegram Bot API restrictions, it is not possible to directly obtain the chat_id; it needs to be acquired through the message object.
    If you are not the type of bot that replies to messages but instead sends messages directly, then you need to obtain the chat_id.
    This method provides a way to obtain the chat_id. For example, you use this type of code:
    application.add_handler(MessageHandler(filters.TEXT, show_chat_id))
    Then, when a user types something in the current channel, this method will print the chat_id.

        Args:
            update (Update): A Telegram update object that contains message and chat information.
            context (ContextTypes.DEFAULT_TYPE): A context object that contains related callback data.

        Returns:
            None
    """
    chat_id = update.message.chat_id
    print(f"Received a message from chat ID: {chat_id}")


def refresh_channels_from_file() -> Tuple[str, ...]:
    """
    刷新频道列表
    
    优先从 config.yaml 读取，如果不存在则从 channels.txt 读取
    
    Returns:
        频道名称元组
    """
    # 优先从 YAML 配置读取
    if load_yaml_config() is not None:
        return _get_channels_from_yaml()
    
    # 回退到从 channels.txt 读取
    return _get_channels_from_txt()

def _get_channels_from_yaml() -> Tuple[str, ...]:
    """从 YAML 配置文件读取频道列表"""
    try:
        channel_groups = get_all_channel_groups()
        
        if not channel_groups:
            print("警告：config.yaml 中未找到频道组配置")
            return ()
        
        # 合并所有频道组的频道列表
        all_channels: List[str] = []
        for group in channel_groups:
            youtube_channels = group.get('youtube_channels', [])
            all_channels.extend(youtube_channels)
        
        print(f"从 config.yaml 加载了 {len(all_channels)} 个频道")
        return tuple(all_channels)
    
    except Exception as e:
        print(f"从 config.yaml 读取频道列表时出错: {e}")
        print("将尝试从 channels.txt 读取")
        return _get_channels_from_txt()

def get_channel_groups_with_details(reload: bool = False) -> List[dict]:
    """
    获取所有频道组的详细信息（用于多频道支持）
    
    Args:
        reload: 是否强制重新读取配置文件（用于热重载频道列表）
    
    Returns:
        频道组列表，每个组包含：
        - name: 组名称
        - youtube_channels: YouTube频道列表
        - audio_folder: 音频保存目录（绝对路径）
        - telegram_chat_id: Telegram频道ID
    """
    if load_yaml_config() is None:
        # 如果没有YAML配置，返回单个默认组
        from config import AUDIO_FOLDER
        return [{
            'name': '默认组',
            'youtube_channels': list(_get_channels_from_txt()),
            'audio_folder': AUDIO_FOLDER,
            'telegram_chat_id': None
        }]
    
    try:
        # 根据 reload 参数决定是否使用缓存
        channel_groups = get_all_channel_groups(use_cache=not reload)
        
        if not channel_groups:
            print("警告：config.yaml 中未找到频道组配置")
            return []
        
        result = []
        disabled_groups = []
        
        for group in channel_groups:
            # 检查是否启用（默认为 true）
            enabled = group.get('enabled', True)
            group_name = group.get('name', '未命名组')
            
            if not enabled:
                disabled_groups.append(group_name)
                continue  # 跳过禁用的频道组
            
            # 获取音频目录（转换为绝对路径）
            audio_folder = group.get('audio_folder', 'au')
            if not os.path.isabs(audio_folder):
                audio_folder = os.path.join(PROJECT_ROOT, audio_folder)
            
            result.append({
                'name': group_name,
                'youtube_channels': group.get('youtube_channels', []),
                'audio_folder': audio_folder,
                'telegram_chat_id': group.get('telegram_chat_id'),
                'enabled': enabled
            })
        
        if reload:
            msg = f"🔄 热重载：从 config.yaml 重新加载了 {len(result)} 个启用的频道组"
            if disabled_groups:
                msg += f"（已禁用: {', '.join(disabled_groups)}）"
            print(msg)
        else:
            msg = f"从 config.yaml 加载了 {len(result)} 个启用的频道组"
            if disabled_groups:
                msg += f"（已禁用: {', '.join(disabled_groups)}）"
            print(msg)
        return result
    
    except Exception as e:
        print(f"从 config.yaml 读取频道组时出错: {e}")
        return []

def _get_channels_from_txt() -> Tuple[str, ...]:
    """从 channels.txt 文件读取频道列表（向后兼容）"""
    try:
        # 使用UTF-8编码读取文件以支持中文字符
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        # 过滤掉注释行和空行
        channels = []
        for line in lines:
            line = line.strip()  # 去除首尾空白
            if line and not line.startswith('#'):  # 跳过空行和注释行
                channels.append(line)

        if channels:
            print(f"从 channels.txt 加载了 {len(channels)} 个频道")
        return tuple(channels)
    
    except FileNotFoundError:
        # 创建UTF-8编码的文件
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            f.write("# ChronoLullaby Channels List\n")
            f.write("# 使用 # 开头的行会被忽略\n")
            f.write("# 格式: @channelname 或 channelname\n")
        print(f"已创建空的 channels.txt 文件")
        return ()
    
    except UnicodeDecodeError:
        # 如果UTF-8失败，尝试GBK编码（Windows兼容）
        try:
            with open(CHANNELS_FILE, "r", encoding="gbk") as f:
                lines = f.read().splitlines()

            # 过滤掉注释行和空行
            channels = []
            for line in lines:
                line = line.strip()  # 去除首尾空白
                if line and not line.startswith('#'):  # 跳过空行和注释行
                    channels.append(line)

            if channels:
                print(f"从 channels.txt (GBK编码) 加载了 {len(channels)} 个频道")
            return tuple(channels)
        except Exception as e:
            print(f"读取 channels.txt 文件时出错: {e}")
            return ()
