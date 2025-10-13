# /chatid 命令使用说明

## 功能介绍

`/chatid` 是一个用于获取当前 Telegram 频道 Chat ID 的命令。这个功能已集成到主进程中，无需停止 Bot 即可使用。

## 为什么需要这个功能？

在配置 ChronoLullaby 时，你需要知道目标频道的 Chat ID 才能在 `config.yaml` 中进行配置。对于私有频道，Chat ID 无法直接查看，必须通过 Bot 的消息对象获取。

**之前的问题：**
- 需要停止主进程
- 需要运行单独的工具脚本
- 配置新频道时很不方便

**现在的解决方案：**
- 主进程运行时就可以使用
- 直接在频道中发送命令即可
- 立即获得 Chat ID，方便配置

## 使用方法

### 1. 将 Bot 添加到目标频道

首先，确保你的 Bot 已经被添加到目标频道，并且拥有：
- 读取消息的权限
- 发送消息的权限

### 2. 在频道中发送命令

在目标频道中直接发送：

```
/chatid
```

### 3. 查看 Bot 回复

Bot 会立即回复一条包含频道信息的消息：

```
📍 频道信息

💬 Chat ID: `-1001234567890`
📂 类型: supergroup
📌 标题: 我的测试频道

💡 提示：复制上面的 Chat ID 到配置文件中使用
```

### 4. 复制 Chat ID 到配置

将获得的 Chat ID 复制到 `config/config.yaml` 中：

```yaml
channel_groups:
  - name: "我的测试频道组"
    telegram_chat_id: -1001234567890  # ← 这里使用刚才获取的 Chat ID
    audio_folder: "au/test"
    youtube_channels:
      - "@example_channel"
```

## 支持的频道类型

该命令支持所有 Telegram 频道类型：

- ✅ **私有频道** (private channel / supergroup)
- ✅ **公开频道** (public channel)
- ✅ **私聊** (private chat)
- ✅ **群组** (group)

## 日志记录

每次使用 `/chatid` 命令时，都会在 `logs/bot.log` 中记录：

```
2025-10-13 10:30:45 | INFO | 📍 /chatid 命令 - Chat ID: -1001234567890, 类型: supergroup, 标题: 我的测试频道
```

## 常见问题

### Q: Bot 没有回复？

**可能的原因：**
1. Bot 不在该频道中
2. Bot 没有发送消息的权限
3. 主进程未运行

**解决方法：**
1. 确认 Bot 已被添加到频道
2. 检查 Bot 的频道权限
3. 确认主进程正在运行（`ch-status.ps1`）

### Q: 如何在私聊中使用？

直接在与 Bot 的私聊窗口中发送 `/chatid` 即可。Bot 会显示你的用户 Chat ID。

### Q: 频道类型是什么意思？

常见的频道类型：
- `private`: 私聊
- `group`: 普通群组
- `supergroup`: 超级群组（通常是私有频道）
- `channel`: 公开频道

### Q: Chat ID 为什么是负数？

这是 Telegram 的设计：
- 用户的 Chat ID 是正数
- 群组和频道的 Chat ID 是负数
- 超级群组的 Chat ID 通常以 `-100` 开头

## 与其他工具的对比

### 之前的 `get_channel_id.py` 脚本

```python
# 旧方法：需要停止主进程，运行单独脚本
python scripts/get_channel_id.py
```

**缺点：**
- 需要停止主进程
- 需要手动运行脚本
- 配置不方便

### 新的 `/chatid` 命令

```
# 新方法：直接在频道中发送命令
/chatid
```

**优点：**
- ✅ 主进程无需停止
- ✅ 直接在频道中使用
- ✅ 立即获得结果
- ✅ 配置更方便

## 技术实现

该功能的实现位于：

- **命令处理器**: `src/util.py` - `show_chat_id()` 函数
- **命令注册**: `src/telegram_bot.py` - 在 `main()` 函数中注册

核心代码：

```python
# 注册命令处理器
application.add_handler(CommandHandler("chatid", show_chat_id))
```

## 相关文档

- [配置指南](CONFIG_GUIDE.md)
- [快速参考](QUICK_REFERENCE.md)
- [多 Bot 模式](MULTI_BOT_MODES.md)

## 更新历史

- **2025-10-13**: 首次实现 `/chatid` 命令，集成到主进程中

