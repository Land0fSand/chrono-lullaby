# 故障排除指南

## YouTube 下载失败 (n challenge / 403 错误)

### 症状
- 日志显示 `n challenge solving failed`
- 日志显示 `HTTP Error 403: Forbidden`
- 日志显示 `Requested format is not available`
- 音频文件夹为空

### 原因
YouTube 更新了反机器人算法，旧版 yt-dlp 无法解密。

### 解决方案

1. **升级 yt-dlp**
   ```powershell
   poetry update yt-dlp
   ```

2. **安装 yt-dlp-ejs**（提供 JavaScript 运行时支持）
   ```powershell
   poetry add yt-dlp-ejs
   ```

3. **确保有 Node.js**
   - 程序会自动检测 Node.js 并用于解决 n challenge
   - 需要 Node.js 20.0.0+

4. **重启服务**
   ```powershell
   .\ch restart
   ```

---

## 从 Notion 模式切换到本地模式

### 导出 Notion 配置到本地

```powershell
poetry run python scripts/export_notion_config.py
```

这会输出完整的 YAML 配置。

### 保存到文件

```powershell
poetry run python scripts/export_notion_config.py > config/config_new.yaml
```

### 修改 config.yaml

1. 将 `mode: notion` 改为 `mode: local`
2. 检查 `enabled: true/false` 控制是否发送到 TG
3. Story 类型频道的进度字段会自动从 config.yaml 读取

---

## 本地模式 Story 进度

Story 类型频道的进度字段：

| 字段 | 说明 |
|------|------|
| `story_last_video_id` | 上次下载的视频 ID |
| `story_last_timestamp` | 上次视频的时间戳（可留空） |
| `story_last_run_ts` | 上次运行时间 |

**留空 `story_last_timestamp` 时**：程序会用 `story_last_video_id` 定位，从该视频之后继续下载。

进度保存位置：`data/story_progress.json`

---

## 常用命令

```powershell
.\ch start              # 启动服务
.\ch stop               # 停止服务
.\ch restart            # 重启服务
.\ch status             # 查看状态
.\ch logs               # 查看日志
.\ch logs -f            # 实时跟踪日志
```
