# ChronoLullaby 系统日志文档

## 概述

系统日志是 ChronoLullaby 项目中一个独立的日志子系统，专门用于记录系统级事件和调试信息。它与现有的组件日志（bot.log、downloader.log 等）相互补充，但完全独立运行。

## 设计理念

### 为什么需要系统日志？

在 ChronoLullaby 中，我们有两种配置和日志记录方式：

1. **本地模式**：配置和日志都存储在本地文件中
2. **Notion 模式**：配置从 Notion 读取，部分日志会同步到 Notion

但这两种模式都存在一个问题：**如果 Notion 同步失败，或者 Notion 中的日志没有写上，我们如何知道当时的运行状态？**

因此，我们引入了系统日志作为"最后的防线"：
- **完全本地化**：无论什么模式，系统日志永远保存在本地
- **不依赖外部服务**：即使 Notion 服务挂了，系统日志依然工作
- **专注系统事件**：只记录系统级的关键事件，不重复记录业务日志

### 与组件日志的区别

| 特性 | 组件日志 (bot.log, downloader.log) | 系统日志 (system.log) |
|------|-----------------------------------|----------------------|
| **记录内容** | 业务逻辑、下载进度、文件发送等 | 进程管理、配置加载、服务启动/停止 |
| **Notion 同步** | 部分日志同步到 Notion | 完全不同步，纯本地 |
| **用途** | 业务监控和问题排查 | 系统调试和故障诊断 |
| **日志级别** | 各组件独立配置 | 支持所有级别（DEBUG 到 CRITICAL） |
| **文件位置** | `logs/bot.log`, `logs/downloader.log` 等 | `logs/system.log` |

## 系统日志记录的内容

### 记录的事件

系统日志专门记录以下类型的事件：

1. **进程生命周期**
   - 启动器初始化
   - 子进程启动（下载器、机器人）
   - 进程状态监控
   - 进程意外退出
   - 进程正常停止
   - 信号处理（SIGINT、SIGTERM）

2. **配置管理**
   - 配置提供者初始化
   - 配置模式选择（local/notion）
   - 配置文件加载
   - 配置加载失败和降级
   - YAML 配置重新加载

3. **服务管理**
   - Notion 同步服务启动/停止
   - 同步服务线程状态
   - 日志批量上传统计

4. **异常状态**
   - 配置初始化失败
   - Notion API 错误
   - 进程崩溃
   - 意外的系统状态

5. **调试信息**
   - 可随时添加的临时调试日志
   - 系统状态快照
   - 性能数据

### 不记录的内容（避免重复）

以下内容已经在组件日志中记录，系统日志不重复记录：

- 具体的视频下载进度（在 `downloader.dl_audio.log` 中）
- 文件发送详细信息（在 `bot.send_file.log` 中）
- yt-dlp 的详细输出（在 `downloader.yt-dlp.log` 中）
- 业务逻辑的详细流程

## 日志文件位置和格式

### 文件位置

```
logs/
├── system.log           # 当前系统日志
├── system.log.1         # 轮转备份 1
├── system.log.2         # 轮转备份 2
├── system.log.3         # 轮转备份 3
├── system.log.4         # 轮转备份 4
└── system.log.5         # 轮转备份 5（最老）
```

### 轮转策略

- **最大文件大小**：10 MB
- **备份数量**：5 个
- **轮转行为**：当文件超过 10 MB 时，自动轮转（当前文件变为 .1，.1 变为 .2，以此类推）

### 日志格式

系统日志使用 JSONL（JSON Lines）格式，每行一个 JSON 对象：

```json
{
  "timestamp": "2025-10-21T10:30:45.123456",
  "level": "INFO",
  "component": "chronolullaby.system",
  "message": "启动器初始化完成",
  "process": 12345,
  "thread": 140234567890,
  "config_mode": "notion",
  "machine_id": "cb-pc-hp"
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | ISO 8601 格式的时间戳 |
| `level` | string | 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| `component` | string | 组件名称，系统日志固定为 "chronolullaby.system" |
| `message` | string | 日志消息内容 |
| `process` | integer | 进程 ID |
| `thread` | integer | 线程 ID |
| 其他字段 | any | 通过 `extra_data` 添加的上下文信息 |

## 使用方法

### 在代码中使用

```python
from logger import get_system_logger, log_with_context
import logging

# 获取系统日志 logger
sys_logger = get_system_logger()

# 记录简单消息
sys_logger.info("服务已启动")
sys_logger.debug("进入调试模式")
sys_logger.warning("配置文件缺少可选项")
sys_logger.error("初始化失败")

# 记录带上下文的消息
log_with_context(
    sys_logger, logging.INFO,
    "配置提供者已初始化",
    provider="NotionConfigProvider",
    mode="notion",
    page_id="29220ac1..."
)

# 记录异常
try:
    # some code
    pass
except Exception as e:
    log_with_context(
        sys_logger, logging.ERROR,
        "操作失败",
        error=str(e),
        error_type=type(e).__name__
    )
```

### 查看日志

#### 方法 1：直接查看原始文件

```powershell
# 查看最新的日志
Get-Content logs\system.log -Tail 50

# 实时监控日志
Get-Content logs\system.log -Wait
```

#### 方法 2：使用 jq 格式化查看（推荐）

如果安装了 [jq](https://stedolan.github.io/jq/)，可以格式化查看：

```powershell
# 格式化查看所有日志
Get-Content logs\system.log | jq .

# 查看最后 20 条
Get-Content logs\system.log -Tail 20 | jq .

# 只查看 ERROR 和 CRITICAL 级别
Get-Content logs\system.log | jq 'select(.level == "ERROR" or .level == "CRITICAL")'

# 查看特定时间范围
Get-Content logs\system.log | jq 'select(.timestamp >= "2025-10-21T10:00:00")'

# 按消息内容过滤
Get-Content logs\system.log | jq 'select(.message | contains("Notion"))'
```

#### 方法 3：在 Python 中分析

```python
import json

# 读取并解析系统日志
with open('logs/system.log', 'r', encoding='utf-8') as f:
    for line in f:
        log_entry = json.loads(line)
        if log_entry['level'] in ['ERROR', 'CRITICAL']:
            print(f"{log_entry['timestamp']} [{log_entry['level']}] {log_entry['message']}")
```

## 典型使用场景

### 场景 1：调试进程启动问题

**问题**：启动器启动后，子进程没有正常运行

**解决方法**：

1. 查看系统日志中的进程启动记录：
   ```powershell
   Get-Content logs\system.log | jq 'select(.message | contains("进程"))'
   ```

2. 检查是否有进程启动失败或意外退出的记录

3. 查看 PID 和退出码，结合组件日志进一步排查

### 场景 2：Notion 同步失败

**问题**：配置了 Notion 模式，但日志没有上传到 Notion

**解决方法**：

1. 查看系统日志中的 Notion 相关事件：
   ```powershell
   Get-Content logs\system.log | jq 'select(.message | contains("Notion"))'
   ```

2. 检查是否有初始化失败、API Key 错误等记录

3. 查看日志批量上传的统计信息（成功/失败数量）

### 场景 3：配置模式切换

**问题**：不确定当前使用的是哪种配置模式

**解决方法**：

1. 查看系统日志中的配置初始化记录：
   ```powershell
   Get-Content logs\system.log | jq 'select(.message | contains("配置"))'
   ```

2. 查找 "配置提供者" 相关的日志，确认当前使用的提供者类型

### 场景 4：添加临时调试信息

**问题**：需要调试某个功能，但不想修改现有的组件日志

**解决方法**：

在任何需要的地方添加系统日志：

```python
from logger import get_system_logger

sys_logger = get_system_logger()
sys_logger.debug("临时调试：检查点 A", extra={'extra_data': {'variable': some_value}})
```

这样可以在不影响业务日志的情况下，添加任意调试信息。

## 最佳实践

### 1. 什么时候使用系统日志？

**使用系统日志**：
- 进程管理相关的操作
- 配置加载和切换
- 服务启动和停止
- 系统级的异常状态
- 临时调试信息

**使用组件日志**：
- 业务逻辑流程
- 具体的下载或发送操作
- 用户交互
- API 调用详情

### 2. 日志级别的选择

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| **DEBUG** | 详细的调试信息、临时排查 | "进程状态检查"、"配置参数详情" |
| **INFO** | 正常的系统事件 | "服务已启动"、"配置加载成功" |
| **WARNING** | 潜在问题，但不影响运行 | "配置缺失，使用默认值"、"重复初始化" |
| **ERROR** | 错误，但系统可以继续运行 | "配置加载失败"、"API 调用失败" |
| **CRITICAL** | 严重错误，系统无法继续 | "无法启动必要的服务" |

### 3. 添加上下文信息

始终使用 `log_with_context()` 添加相关的上下文信息：

```python
# ✅ 好的做法 - 包含上下文
log_with_context(
    sys_logger, logging.ERROR,
    "进程意外退出",
    process_name="YouTubeDownloader",
    pid=12345,
    exitcode=-1
)

# ❌ 不好的做法 - 缺少上下文
sys_logger.error("进程意外退出")
```

### 4. 保持消息简洁

系统日志的消息应该简洁明了：

```python
# ✅ 好的做法
sys_logger.info("Notion 配置提供者初始化成功")

# ❌ 不好的做法
sys_logger.info("Notion 配置提供者已经成功完成了初始化过程，所有参数都已正确配置，现在可以正常使用了")
```

### 5. 避免敏感信息

不要在系统日志中记录敏感信息：

```python
# ✅ 好的做法 - 隐藏敏感信息
log_with_context(
    sys_logger, logging.INFO,
    "Notion API 初始化",
    api_key="ntn_...xxxx",  # 只显示前缀
    page_id=page_id[:8] + "..."  # 只显示前几位
)

# ❌ 不好的做法 - 暴露完整密钥
log_with_context(
    sys_logger, logging.INFO,
    "Notion API 初始化",
    api_key="ntn_D8770367242u7gacze0LD1DDt3lNUPalSSAU5bKvbic8vn"
)
```

## 故障排查

### 问题：系统日志没有生成

**可能原因**：
1. logs 目录不存在
2. 权限问题

**解决方法**：
```powershell
# 检查 logs 目录
Test-Path logs

# 如果不存在，创建目录
New-Item -ItemType Directory -Path logs

# 检查权限
Get-Acl logs
```

### 问题：日志文件过大

**原因**：系统日志会自动轮转，但如果日志产生速度过快，可能需要手动清理旧日志。

**解决方法**：
```powershell
# 删除旧的备份日志
Remove-Item logs\system.log.* -Confirm

# 或者归档后删除
Compress-Archive -Path logs\system.log.* -DestinationPath logs\archive\system-$(Get-Date -Format 'yyyyMMdd').zip
Remove-Item logs\system.log.*
```

### 问题：找不到特定的日志

**解决方法**：

1. 检查时间范围是否正确
2. 检查是否被轮转到备份文件中：
   ```powershell
   # 搜索所有系统日志文件
   Get-Content logs\system.log* | jq 'select(.message | contains("关键词"))'
   ```

## 与 Notion 日志的关系

系统日志和 Notion 日志各有分工：

| 特性 | 系统日志 | Notion 日志 |
|------|----------|-------------|
| **存储位置** | 本地文件 | Notion 数据库 |
| **可用性** | 始终可用 | 依赖网络和 Notion 服务 |
| **记录内容** | 系统事件 | 业务日志（下载、发送） |
| **查看方式** | 文本工具、jq | Notion 界面 |
| **适用场景** | 系统调试、故障诊断 | 业务监控、远程查看 |

**最佳实践**：
- 关键的系统事件同时在两个地方记录
- 系统日志作为"最后的防线"，确保本地始终有完整记录
- Notion 日志提供便捷的远程查看和统计分析

## 总结

系统日志是 ChronoLullaby 项目中一个重要的调试和监控工具。它：

- ✅ **完全本地化**：不依赖外部服务
- ✅ **专注系统事件**：不重复记录业务日志
- ✅ **便于调试**：随时可以添加临时调试信息
- ✅ **格式化存储**：JSONL 格式便于程序化分析
- ✅ **自动轮转**：避免文件过大

在日常使用中，建议：
1. 遇到问题时，首先查看系统日志了解系统状态
2. 结合组件日志，全面分析问题
3. 需要调试时，灵活使用系统日志记录调试信息
4. 定期清理或归档旧的日志文件

有了系统日志，即使 Notion 服务不可用，我们也能随时了解系统的运行状态，进行有效的故障诊断和调试。

