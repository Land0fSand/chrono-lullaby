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
   uv pip install -U --pre yt-dlp
   ```

2. **安装 yt-dlp-ejs**（提供 JavaScript 运行时支持）
   ```powershell
   uv pip install -U yt-dlp-ejs
   ```

3. **确保有 Node.js**
   - 程序会自动检测 Node.js 并用于解决 n challenge
   - 需要 Node.js 20.0.0+

4. **重启服务**
   ```powershell
   .\ch restart -m notion
   ```

### 关于 Cookies 的补充说明

- `cookie` 不是公开频道列表抓取、公开节目下载的必需条件。
- 公开内容在未登录状态下通常仍可获取；即使日志提示 `The provided YouTube account cookies are no longer valid`，公开节目仍可能继续下载成功。
- `cookie` 更适用于会员内容、年龄限制内容、部分风控场景，或作为重试时的附加登录态。
- 2026-03-10 之后的聚合日志表明：程序可以在 `cookie invalid` 告警存在时，仍成功获取公开频道 `/videos` 列表并下载公开视频。

### 重构备注

- 后续可考虑将下载策略调整为：
  1. 先尝试不带 `cookie` 获取公开内容。
  2. 若遇到受限内容、权限校验或明确需要登录态的错误，再使用 `cookie` 重试。
- 这样可以避免把 `cookie` 当作公开视频下载的前置依赖，也能减少“cookie 失效”告警对公开内容链路的干扰。
- TODO: 当前部分模块在 import 阶段会触发配置读取、Notion 访问或同步服务初始化。后续可把这类副作用尽量收敛到显式入口 `main()`，降低导入检查、测试和调试时的副作用。

---

## 从 Notion 模式切换到本地模式

### 导出 Notion 配置到本地

```powershell
uv run python scripts/export_notion_config.py
```

这会输出完整的 YAML 配置。

### 保存到文件

```powershell
uv run python scripts/export_notion_config.py > config/config_new.yaml
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
.\ch ytdlp-watch -m notion         # 持续监控 yt-dlp 新版本并自动升级+重启
.\ch ytdlp-watch --once --dry-run  # 单次检测，不执行变更
```
