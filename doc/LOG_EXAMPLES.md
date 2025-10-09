# 日志示例与分析

## 下载成功

```json
{
  "timestamp": "2025-10-09T11:14:30.123",
  "level": "INFO",
  "component": "chronolullaby.downloader.dl_audio",
  "message": "✅ 视频下载成功",
  "channel": "@ChanChanTalk",
  "video_index": "1/6",
  "title": "聊聊最近的科技新闻",
  "video_id": "abc123xyz",
  "file": "ChanChanTalk.聊聊最近的科技新闻.m4a",
  "size_mb": 15.3
}
```

## 跳过已存在的文件

```json
{
  "timestamp": "2025-10-09T11:15:00.456",
  "level": "INFO",
  "component": "chronolullaby.downloader.dl_audio",
  "message": "音频文件已存在，跳过下载",
  "channel": "@ChanChanTalk",
  "video_index": "2/6",
  "title": "上周的精彩回顾",
  "video_id": "def456uvw",
  "file": "ChanChanTalk.上周的精彩回顾.m4a"
}
```

## 过滤会员内容

```json
{
  "timestamp": "2025-10-09T11:15:30.789",
  "level": "INFO",
  "component": "chronolullaby.downloader.dl_audio",
  "message": "跳过会员内容",
  "video_id": "ghi789rst",
  "title": "会员专属内容"
}
```

## 下载失败

```json
{
  "timestamp": "2025-10-09T11:16:00.012",
  "level": "ERROR",
  "component": "chronolullaby.downloader.dl_audio",
  "message": "❌ 视频下载失败 - yt-dlp错误",
  "channel": "@ChanChanTalk",
  "video_index": "4/6",
  "title": "某个视频标题",
  "video_id": "jkl012mno",
  "error": "Video unavailable",
  "file": "downloader.py",
  "line": 543
}
```

## 频道处理完成汇总

```json
{
  "timestamp": "2025-10-09T11:20:00.000",
  "level": "INFO",
  "component": "chronolullaby.downloader.dl_audio",
  "message": "============================================================\n频道处理完成 - 汇总统计",
  "channel": "@ChanChanTalk",
  "total_videos": 6,
  "success": 3,
  "already_exists": 2,
  "filtered": 1,
  "archived": 0,
  "member_only": 0,
  "error": 0,
  "success_rate": "50.0%"
}
```

## Bot 发送成功

```json
{
  "timestamp": "2025-10-09T11:21:00.123",
  "level": "INFO",
  "component": "chronolullaby.bot.send_file",
  "message": "文件发送成功",
  "file_name": "ChanChanTalk.聊聊最近的科技新闻.m4a",
  "size_mb": 15.3,
  "duration_seconds": 2.5
}
```

## Bot 大文件自动分割

```json
{
  "timestamp": "2025-10-09T11:22:00.456",
  "level": "INFO",
  "component": "chronolullaby.bot.send_file",
  "message": "文件过大，开始分割",
  "file_name": "LongPodcast.三小时深度访谈.m4a",
  "size_mb": 125.8,
  "num_parts": 3
}
```

## 实用查询示例

### 查看某个频道的所有操作

```powershell
# PowerShell
Get-Content logs/downloader.log | Where-Object { $_ -like '*@ChanChanTalk*' }

# jq
jq 'select(.channel=="@ChanChanTalk")' logs/downloader.log
```

### 统计各频道成功率

```bash
# jq
jq -s '
  map(select(.message | contains("频道处理完成"))) |
  group_by(.channel) |
  map({
    channel: .[0].channel,
    success: .[0].success,
    total: .[0].total_videos,
    rate: .[0].success_rate
  })
' logs/downloader.log
```

### 找出所有错误

```bash
# jq
jq 'select(.level=="ERROR")' logs/downloader.log

# PowerShell
Get-Content logs/downloader_error.log
```

### 统计今天下载了多少视频

```bash
# jq
jq -s '
  map(select(.message | contains("✅ 视频下载成功"))) |
  length
' logs/downloader.log
```

### 查看最耗时的操作

```bash
# jq（如果有 duration_seconds 字段）
jq 'select(.duration_seconds) | {message, duration: .duration_seconds}' logs/*.log | sort -k2 -rn | head -10
```

### 实时监控下载进度

```powershell
# PowerShell
Get-Content logs/downloader.log -Tail 20 -Wait

# 或使用 ch 命令
ch logs downloader -f
```

### 导出错误报告

```bash
# 导出为 CSV
jq -r 'select(.level=="ERROR") | [.timestamp, .component, .message, .error] | @csv' logs/downloader_error.log > errors.csv

# 导出为可读文本
jq -r 'select(.level=="ERROR") | "\(.timestamp) | \(.component) | \(.message)"' logs/downloader_error.log > errors.txt
```

## 日志分析脚本示例

### PowerShell 脚本

```powershell
# 统计今天的下载情况
$today = (Get-Date).ToString("yyyy-MM-dd")
$logs = Get-Content logs/downloader.log | ConvertFrom-Json | Where-Object { $_.timestamp -like "$today*" }

$success = ($logs | Where-Object { $_.message -like "*下载成功*" }).Count
$errors = ($logs | Where-Object { $_.level -eq "ERROR" }).Count
$total = $success + $errors

Write-Host "今日下载统计："
Write-Host "  成功: $success"
Write-Host "  失败: $errors"
Write-Host "  成功率: $([math]::Round($success/$total*100, 2))%"
```

### Python 脚本

```python
#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

# 读取日志
logs = []
with open('logs/downloader.log', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            pass

# 统计频道
channels = Counter(log.get('channel') for log in logs if log.get('channel'))

print("频道处理次数：")
for channel, count in channels.most_common(10):
    print(f"  {channel}: {count}")
```
