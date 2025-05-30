# ChronoLullaby

ChronoLullaby 是一个自动化服务，能够定时从指定的 YouTube 频道下载最新音频，并将其推送到 Telegram 群组。适合需要自动化音频内容分发的社群或频道运营者。

---

## 功能详解

### 1. YouTube 频道音频订阅与下载

- 支持通过 `channels.txt` 文件维护订阅的 YouTube 频道列表。
- 自动定时抓取每个频道最新 1-3 条视频，筛选近一天内发布的视频，下载为 aac 格式音频。
- 下载历史有去重机制，避免重复抓取。
- 支持按需下载指定时间点之后的最近视频。

### 2. Telegram 群组自动推送

- 定时将下载到的音频文件自动发送到指定的 Telegram 群组。
- 支持音频标题、作者信息自动填充。
- 发送成功后自动删除本地音频文件，节省存储空间。
- 针对 Telegram API 超时问题有容错处理，保证推送稳定。

### 3. 频道管理与交互

- 支持通过 Telegram 机器人命令 `/addchannel` 动态添加新的 YouTube 频道，无需手动编辑文件。
- 提供辅助命令获取 chat_id，便于配置目标群组。

---

## 目录结构说明

- `src/main.py`：主程序入口，负责调度定时任务与命令处理。
- `src/task/dl_audio.py`：核心音频下载逻辑，支持最新与指定时间点音频抓取。
- `src/task/send_file.py`：音频文件推送到 Telegram 群组的实现。
- `src/commands/add_channel.py`：实现 `/addchannel` 命令，动态添加频道。
- `src/util.py`：辅助工具函数，如频道列表刷新、chat_id 获取等。
- `src/config.py`：全局路径与配置项定义。

---

## 快速开始

### 1. 环境准备

- 克隆本仓库
- 安装依赖（推荐 Python 3.8+）：
  ```bash
  pip install -r requirements.txt
  ```
- 在项目根目录创建 `.env` 文件，内容示例：
  ```
  BOT_TOKEN=你的TelegramBotToken
  CHAT_ID=目标群组的chat_id
  ```

### 2. 配置频道

- 在 `channels.txt` 文件中，每行填写一个 YouTube 频道名（如 `@channelname` 或频道 ID）。
- 或在 Telegram 群组中对机器人发送 `/addchannel 频道名` 动态添加。

### 3. 启动服务

```bash
python src/main.py
```

---

## 进阶说明

- **音频存储目录**：所有下载的音频默认保存在 `au/` 文件夹，发送后自动清理。
- **定时任务**：下载与推送任务均为定时执行，间隔可在 `main.py` 中调整。
- **日志与调试**：下载过程中的调试信息会写入 `debug_closest_video.json`，便于排查问题。
- **历史记录**：`download_archive.txt` 用于记录已下载视频，`story.txt` 记录频道与时间戳。

---

## 常见问题

- **如何获取 chat_id？**  
  可在 `util.py` 中启用 `show_chat_id`，让机器人监听消息并打印 chat_id。
- **推送超时怎么办？**  
  已内置超时容错，绝大多数情况下不会影响音频推送。

---

## 许可证

本项目基于 GNU 通用公共许可证（GPL）开源。详情请参阅 [LICENSE](LICENSE) 文件。

---

如需进一步定制或有其他问题，欢迎提交 issue 或联系作者。
