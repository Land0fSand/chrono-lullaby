# YouTube Premiere 视频处理优化

## 📅 更新时间
2025-10-10

## 🎯 问题说明

### **原问题**
日志中出现 ERROR 级别错误：
```
ERROR: [youtube] gbmH-VEYtOw: Premieres in 48 minutes
```

### **问题分析**

| 项目 | 说明 |
|------|------|
| **是否正常** | ✅ 完全正常 - YouTube Premiere 功能特性 |
| **原因** | 视频设置了首映时间，在首映前无法下载 |
| **影响** | 程序将其当作严重错误，导致频道处理失败 |
| **需要修复** | ✅ 是的，应作为正常情况处理 |

---

## 🔧 修复内容

### **修改文件**
`src/task/dl_audio.py`

### **三处改进**

#### **1. 外层异常处理（第 742-751 行）**
**修改前：**
```python
except Exception as e:
    log_with_context(logger, logging.ERROR, "处理频道时发生错误", ...)
    # 所有异常都记录为 ERROR
```

**修改后：**
```python
except Exception as e:
    # 检查是否为 YouTube Premiere（首映）视频
    if "premieres in" in error_str.lower() or "premiere" in error_str.lower():
        log_with_context(logger, logging.INFO, "频道包含待首映视频，跳过处理", ...)
        return True  # 不算错误，返回成功
    
    # 记录实际错误
    log_with_context(logger, logging.ERROR, "处理频道时发生错误", ...)
```

#### **2. 单个视频下载错误处理（第 648-667 行）**
**新增 premiere 判断：**
```python
elif "premieres in" in error_str.lower() or "premiere" in error_str.lower():
    # YouTube Premiere（首映）视频，尚未到首映时间
    premiere_info = error_str.split(":")[-1].strip() if ":" in error_str else "待首映"
    log_with_context(
        logger, logging.INFO,
        "⏰ 视频待首映，暂时跳过",
        premiere_info=premiere_info
    )
    stats['filtered'] += 1
    stats['details'].append({
        'status': 'premiere',
        'reason': f'待首映: {premiere_info}'
    })
```

#### **3. 日志显示图标（第 748 行）**
**新增状态图标：**
```python
status_icon = {
    'premiere': '⏰',  # 新增
    'member_only': '🔒',
    'archived': '📚',
    ...
}
```

---

## 📊 效果对比

### **修改前**
```
ERROR: 处理频道时发生错误 @dlw2023
  error: ERROR: [youtube] gbmH-VEYtOw: Premieres in 48 minutes
  
结果：频道处理失败 ❌
```

### **修改后**
```
INFO: ⏰ 视频待首映，暂时跳过
  title: 某视频标题
  premiere_info: Premieres in 48 minutes
  
结果：继续处理其他视频 ✅
```

---

## 🎬 处理逻辑

### **识别条件**
检查错误信息中是否包含：
- `"premieres in"` (不区分大小写)
- `"premiere"` (不区分大小写)

### **处理方式**

| 层级 | 行为 | 说明 |
|------|------|------|
| **外层（频道级别）** | 记录 INFO，返回 True | 不影响其他频道处理 |
| **内层（视频级别）** | 记录 INFO，继续下一个 | 不影响同频道其他视频 |
| **统计** | 计入 `filtered` | 与时间过滤视频同类 |
| **日志** | 显示 ⏰ 图标 | 清晰标识待首映状态 |

### **后续处理**
- ✅ 视频首映后，下次运行会自动下载
- ✅ 不会记录到 download_archive.txt
- ✅ 不影响其他视频的处理

---

## 📝 日志示例

### **正常情况下的日志**
```json
{
  "level": "INFO",
  "message": "⏰ 视频待首映，暂时跳过",
  "channel": "@dlw2023",
  "video_index": "1/5",
  "title": "新视频标题",
  "video_id": "gbmH-VEYtOw",
  "premiere_info": "Premieres in 48 minutes"
}
```

### **汇总统计**
```
频道处理完成 - 汇总统计
  total_videos: 5
  success: 3
  filtered: 1  ← 待首映视频计入此项
  error: 0
```

### **详细列表**
```
⏰ [ 1] premiere        | 新视频标题                           | 待首映: Premieres in 48 minutes
✅ [ 2] success         | 另一个视频                           | 下载成功
```

---

## 🔍 其他类似情况

程序已能识别的特殊情况：

| 情况 | 日志级别 | 图标 | 统计分类 |
|------|----------|------|----------|
| 已在存档 | INFO | 📚 | `archived` |
| 会员专属 | INFO | 🔒 | `member_only` |
| 待首映 | INFO | ⏰ | `filtered` |
| 时间过滤 | INFO | 🚫 | `filtered` |
| 已存在文件 | INFO | 📦 | `already_exists` |
| 下载失败 | ERROR | ❌ | `error` |

---

## ✅ 验证清单

- ✅ 代码无 linter 错误
- ✅ 外层异常处理优化
- ✅ 内层视频下载处理优化
- ✅ 日志显示图标添加
- ✅ 不影响其他错误处理逻辑
- ✅ 向后兼容现有功能

---

## 🚀 生效说明

1. ✅ **立即生效** - 重启程序后生效
2. ✅ **无需配置** - 自动识别首映视频
3. ✅ **不影响现有** - 不影响已下载视频
4. ✅ **自动重试** - 首映后下次运行会下载

---

## 💡 使用建议

1. **遇到待首映视频时**
   - 程序会自动跳过并记录
   - 无需手动干预
   - 等待首映后自动下载

2. **日志查看**
   - INFO 级别可忽略
   - 查找 ⏰ 图标了解待首映视频

3. **监控**
   - 如果某个视频一直显示 premiere，可能是频道设置问题
   - 可手动检查视频链接

---

## 📚 相关文件

- ✅ `src/task/dl_audio.py` - 主要修改
- ✅ `PREMIERE_VIDEO_HANDLING.md` - 本文档
- 📝 `logs/downloader.dl_audio.log` - 日志文件

---

**修复完成！现在程序能正确识别并优雅处理 YouTube Premiere 视频了！** 🎊

