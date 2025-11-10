# YouTube 频道 Multi-select 功能说明

## 功能概述

从原来的文本格式（rich_text）迁移到多选格式（multi_select），让 YouTube 频道管理更加灵活。

### 改进前后对比

**改进前（rich_text 格式）：**
- YouTube 频道列表以文本形式存储，每行一个频道
- 需要手动编辑文本内容来添加/删除频道
- 暂时不用的频道需要手动删除或注释掉
- 不够直观，容易出错

**改进后（multi_select 格式）：**
- 每个 YouTube 频道作为独立的选项
- 通过勾选/取消勾选来启用/禁用频道
- 暂时不用的频道保留在选项列表中，随时可以重新启用
- 更加直观和灵活

## 使用方法

### 1. 迁移现有数据（仅需一次）

如果你已经在使用旧的 rich_text 格式，需要运行迁移脚本：

```powershell
ch migrate-multiselect
```

迁移脚本会：
1. 备份现有数据
2. 创建新的 multi_select 字段
3. 将数据从旧格式迁移到新格式
4. 删除旧字段并重命名新字段

**注意：**
- 此操作会修改 Notion 数据库结构
- 建议在执行前在 Notion 中备份数据
- 迁移过程需要你确认操作

### 2. 新建 Notion 数据库

如果是首次初始化 Notion 数据库，直接运行：

```powershell
ch init-notion
```

新创建的数据库会自动使用 multi_select 格式。

### 3. 在 Notion 中管理频道

迁移完成后，在 Notion 的 Config Database 中：

1. **添加新频道：**
   - 点击 `youtube_channels` 字段
   - 输入新的频道名称（如 `@ChannelName`）
   - 按回车创建新选项
   - 勾选该选项以启用

2. **启用/禁用频道：**
   - 勾选 = 启用该频道，下载器会下载此频道的视频
   - 取消勾选 = 禁用该频道，下载器会跳过此频道

3. **删除频道选项：**
   - 如果确定不再需要某个频道，可以在 Notion 的数据库设置中删除该选项
   - 也可以保留选项但取消勾选，方便将来重新启用

### 4. 同步本地配置到 Notion

如果你有本地的 `config.yaml` 配置，想要同步到 Notion：

```powershell
ch sync-to-notion --data config
```

系统会自动将本地配置中的频道列表转换为 multi_select 格式。

## 工作原理

### 数据库 Schema 定义

```python
# notion_adapter.py - NotionDatabaseSchemas.config_database()
"youtube_channels": {
    "multi_select": {}
}
```

### 读取逻辑

系统会自动兼容两种格式：

```python
# config_provider.py - NotionConfigProvider.get_channel_groups()
youtube_channels_data = self.adapter.extract_property_value(page, 'youtube_channels')

if isinstance(youtube_channels_data, list):
    # 新格式：multi_select，直接使用列表
    youtube_channels = [ch.strip() for ch in youtube_channels_data if ch and ch.strip()]
elif isinstance(youtube_channels_data, str):
    # 旧格式：rich_text，按行分割（向后兼容）
    youtube_channels = [ch.strip() for ch in youtube_channels_data.split('\n') if ch.strip()]
```

### 写入逻辑

```python
# sync_to_notion.py - sync_config()
properties = {
    "youtube_channels": adapter.build_multi_select_property(youtube_channels_clean)
}
```

## 向后兼容

系统完全兼容旧的 rich_text 格式：

- 如果你暂时不想迁移，系统仍然可以正常读取旧格式的数据
- 迁移后，如果某些记录仍然是旧格式，系统也能正常处理
- 建议尽快迁移以获得更好的用户体验

## 常见问题

### Q1: 迁移会影响正在运行的服务吗？

A: 不会。迁移过程只修改 Notion 数据库结构，不影响正在运行的下载器或 Bot。但建议迁移后重启服务以确保使用最新配置。

### Q2: 迁移失败怎么办？

A: 迁移脚本会在每个步骤提供详细的错误信息。如果迁移失败：
1. 检查 Notion API Key 和 Database ID 是否正确
2. 确认有足够的 Notion API 权限
3. 查看错误日志，根据提示解决问题
4. 可以重复运行迁移脚本

### Q3: 可以同时使用两种格式吗？

A: 可以。系统会自动识别并处理两种格式。但建议统一使用 multi_select 格式以获得最佳体验。

### Q4: multi_select 格式有数量限制吗？

A: Notion 的 multi_select 字段没有严格的数量限制，但建议每个频道组不超过 100 个频道以保证性能。

### Q5: 如何批量添加频道？

A: 在 Notion 中：
1. 点击 `youtube_channels` 字段
2. 依次输入每个频道名称并按回车
3. 勾选需要启用的频道

或者在本地 `config.yaml` 中配置好后，使用 `ch sync-to-notion --data config` 同步到 Notion。

## 技术细节

### 迁移脚本执行流程

1. **备份现有数据**
   - 读取所有记录的 `youtube_channels` 字段
   - 解析并保存到内存中

2. **更新数据库 Schema**
   - 创建临时字段 `youtube_channels_temp` (multi_select)
   - 等待用户确认

3. **迁移数据**
   - 将每条记录的频道列表迁移到临时字段
   - 显示迁移进度和结果

4. **切换字段**
   - 删除原 `youtube_channels` 字段
   - 将 `youtube_channels_temp` 重命名为 `youtube_channels`

### API 调用说明

迁移过程会调用以下 Notion API：
- `databases.retrieve` - 获取数据库信息
- `databases.update` - 更新数据库结构
- `databases.query` - 查询所有记录
- `pages.update` - 更新单条记录

请确保你的 Notion Integration 有足够的权限。

## 相关文件

- `src/notion_adapter.py` - Notion API 适配器，包含 multi_select 相关方法
- `src/config_provider.py` - 配置提供者，处理频道数据的读取
- `src/commands/sync_to_notion.py` - 同步工具，处理频道数据的写入
- `src/commands/migrate_youtube_channels_to_multiselect.py` - 迁移脚本
- `scripts/ch.ps1` - 命令行工具，包含 `migrate-multiselect` 命令

## 更新日志

### v1.1.0 (2025-11-03)
- 新增 multi_select 格式支持
- 添加迁移工具 `ch migrate-multiselect`
- 完全向后兼容旧的 rich_text 格式
- 优化频道管理体验



