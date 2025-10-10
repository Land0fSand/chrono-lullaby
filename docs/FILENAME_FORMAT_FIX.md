# 🔧 文件名格式修复

**日期**: 2025-10-10  
**版本**: v2.1.1

---

## 🐛 问题描述

发现 `sent_archive.txt` 文件格式错误：

### 错误的格式
```
youtube テレ東BIZ
```

### 正确的格式（应该使用 video_id）
```
youtube cBUvP4MPfcc
youtube V0PizXBxqgk
```

---

## 🔍 根本原因

**文件名模板使用了 `uploader` 而不是 `video_id`**：

```python
# ❌ 错误：使用 uploader 作为前缀
"outtmpl": "%(uploader)s.%(fulltitle)s.tmp"

# 实际文件名：テレ東BIZ.急成長の...m4a
# extract_video_info_from_filename() 提取的第一部分是 uploader，不是 video_id
```

**问题链**：
1. 文件名前缀是 `uploader`（频道名）
2. `extract_video_info_from_filename()` 假设第一部分是 `video_id`
3. `record_sent_file()` 记录了错误的 ID（uploader 而不是 video_id）
4. 导致 `sent_archive.txt` 格式不兼容 yt-dlp

---

## ✅ 修复方案

### 1. 修改文件名模板

**修改位置**: `src/task/dl_audio.py`

#### 修改 1: 第244行（主下载模板）
```python
# 修改前
"outtmpl": os.path.join(AUDIO_FOLDER, "%(uploader)s.%(fulltitle)s.tmp")

# 修改后
"outtmpl": os.path.join(AUDIO_FOLDER, "%(id)s.%(title)s.tmp")
```

#### 修改 2: 第344行（历史下载模板）
```python
# 修改前
"outtmpl": os.path.join(target_folder, "%(uploader)s-%(title)s.%(ext)s")

# 修改后
"outtmpl": os.path.join(target_folder, "%(id)s.%(title)s.%(ext)s")
```

#### 修改 3: 第447行（文件名构建）
```python
# 修改前
safe_uploader = sanitize_filename(uploader)
final_audio_filename_stem = f"{safe_uploader}.{safe_title}"

# 修改后
final_audio_filename_stem = f"{video_id}.{safe_title}"
```

#### 修改 4: 第856行（历史下载文件名构建）
```python
# 修改前
safe_uploader = sanitize_filename(uploader)
final_audio_filename_stem = f"{safe_uploader}.{safe_title}"

# 修改后
video_id_history = closest_video.get('id', 'unknown_id')
final_audio_filename_stem = f"{video_id_history}.{safe_title}"
```

---

### 2. 新的文件名格式

**格式**: `{video_id}.{title}.m4a`

**示例**:
```
cBUvP4MPfcc.【关灯拆电影】国际悬赏令.m4a
V0PizXBxqgk.卢比奥：川普又当爹又当妈的.m4a
```

**优点**:
- ✅ video_id 是唯一的，避免冲突
- ✅ video_id 不需要清理，都是安全字符
- ✅ 与 yt-dlp 的 `download_archive.txt` 格式一致
- ✅ `extract_video_info_from_filename()` 直接工作，无需修改

---

### 3. Archive 文件格式统一

现在所有 archive 文件格式一致：

#### download_archive.txt（yt-dlp 自动维护）
```
youtube cBUvP4MPfcc
youtube V0PizXBxqgk
youtube sbK0XHQ5QRw
```

#### sent_archive_{CHAT_ID}.txt（Bot 记录）
```
youtube cBUvP4MPfcc
youtube V0PizXBxqgk
youtube sbK0XHQ5QRw
```

#### sent_archive_{CHAT_ID}_readable.txt（人类可读）
```
cBUvP4MPfcc [【关灯拆电影】国际悬赏令]
V0PizXBxqgk [卢比奥：川普又当爹又当妈的]
sbK0XHQ5QRw [【关灯拆电影】罗斯柴尔德与金融的战争]
```

---

## 🧪 验证

### 1. 检查文件名格式
```powershell
# 查看新下载的文件
Get-ChildItem -Path au, "au/xixu", "au/xixu2" -Filter "*.m4a" | Select-Object -First 5 Name

# 应该看到类似这样的文件名：
# cBUvP4MPfcc.【关灯拆电影】国际悬赏令.m4a
# V0PizXBxqgk.卢比奥：川普又当爹又当妈的.m4a
```

### 2. 检查 sent_archive 格式
```powershell
# 查看发送记录
Get-Content data/sent_archive_*txt | Select-Object -First 5

# 应该看到：
# youtube cBUvP4MPfcc
# youtube V0PizXBxqgk
```

### 3. 运行测试
```powershell
.\.venv\Scripts\python tests\test_sent_archive.py
```

---

## 🔄 迁移旧文件（可选）

如果你有使用旧格式（uploader前缀）的音频文件，需要重命名：

### 手动迁移脚本
```powershell
# 暂未提供自动迁移脚本
# 建议：让旧文件自然发送完毕，新文件使用新格式
```

### 或者清理旧记录
```powershell
# 删除错误格式的 sent_archive 文件
Remove-Item -Path data/sent_archive_*txt
```

---

## 📊 对比

| 项目 | 旧格式（错误） | 新格式（正确） |
|-----|-------------|-------------|
| **文件名前缀** | `uploader`（频道名） | `video_id` |
| **文件名示例** | `テレ東BIZ.急成長の...m4a` | `cBUvP4MPfcc.【关灯拆电影】国际悬赏令.m4a` |
| **sent_archive** | `youtube テレ東BIZ` ❌ | `youtube cBUvP4MPfcc` ✅ |
| **yt-dlp 兼容** | ❌ 不兼容 | ✅ 完全兼容 |
| **唯一性** | ❌ 可能冲突 | ✅ 唯一 |

---

## 🎯 总结

- ✅ 文件名格式修正为 `{video_id}.{title}.m4a`
- ✅ `sent_archive.txt` 格式与 yt-dlp 标准一致
- ✅ 所有 archive 文件现在使用统一的 `youtube {video_id}` 格式
- ✅ 删除了对 `uploader` 的依赖，使用更可靠的 `video_id`

**修复完成！** 🎉

