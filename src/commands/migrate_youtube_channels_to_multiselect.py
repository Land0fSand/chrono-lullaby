# -*- coding: utf-8 -*-
"""
迁移脚本：将 Notion Config Database 中的 youtube_channels 字段
从 rich_text 格式迁移到 multi_select 格式

使用方法：
    python src/commands/migrate_youtube_channels_to_multiselect.py

注意：
    - 此脚本会修改 Notion 数据库结构
    - 建议在执行前备份 Notion 数据
    - 执行过程不可逆，请谨慎操作
"""

import os
import sys
import yaml
from typing import Dict, Any, List, Optional

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notion_adapter import NotionAdapter
import config


def backup_existing_data(adapter: NotionAdapter, database_id: str) -> List[Dict[str, Any]]:
    """
    备份现有数据
    
    Args:
        adapter: NotionAdapter 实例
        database_id: 数据库 ID
    
    Returns:
        现有数据列表
    """
    print("📦 正在备份现有数据...")
    
    try:
        pages = adapter.query_database(database_id)
        
        backup_data = []
        for page in pages:
            page_id = page.get('id')
            name = adapter.extract_property_value(page, 'name')
            youtube_channels_raw = adapter.extract_property_value(page, 'youtube_channels')
            
            # 解析 YouTube 频道列表
            youtube_channels = []
            if isinstance(youtube_channels_raw, str):
                # 旧格式：按行分割
                youtube_channels = [ch.strip() for ch in youtube_channels_raw.split('\n') if ch.strip()]
            elif isinstance(youtube_channels_raw, list):
                # 已经是新格式
                youtube_channels = youtube_channels_raw
            
            backup_data.append({
                'page_id': page_id,
                'name': name,
                'youtube_channels': youtube_channels
            })
        
        print(f"   ✅ 已备份 {len(backup_data)} 条记录")
        return backup_data
    
    except Exception as e:
        print(f"   ❌ 备份失败: {e}")
        return []


def update_database_schema(adapter: NotionAdapter, database_id: str) -> bool:
    """
    更新数据库 schema，将 youtube_channels 从 rich_text 改为 multi_select
    
    Args:
        adapter: NotionAdapter 实例
        database_id: 数据库 ID
    
    Returns:
        是否成功
    """
    print("🔧 正在更新数据库 schema...")
    
    try:
        # 获取当前数据库信息
        db_info = adapter.client.databases.retrieve(database_id=database_id)
        current_properties = db_info.get('properties', {})
        
        # 检查 youtube_channels 字段类型
        youtube_channels_prop = current_properties.get('youtube_channels', {})
        current_type = youtube_channels_prop.get('type')
        
        if current_type == 'multi_select':
            print("   ℹ️  数据库 schema 已经是 multi_select 格式，无需更新")
            return True
        
        print(f"   当前字段类型: {current_type}")
        print("   目标字段类型: multi_select")
        
        # Notion API 不支持直接修改属性类型
        # 需要先删除旧字段，再创建新字段
        # 但这会导致数据丢失，所以我们采用另一种方案：
        # 1. 创建一个新的 multi_select 字段 (youtube_channels_new)
        # 2. 迁移数据到新字段
        # 3. 删除旧字段
        # 4. 将新字段重命名为 youtube_channels
        
        print("\n⚠️  注意：Notion API 不支持直接修改字段类型")
        print("   将执行以下步骤：")
        print("   1. 创建临时字段 youtube_channels_temp (multi_select)")
        print("   2. 迁移数据到临时字段")
        print("   3. 删除原字段 youtube_channels")
        print("   4. 重命名临时字段为 youtube_channels")
        
        response = input("\n是否继续？(yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("   ❌ 用户取消操作")
            return False
        
        # 步骤1: 创建临时 multi_select 字段
        print("\n步骤 1/4: 创建临时字段...")
        new_properties = {
            "youtube_channels_temp": {
                "multi_select": {}
            }
        }
        adapter.client.databases.update(
            database_id=database_id,
            properties=new_properties
        )
        print("   ✅ 临时字段创建成功")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 更新 schema 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def migrate_data_to_new_field(adapter: NotionAdapter, backup_data: List[Dict[str, Any]]) -> bool:
    """
    迁移数据到新字段
    
    Args:
        adapter: NotionAdapter 实例
        backup_data: 备份的数据
    
    Returns:
        是否成功
    """
    print("\n步骤 2/4: 迁移数据到临时字段...")
    
    success_count = 0
    failed_count = 0
    
    for item in backup_data:
        page_id = item['page_id']
        name = item['name']
        youtube_channels = item['youtube_channels']
        
        try:
            # 构建 multi_select 属性
            properties = {
                "youtube_channels_temp": adapter.build_multi_select_property(youtube_channels)
            }
            
            adapter.update_page(page_id, properties)
            success_count += 1
            print(f"   ✅ 迁移成功: {name} ({len(youtube_channels)} 个频道)")
            
        except Exception as e:
            failed_count += 1
            print(f"   ❌ 迁移失败: {name} - {e}")
    
    print(f"\n   迁移完成: ✅ {success_count} 成功, ❌ {failed_count} 失败")
    return failed_count == 0


def remove_old_field(adapter: NotionAdapter, database_id: str) -> bool:
    """
    删除旧字段
    
    Args:
        adapter: NotionAdapter 实例
        database_id: 数据库 ID
    
    Returns:
        是否成功
    """
    print("\n步骤 3/4: 删除原字段...")
    
    try:
        # 删除字段通过设置为 null
        adapter.client.databases.update(
            database_id=database_id,
            properties={
                "youtube_channels": None
            }
        )
        print("   ✅ 原字段删除成功")
        return True
        
    except Exception as e:
        print(f"   ❌ 删除原字段失败: {e}")
        return False


def rename_new_field(adapter: NotionAdapter, database_id: str) -> bool:
    """
    重命名新字段
    
    Args:
        adapter: NotionAdapter 实例
        database_id: 数据库 ID
    
    Returns:
        是否成功
    """
    print("\n步骤 4/4: 重命名临时字段...")
    
    try:
        # 重命名字段
        adapter.client.databases.update(
            database_id=database_id,
            properties={
                "youtube_channels_temp": {
                    "name": "youtube_channels"
                }
            }
        )
        print("   ✅ 字段重命名成功")
        return True
        
    except Exception as e:
        print(f"   ❌ 重命名字段失败: {e}")
        return False


def main():
    """主函数"""
    
    print("=" * 70)
    print("ChronoLullaby - YouTube 频道字段迁移工具")
    print("将 youtube_channels 从 rich_text 格式迁移到 multi_select 格式")
    print("=" * 70)
    print()
    
    # 1. 加载配置
    print("📖 正在加载配置...")
    yaml_config = config.load_yaml_config()
    
    if not yaml_config:
        print("❌ 配置文件加载失败")
        return False
    
    legacy_source = yaml_config.get('config_source', {})
    notion_config = yaml_config.get('notion', {})
    if not notion_config:
        notion_config = legacy_source.get('notion', {})
    
    api_key = notion_config.get('api_key')
    if not api_key or api_key == 'secret_xxxxx':
        print("❌ Notion API Key 未配置")
        return False
    
    database_ids = notion_config.get('database_ids', {})
    config_db_id = database_ids.get('config')
    
    if not config_db_id:
        print("❌ Config Database ID 未配置")
        print("请先运行: ch init-notion")
        return False
    
    print("✅ 配置加载成功")
    print(f"   Database ID: {config_db_id[:8]}...")
    print()
    
    # 2. 连接 Notion
    print("🔌 正在连接 Notion...")
    try:
        adapter = NotionAdapter(api_key)
        print("✅ Notion 连接成功")
    except Exception as e:
        print(f"❌ 连接 Notion 失败: {e}")
        return False
    
    print()
    
    # 3. 备份现有数据
    backup_data = backup_existing_data(adapter, config_db_id)
    if not backup_data:
        print("⚠️  没有数据需要迁移")
        return True
    
    print()
    
    # 4. 更新数据库 schema
    if not update_database_schema(adapter, config_db_id):
        return False
    
    # 5. 迁移数据
    if not migrate_data_to_new_field(adapter, backup_data):
        print("\n⚠️  部分数据迁移失败，但不影响继续操作")
    
    # 6. 删除旧字段
    if not remove_old_field(adapter, config_db_id):
        print("\n⚠️  删除旧字段失败，请手动删除 youtube_channels 字段")
        print("   然后将 youtube_channels_temp 重命名为 youtube_channels")
        return False
    
    # 7. 重命名新字段
    if not rename_new_field(adapter, config_db_id):
        print("\n⚠️  重命名失败，请手动将 youtube_channels_temp 重命名为 youtube_channels")
        return False
    
    print()
    print("=" * 70)
    print("✅ 迁移完成！")
    print()
    print("现在你可以在 Notion 中使用 multi_select 格式管理 YouTube 频道：")
    print("  - 每个频道作为独立的选项")
    print("  - 可以随时添加/删除频道选项")
    print("  - 不需要删除频道，只需取消勾选即可")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



