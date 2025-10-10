# 多 Bot 模式说明

## 📖 概述

ChronoLullaby 支持两种 Bot 配置模式：

1. **单 Bot 多频道模式**（推荐，当前已实现）
2. **多 Bot 独立模式**（配置已支持，完整运行需阶段2）

---

## 🔀 两种模式对比

### 模式 1：单 Bot 多频道（推荐）✅

**架构：**
```
一个 Telegram Bot (@YourBot)
    ├─→ 发送音频到 Telegram 技术频道 (-1001111111111)
    ├─→ 发送音频到 Telegram 时事频道 (-1002222222222)
    └─→ 发送音频到 Telegram 综合频道 (-1003333333333)
```

**说明：**
- 一个 Telegram Bot 可以向多个频道发送消息
- 只要这个 Bot 在所有目标频道中都是管理员即可
- 这是 Telegram Bot 的**标准用法**

**配置示例：**
```yaml
telegram:
  bot_token: "1234567890:ABCdefGHI_统一的BOT"  # 全局配置一个bot

channel_groups:
  - name: "技术频道"
    telegram_chat_id: "-1001111111111"  # 技术频道ID
    audio_folder: "au/tech"
    youtube_channels:
      - "@JeffTechView"
      - "@Lifeano"
  
  - name: "时事频道"
    telegram_chat_id: "-1002222222222"  # 时事频道ID
    audio_folder: "au/news"
    youtube_channels:
      - "@wenzhaoofficial"
      - "@cui_news"
```

**优点：**
- ✅ 简单，只需管理一个 bot
- ✅ 统一的日志和监控
- ✅ 配置简单
- ✅ 适合个人或小团队

**缺点：**
- ⚠️ 所有频道共享一个 bot 的 API 限制
- ⚠️ 如果 bot token 泄露，所有频道都受影响

**适用场景：**
- 个人使用
- 小团队
- 所有频道归同一管理者
- **推荐大多数用户使用此模式**

---

### 模式 2：多 Bot 独立模式

**架构：**
```
Bot A (@TechBot)    ─→ 发送音频到 Telegram 技术频道
Bot B (@NewsBot)    ─→ 发送音频到 Telegram 时事频道
Bot C (@GeneralBot) ─→ 发送音频到 Telegram 综合频道
```

**说明：**
- 每个频道组有自己独立的 Bot
- 完全隔离，互不影响
- 需要为每个频道创建独立的 bot（从 @BotFather）

**配置示例：**
```yaml
telegram:
  bot_token: ""  # 全局可以留空

channel_groups:
  - name: "技术频道"
    bot_token: "1111111111:AAA_技术频道专用BOT"  # 独立bot
    telegram_chat_id: "-1001111111111"
    audio_folder: "au/tech"
    youtube_channels:
      - "@JeffTechView"
  
  - name: "时事频道"
    bot_token: "2222222222:BBB_时事频道专用BOT"  # 独立bot
    telegram_chat_id: "-1002222222222"
    audio_folder: "au/news"
    youtube_channels:
      - "@wenzhaoofficial"
```

**优点：**
- ✅ 完全隔离，一个 bot 故障不影响其他
- ✅ 每个 bot 有独立的 API 限制配额
- ✅ 更好的安全性（token 隔离）
- ✅ 可以分配给不同的团队管理

**缺点：**
- ❌ 需要管理多个 bot
- ❌ 配置更复杂
- ❌ 需要更多的维护工作

**适用场景：**
- 多团队协作
- 需要权限隔离
- 不同的服务等级要求
- 大规模部署

---

## 🎯 当前实现状态

### 阶段 1（当前）✅

**已实现：**
- ✅ 配置文件支持两种模式的配置语法
- ✅ 可以在全局配置 `telegram.bot_token`
- ✅ 可以在每个频道组配置独立的 `bot_token`
- ✅ 配置读取优先级：频道组配置 > 全局配置 > 环境变量
- ✅ 单频道组完整运行

**限制：**
- ⚠️ 只支持单个频道组运行
- ⚠️ 如果配置了多个频道组，只会处理第一个

**工作方式：**
- 程序读取第一个频道组的配置
- 如果该组有 `bot_token`，使用它
- 否则使用全局 `telegram.bot_token`
- 下载该组的 YouTube 频道
- 发送到该组的 Telegram 频道

### 阶段 2（计划中）🔜

**将要实现：**
- 🔜 支持多个频道组同时运行
- 🔜 每个频道组独立的下载任务
- 🔜 每个频道组独立的发送任务
- 🔜 每个频道组可以有独立的下载间隔、过滤规则等

**技术挑战：**
- 需要为每个频道组创建独立的 Bot Application 实例
- 需要多线程/多进程架构
- 需要独立的任务调度

---

## 🔧 配置优先级

Bot Token 的读取优先级（从高到低）：

1. **频道组独立配置** - `channel_groups[0].bot_token`
2. **全局配置** - `telegram.bot_token`
3. **环境变量** - `.env` 文件中的 `BOT_TOKEN`

**示例：**

```yaml
telegram:
  bot_token: "全局BOT"  # 优先级2

channel_groups:
  - name: "频道A"
    bot_token: "频道A专用BOT"  # 优先级1（最高）
    # ...
  
  - name: "频道B"
    # 没有 bot_token，将使用全局的 "全局BOT"
    # ...
```

---

## 💡 使用建议

### 新手用户 / 个人使用

**推荐：模式 1（单 Bot 多频道）**

1. 在 `telegram.bot_token` 配置一个 bot
2. 在每个频道组配置不同的 `telegram_chat_id`
3. 确保这个 bot 在所有目标频道中都是管理员

### 团队 / 企业使用

**推荐：根据需求选择**

- 如果团队信任度高，用模式 1
- 如果需要权限隔离，用模式 2

### 测试建议

**开发阶段：**
- 先用模式 1 测试功能
- 确认无误后再考虑是否需要模式 2

---

## 🔐 安全建议

### 模式 1 的安全措施

1. ✅ 妥善保管 bot token，不要提交到 Git
2. ✅ 使用 `.gitignore` 忽略 `config.yaml` 或 `.env`
3. ✅ 定期检查 bot 的频道权限

### 模式 2 的安全措施

1. ✅ 每个 bot 只授予最小必要权限
2. ✅ 不同团队使用不同的 bot
3. ✅ 定期审计各个 bot 的活动日志

---

## ❓ 常见问题

### Q1: 一个 bot 可以向多少个频道发送消息？

**A:** Telegram 没有明确限制，但建议：
- 个人使用：10 个频道以内
- 如果超过 20 个频道，考虑拆分为多个 bot

### Q2: 如何知道当前使用的是哪个 bot？

**A:** 查看程序启动日志，会显示：
```
配置加载成功：发送间隔 = 4920 秒 (1.37 小时)
```

或者在代码中添加日志输出 bot 的用户名。

### Q3: 可以混合使用两种模式吗？

**A:** 可以！配置示例：

```yaml
telegram:
  bot_token: "全局BOT"  # 大部分频道组用这个

channel_groups:
  - name: "频道A"
    # 不配置 bot_token，使用全局BOT
    telegram_chat_id: "-1001111111111"
  
  - name: "频道B"
    # 不配置 bot_token，使用全局BOT
    telegram_chat_id: "-1002222222222"
  
  - name: "特殊频道"
    bot_token: "特殊BOT"  # 这个组用独立bot
    telegram_chat_id: "-1003333333333"
```

### Q4: 阶段 2 什么时候发布？

**A:** 取决于以下因素：
- 用户需求
- 技术架构设计
- 测试和稳定性验证

如果您急需多组并行运行，可以：
- 运行多个程序实例（每个实例用不同的 config.yaml）
- 或等待阶段 2 更新

---

## 📚 相关文档

- [配置指南](CONFIG_GUIDE.md) - 完整配置说明
- [快速参考](QUICK_REFERENCE.md) - 常用命令
- [YAML 更新说明](../YAML_CONFIG_UPDATE.md) - 配置系统更新

---

**更新日期：** 2025-10-09  
**版本：** 阶段 1 - 配置支持两种模式，运行支持单频道组

