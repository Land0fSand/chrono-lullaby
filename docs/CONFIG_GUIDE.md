# 配置指南

## 配置文件

ChronoLullaby 使用 `config/config.yaml` 进行配置。

> 提示：新项目可根据需求选择模板：`config/config.notion.example.yaml`（Notion 模式最简配置）或 `config/config.local.example.yaml`（本地模式示例配置）。复制后再进行修改。

---

## 完整配置示例

```yaml
mode: local

log:
  level: INFO

# Telegram Bot 配置
telegram:
  bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
  send_interval: 4920  # 发送间隔（秒），默认82分钟

# YouTube 下载器配置
downloader:
  download_interval: 29520  # 下载轮次间隔（秒），默认约8小时
  cookies_file: "youtube.cookies"  # Cookies文件路径
  download_archive: "download_archive.txt"  # 下载记录
  filter_days: 3  # 只下载最近N天的视频
  max_videos_per_channel: 6  # 每频道最多下载视频数

# 频道组配置
channel_groups:
  - name: "示例频道"
    description: "包含若干的频道"  # 可选
    telegram_chat_id: "-1001234567890"
    audio_folder: "au"  # 音频存储目录
    youtube_channels:
      - "@StorytellerFan"
      - "@meowsir"
      - "@频道3"  # 支持中文
      # - "@暂停的频道"  # 用#注释掉不需要的频道
```
---

## 配置项说明

### Telegram 配置

| 配置项 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `bot_token` | ✅ | - | Bot Token（从 @BotFather 获取） |
| `send_interval` | ❌ | 4920 | 发送文件任务间隔（秒） |

### 下载器配置

| 配置项 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `download_interval` | ❌ | 29520 | 下载轮次间隔（秒） |
| `cookies_file` | ❌ | youtube.cookies | Cookies 文件路径 |
| `download_archive` | ❌ | download_archive.txt | 已下载记录文件 |
| `filter_days` | ❌ | 3 | 只下载最近N天的视频 |
| `max_videos_per_channel` | ❌ | 6 | 每频道检查的最大视频数 |

### 日志设置

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `log.level` | str | INFO | 全局日志级别（DEBUG / INFO / WARNING / ERROR） |

### 频道组配置

| 配置项 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `name` | ✅ | - | 频道组名称（用于日志） |
| `description` | ❌ | - | 频道组描述 |
| `telegram_chat_id` | ✅ | - | Telegram 频道/群组 ID |
| `audio_folder` | ❌ | au | 音频文件存储目录 |
| `youtube_channels` | ✅ | - | YouTube 频道列表 |

---

## 获取 Telegram Chat ID

### 方法1：使用 /chatid 命令（推荐）

这是最简单的方法！

1. 启动 Bot：`ch start`
2. 将 Bot 添加到目标频道（需要管理员权限）
3. 在频道中发送：`/chatid`
4. Bot 会回复包含 Chat ID 的消息

**支持所有频道类型：**
- ✅ 私有频道/超级群组
- ✅ 公开频道
- ✅ 群组
- ✅ 私聊

详见：[CHATID_COMMAND.md](CHATID_COMMAND.md)

### 方法2：使用 @userinfobot

1. 在 Telegram 搜索 `@userinfobot`
2. 将它添加到你的频道
3. 在频道发送任何消息
4. Bot 会回复 Chat ID

### 方法3：Telegram API

访问（替换 `YOUR_BOT_TOKEN`）：
```
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

在返回的 JSON 中查找 `"chat":{"id":-1001234567890}`

---

## YouTube 频道格式

支持以下格式：

```yaml
youtube_channels:
  - "@频道handle"              # 推荐：频道handle
  - "https://youtube.com/@handle"  # 完整URL
  - "UCxxxxxxxxxxxxxxxxxxxxxxx"    # 频道ID
  - "@中文频道名"              # 支持中文
```

---

## 配置文件位置

| 文件 | 说明 |
|------|------|
| `config/config.yaml` | 当前生效的配置文件 |
| `config/config.notion.example.yaml` | Notion 模式最简模板 |
| `config/config.local.example.yaml` | 本地模式示例模板 |
| `config/youtube.cookies` | YouTube Cookies（可选，用于会员内容） |

---

## 快速开始

### 1. 复制配置示例

```powershell
copy config\config.local.example.yaml config\config.yaml
```

### 2. 编辑配置

填写 Bot Token 和 Chat ID（其他使用默认值即可）：

```yaml
telegram:
  bot_token: "你的BOT_TOKEN"

channel_groups:
  - name: "主频道"
    telegram_chat_id: "你的CHAT_ID"
    youtube_channels:
      - "@频道1"
      - "@频道2"
```

### 3. 启动服务

```powershell
ch start
```

---

## 常见问题

### Q: 配置修改后需要重启吗？

A: 频道列表修改会自动生效。Bot Token 和 Chat ID 修改需要重启：
```powershell
ch stop
ch start
```

### Q: 如何暂停某个频道？

A: 在该频道前加 `#` 注释：
```yaml
youtube_channels:
  - "@正常频道"
  # - "@暂停的频道"
```

### Q: Chat ID 为什么是负数？

A: Telegram 设计：
- 用户 ID 是正数
- 群组/频道 ID 是负数
- 超级群组通常以 `-100` 开头

### Q: 如何下载会员专属内容？

A: 需要提供 YouTube Cookies：
1. 使用浏览器扩展导出 cookies（如 "Get cookies.txt"）
2. 保存为 `config/youtube.cookies`
3. 配置中设置：
   ```yaml
   downloader:
     cookies_file: "youtube.cookies"
   ```

---

## 更多文档

- [主文档](../readme.md)
- [/chatid 命令说明](CHATID_COMMAND.md)

---

## 同步到 Notion

若已完成本地配置，想切换到 Notion 模式，可运行：
```powershell
ch sync-to-notion --data config
```
也可将 `config` 替换为 `all` / `archive` / `logs` 以同步其他数据。

### 故事型频道说明
- 在 channel_groups 中设置 channel_type: story（默认 realtime）
- 故事型频道建议仅配置 1 个 YouTube 频道
- 在该频道组下配置 story.interval_seconds（秒）和 story.items_per_run（每轮抓取条数），用于控制抓取频率
- 故事型按发布时间顺序补全历史内容，不受 ilter_days/max_videos_per_channel 限制
