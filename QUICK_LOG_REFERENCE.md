# 日志系统快速参考

## 🚀 快速查看日志

### 基础命令

```bash
# 查看所有日志
python view_logs.py

# 查看 Bot 日志
python view_logs.py bot

# 查看下载器日志
python view_logs.py downloader

# 只看错误
python view_logs.py --error-only

# 显示最后 50 条
python view_logs.py --last 50
```

### PowerShell 版本

```powershell
# 查看所有日志
.\ch-logs-viewer.ps1

# 实时跟踪
.\ch-logs-viewer.ps1 -Follow

# 只看错误
.\ch-logs-viewer.ps1 -ErrorOnly

# 显示统计
.\ch-logs-viewer.ps1 -Stats
```

## 📊 频道下载分析（新功能）

### 查看频道汇总

```bash
# 查看所有频道的下载汇总
python view_logs.py downloader --filter "频道处理完成"

# 查看特定频道
python view_logs.py downloader --filter "@ChanChanTalk"

# 只看下载失败的
python view_logs.py downloader --filter "下载失败" --error-only
```

### 使用 jq 分析

```bash
# 提取所有频道的统计
jq 'select(.message | contains("频道处理完成")) | {channel, total: .total_videos, success: .success, error: .error, rate: .success_rate}' logs/downloader.log

# 找出成功率低于50%的频道
jq 'select(.message | contains("频道处理完成")) | select(.success * 100 / .total_videos < 50) | {channel, rate: .success_rate}' logs/downloader.log

# 列出所有失败的视频
jq 'select(.message | contains("视频下载失败")) | {channel, title, error}' logs/downloader.log
```

## 📋 日志状态说明

| 状态              | 说明         |
| ----------------- | ------------ |
| ✅ success        | 本次下载成功 |
| 📦 already_exists | 文件已存在   |
| 📚 archived       | 已在存档中   |
| 🔒 member_only    | 会员专属内容 |
| ❌ error          | 下载失败     |

## 💡 常用场景

### 1. 检查某个频道是否有遗漏

```bash
# 步骤1: 查看频道汇总
python view_logs.py downloader --filter "@ChanChanTalk" --filter "频道处理完成"

# 步骤2: 查看详细列表
python view_logs.py downloader --filter "@ChanChanTalk" --filter "详细列表"

# 步骤3: 如果有错误，查看错误详情
python view_logs.py downloader --filter "@ChanChanTalk" --error-only
```

### 2. 找出所有需要重试的视频

```bash
# 找出所有错误（排除会员内容）
jq 'select(.level=="ERROR" and (.message | contains("视频下载失败"))) | {channel, title, video_id, error}' logs/downloader.log > failed_videos.json
```

### 3. 统计今天的下载情况

```bash
# 获取今天的日期
TODAY=$(date +%Y-%m-%d)

# 统计今天的下载
grep "$TODAY" logs/downloader.log | jq 'select(.message | contains("视频下载成功"))' | jq -s 'length'
```

### 4. 查看实时下载进度

```powershell
# 实时跟踪下载器日志
.\ch-logs-viewer.ps1 downloader -Follow

# 只看重要信息（INFO及以上）
.\ch-logs-viewer.ps1 downloader -Follow -Level INFO
```

## 🔍 故障排查

### 问题：某个频道下载数量不对

```bash
# 1. 查看频道汇总
python view_logs.py downloader --filter "@频道名" --filter "频道处理完成"

# 2. 检查是否有错误
python view_logs.py downloader --filter "@频道名" --error-only

# 3. 查看详细列表
python view_logs.py downloader --filter "@频道名" --filter "详细列表"
```

### 问题：想知道哪些频道下载失败率高

```bash
# 提取所有频道统计并按错误数排序
jq 'select(.message | contains("频道处理完成")) | {channel, error: .error, total: .total_videos, rate: (.error * 100 / .total_videos)}' logs/downloader.log | jq -s 'sort_by(.rate) | reverse'
```

### 问题：某个视频下载失败了，原因是什么？

```bash
# 搜索特定视频标题
python view_logs.py downloader --filter "视频标题关键词"

# 或使用 jq 查询
jq 'select(.title | contains("视频标题关键词"))' logs/downloader.log
```

## 📝 日志文件位置

```
logs/
├── bot.log                  # Bot 组件日志
├── bot_error.log            # Bot 错误日志
├── downloader.log           # 下载器日志（包含所有频道下载信息）
├── downloader_error.log     # 下载器错误日志
├── launcher.log             # 启动器日志
└── *.log.1, *.log.2 ...    # 轮转备份
```

## 🎯 推荐工作流

### 每次下载后检查

1. 查看汇总统计：

   ```bash
   python view_logs.py downloader --filter "频道处理完成" --last 10
   ```

2. 如果有错误，查看详情：

   ```bash
   python view_logs.py downloader --error-only --last 20
   ```

3. 查看详细列表确认没有遗漏：
   ```bash
   python view_logs.py downloader --filter "详细列表" --last 50
   ```

### 定期分析

```bash
# 每周运行一次，检查整体情况
python view_logs.py downloader --filter "频道处理完成" > weekly_summary.txt

# 使用 jq 生成 CSV 报告
jq -r 'select(.message | contains("频道处理完成")) | [.channel, .total_videos, .success, .error, .success_rate] | @csv' logs/downloader.log > download_report.csv
```

## 📚 更多信息

- 完整指南：`doc/LOG_SYSTEM_GUIDE.md`
- 下载日志详解：`doc/ENHANCED_DOWNLOAD_LOGS.md`
- 更新日志：`CHANGELOG_LOG_SYSTEM.md`
