# -*- coding: utf-8 -*-
"""
Notion 日志清理工具

功能：
1. 按时间清理：删除超过指定天数的日志
2. 按级别清理：可选择只清理特定级别的日志
3. 按机器清理：可选择清理特定 machine_id 的日志
4. 全清理模式：带二次确认的全清理功能
5. 预览模式：先显示将要删除的数量，再确认执行
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config_provider import NotionConfigProvider
from src.notion_adapter import NotionAdapter


def load_config() -> tuple:
    """
    加载配置
    
    Returns:
        (NotionConfigProvider, NotionAdapter, logs_database_id)
    """
    try:
        provider = NotionConfigProvider()
        adapter = provider.adapter
        database_id = provider.config_data.get('database_ids', {}).get('logs')
        
        if not database_id:
            print("❌ 错误：Logs 数据库 ID 未配置")
            print("   请先运行: ch init-notion")
            sys.exit(1)
        
        return provider, adapter, database_id
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        sys.exit(1)


def query_logs_to_clean(
    adapter: NotionAdapter,
    database_id: str,
    days: Optional[int] = None,
    levels: Optional[List[str]] = None,
    log_types: Optional[List[str]] = None,
    machine_id: Optional[str] = None,
    all_logs: bool = False
) -> List[Dict]:
    """
    查询需要清理的日志
    
    Args:
        adapter: NotionAdapter 实例
        database_id: 日志数据库 ID
        days: 保留最近 N 天的日志（删除 N 天前的）
        levels: 要清理的日志级别列表，如 ["INFO", "WARNING"]
        log_types: 要清理的日志类型列表，如 ["downloader", "bot"]
        machine_id: 要清理的机器 ID
        all_logs: 是否清理所有日志
    
    Returns:
        需要清理的日志页面列表
    """
    print("\n🔍 正在查询日志...")
    
    # 构建过滤条件
    filters = []
    
    if not all_logs:
        # 时间过滤
        if days is not None:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            filters.append({
                "property": "timestamp",
                "date": {
                    "before": cutoff_date.isoformat()
                }
            })
        
        # 级别过滤
        if levels:
            level_filters = [
                {
                    "property": "level",
                    "select": {"equals": level}
                }
                for level in levels
            ]
            if len(level_filters) > 1:
                filters.append({"or": level_filters})
            elif len(level_filters) == 1:
                filters.append(level_filters[0])
        
        # 类型过滤
        if log_types:
            type_filters = [
                {
                    "property": "log_type",
                    "select": {"equals": log_type}
                }
                for log_type in log_types
            ]
            if len(type_filters) > 1:
                filters.append({"or": type_filters})
            elif len(type_filters) == 1:
                filters.append(type_filters[0])
        
        # 机器 ID 过滤
        if machine_id:
            filters.append({
                "property": "machine_id",
                "rich_text": {"equals": machine_id}
            })
    
    # 组合过滤条件
    filter_obj = None
    if filters:
        if len(filters) > 1:
            filter_obj = {"and": filters}
        elif len(filters) == 1:
            filter_obj = filters[0]
    
    # 查询日志
    try:
        pages = adapter.query_database(
            database_id,
            filter_obj=filter_obj,
            page_size=100
        )
        return pages
    except Exception as e:
        print(f"❌ 查询日志失败: {e}")
        return []


def preview_cleanup(pages: List[Dict], adapter: NotionAdapter):
    """
    预览要清理的日志
    
    Args:
        pages: 日志页面列表
        adapter: NotionAdapter 实例
    """
    total = len(pages)
    print(f"\n📊 查询结果：共找到 {total} 条日志")
    
    if total == 0:
        return
    
    # 统计信息
    level_counts = {}
    type_counts = {}
    machine_counts = {}
    
    for page in pages:
        level = adapter.extract_property_value(page, 'level')
        log_type = adapter.extract_property_value(page, 'log_type')
        machine_id = adapter.extract_property_value(page, 'machine_id')
        
        level_counts[level] = level_counts.get(level, 0) + 1
        type_counts[log_type] = type_counts.get(log_type, 0) + 1
        machine_counts[machine_id] = machine_counts.get(machine_id, 0) + 1
    
    print("\n📈 统计信息：")
    print(f"  按级别：")
    for level, count in sorted(level_counts.items()):
        print(f"    - {level}: {count} 条")
    
    print(f"  按类型：")
    for log_type, count in sorted(type_counts.items()):
        print(f"    - {log_type}: {count} 条")
    
    print(f"  按机器：")
    for machine_id, count in sorted(machine_counts.items()):
        print(f"    - {machine_id or '(未设置)'}: {count} 条")
    
    # 显示最早和最晚的日志时间
    timestamps = []
    for page in pages:
        timestamp_str = adapter.extract_property_value(page, 'timestamp')
        if timestamp_str:
            try:
                timestamps.append(datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')))
            except:
                pass
    
    if timestamps:
        timestamps.sort()
        print(f"\n⏰ 时间范围：")
        print(f"  最早：{timestamps[0].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  最晚：{timestamps[-1].strftime('%Y-%m-%d %H:%M:%S')}")


def clean_logs(
    adapter: NotionAdapter,
    database_id: str,
    days: Optional[int] = None,
    levels: Optional[List[str]] = None,
    log_types: Optional[List[str]] = None,
    machine_id: Optional[str] = None,
    all_logs: bool = False,
    preview_only: bool = True
) -> bool:
    """
    清理日志
    
    Args:
        adapter: NotionAdapter 实例
        database_id: 日志数据库 ID
        days: 保留最近 N 天的日志
        levels: 要清理的日志级别列表
        log_types: 要清理的日志类型列表
        machine_id: 要清理的机器 ID
        all_logs: 是否清理所有日志
        preview_only: 是否只预览，不实际删除
    
    Returns:
        是否成功
    """
    # 查询日志
    pages = query_logs_to_clean(
        adapter, database_id, days, levels, log_types, machine_id, all_logs
    )
    
    # 预览
    preview_cleanup(pages, adapter)
    
    if len(pages) == 0:
        print("\n✅ 没有需要清理的日志")
        return True
    
    if preview_only:
        print("\n💡 提示：这是预览模式，未实际删除。添加 --confirm 参数以执行删除。")
        return True
    
    # 二次确认
    print("\n⚠️  警告：即将删除以上日志！")
    confirmation = input("请输入 'yes' 确认删除，或其他任意键取消: ").strip().lower()
    
    if confirmation != 'yes':
        print("❌ 操作已取消")
        return False
    
    # 执行删除
    print(f"\n🗑️  正在删除 {len(pages)} 条日志...")
    
    page_ids = [page['id'] for page in pages]
    success_count, failed_count = adapter.batch_archive_pages(page_ids)
    
    print(f"\n✅ 删除完成：")
    print(f"  成功：{success_count} 条")
    print(f"  失败：{failed_count} 条")
    
    return failed_count == 0


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="ChronoLullaby Notion 日志清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：

  1. 预览删除 30 天前的日志（推荐）：
     python -m src.commands.clean_notion_logs --days 30

  2. 实际删除 30 天前的日志：
     python -m src.commands.clean_notion_logs --days 30 --confirm

  3. 只删除 INFO 级别的旧日志，保留 ERROR 和 WARNING：
     python -m src.commands.clean_notion_logs --days 30 --levels INFO --confirm

  4. 删除特定机器的日志：
     python -m src.commands.clean_notion_logs --days 30 --machine machine-1 --confirm

  5. 删除特定类型的日志：
     python -m src.commands.clean_notion_logs --days 30 --types downloader --confirm

  6. 全清理（危险！会删除所有日志）：
     python -m src.commands.clean_notion_logs --all --confirm

推荐配置：
  - 每周清理一次 30 天前的 INFO 级别日志
  - 每月清理一次 90 天前的所有日志
        """
    )
    
    # 清理模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--days',
        type=int,
        help='删除 N 天前的日志（例如 --days 30 删除 30 天前的日志）'
    )
    mode_group.add_argument(
        '--all',
        action='store_true',
        help='删除所有日志（危险操作！）'
    )
    
    # 过滤条件
    parser.add_argument(
        '--levels',
        nargs='+',
        choices=['INFO', 'WARNING', 'ERROR', 'DEBUG'],
        help='只清理指定级别的日志（可多选）'
    )
    parser.add_argument(
        '--types',
        nargs='+',
        choices=['downloader', 'bot', 'error', 'system'],
        help='只清理指定类型的日志（可多选）'
    )
    parser.add_argument(
        '--machine',
        type=str,
        help='只清理指定机器的日志（例如 machine-1）'
    )
    
    # 执行选项
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='确认执行删除（不加此参数则只预览）'
    )
    
    args = parser.parse_args()
    
    # 打印标题
    print("=" * 70)
    print("  ChronoLullaby - Notion 日志清理工具")
    print("=" * 70)
    
    # 加载配置
    provider, adapter, database_id = load_config()
    
    # 显示清理参数
    print("\n📝 清理参数：")
    if args.all:
        print("  模式：全清理（删除所有日志）")
        print("  ⚠️  警告：这是危险操作！")
    else:
        print(f"  模式：按时间清理（保留最近 {args.days} 天）")
    
    if args.levels:
        print(f"  级别：{', '.join(args.levels)}")
    else:
        print("  级别：全部")
    
    if args.types:
        print(f"  类型：{', '.join(args.types)}")
    else:
        print("  类型：全部")
    
    if args.machine:
        print(f"  机器：{args.machine}")
    else:
        print("  机器：全部")
    
    if args.confirm:
        print("  执行：实际删除")
    else:
        print("  执行：仅预览（添加 --confirm 以实际删除）")
    
    # 执行清理
    success = clean_logs(
        adapter=adapter,
        database_id=database_id,
        days=args.days,
        levels=args.levels,
        log_types=args.types,
        machine_id=args.machine,
        all_logs=args.all,
        preview_only=not args.confirm
    )
    
    print("\n" + "=" * 70)
    
    if success:
        if args.confirm:
            print("✅ 清理完成！")
        else:
            print("✅ 预览完成！")
    else:
        print("❌ 清理失败！")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

