# /chatid 命令使用说明

## 功能介绍

`/chatid` 命令用于快速获取 Telegram 频道的 Chat ID，无需停止 Bot 或运行额外脚本。

---

## 使用方法

### 1. 将 Bot 添加到目标频道

确保你的 Bot 已被添加到目标频道，并拥有：
- 读取消息的权限
- 发送消息的权限

### 2. 发送命令

在频道中直接发送：

```
/chatid
```

### 3. 查看回复

Bot 会立即回复频道信息：

```
📍 频道信息

💬 Chat ID: `-1001234567890`
📂 类型: supergroup
📌 标题: 我的测试频道

💡 提示：复制上面的 Chat ID 到配置文件中使用
```

### 4. 配置到 config.yaml

将获得的 Chat ID 填入配置：

```yaml
channel_groups:
  - name: "我的测试频道组"
    telegram_chat_id: -1001234567890  # ← 这里
    audio_folder: "au"
    youtube_channels:
      - "@频道1"
```

---

## 支持的频道类型

- ✅ 私有频道/超级群组 (supergroup)
- ✅ 公开频道 (channel)
- ✅ 群组 (group)
- ✅ 私聊 (private)

---

## 常见问题

### Q: Bot 没有回复？

**可能原因：**
1. Bot 不在该频道中
2. Bot 没有发送消息权限
3. 主进程未运行

**解决方法：**
```powershell
# 确认主进程运行中
ch status

# 如未运行，启动服务
ch start
```

### Q: Chat ID 为什么是负数？

Telegram 的设计：
- 用户 ID 是正数
- 群组/频道 ID 是负数
- 超级群组通常以 `-100` 开头

### Q: 在私聊中使用？

直接在与 Bot 的私聊窗口中发送 `/chatid`，会显示你的用户 Chat ID。

---

## 日志记录

每次使用命令都会在 `logs/bot.log` 中记录：

```json
{
  "timestamp": "2025-10-13T10:30:45",
  "level": "INFO",
  "component": "bot",
  "message": "📍 /chatid 命令",
  "chat_id": -1001234567890,
  "chat_type": "supergroup",
  "title": "我的测试频道"
}
```

---

## 技术实现

- **命令处理器**: `src/util.py` - `show_chat_id()`
- **命令注册**: `src/telegram_bot.py`

```python
application.add_handler(CommandHandler("chatid", show_chat_id))
```

---

## 相关文档

- [配置指南](CONFIG_GUIDE.md)
- [使用文档](README.md)
