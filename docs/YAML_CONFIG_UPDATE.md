# YAML 配置支持更新说明

## 🎉 新功能

ChronoLullaby 现在支持使用 YAML 配置文件进行统一配置管理！

## ✨ 主要改进

### 1. 统一配置管理
- ✅ 所有配置集中在一个 `config.yaml` 文件
- ✅ 支持注释，配置更清晰
- ✅ 可配置下载间隔、发送间隔等参数

### 2. 向后兼容
- ✅ 完全兼容现有的 `channels.txt` + `.env` 配置方式
- ✅ 自动检测配置方式，无缝切换
- ✅ 无需修改现有配置即可继续使用

### 3. 为未来扩展做准备
- 🔜 支持多组频道配置（不同 YouTube 频道组 → 不同 Telegram 频道）
- 🔜 每组独立的下载策略
- 🔜 更灵活的过滤规则

## 📦 依赖更新

新增依赖：**PyYAML**

安装命令：
```bash
pip install PyYAML==6.0.2
# 或者
pip install -r requirements.txt
```

## 🚀 快速开始

### 方式 1：继续使用现有配置（推荐）

**什么都不用改！** 程序会自动使用现有的 `channels.txt` 和 `.env` 文件。

运行时会看到提示：
```
ℹ️  未找到 config.yaml，使用传统配置方式（channels.txt + .env）
```

### 方式 2：迁移到 YAML 配置

1. **复制示例配置：**
   ```bash
   copy config.yaml.example config.yaml
   ```

2. **编辑 config.yaml，填入你的配置：**
   ```yaml
   telegram:
     bot_token: "你的_BOT_TOKEN"
   
   channel_groups:
     - name: "主频道"
       telegram_chat_id: "你的_CHAT_ID"
       youtube_channels:
         - "@StorytellerFan"
         - "@meowsir"
         # ... 其他频道
   ```

3. **运行程序：**
   ```bash
   .\ch.ps1
   ```

   看到以下提示说明成功：
   ```
   ✅ 使用 config.yaml 配置文件
   ```

## 📖 详细文档

请查看 [配置指南](doc/CONFIG_GUIDE.md) 了解完整的配置说明。

## 🔧 配置优先级

程序会按以下顺序查找配置：

1. 首先检查 `config.yaml` 是否存在
   - 如果存在，使用 YAML 配置
   - 如果不存在，继续下一步

2. 使用传统配置方式（`channels.txt` + `.env`）

## 📝 配置示例对比

### 旧方式（仍然支持）

**channels.txt:**
```
@StorytellerFan
@meowsir
@wuyuesanren
# @vexilla01
```

**.env:**
```
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHAT_ID=-1001234567890
```

### 新方式（推荐）

**config.yaml:**
```yaml
telegram:
  bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
  send_interval: 4920

downloader:
  download_interval: 29520
  filter_days: 3

channel_groups:
  - name: "主频道"
    telegram_chat_id: "-1001234567890"
    youtube_channels:
      - "@StorytellerFan"
      - "@meowsir"
      - "@wuyuesanren"
      # - "@vexilla01"
```

**优势：**
- 更清晰的结构
- 可配置更多参数
- 支持多组配置（将来）
- 更易于维护和扩展

## 🛠️ 技术实现

### 修改的文件

1. **requirements.txt** & **pyproject.toml** - 添加 PyYAML 依赖
2. **config.yaml.example** - 示例配置文件
3. **src/config.py** - 添加 YAML 配置加载功能
4. **src/util.py** - 支持从 YAML 读取频道列表
5. **src/telegram_bot.py** - 使用新的配置函数
6. **src/yt_dlp_downloader.py** - 使用配置的下载间隔
7. **doc/CONFIG_GUIDE.md** - 完整配置文档

### 向后兼容设计

- 使用缓存机制提高配置读取性能
- 配置函数返回默认值，确保程序正常运行
- 优先读取 YAML，自动回退到传统配置
- 保留所有原有的配置常量和函数接口

## ❓ 常见问题

### Q: 需要立即迁移到 YAML 配置吗？

**A:** 不需要！现有配置完全可以继续使用。YAML 配置是可选的。

### Q: 如何知道程序在使用哪种配置？

**A:** 程序启动时会显示：
- `✅ 使用 config.yaml 配置文件` - 使用 YAML
- `ℹ️  未找到 config.yaml，使用传统配置方式` - 使用传统配置

### Q: YAML 配置有什么好处？

**A:** 
- 所有配置集中管理
- 可配置更多参数（间隔、过滤天数等）
- 为未来的多组配置做准备
- 更清晰的结构和注释

### Q: 我可以同时保留两种配置吗？

**A:** 可以！程序会优先使用 YAML，但如果 YAML 中某些值是占位符，会回退到 .env 中的值。

## 🔮 未来计划

### 阶段 2：多频道组支持

将支持以下配置：

```yaml
channel_groups:
  # 技术类 → Telegram 技术频道
  - name: "技术频道"
    telegram_chat_id: "-1001111111111"
    audio_folder: "au/tech"
    youtube_channels:
      - "@JeffTechView"
      - "@Lifeano"
  
  # 时事类 → Telegram 时事频道
  - name: "时事评论"
    telegram_chat_id: "-1002222222222"
    audio_folder: "au/news"
    youtube_channels:
      - "@wenzhaoofficial"
      - "@cui_news"
```

每组可以：
- 发送到不同的 Telegram 频道
- 使用独立的音频目录
- 配置独立的下载策略

### 阶段 3：高级功能

- 每组独立的下载间隔
- 每组独立的过滤规则（天数、关键词等）
- 下载优先级
- 条件触发下载

---

**更新日期：** 2025-10-09  
**版本：** 阶段 1 - 基础 YAML 支持

