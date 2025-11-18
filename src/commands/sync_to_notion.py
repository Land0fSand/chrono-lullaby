# -*- coding: utf-8 -*-
"""
手动同步本地数据到 Notion
"""

import os
import sys
import argparse
from datetime import datetime

import yaml

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from config_provider import LocalConfigProvider, NotionConfigProvider
from notion_adapter import NotionAdapter


def sync_download_archive(local_provider: LocalConfigProvider, notion_provider: NotionConfigProvider):
    """同步下载记录"""
    print("📥 正在同步下载记录...")
    
    # 从本地读取下载记录
    local_archive = local_provider._load_download_archive()
    
    if not local_archive:
        print("  ℹ️ 没有本地下载记录需要同步")
        return
    
    print(f"  发现 {len(local_archive)} 条本地下载记录")
    
    # 同步到 Notion
    synced = 0
    failed = 0
    
    for video_id in local_archive:
        # 检查是否已存在
        if notion_provider.has_download_record(video_id):
            continue
        
        # 添加到 Notion
        if notion_provider.add_download_record(video_id, "unknown", "completed"):
            synced += 1
        else:
            failed += 1
    
    print(f"  ✅ 成功同步 {synced} 条记录")
    if failed > 0:
        print(f"  ⚠️ 失败 {failed} 条记录")


def sync_sent_archive(local_provider: LocalConfigProvider, notion_provider: NotionConfigProvider):
    """同步已发送记录"""
    print("📤 正在同步已发送记录...")
    
    # 获取所有频道组
    channel_groups = local_provider.get_channel_groups()
    
    total_synced = 0
    total_failed = 0
    
    for group in channel_groups:
        chat_id = group.get('telegram_chat_id')
        if not chat_id:
            continue
        
        # 从本地读取已发送记录
        local_sent = local_provider._load_sent_archive(chat_id)
        
        if not local_sent:
            continue
        
        print(f"  频道 {chat_id}: {len(local_sent)} 条记录")
        
        synced = 0
        failed = 0
        
        for video_id in local_sent:
            # 检查是否已存在
            if notion_provider.has_sent_record(video_id, chat_id):
                continue
            
            # 添加到 Notion
            if notion_provider.add_sent_record(video_id, chat_id, "unknown", "unknown"):
                synced += 1
            else:
                failed += 1
        
        total_synced += synced
        total_failed += failed
        
        if synced > 0:
            print(f"    ✅ 成功同步 {synced} 条")
        if failed > 0:
            print(f"    ⚠️ 失败 {failed} 条")
    
    print(f"  总计: ✅ {total_synced} 条成功, ⚠️ {total_failed} 条失败")


def sync_config(local_provider: LocalConfigProvider, notion_provider: NotionConfigProvider):
    """同步频道配置"""
    print("==> 正在同步频道配置到 Notion...")

    config_db_id = notion_provider.config_data.get('database_ids', {}).get('config')
    if not config_db_id:
        print("  [错误] Notion Config Database ID 未配置")
        print("  [提示] 请先运行 ch init-notion")
        return

    adapter = notion_provider.adapter

    # 确保新增字段存在（兼容已有数据库）
    ensure_props = [
        ("channel_type", {"type": "select", "select": {"options": [{"name": "realtime"}, {"name": "story"}]}}),
        ("story_last_video_id", {"type": "rich_text", "rich_text": {}}),
        ("story_last_timestamp", {"type": "number", "number": {}}),
        ("story_interval_seconds", {"type": "number", "number": {}}),
        ("story_items_per_run", {"type": "number", "number": {}}),
        ("story_last_run_ts", {"type": "number", "number": {}}),
    ]
    for prop_name, schema in ensure_props:
        try:
            adapter.ensure_database_property(config_db_id, prop_name, schema)
        except Exception as e:
            print(f"  [提示] 确保 Notion 字段 {prop_name} 时出错: {e}")

    channel_groups = local_provider.get_channel_groups()
    if not channel_groups:
        print("  [跳过] 本地配置中没有频道组数据（已确保 Notion 字段存在）")
        return

    try:
        existing_pages = adapter.query_database(config_db_id)
    except Exception as e:
        print(f"  [错误] 查询 Notion Config Database 失败: {e}")
        return

    existing_by_chat = {}
    existing_by_name = {}
    for page in existing_pages:
        pid = page.get("id")
        chat = adapter.extract_property_value(page, 'telegram_chat_id')
        name = adapter.extract_property_value(page, 'name')
        if chat:
            existing_by_chat[str(chat).strip()] = pid
        if name:
            existing_by_name[str(name).strip()] = pid

    def text_prop(value: str) -> dict:
        return adapter.build_text_property(value) if value else {"rich_text": []}

    created = 0
    updated = 0
    skipped = 0
    matched_page_ids = set()
    issues = []

    for group in channel_groups:
        name = (group.get('name') or '').strip()
        description = (group.get('description') or '').strip()
        chat_id = str(group.get('telegram_chat_id') or '').strip()
        audio_folder = str(group.get('audio_folder') or '').strip()
        youtube_channels = group.get('youtube_channels') or []
        enabled = bool(group.get('enabled', True))
        channel_type = (group.get('channel_type') or 'realtime').lower()
        story_interval_seconds = int(group.get('story_interval_seconds', 86400))
        story_items_per_run = int(group.get('story_items_per_run', 1))

        if not chat_id:
            issues.append(f"频道组『{name or '未命名'}』缺少 telegram_chat_id，已跳过")
            skipped += 1
            continue

        page_id = existing_by_chat.get(chat_id)
        if not page_id and name:
            page_id = existing_by_name.get(name)

        # 使用 multi_select 格式存储 YouTube 频道列表
        youtube_channels_clean = [ch for ch in youtube_channels if ch]

        properties = {
            "name": adapter.build_title_property(name or "未命名频道"),
            "description": text_prop(description),
            "enabled": adapter.build_checkbox_property(enabled),
            "telegram_chat_id": text_prop(chat_id),
            "audio_folder": text_prop(audio_folder),
            "youtube_channels": adapter.build_multi_select_property(youtube_channels_clean),
            "channel_type": adapter.build_select_property('story' if channel_type == 'story' else 'realtime'),
            "story_interval_seconds": {"number": story_interval_seconds},
            "story_items_per_run": {"number": story_items_per_run},
        }

        try:
            if page_id:
                adapter.update_page(page_id, properties)
                matched_page_ids.add(page_id)
                updated += 1
            else:
                new_page_id = adapter.add_page_to_database(config_db_id, properties)
                matched_page_ids.add(new_page_id)
                created += 1
        except Exception as e:
            issues.append(f"频道组『{name or chat_id}』同步失败: {e}")

    stale_pages = []
    for page in existing_pages:
        pid = page.get("id")
        if pid not in matched_page_ids:
            stale_name = adapter.extract_property_value(page, 'name') or "(未命名)"
            stale_chat = adapter.extract_property_value(page, 'telegram_chat_id') or "(无 chat_id)"
            stale_pages.append(f"{stale_name} / {stale_chat}")

    notion_provider._channel_groups_cache = None

    print(f"  [完成] 新增 {created} 条，更新 {updated} 条，跳过 {skipped} 条")
    if stale_pages:
        print("  [提示] Notion 中存在未匹配的旧记录（未自动删除）：")
        for item in stale_pages:
            print(f"    - {item}")

    if issues:
        print("  [警告] 以下项目同步失败：")
        for item in issues:
            print(f"    - {item}")
    else:
        print("  [完成] 所有频道组同步成功")


def sync_global_settings(yaml_config: dict, notion_provider: NotionConfigProvider):
    """同步全局（telegram/downloader）配置"""
    print("==> 正在同步全局设置到 Notion...")
    
    page_id = notion_provider.config_data.get('page_ids', {}).get('global_settings')
    if not page_id:
        print("  [错误] 未找到 GlobalSettings 页面 ID")
        print("  [提示] 请先运行 ch init-notion")
        return
    
    adapter = notion_provider.adapter
    
    global_settings = {}
    telegram_cfg = yaml_config.get('telegram')
    downloader_cfg = yaml_config.get('downloader')
    
    if isinstance(telegram_cfg, dict):
        global_settings['telegram'] = telegram_cfg
    if isinstance(downloader_cfg, dict):
        global_settings['downloader'] = downloader_cfg
    
    if not global_settings:
        print("  [跳过] 未在本地配置中找到 telegram/downloader 节")
        return
    
    yaml_text = yaml.dump(global_settings, allow_unicode=True, sort_keys=False)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    blocks = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": f"同步于 {timestamp}"}
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": yaml_text}
                    }
                ],
                "language": "yaml"
            }
        }
    ]
    
    try:
        adapter.append_blocks(page_id, blocks)
        print("  [完成] 全局设置已追加到 Notion")
    except Exception as e:
        print(f"  [错误] 同步全局设置失败: {e}")


def main():
    parser = argparse.ArgumentParser(description='同步本地数据到 Notion')
    parser.add_argument('--data', choices=['all', 'config', 'archive', 'logs'], 
                       default='all', help='要同步的数据类型')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ChronoLullaby - 数据同步到 Notion")
    print("=" * 60)
    print()
    
    # 1. 加载配置
    print("📖 正在加载配置...")
    yaml_config = config.load_yaml_config()
    
    if not yaml_config:
        print("❌ 配置文件加载失败")
        return False
    
    legacy_source = yaml_config.get('config_source', {}) if yaml_config else {}
    notion_config = yaml_config.get('notion', {}) if yaml_config else {}
    if not notion_config:
        notion_config = legacy_source.get('notion', {})
    
    api_key = notion_config.get('api_key')
    if not api_key or api_key == 'secret_xxxxx':
        print("❌ Notion API Key 未配置")
        return False
    
    # 检查数据库 ID
    database_ids = notion_config.get('database_ids', {})
    if not database_ids.get('sent_archive') or not database_ids.get('download_archive'):
        print("❌ Notion 数据库 ID 未配置")
        print("请先运行: ch init-notion")
        return False
    
    print("✅ 配置加载成功")
    print()
    
    # 2. 初始化提供者
    print("🔌 正在初始化配置提供者...")
    
    local_provider = LocalConfigProvider(config.PROJECT_ROOT, config.CONFIG_YAML_FILE)
    
    try:
        adapter = NotionAdapter(api_key)
        notion_provider = NotionConfigProvider(adapter, notion_config)
        print("✅ 连接 Notion 成功")
    except Exception as e:
        print(f"❌ 连接 Notion 失败: {e}")
        return False
    
    print()
    
    # 3. 执行同步
    data_type = args.data
    
    try:
        if data_type == 'all' or data_type == 'archive':
            sync_download_archive(local_provider, notion_provider)
            print()
            sync_sent_archive(local_provider, notion_provider)
            print()
        
        if data_type == 'all' or data_type == 'config':
            sync_config(local_provider, notion_provider)
            print()
            sync_global_settings(yaml_config, notion_provider)
            print()
        
        if data_type == 'all' or data_type == 'logs':
            print("📝 日志同步功能待实现")
            print()
        
        print("=" * 60)
        print("✅ 数据同步完成！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ 同步过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
