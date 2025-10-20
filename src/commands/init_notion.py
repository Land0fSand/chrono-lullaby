# -*- coding: utf-8 -*-
"""
初始化 Notion 数据库结构
"""

import os
import sys
import uuid
import yaml
from typing import Dict, Any, Optional

# 设置默认编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PLACEHOLDER_PAGE_IDS = {
    "xxxxx",
    "your-page-id-here",
    "your-page-id",
    "page-id-placeholder",
}


def _normalize_page_id(raw_page_id: str) -> Optional[str]:
    """将各种形式的 Notion 页面标识转换为标准 UUID 形式"""
    if not raw_page_id:
        return None

    candidate = raw_page_id.strip()
    if not candidate:
        return None

    # 如果是完整链接，截取最后一段 slug
    if candidate.startswith(("http://", "https://")):
        candidate = candidate.split("?", 1)[0]
        candidate = candidate.rstrip("/")
        candidate = candidate.split("/")[-1]

    # 仅保留十六进制字符，并取最后 32 位
    hex_chars = "".join(ch for ch in candidate if ch.lower() in "0123456789abcdef")
    if len(hex_chars) < 32:
        return None

    hex_id = hex_chars[-32:].lower()
    hyphenated = (
        f"{hex_id[0:8]}-{hex_id[8:12]}-{hex_id[12:16]}-"
        f"{hex_id[16:20]}-{hex_id[20:32]}"
    )

    try:
        uuid.UUID(hyphenated)
    except ValueError:
        return None

    return hyphenated


def _is_placeholder_page_id(page_id: str) -> bool:
    """判断 page_id 是否仍然使用占位符"""
    if not page_id:
        return True
    return page_id.strip().lower() in _PLACEHOLDER_PAGE_IDS

from notion_adapter import NotionAdapter, NotionDatabaseSchemas
import config


def init_notion_structure():
    """初始化 Notion 数据库结构"""
    
    print("=" * 60)
    print("ChronoLullaby - Notion 初始化工具")
    print("=" * 60)
    print()
    
    # 1. 加载配置
    print("📖 正在加载配置...")
    config_file = config.CONFIG_YAML_FILE
    
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        print("请先创建 config.yaml 文件")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return False
    
# 2. 检查 Notion 配置
    legacy_source = yaml_config.get('config_source', {})
    notion_config = yaml_config.get('notion', {})
    if not notion_config:
        notion_config = legacy_source.get('notion', {})
    
    if not notion_config:
        print("❌ 配置文件中没有 notion 配置节")
        print("请参考文档或模板填写 Notion 配置信息")
        return False
    
    api_key = notion_config.get('api_key', '')
    raw_page_id = notion_config.get('page_id', '')
    
    if not api_key or api_key == 'secret_xxxxx':
        print("❌ Notion API Key 未配置")
        print("请在 config.yaml 的 notion.api_key（或 legacy config_source.notion.api_key）中填入有效的 API Key")
        return False
    
    if _is_placeholder_page_id(raw_page_id):
        print("❌ Notion Page ID 未配置")
        print("请在 config.yaml 的 notion.page_id（或 config_source.notion.page_id）中填入父页面 ID（可直接粘贴 Notion 页面链接，末尾 32 位为 UUID）")
        return False
    
    page_id = _normalize_page_id(raw_page_id)
    if not page_id:
        print("❌ Notion Page ID 格式无效")
        print("提示：请直接复制 Notion 父页面地址；或手动填写 32/36 位 UUID，例如 12345678-1234-1234-1234-123456789012")
        return False
    
    if page_id != (raw_page_id or '').strip():
        print("ℹ️ 已自动将 Notion Page ID 转换为标准 UUID 格式")
        notion_config['page_id'] = page_id
    
    print(f"✅ 配置加载成功")
    print(f"   API Key: {api_key[:20]}...")
    print(f"   Page ID: {page_id}")
    print()
    
    # 3. 连接 Notion
    print("🔌 正在连接 Notion...")
    try:
        adapter = NotionAdapter(api_key)
        # 测试连接
        adapter.get_page(page_id)
        print("✅ Notion 连接成功")
    except Exception as e:
        print(f"❌ 连接 Notion 失败: {e}")
        print("请检查 API Key 和 Page ID 是否正确")
        return False
    
    print()
    
    # 4. 创建数据库
    database_ids = {}
    page_ids = {}
    
    print("📊 正在创建数据库...")
    print()
    
    # 准备全局配置 YAML
    global_settings_data = {}
    telegram_cfg = yaml_config.get('telegram')
    downloader_cfg = yaml_config.get('downloader')
    if isinstance(telegram_cfg, dict) and telegram_cfg:
        global_settings_data['telegram'] = telegram_cfg
    if isinstance(downloader_cfg, dict) and downloader_cfg:
        global_settings_data['downloader'] = downloader_cfg
    global_settings_yaml = ""
    if global_settings_data:
        global_settings_yaml = yaml.dump(global_settings_data, allow_unicode=True, sort_keys=False)
    
    # 4.1 创建 Config Database
    try:
        print("  创建 Config Database (频道配置)...")
        db_id = adapter.create_database(
            page_id,
            "ChronoLullaby - 频道配置",
            NotionDatabaseSchemas.config_database()
        )
        database_ids['config'] = db_id
        print(f"  ✅ Config Database 创建成功: {db_id}")
    except Exception as e:
        print(f"  ❌ 创建 Config Database 失败: {e}")
        return False
    
    # 4.2 创建 SentArchive Database
    try:
        print("  创建 SentArchive Database (已发送记录)...")
        db_id = adapter.create_database(
            page_id,
            "ChronoLullaby - 已发送记录",
            NotionDatabaseSchemas.sent_archive_database()
        )
        database_ids['sent_archive'] = db_id
        print(f"  ✅ SentArchive Database 创建成功: {db_id}")
    except Exception as e:
        print(f"  ❌ 创建 SentArchive Database 失败: {e}")
        return False
    
    # 4.3 创建 DownloadArchive Database
    try:
        print("  创建 DownloadArchive Database (下载记录)...")
        db_id = adapter.create_database(
            page_id,
            "ChronoLullaby - 下载记录",
            NotionDatabaseSchemas.download_archive_database()
        )
        database_ids['download_archive'] = db_id
        print(f"  ✅ DownloadArchive Database 创建成功: {db_id}")
    except Exception as e:
        print(f"  ❌ 创建 DownloadArchive Database 失败: {e}")
        return False
    
    # 4.4 创建 Logs Database
    try:
        print("  创建 Logs Database (日志)...")
        db_id = adapter.create_database(
            page_id,
            "ChronoLullaby - 日志",
            NotionDatabaseSchemas.logs_database()
        )
        database_ids['logs'] = db_id
        print(f"  ✅ Logs Database 创建成功: {db_id}")
    except Exception as e:
        print(f"  ❌ 创建 Logs Database 失败: {e}")
        return False
    
    print()
    
    # 5. 创建页面
    print("📄 正在创建配置页面...")
    print()
    
    # 5.1 创建 Cookies 页面
    try:
        print("  创建 Cookies 页面...")
        cookies_page_id = adapter.create_page(
            page_id,
            "ChronoLullaby - Cookies",
            content_blocks=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "在下方 Code Block 中粘贴 YouTube cookies 文件内容"}
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
                                "text": {"content": "# 将 YouTube cookies 文件内容粘贴到这里"}
                            }
                        ],
                        "language": "plain text"
                    }
                }
            ]
        )
        page_ids['cookies'] = cookies_page_id
        print(f"  ✅ Cookies 页面创建成功: {cookies_page_id}")
    except Exception as e:
        print(f"  ❌ 创建 Cookies 页面失败: {e}")
        return False
    
    # 5.2 创建 GlobalSettings 页面
    try:
        print("  创建 GlobalSettings 页面...")
        settings_page_id = adapter.create_page(
            page_id,
            "ChronoLullaby - 全局设置",
            content_blocks=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "全局设置说明：目前从 config.yaml 的 telegram 和 downloader 节读取"}
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "后续版本将支持从此页面读取全局设置"}
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
                                "text": {
                                    "content": global_settings_yaml or "# 暂无配置，请运行 ch sync-to-notion --data config 将设置同步到此处"
                                }
                            }
                        ],
                        "language": "yaml"
                    }
                }
            ]
        )
        page_ids['global_settings'] = settings_page_id
        print(f"  ✅ GlobalSettings 页面创建成功: {settings_page_id}")
    except Exception as e:
        print(f"  ❌ 创建 GlobalSettings 页面失败: {e}")
        return False
    
    print()
    
    # 6. 更新 config.yaml
    print("💾 正在更新配置文件...")
    
    try:
        # 更新配置
        if 'database_ids' not in notion_config:
            notion_config['database_ids'] = {}
        if 'page_ids' not in notion_config:
            notion_config['page_ids'] = {}
        
        notion_config['database_ids'].update(database_ids)
        notion_config['page_ids'].update(page_ids)
        
        # 写回文件
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        
        print("✅ 配置文件更新成功")
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        print("请手动将以下 ID 添加到 config.yaml:")
        print()
        print("database_ids:")
        for name, db_id in database_ids.items():
            print(f"  {name}: \"{db_id}\"")
        print()
        print("page_ids:")
        for name, pg_id in page_ids.items():
            print(f"  {name}: \"{pg_id}\"")
        return False
    
    print()
    print("=" * 60)
    print("✅ Notion 初始化完成！")
    print("=" * 60)
    print()
    print("📝 创建的数据库:")
    for name, db_id in database_ids.items():
        print(f"  - {name}: {db_id}")
    print()
    print("📄 创建的页面:")
    for name, pg_id in page_ids.items():
        print(f"  - {name}: {pg_id}")
    print()
    print("💡 下一步:")
    print("  1. 在 Notion 中打开父页面，查看创建的数据库和页面")
    print("  2. （可选）在 Config Database 中添加频道配置")
    print("  3. （可选）在 Cookies 页面中粘贴 YouTube cookies")
    print("  4. 使用 'ch start --mode notion' 启动服务")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = init_notion_structure()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

