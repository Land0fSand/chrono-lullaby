# ChronoLullaby 使用文档

> YouTube 频道音频自动下载 + Telegram Bot 推送工具

---

## 快速命令

```powershell
ch start      # 启动服务
ch stop       # 停止服务
ch status     # 查看状态
ch logs       # 查看日志
ch logs -f    # 实时日志
ch cleanup    # 强制清理
```

## 初次使用

如果你是第一次使用 ChronoLullaby，程序会自动为你创建必要的目录：

- **`au/`** - 存放下载的音频文件
- **`data/`** - 存放下载记录和发送记录

只需要：
1. 克隆项目并配置 `config/config.yaml`
2. 运行 `ch start` 启动服务

程序会自动创建所需的所有目录结构，无需手动操作。

---

## 配置指南

### 1. Telegram Bot 配置

编辑 `config/config.yaml`：

```yaml
telegram:
  bot_token: "你的BOT_TOKEN"
  send_interval: 4920  # 发送间隔（秒）

channel_groups:
  - name: "主频道"
    telegram_chat_id: "你的CHAT_ID"  # 使用 /chatid 命令获取
    audio_folder: "au"
    youtube_channels:
      - "@频道1"
      - "@频道2"
```

**获取 Chat ID：**
1. 将 Bot 添加到目标频道
2. 在频道中发送 `/chatid`
3. 复制 Bot 回复的 Chat ID

详见：[CHATID_COMMAND.md](CHATID_COMMAND.md)

### 2. YouTube 频道管理

直接在 `config/config.yaml` 中编辑 `youtube_channels` 列表，保存后自动生效。

**下载规则：**
- 每频道最多下载 6 个最新视频
- 只下载最近 3 天内的视频
- 自动跳过：已下载、会员专属、已归档的视频
- 每 8 小时循环一次

---

## 日志系统

### 日志文件

| 文件 | 说明 |
|------|------|
| `logs/downloader.log` | 下载器日志（JSONL格式） |
| `logs/downloader_error.log` | 下载错误日志 |
| `logs/bot.log` | Bot 日志 |
| `logs/bot_error.log` | Bot 错误日志 |

### 常用日志命令

```powershell
# 查看所有日志
ch logs

# 查看下载器日志
ch logs downloader

# 实时跟踪
ch logs downloader -f

# 查看错误
ch logs error

# 查看最近100行
ch logs --lines 100
```

### 使用 PowerShell 查询

```powershell
# 查找特定频道
Get-Content logs/downloader.log | Select-String "@频道名"

# 最后50行
Get-Content logs/downloader.log -Tail 50

# 实时跟踪
Get-Content logs/downloader.log -Tail 10 -Wait
```

### 使用 jq 分析（推荐）

```bash
# 安装: winget install jqlang.jq

# 只看错误
jq 'select(.level=="ERROR")' logs/downloader.log

# 查看特定频道
jq 'select(.channel=="@频道名")' logs/downloader.log

# 统计下载成功率
jq -s 'map(select(.message | contains("频道处理完成")))' logs/downloader.log
```

---

## 故障排查

### Bot 启动失败

```powershell
# 查看错误日志
ch logs error

# 检查状态
ch status

# 强制清理并重启
ch cleanup
ch start
```

### 下载失败

```powershell
# 查看下载器错误
Get-Content logs/downloader_error.log

# 检查频道处理汇总
Get-Content logs/downloader.log | Select-String "频道处理完成"
```

### 清理日志

```powershell
# 停止服务
ch stop

# 删除旧日志（日志会自动轮转，10MB/文件）
Remove-Item logs/*.log.* -Force

# 重启
ch start
```

---

## 高级配置

### 调整下载间隔

编辑 `config/config.yaml`：

```yaml
downloader:
  download_interval: 29520  # 秒（默认约8小时）
  filter_days: 3            # 只下载最近N天的视频
  max_videos_per_channel: 6 # 每频道检查的最大视频数
```

### 调整发送间隔

```yaml
telegram:
  send_interval: 4920  # 秒（默认82分钟）
```

### 使用 YouTube Cookies（下载会员内容）

将 cookies 文件放在 `config/youtube.cookies`，配置文件会自动读取。

---

## 技术栈

- Python 3.9+ / Poetry
- yt-dlp（YouTube下载）
- python-telegram-bot（Bot框架）
- ffmpeg（音频处理）
- PowerShell 7+（管理脚本）

---

## 相关文档

- [配置指南详解](CONFIG_GUIDE.md)
- [/chatid 命令说明](CHATID_COMMAND.md)

---

## 许可证

本项目基于 GNU 通用公共许可证（GPL）开源。
