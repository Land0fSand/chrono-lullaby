# ChronoLullaby

> 自动下载 YouTube 频道音频并推送到 Telegram 的工具

**ChronoLullaby** 能够定时从指定的 YouTube 频道下载最新音频，并自动推送到 Telegram 群组/频道。支持多频道组管理、大文件自动分割、Notion 远程配置等功能。

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

**Notion 模式（推荐）**：
```powershell
copy config\config.notion.example.yaml config\config.yaml
```
填写 Notion Integration API Key 与父页面 Page ID 后，运行 `ch init-notion` 初始化。

**本地模式**：
```powershell
copy config\config.local.example.yaml config\config.yaml
```
按需调整 telegram / downloader / 频道组配置即可。

### 3. 启动服务

```powershell
.\ch start
```

---

## 命令参考

### 基本命令

```powershell
.\ch start                   # 启动服务（后台运行）
.\ch start --mode notion     # 使用 Notion 模式启动
.\ch stop                    # 停止服务
.\ch status                  # 查看运行状态
.\ch logs                    # 查看日志
.\ch logs -f                 # 实时日志
.\ch logs downloader         # 下载器日志
.\ch logs bot                # Bot 日志
.\ch logs error              # 错误日志
.\ch logs --lines 100        # 最近 100 行
.\ch cleanup                 # 强制清理进程
.\ch restart                 # 重启服务
```

### Notion 远程配置

```powershell
.\ch init-notion                            # 初始化 Notion 数据库结构
.\ch sync-to-notion                         # 手动同步本地数据到 Notion
.\ch sync-to-notion --data config           # 仅同步配置
.\ch migrate-multiselect                    # 迁移频道配置为多选格式（仅需一次）
.\ch clean-notion-logs --days 30            # 预览 30 天前的日志
.\ch clean-notion-logs --days 30 --confirm  # 确认清理 30 天前的日志
```

### 获取 Telegram Chat ID

1. 启动服务：`.\ch start`
2. 将 Bot 添加到目标频道（需要管理员权限）
3. 在频道中发送：`/chatid`
4. Bot 会回复包含 Chat ID 的消息

---

## 下载规则

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 检查视频数 | 6 个 | 每频道检查的最新视频数量 |
| 时间过滤 | 3 天 | 只下载最近 N 天内的视频 |
| 下载间隔 | ~8 小时 | 下载轮次间隔 |
| 发送间隔 | ~82 分钟 | 文件发送任务间隔 |

自动跳过：已下载、会员专属、已归档的内容。

---

## 项目结构

```
chronolullaby/
├── ch.ps1                      # 主命令脚本
├── config/
│   ├── config.yaml             # 配置文件
│   └── youtube.cookies         # YouTube Cookies（可选）
├── src/                        # 源代码
├── logs/                       # 日志目录
├── data/                       # 数据存储
├── au/                         # 音频临时目录
└── docs/                       # 详细文档
```

---

## 详细文档

| 文档 | 说明 |
|------|------|
| [配置指南](docs/CONFIG_GUIDE.md) | 完整配置说明和参数解释 |
| [Notion 设置](docs/NOTION_SETUP.md) | Notion 模式配置和使用 |
| [Notion 日志清理](docs/NOTION_LOG_CLEANUP.md) | 日志清理和自动化方案 |
| [Cookie 更新](docs/COOKIE_UPDATE_GUIDE.md) | YouTube Cookies 更新方法 |
| [/chatid 命令](docs/CHATID_COMMAND.md) | 获取 Telegram Chat ID |
| [多选频道管理](docs/YOUTUBE_CHANNELS_MULTISELECT.md) | 多选格式迁移说明 |

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

# 强制清理所有进程
.\ch cleanup
```

### Cookie 过期（403 错误）

```powershell
# 使用 yt-dlp 从浏览器提取
yt-dlp --cookies-from-browser chrome --cookies config/youtube.cookies https://www.youtube.com

# 重启服务
.\ch restart
```

详见：[Cookie 更新指南](docs/COOKIE_UPDATE_GUIDE.md)

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
