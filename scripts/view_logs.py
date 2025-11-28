#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChronoLullaby 日志查看工具 (Python 版本)
用于查看和过滤 JSONL 格式的日志
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 颜色代码
COLORS = {
    'DEBUG': '\033[36m',      # 青色
    'INFO': '\033[32m',       # 绿色
    'WARNING': '\033[33m',    # 黄色
    'ERROR': '\033[31m',      # 红色
    'CRITICAL': '\033[35m',   # 紫色
    'RESET': '\033[0m',       # 重置
    'GRAY': '\033[90m',       # 灰色
}


def colorize(text: str, color: str) -> str:
    """给文本添加颜色"""
    return f"{COLORS.get(color, '')}{text}{COLORS['RESET']}"


def format_log_line(log_entry: Dict, raw: bool = False) -> str:
    """格式化日志行"""
    if raw:
        return json.dumps(log_entry, ensure_ascii=False)
    
    timestamp = log_entry.get('timestamp', '')
    level = log_entry.get('level', 'UNKNOWN')
    component = log_entry.get('component', 'unknown')
    message = log_entry.get('message', '')
    
    # 提取时间部分
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        time_str = timestamp[:19] if len(timestamp) >= 19 else timestamp
    
    # 构建输出行
    level_colored = colorize(f"{level:<8}", level)
    component_colored = colorize(f"{component:<20}", 'GRAY')
    
    line = f"{time_str} | {level_colored} | {component_colored} | {message}"
    
    # 显示额外数据
    extra_lines = []
    for key, value in log_entry.items():
        if key not in ('timestamp', 'level', 'component', 'message', 'process', 'thread'):
            extra_lines.append(f"    {colorize(key + ':', 'GRAY')} {value}")
    
    if extra_lines:
        line += '\n' + '\n'.join(extra_lines)
    
    return line


def show_stats(logs: List[Dict]):
    """显示日志统计信息"""
    total = len(logs)
    
    # 按级别统计
    by_level = {}
    by_component = {}
    
    for log in logs:
        level = log.get('level', 'UNKNOWN')
        component = log.get('component', 'unknown')
        
        by_level[level] = by_level.get(level, 0) + 1
        by_component[component] = by_component.get(component, 0) + 1
    
    print(colorize("\n=== 日志统计 ===", 'INFO'))
    print(f"总日志数: {total}\n")
    
    print(colorize("按级别统计:", 'WARNING'))
    for level in sorted(by_level.keys(), key=lambda x: by_level[x], reverse=True):
        count = by_level[level]
        percent = (count / total) * 100
        level_colored = colorize(f"  {level:<10}", level)
        print(f"{level_colored}: {count:>6} ({percent:>5.1f}%)")
    
    print(colorize("\n按组件统计:", 'WARNING'))
    for component in sorted(by_component.keys(), key=lambda x: by_component[x], reverse=True):
        count = by_component[component]
        percent = (count / total) * 100
        print(colorize(f"  {component:<30}: {count:>6} ({percent:>5.1f}%)", 'GRAY'))
    print()


def read_log_file(file_path: Path) -> List[Dict]:
    """读取日志文件"""
    logs = []
    
    if not file_path.exists():
        return logs
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                log_entry = json.loads(line)
                logs.append(log_entry)
            except json.JSONDecodeError:
                # 跳过无效的行
                continue
    
    return logs


def main():
    parser = argparse.ArgumentParser(
        description='ChronoLullaby 日志查看工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python view_logs.py                          # 查看所有日志
  python view_logs.py bot                      # 只查看 bot 组件日志
  python view_logs.py --level ERROR            # 只查看 ERROR 级别日志
  python view_logs.py --filter "下载"           # 过滤包含"下载"的日志
  python view_logs.py --last 50                # 显示最后 50 条日志
  python view_logs.py --stats                  # 显示统计信息
  python view_logs.py --error-only             # 只显示错误日志
        """
    )
    
    parser.add_argument('component', nargs='?', default='all',
                        help='要查看的组件 (默认: all，可输入 bot/downloader/launcher 或子组件如 downloader.yt-dlp)')
    parser.add_argument('--level', '-l', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='按日志级别过滤')
    parser.add_argument('--filter', '-f', type=str,
                        help='按消息内容过滤')
    parser.add_argument('--last', '-n', type=int,
                        help='显示最后 N 条日志')
    parser.add_argument('--error-only', '-e', action='store_true',
                        help='只显示错误日志 (ERROR 和 CRITICAL)')
    parser.add_argument('--raw', '-r', action='store_true',
                        help='显示原始 JSON 格式')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='显示日志统计信息')
    
    args = parser.parse_args()
    
    # 确定日志目录
    script_root = Path(__file__).resolve().parent
    project_root = script_root.parent
    logs_dir = project_root / 'logs'
    if not logs_dir.exists():
        logs_dir = script_root / 'logs'
    
    if not logs_dir.exists():
        print(colorize(f"错误: 日志目录不存在 {logs_dir}", 'ERROR'))
        sys.exit(1)
    
    # 选择日志文件
    log_files = sorted(
        [f for f in logs_dir.glob('all.log*') if f.is_file()],
        key=lambda f: f.stat().st_mtime
    )
    
    if not log_files:
        print(colorize('错误: 未找到日志文件 all.log', 'WARNING'))
        print(colorize('提示: 请先运行任一组件产生日志', 'GRAY'))
        sys.exit(1)
    
    
    # 读取日志
    all_logs = []
    for log_file in log_files:
        logs = read_log_file(log_file)
        all_logs.extend(logs)
    
    # 应用过滤器
    def _match_component(component_value: str) -> bool:
        if args.component == 'all':
            return True
        if not component_value:
            return False
        normalized = component_value
        if normalized.startswith('chronolullaby.'):
            normalized = normalized[len('chronolullaby.'):]
        if normalized == args.component or component_value == args.component:
            return True
        if normalized.startswith(f'{args.component}.'):
            return True
        base = normalized.split('.')[0]
        return base == args.component

    filtered_logs = []
    for log in all_logs:
        if not _match_component(log.get('component', '')):
            continue
        # 级别过滤
        if args.level and log.get('level') != args.level:
            continue
        
        # 错误过滤
        if args.error_only and log.get('level') not in ('ERROR', 'CRITICAL'):
            continue
        
        # 消息过滤
        if args.filter and args.filter not in log.get('message', ''):
            continue
        
        filtered_logs.append(log)
    
    # 按时间排序
    filtered_logs.sort(key=lambda x: x.get('timestamp', ''))
    
    # 显示统计信息
    if args.stats:
        show_stats(filtered_logs)
        sys.exit(0)
    
    # 应用 last 参数
    if args.last and args.last > 0:
        filtered_logs = filtered_logs[-args.last:]
    
    # 显示日志
    print(colorize("=== ChronoLullaby 日志查看器 ===", 'INFO'))
    print(colorize(f"查看组件: {args.component}", 'GRAY'))
    if args.level:
        print(colorize(f"日志级别: {args.level}", 'GRAY'))
    if args.filter:
        print(colorize(f"过滤关键词: {args.filter}", 'GRAY'))
    print()
    
    if not filtered_logs:
        print(colorize("未找到匹配的日志", 'WARNING'))
        sys.exit(0)
    
    for log in filtered_logs:
        print(format_log_line(log, args.raw))
    
    print(colorize(f"\n共 {len(filtered_logs)} 条日志", 'GRAY'))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(colorize("\n\n已取消", 'WARNING'))
        sys.exit(0)

