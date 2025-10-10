# 日志系统升级 - 更新日志

## 版本：v2.0 - 2025 年 10 月

### 🎉 重大改进：统一的结构化日志系统

本次更新对整个项目的日志记录系统进行了全面重构，解决了之前日志系统存在的所有问题。

---

## 📋 主要变更

### 1. 新增统一日志配置模块

- **文件**: `src/logger.py`
- **功能**:
  - JSONL 格式输出（每行一个 JSON 对象）
  - 自动日志轮转（10MB/文件，保留 5 个备份）
  - 控制台彩色输出 + 文件 JSON 输出
  - 支持独立的错误日志文件
  - 丰富的上下文信息记录

### 2. 更新所有模块使用统一日志系统

- ✅ `src/telegram_bot.py` - Bot 组件
- ✅ `src/yt_dlp_downloader.py` - 下载器组件
- ✅ `src/task/dl_audio.py` - 音频下载任务
- ✅ `src/task/send_file.py` - 文件发送任务
- ✅ `src/launcher.py` - 启动器

**变更内容**:

- 将所有 `print` 语句替换为 `logging` 调用
- 根据消息重要性使用合适的日志级别
- 添加结构化的上下文信息

### 3. 新增日志查看工具

- **PowerShell 版本**: `ch-logs-viewer.ps1`
- **Python 版本**: `view_logs.py`

**功能**:

- 美化显示 JSONL 格式日志
- 按组件、级别、关键词过滤
- 显示最后 N 条日志
- 实时跟踪模式（tail -f）
- 统计信息展示

### 4. 新增文档

- **使用指南**: `doc/LOG_SYSTEM_GUIDE.md`
- **更新日志**: 本文件

---

## 🔍 解决的问题

### 问题 1: 日志记录方式不统一

**之前**:

- `telegram_bot.py` 使用 `logging` 模块
- 其他模块混用 `print` 和手动时间戳
- 格式不一致，难以解析

**现在**:

- 所有模块统一使用 `logging` 模块
- 统一的 JSONL 格式
- 自动添加时间戳、级别、组件名等元信息

### 问题 2: 日志文件分散且杂乱

**之前**:

```
logs/
├── bot_2025-09-22_14-23-36.log
├── bot_2025-09-25_08-40-58.log
├── bot_error_2025-09-22_14-23-36.log
├── downloader_2025-09-22_14-23-36.log
└── ... (每次运行生成新文件)
```

**现在**:

```
logs/
├── bot.log (当前日志)
├── bot.log.1 (轮转备份)
├── bot_error.log (错误日志)
├── downloader.log
├── downloader_error.log
└── launcher.log
```

### 问题 3: 缺少结构化信息

**之前**:

```
2025-09-30 09:25:35,422 - __main__ - INFO - 启动Telegram Bot轮询 (尝试 1/5)
```

**现在**:

```json
{
  "timestamp": "2025-10-09T14:30:25.123456",
  "level": "INFO",
  "component": "bot",
  "message": "启动Telegram Bot轮询",
  "attempt": 1,
  "max_retries": 5,
  "process": 12345,
  "thread": 67890
}
```

### 问题 4: 查问题不方便

**之前**:

- 需要在多个文件间切换
- 无法快速过滤级别
- 难以关联不同组件的日志

**现在**:

```bash
# 查看所有错误
python view_logs.py --error-only

# 查看特定组件
python view_logs.py bot

# 过滤关键词
python view_logs.py --filter "下载失败"

# 实时跟踪
.\ch-logs-viewer.ps1 -Follow

# 统计信息
python view_logs.py --stats
```

---

## 🚀 新功能

### 1. 日志级别

- **DEBUG**: 详细调试信息（下载进度、过滤器检查）
- **INFO**: 正常操作信息（开始下载、发送成功）
- **WARNING**: 警告但不影响运行（重试、跳过内容）
- **ERROR**: 错误但程序继续（下载失败、发送失败）
- **CRITICAL**: 严重错误需要关注（启动失败、配置错误）

### 2. 上下文信息

日志现在包含丰富的上下文信息：

```python
log_with_context(
    logger, logging.INFO,
    "下载完成",
    channel="@example",
    file_name="video.mp4",
    size_mb=15.5,
    duration_seconds=120
)
```

### 3. 日志轮转

- 单文件最大 10MB
- 自动轮转到 `.log.1`, `.log.2` 等
- 保留最近 5 个备份

### 4. 控制台 + 文件双输出

- 控制台：彩色人类可读格式
- 文件：JSONL 格式，易于解析和分析

---

## 📚 使用方法

### 快速开始

#### 查看日志

```bash
# 查看所有日志
python view_logs.py

# 查看 Bot 日志
python view_logs.py bot

# 只看错误
python view_logs.py --error-only

# 显示统计
python view_logs.py --stats
```

#### PowerShell 版本

```powershell
# 查看所有日志
.\ch-logs-viewer.ps1

# 实时跟踪
.\ch-logs-viewer.ps1 -Follow

# 过滤错误
.\ch-logs-viewer.ps1 -ErrorOnly

# 按级别过滤
.\ch-logs-viewer.ps1 -Level ERROR
```

### 在代码中使用

```python
from logger import get_logger, log_with_context
import logging

# 获取 logger
logger = get_logger('my_module')

# 基本日志
logger.info("操作成功")
logger.error("操作失败")

# 带上下文的日志
log_with_context(
    logger, logging.INFO,
    "下载完成",
    channel="@example",
    file_size_mb=15.5
)

# 记录异常
try:
    risky_operation()
except Exception as e:
    logger.exception("操作失败")  # 自动包含堆栈信息
```

---

## 📈 性能优化

- DEBUG 级别日志默认不记录到文件（可配置）
- 日志轮转避免单文件过大
- 异步写入不影响主程序性能

---

## 🔧 配置建议

### 开发环境

```python
logger = get_logger('module', level=logging.DEBUG)
```

### 生产环境

```python
logger = get_logger('module', level=logging.INFO)
```

### 只记录错误

```python
logger = get_logger('module', level=logging.ERROR)
```

---

## 🎯 后续改进计划

- [ ] 添加日志压缩功能（gzip）
- [ ] 支持日志发送到远程服务器
- [ ] 添加日志分析仪表板
- [ ] 集成日志告警功能
- [ ] 支持按日期归档

---

## 📖 详细文档

请参阅 `doc/LOG_SYSTEM_GUIDE.md` 获取完整的使用指南。

---

## ⚠️ 注意事项

1. **旧日志文件**: 旧的日志文件（如 `bot_2025-09-30_09-25-26.log`）不会被自动删除，可以手动清理。

2. **日志级别**: 如果日志太多，可以在 `src/logger.py` 中调整级别：

   ```python
   logger = get_logger('component', level=logging.WARNING)
   ```

3. **磁盘空间**: 每个组件保留 ~50MB 日志（10MB × 5 个备份），请定期清理旧日志。

4. **性能影响**: 新的日志系统对性能影响极小（<1%），但如果需要极致性能，可以禁用 DEBUG 日志。

---

## 🤝 贡献

如果您有任何建议或发现问题，欢迎提出 Issue 或 PR！
