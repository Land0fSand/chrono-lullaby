# Notion 日志清理 - 快速参考

## ⭐ 推荐：集成到主程序（自动清理）

在 `config/config.yaml` 中启用：

```yaml
notion:
  sync:
    auto_cleanup:
      enabled: true               # 启用自动清理
      check_interval_days: 7      # 每 7 天检查一次
      keep_days: 30               # 普通日志保留 30 天（INFO/WARNING/DEBUG）
      error_keep_days: 90         # 错误日志保留 90 天（ERROR）
```

✅ 优点：
- 无需手动操作，主程序自动在空闲时清理
- ERROR 日志保留更长时间，便于问题追踪
- 普通日志及时清理，节省空间

---

## 🚀 手动清理命令

### 日常维护（推荐）
```powershell
# 步骤 1：预览
ch clean-notion-logs --days 30

# 步骤 2：确认执行
ch clean-notion-logs --days 30 --confirm
```

### 只清理 INFO 日志
```powershell
ch clean-notion-logs --days 30 --levels INFO --confirm
```

### 长期归档
```powershell
ch clean-notion-logs --days 90 --confirm
```

## 📋 参数速查

| 参数 | 说明 | 示例 |
|------|------|------|
| `--days N` | 保留最近 N 天 | `--days 30` |
| `--levels` | 指定级别 | `--levels INFO WARNING` |
| `--types` | 指定类型 | `--types downloader bot` |
| `--machine` | 指定机器 | `--machine machine-1` |
| `--all` | 全清理（危险） | `--all` |
| `--confirm` | 确认执行 | `--confirm` |

## 🎯 常见场景

### 场景 1：每周维护
```powershell
ch clean-notion-logs --days 30 --levels INFO --confirm
```

### 场景 2：空间不足
```powershell
# 先清理 INFO
ch clean-notion-logs --days 60 --levels INFO --confirm

# 再清理所有旧日志
ch clean-notion-logs --days 60 --confirm
```

### 场景 3：测试环境清理
```powershell
ch clean-notion-logs --all --machine machine-test --confirm
```

## ⚠️ 注意事项

- ✅ 先预览后删除（不加 `--confirm` 只预览）
- ✅ 保留 ERROR 日志用于问题追踪
- ❌ 删除后无法恢复
- ❌ 不要频繁清理（建议每周或每月）

## 🔗 详细文档

完整使用说明和高级功能请参考：[NOTION_LOG_CLEANUP.md](NOTION_LOG_CLEANUP.md)

