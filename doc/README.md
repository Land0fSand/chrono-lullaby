# ChronoLullaby 使用文档

> YouTube 频道音频自动下载 + Telegram Bot 发送工具

## 快速开始

```powershell
# 启动服务
ch start

# 查看状态
ch status

# 查看日志
ch logs

# 重启服务
ch restart

# 停止服务
ch stop
```

## 命令详解

### `ch start`

后台启动下载器和 Bot，自动创建日志文件。

### `ch stop`

停止所有相关进程，清理进程信息。

### `ch restart`

重启服务，等同于 stop + 等待 + start。

### `ch status`

显示进程运行状态、PID、运行时间、资源占用。

### `ch logs [类型] [选项]`

**日志类型**：

- `all` - 所有日志（默认）
- `downloader` - 下载器日志
- `bot` - Bot 日志
- `error` - 错误日志

**选项**：

- `--lines N` - 显示最后 N 行（默认 50）
- `-f` / `--follow` - 实时跟踪
- `-l` / `--list` - 列出所有日志文件

**示例**：

```powershell
ch logs                    # 查看所有日志
ch logs downloader -f      # 实时跟踪下载器日志
ch logs error              # 只看错误
ch logs --lines 100        # 最后 100 行
ch logs --list             # 列出所有日志文件
```

### `ch cleanup`

强制清理所有 Python/Poetry 进程（危险操作，会影响其他项目）。

## 日志系统

### 日志文件

```
logs/
├── downloader.log          # 下载器日志（JSONL）
├── downloader_error.log    # 下载器错误日志
├── bot.log                 # Bot 日志（JSONL）
├── bot_error.log           # Bot 错误日志
└── *.log.1, *.log.2        # 轮转的旧日志（10MB/文件）
```

### 日志级别

| 级别     | 说明     | 示例                 |
| -------- | -------- | -------------------- |
| DEBUG    | 调试信息 | 过滤器检查、文件路径 |
| INFO     | 正常操作 | 下载成功、发送完成   |
| WARNING  | 警告     | 重试操作、跳过内容   |
| ERROR    | 错误     | 下载失败、转换失败   |
| CRITICAL | 严重错误 | 启动失败、配置错误   |

### 日志格式

**文件（JSONL）**：

```json
{
  "timestamp": "2025-10-09T14:30:25",
  "level": "INFO",
  "component": "downloader.dl_audio",
  "message": "✅ 视频下载成功",
  "channel": "@example",
  "video_id": "abc123",
  "file": "audio.m4a",
  "size_mb": 5.2
}
```

**控制台（彩色）**：

```
2025-10-09 14:30:25 | INFO     | dl_audio     | ✅ 视频下载成功
```

### 查询日志

**PowerShell（Windows）**：

```powershell
# 查询特定频道的日志
Get-Content logs/downloader.log | Where-Object { $_ -like '*@ChanChanTalk*' }

# 只看错误
Get-Content logs/downloader_error.log

# 最后 50 行
Get-Content logs/downloader.log -Tail 50
```

**使用 jq（推荐）**：

```bash
# 安装 jq: winget install jqlang.jq

# 查看格式化的日志
jq . logs/downloader.log

# 只看 ERROR 级别
jq 'select(.level=="ERROR")' logs/downloader.log

# 查看特定频道
jq 'select(.channel=="@ChanChanTalk")' logs/downloader.log

# 统计下载成功率
jq -s 'group_by(.channel) | map({channel: .[0].channel, total: length})' logs/downloader.log
```

## 频道管理

### 添加频道

编辑 `channels.txt`，每行一个频道 URL 或 ID：

```
https://www.youtube.com/@ChanChanTalk
@TechChannel
UCxxxxxxxxxxxxxxxxxxxxx
```

保存后，下载器会自动刷新频道列表（无需重启）。

### 下载规则

- 每个频道下载最近 **6 个视频**
- 跳过**已下载**的视频（根据文件名判断）
- 跳过**会员专属**内容
- 跳过**已归档**的视频（记录在 `download_archive.txt`）
- 每 **24 小时**循环一次

### 下载统计

每个频道处理完成后会输出汇总：

```json
{
  "message": "频道处理完成 - 汇总统计",
  "channel": "@example",
  "total_videos": 15,
  "success": 4,
  "already_exists": 2,
  "filtered": 3,
  "archived": 5,
  "error": 1,
  "success_rate": "26.7%"
}
```

**状态说明**：

- `success` - 成功下载
- `already_exists` - 文件已存在，跳过
- `filtered` - 被过滤器跳过（会员内容、时间范围外等）
- `archived` - 已在归档中记录
- `error` - 下载失败

## Bot 功能

### 支持的命令

- `/add <频道URL>` - 添加新频道
- 其他命令（根据 `telegram_bot.py` 实现）

### 文件发送

- 自动发送到配置的 Telegram 频道
- **大文件自动分割**（每段 ≤ 45MB，避免 Telegram 50MB 限制）
- 使用 **ffmpeg** 无损分割
- 发送失败自动重试（最多 3 次，每次间隔 10 秒）

### 错误处理

- 超时自动重试
- Bot 冲突检测（防止多实例）
- 详细错误日志（`logs/bot_error.log`）

## 故障排查

### 问题：Bot 启动失败

**检查**：

```powershell
# 查看错误日志
Get-Content logs/bot_error.log

# 检查是否有多个实例运行
ch status

# 如果有冲突，强制停止
ch cleanup
```

### 问题：下载失败

**检查**：

```powershell
# 查看错误日志
ch logs error

# 查看特定频道的下载情况
Get-Content logs/downloader.log | Select-String "频道处理完成"

# 检查 cookies 是否过期
# 如果需要会员内容，更新 youtube.cookies
```

### 问题：日志文件太大

日志自动轮转（10MB/文件，保留 5 个备份），但如果需要手动清理：

```powershell
# 停止服务
ch stop

# 删除旧日志
Remove-Item logs/*.log.* -Force

# 或删除所有日志
Remove-Item logs/* -Force

# 重新启动
ch start
```

## 配置文件

### `.env`

Bot 配置（Token、频道 ID 等）：

```env
TELEGRAM_BOT_TOKEN=your_token_here
CHANNEL_ID=@your_channel
```

### `youtube.cookies`

YouTube Cookies（用于下载会员内容）。

### `download_archive.txt`

已下载视频记录（自动管理，无需手动编辑）。

## 技术细节

### 项目结构

```
chronolullaby/
├── src/
│   ├── logger.py              # 统一日志系统
│   ├── yt_dlp_downloader.py   # 下载器主程序
│   ├── telegram_bot.py        # Bot 主程序
│   ├── task/
│   │   ├── dl_audio.py        # 音频下载逻辑
│   │   └── send_file.py       # 文件发送逻辑
│   └── commands/
│       └── add_channel.py     # /add 命令处理
├── ch.ps1                     # 主命令脚本
├── ch-stop.ps1                # 停止脚本
├── ch-cleanup.ps1             # 清理脚本
├── channels.txt               # 频道列表
└── logs/                      # 日志目录
```

### 依赖

- Python 3.9+
- Poetry（依赖管理）
- yt-dlp（视频下载）
- python-telegram-bot（Bot 框架）
- ffmpeg（音频处理）

### 日志轮转

- 单文件最大 10MB
- 保留 5 个备份（`*.log.1` - `*.log.5`）
- 超过限制自动创建新文件

## 更新历史

### v1.1.0 (2025-10-09)

- ✅ 重构日志系统为 JSONL 格式
- ✅ 新增 `restart` 命令
- ✅ 修复 PowerShell 日志清理错误
- ✅ 修复 Bot proxy_url 参数错误
- ✅ 优化下载过滤器逻辑
- ✅ 增强频道下载统计

### v1.0.0

- 初始版本
