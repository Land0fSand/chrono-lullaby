# 配置热重载说明

## 概述

ChronoLullaby 现在支持以下配置的**热重载**（下一轮下载自动生效）：

- ✅ `filter_days` - 视频过滤天数
- ✅ `max_videos_per_channel` - 每个频道检查的最大视频数

这意味着你可以在运行时修改这些配置，**无需重启服务**，下一轮下载时自动生效！

---

## 🎯 支持热重载的配置

### 1. `filter_days` - 视频过滤天数

**位置**：`config/config.yaml`

```yaml
downloader:
  # 视频过滤：只下载最近 N 天的视频
  filter_days: 1  # 改为 1 天，下一轮立即生效
```

**作用**：
- 只下载最近 N 天内发布的视频
- 例如设为 `1`，则只下载最近 1 天的视频
- 例如设为 `7`，则下载最近 7 天的视频

**默认值**：3 天

**何时生效**：下一轮下载开始时

---

### 2. `max_videos_per_channel` - 每个频道最大视频数

**位置**：`config/config.yaml`

```yaml
downloader:
  # 每个频道检查的最大视频数
  max_videos_per_channel: 6  # 改为其他值，下一轮立即生效
```

**作用**：
- 限制每个 YouTube 频道检查的视频数量
- 例如设为 `3`，每个频道只检查最新的 3 个视频
- 例如设为 `10`，每个频道检查最新的 10 个视频

**默认值**：6

**何时生效**：下一轮下载开始时

---

## 📝 使用示例

### 场景 1：临时加快下载速度

如果你想快速下载最新内容：

```yaml
downloader:
  filter_days: 1              # 只下载最近1天的视频
  max_videos_per_channel: 3   # 每个频道只检查3个视频
```

**修改后**：
1. ✅ 保存 `config.yaml`
2. ✅ 无需重启服务
3. ✅ 等待当前轮次完成
4. ✅ 下一轮自动使用新配置

---

### 场景 2：捕获更多历史视频

如果某个频道更新频繁，想捕获更多视频：

```yaml
downloader:
  filter_days: 7              # 下载最近7天的视频
  max_videos_per_channel: 15  # 每个频道检查15个视频
```

**修改后自动生效**，无需任何操作！

---

### 场景 3：实时调整配置

**步骤**：

1. **查看当前运行状态**：
   ```powershell
   ch logs downloader
   ```

2. **修改配置**：
   编辑 `config/config.yaml`，修改 `filter_days` 或 `max_videos_per_channel`

3. **保存文件**
   
4. **等待生效**：
   - 当前轮次会继续使用旧配置
   - 下一轮下载会自动使用新配置
   - 在日志中可以看到实际使用的值

---

## 🔍 如何验证配置已生效

### 方法 1：查看日志

下载时会在日志中记录实际使用的配置：

```powershell
ch logs downloader | Select-String "视频超过"
```

你会看到类似：
```
"reason": "视频超过1天"  # 如果 filter_days = 1
"reason": "视频超过3天"  # 如果 filter_days = 3
```

### 方法 2：观察下载行为

- 如果 `max_videos_per_channel = 3`，每个频道最多下载 3 个视频
- 如果 `filter_days = 1`，只会下载最近 1 天的视频

---

## ⚠️ 注意事项

### 1. 何时生效

- ✅ **下一轮下载开始时**自动生效
- ❌ **当前轮次不会中断**，会继续使用旧配置

### 2. 配置验证

修改前请确保：
- `filter_days` 是正整数（1, 2, 3, 7, 30 等）
- `max_videos_per_channel` 是正整数（3, 6, 10, 15 等）

### 3. 性能考虑

**如果设置过大**：
- `filter_days: 30` + `max_videos_per_channel: 50`
- 会导致每个频道检查和下载大量视频
- 可能显著增加下载时间

**推荐设置**：
- 日常使用：`filter_days: 1-3`, `max_videos_per_channel: 3-6`
- 初次运行/补充历史：`filter_days: 7`, `max_videos_per_channel: 10-15`

---

## 🚫 不支持热重载的配置

以下配置**需要重启服务**才能生效：

- ❌ `bot_token` - Bot Token
- ❌ `telegram_chat_id` - Telegram 频道 ID
- ❌ `download_interval` - 下载轮次间隔
- ❌ `video_delay_min/max` - 视频间延迟
- ❌ `channel_delay_min/max` - 频道间延迟
- ❌ `youtube_channels` - YouTube 频道列表（需要重启，虽然有 reload 机制但需要新进程）

修改这些配置后，需要运行：
```powershell
ch restart
```

---

## 🔧 技术实现

### 配置读取机制

```python
def get_filter_days() -> int:
    """获取视频过滤天数（支持热重载）"""
    return get_config_value('downloader.filter_days', 3, reload=True)
    #                                                      ↑
    #                                        强制重新读取配置，不使用缓存
```

### 使用位置

1. **filter_days**：
   - 文件：`src/task/dl_audio.py`
   - 函数：`oneday_filter()`
   - 每次过滤视频时都会重新读取配置

2. **max_videos_per_channel**：
   - 文件：`src/task/dl_audio.py`
   - 函数：`dl_audio_latest()`
   - 每个频道下载开始时都会重新读取配置

---

## 📊 配置生效时间线

```
修改 config.yaml
    ↓
保存文件
    ↓
等待当前轮次完成（继续使用旧配置）
    ↓
下一轮下载开始
    ↓
✅ 自动读取新配置
    ↓
使用新配置下载
```

**典型时间**：
- 如果 `download_interval = 0`：当前轮次完成后立即生效（通常几分钟到几十分钟）
- 如果 `download_interval > 0`：当前轮次完成 + 等待间隔后生效

---

## 🎉 优势

### 之前（硬编码）
```python
"playlistend": 6,  # 硬编码，修改需要改代码+重启
timedelta(days=3)  # 硬编码，修改需要改代码+重启
```

❌ 修改麻烦
❌ 需要重启服务
❌ 不够灵活

### 现在（热重载）
```python
"playlistend": get_max_videos_per_channel(),  # 从配置读取
timedelta(days=get_filter_days())             # 从配置读取
```

✅ 修改简单（只改配置文件）
✅ 无需重启服务
✅ 下一轮自动生效
✅ 灵活调整

---

## 🔗 相关文档

- [配置指南](CONFIG_GUIDE.md)
- [快速参考](QUICK_REFERENCE.md)

---

## 更新历史

- **2025-10-13**: 实现 `filter_days` 和 `max_videos_per_channel` 热重载功能

