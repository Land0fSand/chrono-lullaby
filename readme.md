# ChronoLullaby

> 自动下载 YouTube 频道音频并推送到 Telegram 的工具

**ChronoLullaby** 能够定时从指定的 YouTube 频道下载最新音频，并自动推送到 Telegram 群组/频道。适合需要自动化音频内容分发的场景。

---

## 核心功能

- 🎵 **自动下载** - 定时抓取 YouTube 频道最新音频（AAC 格式）
- 📤 **自动推送** - 将音频推送到 Telegram 频道，支持大文件自动分割
- 🔄 **去重机制** - 避免重复下载，自动跳过已处理的内容
- 📊 **日志系统** - JSONL 格式日志，便于查询和分析
- ☁️ **远程配置** - 支持 Notion 作为配置和数据存储，实现跨机器无缝切换
- 🧹 **自动清理** - Notion 日志自动清理，保持数据库性能
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

根据使用场景选择并复制模板为 `config/config.yaml`：

- **Notion 模式（推荐）**：
  ```powershell
  copy config\config.notion.example.yaml config\config.yaml
  ```
  填写 Notion Integration API Key 与父页面 Page ID 后，运行 `ch init-notion` 初始化。

- **本地模式（可选）**：
  ```powershell
  copy config\config.local.example.yaml config\config.yaml
  ```
  按需调整 telegram / downloader / 频道组配置，即可直接在本地运行。

**Notion 模式下获取频道 Chat ID：**
1. 在 Notion Config Database 中添加频道信息
2. （可选）运行 `ch sync-to-notion --data config` 让本地 YAML 与 Notion 保持一致
3. 将 Bot 加入目标频道后，在频道内发送 `/chatid`
4. 记录 Bot 回复的 Chat ID 并写入 Notion 配置

### 3. 启动服务

```powershell
.\ch start
```

---

## 常用命令

### 基本命令
```powershell
.\ch start              # 启动服务（后台运行）
.\ch start --mode notion # 使用 Notion 模式启动
.\ch stop               # 停止服务
.\ch status             # 查看运行状态
.\ch logs               # 查看日志
.\ch logs -f            # 实时日志
.\ch cleanup            # 强制清理进程
```

### Notion 远程配置
```powershell
.\ch init-notion              # 初始化 Notion 数据库结构
.\ch sync-to-notion           # 手动同步本地数据到 Notion
.\ch migrate-multiselect      # 迁移频道配置为多选格式（仅需一次）
.\ch clean-notion-logs --days 30 --confirm  # 清理 30 天前的日志
```

### Cookie 更新
```powershell
# 当遇到 403 错误时，更新 YouTube Cookies
# 使用 Cookie-Editor 扩展导出 Netscape 格式到 config/youtube.cookies
.\ch restart  # 重启服务生效
```

> 📘 **配置指南**: [docs/CONFIG_GUIDE.md](docs/CONFIG_GUIDE.md) | [Notion 设置](docs/NOTION_SETUP.md)  
> 🍪 **Cookie 更新**: [docs/COOKIE_UPDATE_GUIDE.md](docs/COOKIE_UPDATE_GUIDE.md)  
> 🧹 **日志清理**: [docs/NOTION_LOG_CLEANUP.md](docs/NOTION_LOG_CLEANUP.md)

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

### 基础文档
- **[使用文档](docs/README.md)** - 完整使用说明、日志系统、故障排查
- **[配置指南](docs/CONFIG_GUIDE.md)** - 详细配置说明和参数解释

### 功能指南
- **[Notion 设置](docs/NOTION_SETUP.md)** - Notion 模式配置和使用
- **[Notion 日志清理](docs/NOTION_LOG_CLEANUP.md)** - 日志清理和自动化方案
- **[多选频道管理](docs/YOUTUBE_CHANNELS_MULTISELECT.md)** - 多选格式迁移和使用
- **[Cookie 更新](docs/COOKIE_UPDATE_GUIDE.md)** - YouTube Cookies 更新方法
- **[/chatid 命令](docs/CHATID_COMMAND.md)** - 获取 Telegram Chat ID

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
