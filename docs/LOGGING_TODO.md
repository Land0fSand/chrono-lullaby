# Logging TODO

短期修复已完成：

- 本地日志默认按组件文件写入，避免 Windows 多进程同时争抢 `logs/all.log`。
- 本地日志轮转配置显式化：单文件 20MB，保留 10 个备份。
- 本地轮转遇到文件占用时不再刷屏影响服务。
- Notion 日志自动清理在当前配置中启用：普通日志保留 30 天，ERROR 保留 90 天。

后续可做：

- 增加 `ch doctor logs`，检查本地日志大小、轮转失败、Notion 上传失败、Notion 清理是否启用。
- 如果仍需要统一视图，实现 `ch logs --all` 按时间合并 `launcher.log`、`downloader.log`、`bot.log`、`system.log`。
- 如果仍需要 `all.log`，改为单写入者模型：各进程通过队列、pipe 或 socket 发给 launcher，由 launcher 独占写入和轮转。
- 给 Notion 上传做降噪策略，只上传关键 INFO、WARNING、ERROR，过滤高频调度心跳类日志。
- 给 Notion 清理增加状态日志和失败告警，避免清理线程静默失效。
- 给日志配置加文档：本地日志用于排障，Notion 日志用于远程观察和长期索引。
