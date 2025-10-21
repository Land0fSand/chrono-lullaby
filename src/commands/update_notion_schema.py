# -*- coding: utf-8 -*-
"""
升级 Notion 数据库结构：补充 machine_id 字段、枚举项等
"""

import os
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# 将 src 目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from notion_adapter import NotionAdapter


def ensure_machine_id(adapter: NotionAdapter, database_id: str, name: str):
    if not database_id:
        print(f"⚠️  跳过 {name}：未找到数据库 ID")
        return
    added = adapter.ensure_database_property(
        database_id,
        "machine_id",
        {"type": "rich_text", "rich_text": {}}
    )
    if added:
        print(f"✅ 已为 {name} 添加 machine_id 字段")
    else:
        print(f"ℹ️  {name} 已包含 machine_id 字段")


def ensure_log_levels(adapter: NotionAdapter, database_id: str, options):
    if not database_id:
        return
    for option in options:
        added = adapter.ensure_select_option(
            database_id,
            "level",
            option
        )
        if added:
            print(f"✅ Logs 数据库新增 level 选项: {option['name']}")


def main():
    print("=== ChronoLullaby Notion Schema 升级 ===\n")

    yaml_config = config.load_yaml_config()
    if not yaml_config:
        print("❌ 无法加载 config.yaml")
        return False

    notion_config = yaml_config.get("notion") or yaml_config.get("config_source", {}).get("notion", {})
    if not notion_config:
        print("❌ 未找到 notion 配置")
        return False

    api_key = notion_config.get("api_key")
    if not api_key or api_key.startswith("secret_"):
        print("❌ 请在 config.yaml 中填写有效的 notion.api_key")
        return False

    database_ids = notion_config.get("database_ids", {})
    if not database_ids:
        print("❌ notion.database_ids 尚未初始化，请先运行 ch init-notion")
        return False

    adapter = NotionAdapter(api_key)

    print("👉 正在检查 machine_id 字段")
    ensure_machine_id(adapter, database_ids.get("download_archive"), "DownloadArchive")
    ensure_machine_id(adapter, database_ids.get("sent_archive"), "SentArchive")
    ensure_machine_id(adapter, database_ids.get("logs"), "Logs")

    print("\n👉 正在补充日志级别枚举")
    ensure_log_levels(
        adapter,
        database_ids.get("logs"),
        [
            {"name": "TRACE", "color": "gray"},
            {"name": "CRITICAL", "color": "red"},
        ],
    )

    print("\n✅ Schema 升级完成")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"❌ 升级过程中发生异常: {exc}")
        sys.exit(1)
