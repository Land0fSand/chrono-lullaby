# ChronoLullaby

> 自动下载 YouTube 频道音频并推送到 Telegram 的工具

**ChronoLullaby** 能够定时从指定的 YouTube 频道下载最新音频，并自动推送到 Telegram 群组/频道。适合需要自动化音频内容分发的场景。

---

## 核心功能

- 🎵 **自动下载** - 定时抓取 YouTube 频道最新音频（AAC 格式）
- 📤 **自动推送** - 将音频推送到 Telegram 频道，支持大文件自动分割
- 🔄 **去重机制** - 避免重复下载，自动跳过已处理的内容
- 📊 **日志系统** - JSONL 格式日志，便于查询和分析
- ⚙️ **简单管理** - 统一的 `ch` 命令管理所有功能

---

## 快速开始

### 1. 安装依赖

```powershell
# 使用 Poetry（推荐）
poetry install

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置

复制配置示例：
```powershell
copy config\config.yaml.example config\config.yaml
```

编辑 `config/config.yaml`：
```yaml
telegram:
  bot_token: "你的BOT_TOKEN"  # 从 @BotFather 获取

channel_groups:
  - name: "主频道"
    telegram_chat_id: "你的CHAT_ID"  # 使用 /chatid 命令获取
    youtube_channels:
      - "@频道1"
      - "@频道2"
```

**获取 Chat ID：**
1. 启动 Bot：`.\ch start`
2. 将 Bot 添加到目标频道
3. 在频道中发送 `/chatid`
4. 复制 Bot 回复的 Chat ID

### 3. 启动服务

```powershell
.\ch start
```

---

## 常用命令

```powershell
.\ch start      # 启动服务（后台运行）
.\ch stop       # 停止服务
.\ch status     # 查看运行状态
.\ch logs       # 查看日志
.\ch logs -f    # 实时日志
.\ch cleanup    # 强制清理进程
```

---

## 项目结构

```
chronolullaby/
├── ch.ps1                      # 主命令脚本
├── config/
│   ├── config.yaml             # 配置文件
│   └── youtube.cookies         # YouTube Cookies（可选）
├── src/
│   ├── launcher.py             # 启动入口
│   ├── yt_dlp_downloader.py    # 下载器
│   ├── telegram_bot.py         # Bot主程序
│   ├── logger.py               # 日志系统
│   └── task/
│       ├── dl_audio.py         # 下载逻辑
│       └── send_file.py        # 发送逻辑
├── logs/                       # 日志目录
├── data/                       # 数据存储（归档记录等）
├── au/                         # 音频临时目录
└── docs/                       # 详细文档
    ├── README.md               # 使用文档
    ├── CONFIG_GUIDE.md         # 配置指南
    └── CHATID_COMMAND.md       # /chatid 命令说明
```

---

## 下载规则

- 每个频道检查最近 **6 个视频**
- 只下载最近 **3 天**内的视频
- 自动跳过：已下载、会员专属、已归档的内容
- 下载间隔：约 **8 小时**一次

---

## 日志查询

### 使用 ch 命令

```powershell
.\ch logs                    # 查看所有日志
.\ch logs downloader         # 下载器日志
.\ch logs bot                # Bot日志
.\ch logs error              # 错误日志
.\ch logs -f                 # 实时跟踪
```

### 使用 PowerShell

```powershell
# 查找特定频道
Get-Content logs/downloader.log | Select-String "@频道名"

# 最后50行
Get-Content logs/downloader.log -Tail 50

# 实时跟踪
Get-Content logs/downloader.log -Tail 10 -Wait
```

### 使用 jq 分析

```bash
# 安装 jq: winget install jqlang.jq

# 只看错误
jq 'select(.level=="ERROR")' logs/downloader.log

# 查看特定频道
jq 'select(.channel=="@频道名")' logs/downloader.log
```

---

## 故障排查

```powershell
# 查看错误日志
.\ch logs error

# 检查运行状态
.\ch status

# 完全重启
.\ch stop
.\ch start

# 强制清理所有进程（会终止所有Python进程）
.\ch cleanup
```

---

## 详细文档

- **[使用文档](docs/README.md)** - 完整的使用说明、日志系统、故障排查
- **[配置指南](docs/CONFIG_GUIDE.md)** - 详细的配置说明和参数解释
- **[/chatid 命令](docs/CHATID_COMMAND.md)** - 获取 Telegram Chat ID 的方法

---

## 技术栈

- Python 3.9+ / Poetry
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube 下载
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot 框架
- ffmpeg - 音频处理
- PowerShell 7+ - 管理脚本

---

## 许可证

本项目基于 [GNU 通用公共许可证（GPL）](LICENSE) 开源。

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**Enjoy automating your audio content distribution! 🎵**
