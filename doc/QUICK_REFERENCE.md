# ChronoLullaby 快速参考

## 常用命令

```powershell
ch start            # 启动
ch stop             # 停止
ch restart          # 重启
ch status           # 状态
ch logs             # 查看日志
ch logs -f          # 实时日志
ch logs error       # 错误日志
ch logs --list      # 列出所有日志
ch cleanup          # 强制清理（危险）
```

## 日志文件

| 文件                        | 说明                      |
| --------------------------- | ------------------------- |
| `logs/downloader.log`       | 下载器主日志（JSONL）     |
| `logs/downloader_error.log` | 下载器错误日志            |
| `logs/bot.log`              | Bot 主日志（JSONL）       |
| `logs/bot_error.log`        | Bot 错误日志              |
| `logs/*.log.1-5`            | 轮转的旧日志（10MB/文件） |

## 日志查询

```powershell
# 最后 50 行
Get-Content logs/downloader.log -Tail 50

# 实时跟踪
Get-Content logs/downloader.log -Tail 10 -Wait

# 查找特定频道
Get-Content logs/downloader.log | Select-String "@ChanChanTalk"

# 只看错误
Get-Content logs/downloader_error.log

# 使用 jq（推荐）
jq 'select(.level=="ERROR")' logs/downloader.log
jq 'select(.channel=="@example")' logs/downloader.log
```

## 频道管理

编辑 `channels.txt`：

```
https://www.youtube.com/@ChanChanTalk
@TechChannel
UCxxxxxxxxxxxxxxxxxxxxx
```

保存后自动刷新，无需重启。

## 下载规则

- 每频道最多 6 个最新视频
- 跳过：已下载、会员内容、已归档
- 循环间隔：24 小时

## 故障排查

```powershell
# 查看错误
ch logs error

# 检查状态
ch status

# 完全重启
ch stop
Start-Sleep 3
ch start

# 强制清理（会杀掉所有 Python 进程）
ch cleanup
```

## 配置文件

| 文件                   | 说明                        |
| ---------------------- | --------------------------- |
| `.env`                 | Bot Token、频道 ID          |
| `youtube.cookies`      | YouTube Cookies（会员内容） |
| `channels.txt`         | 频道列表                    |
| `download_archive.txt` | 已下载记录（自动管理）      |

## 日志级别

| 级别     | 说明     |
| -------- | -------- |
| DEBUG    | 调试信息 |
| INFO     | 正常操作 |
| WARNING  | 警告     |
| ERROR    | 错误     |
| CRITICAL | 严重错误 |

## 下载状态

| 状态           | 图标 | 说明         |
| -------------- | ---- | ------------ |
| success        | ✅   | 成功下载     |
| already_exists | 📦   | 文件已存在   |
| filtered       | 🚫   | 被过滤器跳过 |
| archived       | 📚   | 已在归档中   |
| member_only    | 🔒   | 会员专属内容 |
| error          | ❌   | 下载失败     |

## 汇总统计字段

```json
{
  "total_videos": 15, // 总视频数
  "success": 4, // 成功下载
  "already_exists": 2, // 已存在
  "filtered": 3, // 被过滤
  "archived": 5, // 已归档
  "member_only": 0, // 会员内容
  "error": 1, // 错误
  "success_rate": "26.7%" // 成功率
}
```

## Bot 功能

- `/add <频道URL>` - 添加新频道
- 自动发送到配置的 Telegram 频道
- 大文件自动分割（每段 ≤45MB）
- 失败自动重试（3 次）

## 技术栈

- Python 3.9+ / Poetry
- yt-dlp（下载）
- python-telegram-bot（Bot）
- ffmpeg（音频处理）
- PowerShell 7+（管理脚本）

## 项目目录

```
chronolullaby/
├── ch.ps1                  # 主命令
├── src/
│   ├── yt_dlp_downloader.py
│   ├── telegram_bot.py
│   ├── logger.py           # 日志系统
│   └── task/
│       ├── dl_audio.py     # 下载逻辑
│       └── send_file.py    # 发送逻辑
├── channels.txt            # 频道列表
├── logs/                   # 日志目录
└── doc/                    # 文档
```

## 实用技巧

### 批量查询日志

```bash
# 统计各频道下载数量
jq -s 'group_by(.channel) | map({channel: .[0].channel, count: length})' logs/downloader.log

# 导出错误为 CSV
jq -r 'select(.level=="ERROR") | [.timestamp, .message] | @csv' logs/downloader_error.log > errors.csv
```

### 清理日志

```powershell
# 停止服务
ch stop

# 删除旧日志
Remove-Item logs/*.log.* -Force

# 或删除全部
Remove-Item logs/* -Force

# 重启
ch start
```

### 监控运行

```powershell
# 循环检查状态
while ($true) {
    Clear-Host
    ch status
    Start-Sleep 60
}
```

## 支持

- 文档：`doc/README.md`
- 示例：`doc/LOG_EXAMPLES.md`
- 帮助：`ch help`
