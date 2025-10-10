# 📦 发送记录功能更新日志

**更新日期**: 2025-10-10  
**版本**: v2.1

---

## ✨ 新增功能

### 1. **每个TG频道独立的发送记录**

之前：Bot发送文件后直接删除，无任何记录  
现在：每个Telegram频道维护独立的发送记录

**自动生成的文件**：
- `data/sent_archive_{CHAT_ID}.txt` - 机器格式（yt-dlp兼容）
- `data/sent_archive_{CHAT_ID}_readable.txt` - 人类可读格式（带视频标题）

**示例**：
```
# 机器格式 (sent_archive_1002441077579.txt)
youtube cBUvP4MPfcc
youtube sbK0XHQ5QRw

# 人类可读格式 (sent_archive_1002441077579_readable.txt)
cBUvP4MPfcc [【关灯拆电影】国际悬赏令：通缉拜登、加兰、麦康诺、川普以及佩洛西等。]
sbK0XHQ5QRw [【关灯拆电影】罗斯柴尔德与金融的战争。]
```

---

### 2. **便捷的查看工具**

新增 PowerShell 脚本，快速查看发送记录：

```powershell
# 查看所有频道的发送记录
.\scripts\view_sent_records.ps1 -All

# 查看特定频道
.\scripts\view_sent_records.ps1 -ChatId -1002441077579

# 只看最近10条
.\scripts\view_sent_records.ps1 -ChatId -1002441077579 -Tail 10

# 查看所有频道的最近5条
.\scripts\view_sent_records.ps1 -All -Tail 5
```

---

### 3. **完善的文档**

新增详细的 Archive 文件说明文档：
- 📄 `docs/ARCHIVE_FILES.md` - 完整的 archive 文件体系说明
- 工作流程图示
- 常见问题解答
- 维护建议

---

## 🔧 技术实现

### 核心函数

#### 1. `extract_video_info_from_filename(filename: str)`
从文件名中提取视频ID和标题

```python
# 支持的文件名格式：
# - video_id.title.m4a
# - video_id.title_0.m4a (分段文件)
# - video_id.title_1.m4a (分段文件)

video_id, title = extract_video_info_from_filename("cBUvP4MPfcc.【关灯拆电影】国际悬赏令.m4a")
# 返回: ("cBUvP4MPfcc", "【关灯拆电影】国际悬赏令")
```

#### 2. `record_sent_file(chat_id: str, video_id: str, title: str)`
记录已发送的文件到两个archive文件

```python
# 自动处理：
# 1. 检查是否已存在（避免重复记录）
# 2. 写入机器格式文件
# 3. 写入人类可读文件
# 4. 记录日志
```

#### 3. `get_sent_archive_path(chat_id: str, readable: bool = False)`
获取频道archive文件路径

```python
from config import get_sent_archive_path

# 机器格式
machine_path = get_sent_archive_path("-1002441077579", readable=False)
# 返回: "D:/usr/.../data/sent_archive_1002441077579.txt"

# 人类可读
readable_path = get_sent_archive_path("-1002441077579", readable=True)
# 返回: "D:/usr/.../data/sent_archive_1002441077579_readable.txt"
```

---

## 📊 文件命名规则

### Chat ID 清理规则
- 移除负号 `-`
- 移除加号 `+`
- 只保留数字

### 示例

| Telegram Chat ID | 机器格式文件 | 人类可读文件 |
|-----------------|-----------|-----------|
| `-1002441077579` | `sent_archive_1002441077579.txt` | `sent_archive_1002441077579_readable.txt` |
| `-1003009234603` | `sent_archive_1003009234603.txt` | `sent_archive_1003009234603_readable.txt` |

---

## 🔄 工作流程

```
Telegram Bot 发送文件
  ↓
发送成功
  ↓
extract_video_info_from_filename()  ← 从文件名提取 video_id 和 title
  ↓
record_sent_file()  ← 记录到两个archive文件
  ↓
删除音频文件
```

---

## 🧪 测试

运行测试脚本验证功能：

```powershell
.\.venv\Scripts\python tests\test_sent_archive.py
```

测试内容：
1. ✅ 文件名解析（支持普通文件和分段文件）
2. ✅ Archive 文件路径生成
3. ✅ Chat ID 清理规则

---

## 📁 相关文件

### 新增/修改的文件

```
src/
  config.py                          ← 新增 get_sent_archive_path()
  task/
    send_file.py                     ← 新增记录功能

docs/
  ARCHIVE_FILES.md                   ← 新增：完整文档
  CHANGELOG_SENT_ARCHIVE.md          ← 新增：更新日志

scripts/
  view_sent_records.ps1              ← 新增：查看工具

tests/
  test_sent_archive.py               ← 新增：测试脚本

config/
  config.yaml                        ← 更新：archive路径说明
  config.yaml.example                ← 更新：同步说明
```

---

## 🎯 设计优势

| 特性 | download_archive | sent_archive (机器) | sent_archive (可读) |
|-----|-----------------|-------------------|-------------------|
| **作用域** | 全局（所有频道组） | 单个 TG 频道 | 单个 TG 频道 |
| **格式** | yt-dlp 格式 | yt-dlp 格式 | 人类可读 |
| **用途** | 避免重复下载 | 追踪发送历史 | 用户查看 |
| **程序使用** | ✅ yt-dlp 自动读取 | ✅ 可用于防重复 | ❌ 仅供查看 |

---

## 💡 使用建议

1. **定期查看记录**：使用 `view_sent_records.ps1` 检查发送历史
2. **搜索特定视频**：在 `*_readable.txt` 中搜索标题关键词
3. **备份记录**：定期备份 `data/sent_archive_*.txt` 文件
4. **清理旧记录**：如需要，可以手动归档或删除旧的记录文件

---

## 🔮 未来可能的增强

1. **防重复发送**：基于 `sent_archive_*.txt` 检查，避免重复发送相同视频
2. **发送统计**：生成每个频道的发送统计报告
3. **Web界面**：可视化查看和管理发送记录
4. **自动清理**：配置保留最近N条记录，自动归档旧记录

---

**完成！** 🎉

