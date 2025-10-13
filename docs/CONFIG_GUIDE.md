# ChronoLullaby 配置指南

## 概述

ChronoLullaby 现在支持两种配置方式：

1. **新方式（推荐）**：使用 `config.yaml` 文件进行统一配置
2. **旧方式（向后兼容）**：使用 `channels.txt` + `.env` 文件

程序会**优先读取 `config.yaml`**，如果不存在则回退到传统配置方式。

---

## 快速开始

### 方式 1：使用 YAML 配置（推荐）

1. **复制示例配置文件：**
   ```bash
   copy config.yaml.example config.yaml
   # 或 Linux/Mac:
   cp config.yaml.example config.yaml
   ```

2. **编辑 config.yaml，填入真实值：**
   ```yaml
   telegram:
     bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # 你的 Bot Token
     send_interval: 4920  # 可选，默认 4920 秒（82 分钟）
   
   channel_groups:
     - name: "主频道"
       telegram_chat_id: "-1001234567890"  # 你的频道 ID
       audio_folder: "au"
       youtube_channels:
         - "@StorytellerFan"
         - "@meowsir"
         # ... 更多频道
   ```

3. **运行程序：**
   ```bash
   .\ch.ps1
   ```

### 方式 2：使用传统配置（向后兼容）

如果你已经有 `channels.txt` 和 `.env` 文件，可以继续使用它们：

1. **channels.txt** - YouTube 频道列表
2. **.env** - Bot Token 和 Chat ID

---

## YAML 配置详解

### 完整配置示例

```yaml
# ============================================================
# Telegram Bot 配置
# ============================================================
telegram:
  # Bot Token（从 @BotFather 获取）
  # 必需
  bot_token: "YOUR_BOT_TOKEN_HERE"
  
  # 发送文件任务间隔（秒）
  # 可选，默认 4920 秒 = 1小时22分钟
  send_interval: 4920

# ============================================================
# YouTube 下载器配置
# ============================================================
downloader:
  # 下载轮次间隔（秒）
  # 可选，默认 29520 秒 = 约 8.2 小时
  download_interval: 29520
  
  # YouTube Cookies 文件路径
  # 可选，默认 "youtube.cookies"
  cookies_file: "youtube.cookies"
  
  # 下载存档文件（记录已下载的视频）
  # 可选，默认 "download_archive.txt"
  download_archive: "download_archive.txt"
  
  # 视频过滤：只下载最近 N 天的视频
  # 可选，默认 3 天
  filter_days: 3
  
  # 每个频道检查的最大视频数
  # 可选，默认 6
  max_videos_per_channel: 6

# ============================================================
# 频道组配置
# ============================================================
channel_groups:
  # 主频道组
  - name: "主频道"  # 频道组名称（用于日志）
    description: "所有订阅的 YouTube 频道"  # 可选描述
    
    # Telegram 聊天 ID（频道/群组）
    # 必需
    telegram_chat_id: "YOUR_CHAT_ID_HERE"
    
    # 音频文件存储目录
    # 可选，默认 "au"
    audio_folder: "au"
    
    # YouTube 频道列表
    # 必需
    youtube_channels:
      - "@StorytellerFan"
      - "@meowsir"
      - "@wuyuesanren"
      # - "@vexilla01"  # 使用 # 注释掉不需要的频道
      - "@夸克说"  # 支持中文频道名
```

### 配置项说明

#### Telegram 配置

| 配置项 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `bot_token` | 字符串 | ✅ 是 | 无 | Telegram Bot Token，从 @BotFather 获取 |
| `send_interval` | 整数 | ❌ 否 | 4920 | 发送文件任务间隔（秒） |

#### 下载器配置

| 配置项 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `download_interval` | 整数 | ❌ 否 | 29520 | 下载轮次间隔（秒） |
| `cookies_file` | 字符串 | ❌ 否 | youtube.cookies | YouTube Cookies 文件路径 |
| `download_archive` | 字符串 | ❌ 否 | download_archive.txt | 下载存档文件路径 |
| `filter_days` | 整数 | ❌ 否 | 3 | 只下载最近 N 天的视频 |
| `max_videos_per_channel` | 整数 | ❌ 否 | 6 | 每个频道检查的最大视频数 |

#### 频道组配置

| 配置项 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `name` | 字符串 | ✅ 是 | 无 | 频道组名称（用于日志） |
| `description` | 字符串 | ❌ 否 | 无 | 频道组描述 |
| `telegram_chat_id` | 字符串 | ✅ 是 | 无 | Telegram 聊天 ID |
| `audio_folder` | 字符串 | ❌ 否 | au | 音频文件存储目录 |
| `youtube_channels` | 列表 | ✅ 是 | 无 | YouTube 频道列表 |

---

## 获取 Telegram Chat ID

### 方法 1：使用 /chatid 命令（推荐）⭐

**这是最简单、最直接的方法！**

1. 确保你的 Bot 已启动（运行 `ch start`）
2. 将你的 Bot 添加到目标频道（包括私有频道）
3. 在频道中发送命令：`/chatid`
4. Bot 会立即回复包含该频道 Chat ID 的消息

**优点：**
- ✅ 无需停止主进程
- ✅ 支持私有频道
- ✅ 直接显示完整信息（Chat ID、类型、标题）
- ✅ 方便快捷

详细说明请参考：[/chatid 命令使用说明](CHATID_COMMAND.md)

### 方法 2：使用 @userinfobot

1. 在 Telegram 中搜索 `@userinfobot`
2. 将 bot 添加到你的频道
3. 在频道发送任何消息
4. Bot 会回复包含 Chat ID 的信息

### 方法 3：使用 Telegram API

访问以下 URL（替换 `YOUR_BOT_TOKEN`）：

```
https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
```

在返回的 JSON 中查找 `"chat":{"id":-1001234567890}`

---

## 从旧配置迁移到 YAML

如果你已经在使用 `channels.txt` 和 `.env`：

### 步骤 1：复制示例配置

```bash
copy config.yaml.example config.yaml
```

### 步骤 2：从 .env 迁移

将 `.env` 中的内容：

```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHAT_ID=-1001234567890
```

迁移到 `config.yaml`：

```yaml
telegram:
  bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

channel_groups:
  - name: "主频道"
    telegram_chat_id: "-1001234567890"
    audio_folder: "au"
    youtube_channels: []  # 先留空
```

### 步骤 3：从 channels.txt 迁移

将 `channels.txt` 中的频道复制到 `config.yaml` 的 `youtube_channels` 列表：

```yaml
    youtube_channels:
      - "@StorytellerFan"
      - "@meowsir"
      - "@wuyuesanren"
      # ... 所有频道
```

### 步骤 4：测试配置

运行程序，查看日志输出：

```bash
.\ch.ps1
```

如果看到 `✅ 使用 config.yaml 配置文件`，说明配置成功！

---

## 多频道组配置（将来支持）

**注意：当前版本（阶段1）只支持单个频道组。多组配置将在阶段2实现。**

将来的多组配置示例：

```yaml
channel_groups:
  # 技术类频道 → Telegram 技术频道
  - name: "技术频道"
    telegram_chat_id: "-1001111111111"
    audio_folder: "au/tech"
    youtube_channels:
      - "@JeffTechView"
      - "@Lifeano"
  
  # 时事类频道 → Telegram 时事频道
  - name: "时事评论"
    telegram_chat_id: "-1002222222222"
    audio_folder: "au/news"
    youtube_channels:
      - "@wenzhaoofficial"
      - "@cui_news"
```

---

## 故障排查

### 问题 1：程序提示 "未找到 BOT_TOKEN 配置"

**原因：** `config.yaml` 不存在且 `.env` 也没有配置

**解决：** 
- 创建 `config.yaml` 并配置 `telegram.bot_token`
- 或创建 `.env` 文件并设置 `BOT_TOKEN=你的token`

### 问题 2：程序显示 "未找到 config.yaml，使用传统配置方式"

**原因：** 这是正常提示，表示程序回退到使用 `channels.txt` + `.env`

**解决：** 如果想使用 YAML 配置，创建 `config.yaml` 文件即可

### 问题 3：YAML 解析错误

**原因：** YAML 语法错误（缩进、引号等）

**解决：**
- 检查缩进是否正确（使用空格，不要用 Tab）
- 检查字符串是否正确引用
- 使用在线 YAML 验证器检查语法

### 问题 4：从 config.yaml 加载了 0 个频道

**原因：** `youtube_channels` 列表为空或格式错误

**解决：**
- 检查 `youtube_channels` 是否正确配置
- 确保每个频道名前有 `-` 和空格
- 示例：
  ```yaml
  youtube_channels:
    - "@频道名1"  # 正确
    - "@频道名2"  # 正确
  ```

---

## 高级技巧

### 1. 分离配置和密钥

可以将敏感信息（Token、Chat ID）单独存放：

**config.yaml**（提交到 Git）：
```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN_HERE"  # 占位符
  send_interval: 4920

channel_groups:
  - name: "主频道"
    telegram_chat_id: "YOUR_CHAT_ID_HERE"  # 占位符
    youtube_channels:
      - "@StorytellerFan"
      # ...
```

**.env**（不提交到 Git）：
```env
BOT_TOKEN=真实的token
CHAT_ID=真实的chat_id
```

程序会优先使用 `.env` 中的真实值（如果 YAML 中是占位符）。

### 2. 环境特定配置

可以为不同环境准备不同的配置文件：

- `config.yaml` - 生产环境
- `config.dev.yaml` - 开发环境
- `config.test.yaml` - 测试环境

然后在代码中根据环境变量选择配置文件。

---

## 配置文件优先级

配置读取优先级（从高到低）：

1. `config.yaml` 中的配置
2. `.env` 中的环境变量（对于 Token 和 Chat ID）
3. 默认值

例如：
- 如果 `config.yaml` 存在且配置了 `bot_token`，使用 YAML 中的值
- 如果 `config.yaml` 中的 `bot_token` 是占位符，回退到 `.env` 中的 `BOT_TOKEN`
- 如果都没有，程序会报错并退出

---

## 相关文档

- [快速参考](QUICK_REFERENCE.md)
- [日志系统](LOG_EXAMPLES.md)
- [主文档](README.md)

---

## 更新日志

### 2025-10-09
- ✅ 添加 YAML 配置支持
- ✅ 保持向后兼容 channels.txt + .env
- ✅ 添加配置验证和错误提示
- 🔜 将来支持多频道组配置

