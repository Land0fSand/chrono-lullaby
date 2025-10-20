# ChronoLullaby 日志埋点详细文档

本文档详细记录了 ChronoLullaby 项目中所有日志埋点的详细信息，包括埋点内容、触发时机、格式、类型和等级等信息。

## 日志系统概述

项目使用统一的日志系统，具有以下特点：
- **输出格式**：控制台（人类可读）和 JSONL 文件格式
- **日志级别**：DEBUG、INFO、WARNING、ERROR、CRITICAL
- **轮转机制**：每个组件日志文件最大 10MB，保留 5 个备份
- **组件命名**：`chronolullaby.{component}`

## 日志埋点详细列表

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

## 上下文日志使用

项目中大量使用了 `log_with_context()` 函数来记录带上下文信息的日志，格式为：
```python
log_with_context(logger, logging.INFO, "下载完成", channel="@example", file_name="video.mp4", size_mb=15.5)
```

这会在日志消息后追加上下文信息，如："下载完成 | channel=@example, file_name=video.mp4, size_mb=15.5"
