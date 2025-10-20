# Notion 远程配置设置指南

ChronoLullaby 支持使用 Notion 作为远程配置和数据存储，实现跨机器无缝切换工作状态。

## 功能特性

使用 Notion 模式后，以下数据将存储在 Notion 中：

- ✅ **频道配置**：YouTube 频道列表、Telegram 频道 ID 等
- ✅ **已发送记录**：跨机器同步，避免重复发送
- ✅ **下载记录**：跨机器同步，避免重复下载
- ✅ **Cookies**：统一管理 YouTube cookies
- ✅ **日志**：集中收集所有机器的日志

## 设置步骤

### 1. 创建 Notion Integration

1. 访问 [Notion Integrations](https://www.notion.so/my-integrations)
2. 点击 "+ New integration"
3. 填写信息：
   - Name: `ChronoLullaby`
   - Associated workspace: 选择你的工作区
   - Type: Internal
4. 点击 "Submit"
5. 复制生成的 **Internal Integration Token**（以 `secret_` 开头）

### 2. 创建 Notion 父页面

1. 在 Notion 中创建一个新页面，例如命名为 "ChronoLullaby Data"
2. 点击页面右上角的 "Share" 按钮
3. 点击 "Invite"，搜索并添加你刚创建的 Integration
4. 获取页面 ID：
   - 打开页面，查看 URL：`https://www.notion.so/xxxxx?v=yyy`
   - 其中 `xxxxx` 部分就是页面 ID

### 3. 配置 config.yaml

复制模板并根据需要填写：
```powershell
copy config\config.notion.example.yaml config\config.yaml
```
然后编辑 `config/config.yaml` 文件，至少填入以下信息：

#### 第1步：配置 Notion 凭据
```yaml
mode: notion

notion:
  # 🔑 填入你的 Notion Integration Token（https://www.notion.so/my-integrations）
  api_key: "secret_your_token_here"

  # 📄 填入你的 Notion 父页面 ID（URL 中的 UUID）
  page_id: "your_page_id_here"

  # 以下字段会在 `ch init-notion` 时自动填充，可暂时留空
  database_ids:
    config: ""
    sent_archive: ""
    download_archive: ""
    logs: ""

  page_ids:
    cookies: ""
    global_settings: ""

  sync:
    log_upload_interval: 300
    archive_sync_interval: 60
    machine_id: "machine-1"

log:
  level: INFO
```

#### 第2步：填入 Telegram Bot Token（必需）
```yaml
telegram:
  bot_token: "你的_BOT_TOKEN"  # 从 @BotFather 获取
```

**重要提示**：
- `api_key` 应该以 `secret_` 开头
- `page_id` 是 Notion 页面 URL 中的 ID 部分
- `machine_id` 用于区分不同机器的日志，建议设置为 `machine-1`、`machine-2` 等

### 4. 初始化 Notion 数据库结构

运行初始化命令：

```powershell
ch init-notion
```

这个命令会：
1. 连接到 Notion
2. 在父页面下创建所需的数据库和页面
3. 自动更新 `config.yaml` 中的 database_ids 和 page_ids

初始化成功后，你会看到类似的输出：

```
✅ Notion 初始化完成！
📝 创建的数据库:
  - config: xxxxx
  - sent_archive: xxxxx
  - download_archive: xxxxx
  - logs: xxxxx
📄 创建的页面:
  - cookies: xxxxx
  - global_settings: xxxxx
```

### 5. 配置频道和 Cookies（可选）

#### 方式一：在 Notion 中配置（推荐）

1. 打开 Notion，找到 "ChronoLullaby - 频道配置" 数据库
2. 添加频道组记录：
   - name: 频道组名称
   - description: 描述
   - enabled: 勾选启用
   - telegram_chat_id: Telegram 频道 ID
   - audio_folder: 音频文件夹路径（如 `au/xixu0`）
   - youtube_channels: YouTube 频道列表（每行一个，如 `@channelname`）

3. 打开 "ChronoLullaby - Cookies" 页面
4. 在 Code Block 中粘贴你的 YouTube cookies 文件内容

#### 方式二：从本地迁移

如果你已经有本地配置，可以使用同步命令：

```powershell
ch sync-to-notion --data config   # 仅同步频道/全局配置
ch sync-to-notion --data all      # 同步所有数据（含日志与存档）
```

根据需要选择同步范围。

### 6. 切换到 Notion 模式

编辑 `config/config.yaml`，修改 mode：

```yaml
mode: notion
```

### 7. 启动服务

```powershell
ch start --mode notion
```

或者（如果 config.yaml 中已设置 mode 为 notion）：

```powershell
ch start
```

## 跨机器使用

### 在新机器上设置

1. 克隆项目代码
2. 安装依赖：
   ```powershell
   poetry install
   ```
3. 复制 `config/config.notion.example.yaml` 为 `config/config.yaml` 并填写 Notion 信息
4. 根据需要调整 `machine_id` 等同步参数
5. 直接启动：
   ```powershell
   ch start --mode notion
   ```

所有配置和记录都会自动从 Notion 加载！

## Notion 数据库说明

### Config Database（频道配置）

存储频道组配置，字段：
- **name**: 频道组名称
- **description**: 描述
- **enabled**: 是否启用
- **telegram_chat_id**: Telegram 频道 ID
- **audio_folder**: 音频文件夹路径
- **youtube_channels**: YouTube 频道列表（每行一个）
- **bot_token**: 独立 Bot Token（可选）

### SentArchive Database（已发送记录）

记录已发送到 Telegram 的文件，字段：
- **video_id**: YouTube 视频 ID
- **chat_id**: Telegram 频道 ID
- **title**: 视频标题
- **sent_date**: 发送日期
- **file_path**: 文件路径

### DownloadArchive Database（下载记录）

记录已下载的视频，字段：
- **video_id**: YouTube 视频 ID
- **download_date**: 下载日期
- **channel**: YouTube 频道
- **status**: 状态（completed/failed）

### Logs Database（日志）

集中存储所有机器的日志，字段：
- **message**: 日志消息
- **timestamp**: 时间戳
- **log_type**: 类型（downloader/bot/error）
- **level**: 级别（INFO/WARNING/ERROR）
- **machine_id**: 机器标识

### Cookies Page（Cookies）

存储 YouTube cookies 文件内容，用于访问会员内容等。

### GlobalSettings Page（全局设置）

存储全局配置（当前版本仍从 config.yaml 读取，未来版本将支持从此页面读取）。

## 常见问题

### 1. 初始化失败："API Key 未配置"

确保你已经：
1. 在 Notion 中创建了 Integration
2. 复制了正确的 Integration Token（以 `secret_` 开头）
3. 在 `config.yaml` 中正确填入了 `api_key`

### 2. 初始化失败："连接 Notion 失败"

确保你已经：
1. 将 Integration 添加到了父页面（Share -> Invite）
2. 填入了正确的页面 ID

### 3. 启动后无法读取配置

检查：
1. `database_ids` 是否已正确填充（运行 `ch init-notion` 后自动填充）
2. 是否在 Notion Config Database 中添加了频道配置
3. 频道配置中的 `enabled` 是否勾选

### 4. 跨机器同步不生效

确保：
1. 两台机器使用相同的 Notion 配置
2. 两台机器的 `machine_id` 不同（用于区分日志来源）
3. 网络连接正常，能够访问 Notion API

### 5. 日志没有上传到 Notion

检查：
1. `log_upload_interval` 配置（默认 5 分钟批量上传一次）
2. Logs Database 是否创建成功
3. 查看控制台是否有上传错误信息

## 性能优化建议

1. **日志上传间隔**：
   - 默认 300 秒（5 分钟）批量上传
   - 可根据需要调整，但不建议设为 0（每条都上传会影响性能）

2. **记录同步间隔**：
   - 默认 60 秒（1 分钟）
   - 跨机器工作时，建议保持此频率

3. **本地缓存**：
   - 系统会自动缓存配置，减少 API 调用
   - 如需立即刷新配置，可重启服务

## 安全建议

1. **API Key 保护**：
   - 不要将 `config.yaml`（包含 API Key）提交到 git
   - 添加到 `.gitignore`：`config/config.yaml`

2. **权限控制**：
   - 只授予 Integration 必要的权限
   - 定期检查 Integration 的访问记录

3. **数据备份**：
   - 虽然数据在 Notion 中，但建议定期导出备份
   - 可使用 Notion 的导出功能

## 混合模式

你也可以只使用部分 Notion 功能：

- **只用 Notion 存储配置**：在 Notion 中配置频道，但记录仍保存在本地
- **只用 Notion 同步记录**：配置仍在 config.yaml，但记录存储在 Notion

目前系统采用"全或无"策略（mode 为 local 或 notion），未来版本可能支持更细粒度的配置。

## 故障恢复

如果 Notion 不可用：

1. 系统会自动降级到本地模式（使用本地缓存的配置）
2. 记录会继续写入本地文件
3. Notion 恢复后，可使用 `ch sync-to-notion --data all` 手动同步全部数据

## 更多信息

- [Notion API 文档](https://developers.notion.com/)
- [ChronoLullaby 配置指南](CONFIG_GUIDE.md)
- [ChronoLullaby 主文档](../readme.md)

