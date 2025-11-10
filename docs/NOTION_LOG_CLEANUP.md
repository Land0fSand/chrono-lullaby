# Notion 日志清理指南

## 概述

ChronoLullaby 的日志会自动上传到 Notion 数据库。长期运行后，日志数据库可能会不断膨胀，影响性能和查询速度。本工具提供了灵活的日志清理功能。

## 为什么需要清理日志？

1. **Notion 性能优化**：大量日志会导致数据库查询变慢
2. **存储空间管理**：Notion 有存储限制，及时清理可避免超限
3. **信息过载**：过多历史日志会干扰查看最近的重要信息
4. **成本控制**：对于付费 Notion 用户，减少存储可降低成本

## 推荐策略

### 日常维护（推荐）

- **保留 30 天的日志**：适合日常调试和问题追踪
- **每周执行一次**：自动化清理，保持数据库在合理大小
- **只清理 INFO 级别**：保留 WARNING 和 ERROR 日志以便长期追踪问题

```powershell
# 每周执行一次
ch clean-notion-logs --days 30 --levels INFO --confirm
```

### 长期归档（可选）

- **保留 90 天的所有日志**：用于重要项目或需要长期追踪
- **每月执行一次**：减少维护频率

```powershell
# 每月执行一次
ch clean-notion-logs --days 90 --confirm
```

### 紧急清理（慎用）

- **全清理**：在 Notion 空间不足或需要全新开始时使用
- **需要二次确认**：防止误删重要日志

```powershell
# 危险操作！会删除所有日志
ch clean-notion-logs --all --confirm
```

## 使用方法

### 基础命令

#### 1. 预览模式（推荐先运行）

```powershell
# 预览将要删除的日志，不实际删除
ch clean-notion-logs --days 30
```

这会显示：
- 将要删除的日志数量
- 按级别、类型、机器的统计信息
- 最早和最晚的日志时间

#### 2. 实际删除

```powershell
# 确认无误后，添加 --confirm 参数实际删除
ch clean-notion-logs --days 30 --confirm
```

### 高级用法

#### 按级别清理

只清理指定级别的日志，保留其他级别：

```powershell
# 只删除 INFO 级别的旧日志，保留 WARNING 和 ERROR
ch clean-notion-logs --days 30 --levels INFO --confirm

# 删除 INFO 和 WARNING 级别的旧日志
ch clean-notion-logs --days 30 --levels INFO WARNING --confirm
```

#### 按类型清理

只清理指定类型的日志：

```powershell
# 只删除下载器日志
ch clean-notion-logs --days 30 --types downloader --confirm

# 删除下载器和机器人日志，保留错误日志
ch clean-notion-logs --days 30 --types downloader bot --confirm
```

#### 按机器清理

只清理特定机器的日志（适合多机器部署）：

```powershell
# 只删除 machine-1 的旧日志
ch clean-notion-logs --days 30 --machine machine-1 --confirm
```

#### 组合条件

可以组合多个条件：

```powershell
# 删除 machine-1 上 30 天前的 INFO 级别下载器日志
ch clean-notion-logs --days 30 --levels INFO --types downloader --machine machine-1 --confirm
```

### 全清理模式

```powershell
# 危险！删除所有日志
ch clean-notion-logs --all --confirm
```

**注意**：全清理会删除 Notion 中的所有日志，无法恢复！

## 完整参数说明

### 清理模式（必选其一）

| 参数 | 说明 | 示例 |
|------|------|------|
| `--days N` | 删除 N 天前的日志 | `--days 30` |
| `--all` | 删除所有日志（危险） | `--all` |

### 过滤条件（可选）

| 参数 | 说明 | 可选值 | 示例 |
|------|------|--------|------|
| `--levels` | 只清理指定级别 | INFO, WARNING, ERROR, DEBUG | `--levels INFO WARNING` |
| `--types` | 只清理指定类型 | downloader, bot, error, system | `--types downloader` |
| `--machine` | 只清理指定机器 | 你的 machine_id | `--machine machine-1` |

### 执行选项

| 参数 | 说明 |
|------|------|
| `--confirm` | 确认执行删除（不加则只预览） |

## 使用示例

### 场景 1：日常维护

```powershell
# 步骤 1：预览
ch clean-notion-logs --days 30

# 步骤 2：确认无误后执行
ch clean-notion-logs --days 30 --confirm
```

### 场景 2：只保留错误日志

```powershell
# 删除 30 天前的 INFO 和 WARNING 日志，保留 ERROR
ch clean-notion-logs --days 30 --levels INFO WARNING --confirm
```

### 场景 3：清理测试机器日志

```powershell
# 删除测试机器 machine-test 的所有日志
ch clean-notion-logs --all --machine machine-test --confirm
```

### 场景 4：Notion 空间不足紧急清理

```powershell
# 先删除 60 天前的 INFO 日志
ch clean-notion-logs --days 60 --levels INFO --confirm

# 如果还不够，再删除 60 天前的所有日志
ch clean-notion-logs --days 60 --confirm

# 最后手段：全清理（慎用！）
ch clean-notion-logs --all --confirm
```

## 自动化方案

ChronoLullaby 提供两种自动化清理方案：

### 方案 1：集成到主程序（推荐）⭐

**优点**：
- ✅ 无需额外配置
- ✅ 利用主程序空闲时间执行
- ✅ 不占用额外系统资源
- ✅ 随主程序启停

**配置方法**：

在 `config/config.yaml` 中启用自动清理：

```yaml
notion:
  sync:
    # 自动日志清理配置
    auto_cleanup:
      enabled: true               # 启用自动清理
      check_interval_days: 7      # 每 7 天检查一次
      keep_days: 30               # 普通日志保留天数（INFO/WARNING/DEBUG）
      error_keep_days: 90         # ERROR 日志保留天数（默认 3 个月）
      min_keep_days: 7            # 安全限制：最少保留 7 天
```

**工作原理**：
1. 主程序启动后，自动清理线程会在后台运行
2. 启动 60 秒后执行首次清理检查
3. 之后每隔 `check_interval_days` 天自动检查并清理
4. 分两步清理：
   - 先清理 30 天前的普通日志（INFO/WARNING/DEBUG）
   - 再清理 90 天前的错误日志（ERROR）
5. 清理过程在后台进行，不影响下载和上传任务
6. 所有清理操作都会记录到日志
7. 清理时间持久化到文件，程序重启不影响清理周期

**启动信息示例**：

```
✅ Notion 同步服务已启动
   日志上传间隔: 300秒
   存档同步间隔: 60秒
   机器标识: machine-1
   自动清理: 已启用
   清理策略: 每 7 天检查
   普通日志: 保留 30 天（INFO/WARNING/DEBUG）
   错误日志: 保留 90 天（ERROR）

📅 上次清理: 3 天前 (2024-11-07 08:30:45)
日志自动清理线程已启动
  检查间隔: 7 天
  普通日志保留: 30 天
  错误日志保留: 90 天
⏰ 下次清理预计: 4 天后
```

**清理执行示例**：

```
🧹 开始自动清理 Notion 日志...
   [1/2] 清理普通日志（INFO/WARNING/DEBUG）- 30 天前...
      → 清理 1234 条: ✅ 1234 成功, ❌ 0 失败
   [2/2] 清理错误日志（ERROR）- 90 天前...
      → 清理 56 条: ✅ 56 成功, ❌ 0 失败
   ✅ 总计清理: 1290 条日志
✅ 自动清理完成，下次清理时间: 7天后
```

### 方案 2：Windows 任务计划程序

创建定时任务，每周自动清理日志：

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每周一次
4. 操作：启动程序
   - 程序：`pwsh.exe`
   - 参数：`-File "D:\path\to\chronolullaby\scripts\ch.ps1" clean-notion-logs --days 30 --levels INFO --confirm`
   - 起始于：`D:\path\to\chronolullaby`

### PowerShell 脚本

创建一个自动化清理脚本 `scripts/auto-clean-logs.ps1`：

```powershell
# 自动日志清理脚本
# 建议放在 Windows 任务计划程序中定期运行

$projectRoot = Split-Path $PSScriptRoot -Parent
cd $projectRoot

Write-Host "=== 自动日志清理 ===" -ForegroundColor Green
Write-Host "时间: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# 清理 30 天前的 INFO 日志
Write-Host "正在清理 30 天前的 INFO 级别日志..." -ForegroundColor Cyan
& "$projectRoot\scripts\ch.ps1" clean-notion-logs --days 30 --levels INFO --confirm

Write-Host ""
Write-Host "=== 清理完成 ===" -ForegroundColor Green
```

## 注意事项

1. **先预览后删除**：强烈建议先运行预览模式，确认无误后再添加 `--confirm`
2. **无法恢复**：删除的日志无法恢复，请谨慎操作
3. **保留关键日志**：建议保留 ERROR 级别的日志以便长期追踪问题
4. **避免频繁清理**：建议每周或每月清理一次，不要每天清理
5. **API 限流**：大量删除时可能触发 Notion API 限流，工具会自动重试
6. **网络要求**：需要稳定的网络连接到 Notion API

## 常见问题

### Q: 删除后还能恢复吗？

A: 不能。日志在 Notion 中被归档（archived）后，需要在 Notion 界面手动恢复，且仅在短时间内有效。建议在删除前做好备份。

### Q: 清理会影响正在运行的服务吗？

A: 不会。清理只删除 Notion 中的历史日志，不影响正在运行的服务和新日志的上传。

### Q: 如何备份日志？

A: 在 Notion 中打开日志数据库，点击右上角 "..." -> "Export" 即可导出所有日志。

### Q: 清理需要多长时间？

A: 取决于日志数量和网络速度。通常 1000 条日志需要 1-2 分钟。

### Q: 如何查看当前日志数量？

A: 在 Notion 中打开日志数据库，底部会显示总记录数。或运行预览命令：
```powershell
ch clean-notion-logs --all  # 不加 --confirm 只预览
```

### Q: 误删了重要日志怎么办？

A: 
1. 立即在 Notion 中查看回收站（Trash）
2. 找到被归档的日志页面，点击 "Restore"
3. 如果已经超过时间限制，只能从之前的备份恢复

## 性能优化建议

- **日志数量 < 10,000**：性能良好，无需特别优化
- **日志数量 10,000 - 50,000**：建议每月清理一次
- **日志数量 > 50,000**：建议每周清理一次，或减少上传频率

可以在 `config.yaml` 中调整日志上传频率：

```yaml
notion:
  sync:
    log_upload_interval: 600  # 从 300 秒（5分钟）改为 600 秒（10分钟）
```

## 相关文档

- [Notion 设置指南](NOTION_SETUP.md)
- [配置指南](CONFIG_GUIDE.md)
- [主文档](../readme.md)

