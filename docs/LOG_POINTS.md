# ChronoLullaby 日志埋点详细文档

本文档详细记录了 ChronoLullaby 项目中所有日志埋点的详细信息，包括埋点内容、触发时机、格式、类型和等级等信息。

## 日志系统概述

项目使用统一的日志系统，具有以下特点：
- **输出格式**：控制台（人类可读）和 JSONL 文件格式
- **日志级别**：DEBUG、INFO、WARNING、ERROR、CRITICAL
- **轮转机制**：每个组件日志文件最大 10MB，保留 5 个备份
- **组件命名**：`chronolullaby.{component}`

### 日志分类

ChronoLullaby 的日志系统分为两大类：

1. **组件日志**：记录各个业务组件的运行日志
   - `bot.log` - Telegram 机器人日志
   - `downloader.log` - 下载器主日志
   - `bot.send_file.log` - 文件发送详细日志
   - `downloader.dl_audio.log` - 音频下载详细日志
   - `downloader.yt-dlp.log` - yt-dlp 输出日志
   - 部分日志会同步到 Notion（如果配置了 Notion 模式）

2. **系统日志**：记录系统级事件和调试信息（**本文档新增**）
   - `system.log` - 系统级事件日志
   - 完全本地存储，不同步到 Notion
   - 专注于进程管理、配置加载、服务启动等系统事件
   - 详细说明请参见 [SYSTEM_LOG.md](SYSTEM_LOG.md)

## 日志埋点详细列表

### 0. 系统日志 (system.log)

系统日志是一个独立的日志子系统，专门记录系统级事件。详细文档请参见 [SYSTEM_LOG.md](SYSTEM_LOG.md)。

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "ChronoLullaby 启动器开始初始化" | 启动器 main 函数开始时 | INFO | chronolullaby.system | src/launcher.py:242 |
| "配置模式被环境变量覆盖" | 使用环境变量覆盖配置模式时 | INFO | chronolullaby.system | src/launcher.py:248-253 |
| "配置提供者初始化成功" | 配置提供者初始化成功时 | INFO | chronolullaby.system | src/launcher.py:257 |
| "配置提供者初始化失败" | 配置提供者初始化失败时 | ERROR | chronolullaby.system | src/launcher.py:261-266 |
| "当前配置提供者" | 确定配置提供者类型后 | INFO | chronolullaby.system | src/launcher.py:271-275 |
| "启动 Notion 同步服务" | 准备启动 Notion 同步服务时 | DEBUG | chronolullaby.system | src/launcher.py:287 |
| "Notion 同步服务启动成功" | Notion 同步服务成功启动时 | INFO | chronolullaby.system | src/launcher.py:290 |
| "Notion 同步服务启动失败" | Notion 同步服务启动失败时 | WARNING | chronolullaby.system | src/launcher.py:293-297 |
| "启动器初始化" | ProcessManager.start() 开始时 | INFO | chronolullaby.system | src/launcher.py:122 |
| "信号处理器已注册" | 注册 SIGINT/SIGTERM 处理器后 | DEBUG | chronolullaby.system | src/launcher.py:127 |
| "下载器进程已启动" | 下载器进程启动后 | INFO | chronolullaby.system | src/launcher.py:141-146 |
| "机器人进程已启动" | 机器人进程启动后 | INFO | chronolullaby.system | src/launcher.py:162-167 |
| "进程信息已保存" | 进程信息写入文件后 | DEBUG | chronolullaby.system | src/launcher.py:183-189 |
| "所有服务已启动，进入监控循环" | 服务启动完成，开始监控时 | INFO | chronolullaby.system | src/launcher.py:191 |
| "下载器进程意外退出" | 监测到下载器进程退出时 | WARNING | chronolullaby.system | src/launcher.py:200-206 |
| "机器人进程意外退出" | 监测到机器人进程退出时 | WARNING | chronolullaby.system | src/launcher.py:211-217 |
| "接收到 KeyboardInterrupt" | 接收到键盘中断时 | INFO | chronolullaby.system | src/launcher.py:222 |
| "启动器异常" | 启动过程发生异常时 | ERROR | chronolullaby.system | src/launcher.py:229-234 |
| "接收到系统信号" | 信号处理器被调用时 | INFO | chronolullaby.system | src/launcher.py:74-80 |
| "开始停止所有子进程" | 开始停止进程时 | INFO | chronolullaby.system | src/launcher.py:87 |
| "终止下载器进程" | 终止下载器进程时 | INFO | chronolullaby.system | src/launcher.py:91-95 |
| "下载器进程未响应 terminate，使用 kill" | 下载器进程需要强制 kill 时 | WARNING | chronolullaby.system | src/launcher.py:99 |
| "终止机器人进程" | 终止机器人进程时 | INFO | chronolullaby.system | src/launcher.py:104-108 |
| "机器人进程未响应 terminate，使用 kill" | 机器人进程需要强制 kill 时 | WARNING | chronolullaby.system | src/launcher.py:112 |
| "所有子进程已停止" | 所有进程停止完成时 | INFO | chronolullaby.system | src/launcher.py:116 |

**配置模块系统日志** (config.py):

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "开始初始化配置提供者" | init_config_provider 开始时 | DEBUG | chronolullaby.system | src/config.py:62 |
| "配置文件不存在，使用本地配置提供者" | 配置文件不存在时 | INFO | chronolullaby.system | src/config.py:71 |
| "确定配置模式" | 确定配置模式后 | INFO | chronolullaby.system | src/config.py:81-87 |
| "Notion API Key 未配置，降级到本地模式" | Notion API Key 验证失败时 | WARNING | chronolullaby.system | src/config.py:103 |
| "Notion 配置提供者初始化成功" | Notion 配置提供者创建成功时 | INFO | chronolullaby.system | src/config.py:115-119 |
| "Notion 配置提供者初始化失败，降级到本地模式" | Notion 初始化异常时 | ERROR | chronolullaby.system | src/config.py:127-132 |
| "本地配置提供者初始化成功" | 本地配置提供者创建成功时 | INFO | chronolullaby.system | src/config.py:141 |
| "配置文件不存在" | load_yaml_config 检测到文件不存在 | DEBUG | chronolullaby.system | src/config.py:182-186 |
| "YAML 配置已重新加载" | reload=True 时重新加载配置 | DEBUG | chronolullaby.system | src/config.py:193 |
| "加载 YAML 配置失败" | YAML 解析失败时 | ERROR | chronolullaby.system | src/config.py:201-206 |

**Notion 同步服务系统日志** (notion_sync.py):

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "尝试启动已运行的 Notion 同步服务" | 重复调用 start() 时 | WARNING | chronolullaby.system | src/notion_sync.py:71 |
| "Notion 同步服务已启动" | 同步服务启动后 | INFO | chronolullaby.system | src/notion_sync.py:96-103 |
| "开始停止 Notion 同步服务" | 调用 stop() 时 | INFO | chronolullaby.system | src/notion_sync.py:115 |
| "Notion 同步服务已停止" | 同步服务完全停止后 | INFO | chronolullaby.system | src/notion_sync.py:123 |
| "Logs 数据库 ID 未配置，无法上传日志到 Notion" | 数据库 ID 缺失时 | WARNING | chronolullaby.system | src/notion_sync.py:196 |
| "Notion 日志批量上传完成" | 批量上传日志完成后 | DEBUG | chronolullaby.system | src/notion_sync.py:229-235 |
| "尝试重复初始化 Notion 同步服务" | 重复调用 init_sync_service() 时 | WARNING | chronolullaby.system | src/notion_sync.py:261 |
| "初始化 Notion 同步服务" | 开始初始化同步服务时 | DEBUG | chronolullaby.system | src/notion_sync.py:267-271 |
| "请求停止 Notion 同步服务" | 调用 stop_sync_service() 时 | INFO | chronolullaby.system | src/notion_sync.py:286 |

### 1. 启动器 (launcher.py)

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "启动 YouTube 下载器..." | 下载器进程启动时 | INFO | chronolullaby.launcher | src/launcher.py:38 |
| "启动 Telegram 机器人..." | Telegram机器人进程启动时 | INFO | chronolullaby.launcher | src/launcher.py:55 |
| "接收到停止信号，正在关闭所有进程..." | 接收到停止信号时 | INFO | chronolullaby.launcher | src/launcher.py:71 |
| "停止 YouTube 下载器..." | 停止下载器进程时 | INFO | chronolullaby.launcher | src/launcher.py:80 |
| "停止 Telegram 机器人..." | 停止Telegram机器人进程时 | INFO | chronolullaby.launcher | src/launcher.py:87 |
| "所有进程已停止" | 所有进程停止完成时 | INFO | chronolullaby.launcher | src/launcher.py:93 |
| "=== ChronoLullaby 启动器 ===" | 启动器开始运行时 | INFO | chronolullaby.launcher | src/launcher.py:97 |
| "按 Ctrl+C 停止所有服务" | 显示操作提示时 | INFO | chronolullaby.launcher | src/launcher.py:98 |
| "进程信息已保存到 data/process_info.json" | 进程信息保存成功时 | INFO | chronolullaby.launcher | src/launcher.py:145 |
| "服务正在运行..." | 服务运行状态提示时 | INFO | chronolullaby.launcher | src/launcher.py:146 |
| "YouTube 下载器进程意外退出" | 监控到下载器进程退出时 | WARNING | chronolullaby.launcher | src/launcher.py:154 |
| "Telegram 机器人进程意外退出" | 监控到机器人进程退出时 | WARNING | chronolullaby.launcher | src/launcher.py:158 |
| "接收到中断信号..." | 接收到中断信号时 | INFO | chronolullaby.launcher | src/launcher.py:162 |
| "使用命令行指定的配置模式: {mode_override}" | 使用命令行指定配置模式时 | INFO | chronolullaby.launcher | src/launcher.py:179 |
| "初始化配置提供者失败: {e}" | 配置初始化失败时 | ERROR | chronolullaby.launcher | src/launcher.py:184 |
| "将使用默认本地配置模式" | 使用默认配置模式时 | WARNING | chronolullaby.launcher | src/launcher.py:185 |
| "Notion 同步服务已启动" | Notion同步服务启动成功时 | INFO | chronolullaby.launcher | src/launcher.py:200 |
| "启动 Notion 同步服务失败: {e}" | Notion同步服务启动失败时 | WARNING | chronolullaby.launcher | src/launcher.py:202 |

### 2. Telegram机器人 (telegram_bot.py)

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "❌ 未找到 BOT_TOKEN 配置！" | 启动时未找到Token配置 | ERROR | chronolullaby.bot | src/telegram_bot.py:42 |
| "请在 config.yaml 或 .env 文件中配置 BOT_TOKEN" | 启动时未找到Token配置 | ERROR | chronolullaby.bot | src/telegram_bot.py:43 |
| "❌ 未找到 CHAT_ID 配置！" | 启动时未找到ChatID配置 | ERROR | chronolullaby.bot | src/telegram_bot.py:47 |
| "请在 config.yaml 或 .env 文件中配置 CHAT_ID" | 启动时未找到ChatID配置 | ERROR | chronolullaby.bot | src/telegram_bot.py:48 |
| "配置加载成功：发送间隔 = {SEND_INTERVAL} 秒 ({SEND_INTERVAL/3600:.2f} 小时)" | 启动时配置加载成功 | INFO | chronolullaby.bot | src/telegram_bot.py:51 |
| "执行发送任务 - 频道组: {group_name}" | 执行发送任务时 | INFO | chronolullaby.bot | src/telegram_bot.py:67 |
| "发送文件任务错误 (频道组: {group_name}): {e}" | 发送任务出错时 | ERROR | chronolullaby.bot | src/telegram_bot.py:70 |
| "发送文件任务错误: {e}" | 发送任务出错时 | ERROR | chronolullaby.bot | src/telegram_bot.py:79 |
| "🧪 /test 命令 - Chat ID: {chat_id}, 类型: {chat_type}, 标题: {chat_title}" | /test命令执行时 | INFO | chronolullaby.bot | src/telegram_bot.py:100 |
| "❌ /test 命令执行失败: {e}" | /test命令执行失败时 | ERROR | chronolullaby.bot | src/telegram_bot.py:102 |

### 3. 文件发送任务 (task/send_file.py)

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "视频 {video_id} 已在发送记录中" | 检查视频是否已在发送记录时 | DEBUG | chronolullaby.bot.send_file | src/task/send_file.py:80 |
| 各种文件处理和发送的上下文日志 | 文件处理过程中 | INFO/DEBUG/WARNING/ERROR | chronolullaby.bot.send_file | src/task/send_file.py:88-412 |

### 4. 音频下载任务 (task/dl_audio.py)

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "⏭️ 跳过私人视频: {video_id}" | 跳过私人视频时 | INFO | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:151 |
| "会员过滤器错误: {e}" | 会员过滤器处理出错时 | WARNING | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:159 |
| "过滤器跳过: {info_dict.get('title', '未知标题')} - {member_result}" | 会员过滤器跳过视频时 | DEBUG | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:169 |
| "过滤器跳过: {info_dict.get('title', '未知标题')} - {time_result}" | 时间过滤器跳过视频时 | DEBUG | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:175 |
| "组合过滤器错误: {e}" | 组合过滤器处理出错时 | WARNING | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:180 |
| "过滤器错误: {str(e)}" | 过滤器处理出错时 | WARNING | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:216 |
| "未找到cookies文件！" | 未找到cookies文件时 | ERROR | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:223 |
| "请按以下步骤操作：" (cookies配置步骤) | 未找到cookies文件时 | INFO | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:224-230 |
| "已创建音频目录: {AUDIO_FOLDER}" | 创建音频目录成功时 | INFO | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:239 |
| "下载进度: {percent:.1f}% - {speed_mb:.1f}MB/s" | 下载过程中 | DEBUG | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:291 |
| "下载进度: {percent:.1f}%" | 下载过程中 | DEBUG | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:293 |
| "下载完成: {os.path.basename(d.get('filename', ''))}" | 下载完成时 | DEBUG | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:297 |
| "已存在: {d.get('title', '')}" | 文件已存在时 | DEBUG | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:299 |
| "已创建音频目录: {target_folder}" | 创建目标音频目录时 | INFO | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:340 |
| "频道 {channel_name} 包含直播预告视频，稍后自动下载" | 发现直播预告视频时 | INFO | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:710 |
| "频道 {channel_name} 包含待首映视频，稍后自动下载" | 发现待首映视频时 | INFO | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:715 |
| "频道 {channel_name} 不存在或无法访问，请检查频道名称是否正确。" | 频道不存在或无法访问时 | ERROR | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:740 |
| "Cookies可能已过期或需要同意YouTube政策！" | Cookies过期或需要同意政策时 | ERROR | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:742 |
| "请按以下步骤更新cookies：" (cookies更新步骤) | Cookies过期时 | INFO | chronolullaby.downloader.dl_audio | src/task/dl_audio.py:743-747 |

### 5. YouTube下载器主程序 (yt_dlp_downloader.py)

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "下载间隔配置：{DOWNLOAD_INTERVAL} 秒 ({DOWNLOAD_INTERVAL/3600:.2f} 小时)" | 启动时显示配置信息 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:28 |
| "开始批量下载，共 {len(channel_groups)} 个频道组，{total_channels} 个YouTube频道" | 开始批量下载时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:94 |
| "频道间延迟：{delay_min}-{delay_max}秒（随机）" | 显示延迟配置时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:95 |
| "频道组配置" (带上下文信息) | 显示频道组配置时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:100-107 |
| "已优化下载顺序：多个频道组交替进行，确保及时性" | 显示下载顺序优化信息时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:112 |
| "⏳ 频道间延迟 - 准备处理频道 [{idx}/{total_channels}]" (带上下文) | 频道间延迟时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:124-132 |
| "处理频道 [{idx}/{total_channels}]" (带上下文) | 处理频道时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:134-140 |
| "下载频道失败" (带上下文) | 下载频道失败时 | ERROR | chronolullaby.downloader | src/yt_dlp_downloader.py:149-158 |
| "本轮下载任务完成" | 本轮下载任务完成时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:160 |
| "开始批量下载，共 {len(channels)} 个频道" | 开始批量下载（旧接口）时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:164 |
| "处理频道 [{idx}/{len(channels)}]" (带上下文) | 处理频道（旧接口）时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:169-176 |
| "下载频道失败" (带上下文，旧接口) | 下载频道失败（旧接口）时 | ERROR | chronolullaby.downloader | src/yt_dlp_downloader.py:181-188 |
| "YouTube 下载器启动" | 下载器启动时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:194 |
| "未找到任何频道组配置" | 未找到频道组配置时 | WARNING | chronolullaby.downloader | src/yt_dlp_downloader.py:202 |
| "刷新频道组列表" (带上下文) | 刷新频道组列表时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:208-214 |
| "等待下一轮下载" (带上下文) | 等待下一轮下载时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:221-227 |
| "轮次间隔为0，立即开始下一轮（视频级延迟已足够拉开频率）" | 轮次间隔为0时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:230 |
| "接收到停止信号，正在退出..." | 接收到停止信号时 | INFO | chronolullaby.downloader | src/yt_dlp_downloader.py:234 |
| "下载器主循环发生未预期的错误" | 主循环发生错误时 | EXCEPTION | chronolullaby.downloader | src/yt_dlp_downloader.py:237 |

### 6. 工具函数 (util.py)

| 埋点内容 | 触发时机 | 日志级别 | 组件名称 | 文件位置 |
|---------|---------|---------|---------|---------|
| "📍 /chatid 命令 - Chat ID: {chat_id}, 类型: {chat_type}, 标题: {chat_title}" | /chatid命令执行时 | INFO | chronolullaby.bot | src/util.py:78 |
| "❌ /chatid 命令执行失败: {e}" | /chatid命令执行失败时 | ERROR | chronolullaby.bot | src/util.py:94 |

## 日志格式说明

### 文件日志格式 (JSONL)
```json
{
  "timestamp": "2025-01-20T10:30:45.123456",
  "level": "INFO",
  "component": "chronolullaby.bot",
  "message": "配置加载成功：发送间隔 = 300 秒 (0.08 小时)",
  "process": 12345,
  "thread": 140234567890,
  "file": "src/telegram_bot.py",
  "line": 51,
  "function": "<module>"
}
```

### 控制台日志格式
```
2025-01-20 10:30:45 | INFO     | bot         | 配置加载成功：发送间隔 = 300 秒 (0.08 小时)
```

## 日志级别说明

- **DEBUG**: 详细的调试信息，通常用于开发和故障排查
- **INFO**: 一般信息，记录程序的正常运行状态
- **WARNING**: 警告信息，表示可能的问题但不影响程序继续运行
- **ERROR**: 错误信息，表示发生了错误但程序仍能继续运行
- **CRITICAL**: 严重错误信息，表示程序无法继续运行

## 日志文件位置

- 所有日志文件保存在 `logs/` 目录下
- 各组件日志文件命名：`{component}.log`
- 错误日志文件：`{component}_error.log`（仅记录 ERROR 及以上级别）

## Notion集成

部分日志（downloader 和 bot 组件）会自动同步到 Notion 的日志数据库中，格式为：
- 日志类型：根据组件确定（downloader/bot 组件为对应类型，其他为 error）
- 日志级别：转换为大写格式（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 消息内容：原始日志消息，带上下文信息时会合并显示

**重要说明**：系统日志（`system.log`）**不会**同步到 Notion，它是完全本地化的日志，用于系统调试和故障诊断。即使 Notion 服务不可用，系统日志也能正常工作。

## 上下文日志使用

项目中大量使用了 `log_with_context()` 函数来记录带上下文信息的日志，格式为：
```python
log_with_context(logger, logging.INFO, "下载完成", channel="@example", file_name="video.mp4", size_mb=15.5)
```

这会在日志消息后追加上下文信息，如："下载完成 | channel=@example, file_name=video.mp4, size_mb=15.5"

## 系统日志使用指南

系统日志是项目中一个独立的日志子系统，专门用于记录系统级事件和调试信息。

### 使用场景

- **进程管理**：启动、停止、监控子进程
- **配置管理**：配置加载、模式切换、配置错误
- **服务管理**：Notion 同步服务、后台任务
- **故障诊断**：系统异常、错误降级
- **临时调试**：需要调试时添加的临时日志

### 快速使用

```python
from logger import get_system_logger, log_with_context
import logging

# 获取系统 logger
sys_logger = get_system_logger()

# 记录简单消息
sys_logger.info("服务已启动")
sys_logger.debug("调试信息")

# 记录带上下文的消息
log_with_context(
    sys_logger, logging.INFO,
    "配置加载成功",
    mode="notion",
    provider="NotionConfigProvider"
)
```

### 与组件日志的区别

| 特性 | 组件日志 | 系统日志 |
|------|----------|----------|
| **文件** | bot.log, downloader.log 等 | system.log |
| **内容** | 业务逻辑、下载/发送详情 | 系统事件、进程管理 |
| **Notion 同步** | 部分同步 | 完全不同步 |
| **用途** | 业务监控 | 系统调试 |

### 详细文档

完整的系统日志使用说明、最佳实践和故障排查，请参见：
- [SYSTEM_LOG.md](SYSTEM_LOG.md) - 系统日志完整文档
