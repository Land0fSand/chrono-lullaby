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
- 提供 `/chatid` 命令直接获取频道 chat_id，便于配置目标群组（无需停止主进程）。

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
  在任何频道（包括私有频道）中向机器人发送 `/chatid` 命令，即可获得该频道的 Chat ID，无需停止主进程。详见 [/chatid 命令使用说明](docs/CHATID_COMMAND.md)。
- **推送超时怎么办？**  
  已内置超时容错，绝大多数情况下不会影响音频推送。

---

## 许可证

本项目基于 GNU 通用公共许可证（GPL）开源。详情请参阅 [LICENSE](LICENSE) 文件。

---

## 🚀 快速启动（推荐）

### 统一命令管理（推荐）

项目提供了统一的 `ch` 命令，支持所有管理功能：

```powershell
# 启动服务（后台运行）
.\ch start

# 查看状态
.\ch status

# 查看日志
.\ch logs

# 查看下载器日志（实时）
.\ch logs downloader --follow

# 查看错误日志
.\ch logs error

# 列出所有日志文件
.\ch logs --list

# 停止服务
.\ch stop

# 强制清理所有进程
.\ch cleanup

# 显示帮助信息
.\ch help
```

### 全局命令（安装后可在任意位置使用）

**自动安装（推荐）：**

```powershell
# 永久添加到系统 PATH
.\ch add-chtopath
```

**手动安装：**
将 `ch.ps1` 复制到 PATH 目录，或将项目目录添加到环境变量：

```powershell
# 在任何位置运行
ch start        # 启动服务
ch status       # 查看状态
ch logs         # 查看日志
ch stop         # 停止服务
ch cleanup      # 强制清理
ch help         # 帮助信息
```

**临时使用（仅当前会话）：**

```powershell
# 临时添加到 PATH（仅当前 PowerShell 会话有效）
$env:PATH = "项目目录;$env:PATH"
```

### 传统启动方式

```bash
# 使用 Poetry（推荐）
poetry install
cd src
poetry run python launcher.py

# 或直接使用 Python
python src/main.py
```

### 调试模式

```powershell
# 交互式启动（调试用）
.\start-simple.ps1
```

---

## 📋 命令参数说明

### ch logs 命令参数

```powershell
# 查看所有日志（最近50行）
ch logs

# 查看特定类型日志
ch logs downloader          # 查看下载器日志
ch logs bot                 # 查看机器人日志
ch logs error               # 查看错误日志

# 实时跟踪日志
ch logs downloader --follow # 实时查看下载器日志
ch logs bot -f              # 实时查看机器人日志（短参数）

# 列出所有日志文件
ch logs --list
ch logs -l

# 查看指定行数
ch logs --lines 100         # 查看最近100行
ch logs 200                 # 查看最近200行（直接数字）

# 组合使用
ch logs downloader --follow --lines 100
```

### 故障排除

```powershell
# 清理冲突进程（强制终止所有相关进程）
.\ch cleanup

# 传统清理方式（如果统一命令不可用）
.\ch-cleanup.ps1

# 手动停止所有进程
Get-Process *python* | Stop-Process -Force
```

### 其他命令

```powershell
# 查看帮助信息
ch help
ch --help

# 查看版本信息
ch version
ch --version

# 所有可用命令
ch start      # 启动服务
ch stop       # 停止服务
ch status     # 查看状态
ch logs       # 查看日志
ch cleanup    # 强制清理
```

---

如需进一步定制或有其他问题，欢迎提交 issue 或联系作者。
