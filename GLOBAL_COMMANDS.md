# ChronoLullaby 全局命令使用指南

## 🌟 安装全局命令

将以下文件复制到 PATH 环境变量中的任意目录（如 `C:\Windows\System32\`）：

- `ch.ps1` - 启动服务
- `ch-status.ps1` - 查看状态
- `ch-logs.ps1` - 查看日志
- `ch-stop.ps1` - 停止服务

## 📋 基本用法

### 1️⃣ 启动服务

```powershell
ch
```

- 自动检测项目目录
- 后台启动 YouTube 下载器和 Telegram 机器人
- 创建日志文件并保存进程信息

### 2️⃣ 查看状态

```powershell
ch-status
```

- 显示进程运行状态
- 显示运行时间、CPU 和内存使用
- 显示日志文件路径

### 3️⃣ 查看日志

```powershell
# 查看所有日志（最近50行）
ch-logs

# 实时跟踪下载器日志
ch-logs -Type downloader -Follow

# 查看错误日志
ch-logs -Type error

# 列出所有日志文件
ch-logs -List
```

### 4️⃣ 停止服务

```powershell
ch-stop
```

- 优雅停止所有进程
- 清理进程信息文件

## ✨ 特点

- **自动路径检测**：无论在哪个目录运行都能找到项目
- **完整日志支持**：后台运行时也能看到所有输出
- **智能进程管理**：准确识别和管理相关进程
- **Poetry 环境支持**：自动使用正确的 Python 环境

## 🔧 故障排除

如果命令无法找到项目目录，请确保：

1. 脚本与项目在同一目录，或
2. 已经在项目目录内运行过 `ch` 命令

现在你可以在任何地方轻松管理 ChronoLullaby 服务！🎉
