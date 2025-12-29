# -*- coding: utf-8 -*-
"""
从 Notion 导出配置到本地 YAML 格式
"""
import yaml
import sys
import os

# 添加 src 目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, 'src'))

from config import get_config_provider, init_config_provider

def export_notion_config():
    """从 Notion 获取配置并生成 YAML 格式"""
    
    # 初始化 Notion 提供者
    init_config_provider('notion')
    provider = get_config_provider()
    
    # 获取频道组
    groups = provider.get_channel_groups(use_cache=False)
    
    # 获取全局设置
    config = {
        'mode': 'local',  # 切换到本地模式
        
        'telegram': {
            'bot_token': provider.get_telegram_token() or 'YOUR_BOT_TOKEN',
            'send_interval': provider.get_send_interval(),
        },
        
        'downloader': {
            'download_interval': provider.get_download_interval(),
            'filter_days': provider.get_filter_days(),
            'max_videos_per_channel': provider.get_max_videos_per_channel(),
            'channel_delay_min': provider.get_channel_delay_min(),
            'channel_delay_max': provider.get_channel_delay_max(),
            'video_delay_min': provider.get_video_delay_min(),
            'video_delay_max': provider.get_video_delay_max(),
        },
        
        'channel_groups': []
    }
    
    # 转换频道组
    for g in groups:
        group = {
            'name': g.get('name', ''),
            'enabled': False,  # 默认禁用 TG 发送
            'telegram_chat_id': g.get('telegram_chat_id', ''),
            'audio_folder': g.get('audio_folder', ''),
            'youtube_channels': g.get('youtube_channels', []),
            'channel_type': g.get('channel_type', 'realtime'),  # 添加类型
        }
        
        # 如果是 story 类型，添加相关字段
        if g.get('channel_type') == 'story':
            group['story_interval_seconds'] = g.get('story_interval_seconds', 86400)
            group['story_items_per_run'] = g.get('story_items_per_run', 1)
            # 进度字段（用于还原 story 进度）
            if g.get('story_last_video_id'):
                group['story_last_video_id'] = g.get('story_last_video_id')
            if g.get('story_last_timestamp') is not None:
                group['story_last_timestamp'] = g.get('story_last_timestamp')
            if g.get('story_last_run_ts') is not None:
                group['story_last_run_ts'] = g.get('story_last_run_ts')
        
        config['channel_groups'].append(group)
    
    # 输出 YAML
    print("# 从 Notion 导出的配置 (所有频道组已禁用)")
    print(yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False))

if __name__ == '__main__':
    export_notion_config()
